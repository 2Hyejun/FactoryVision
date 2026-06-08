import os
import cv2
import json
import time
import paho.mqtt.client as mqtt
import numpy as np
from ultralytics import YOLO

# ==========================================
# 0. MQTT 브로커 및 이미지 서버 세팅
# ==========================================
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "capstone/line1/state/lhj" 

client = mqtt.Client()
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()
print("🌐 MQTT 실시간 통신망 가동 완료!")

# ==========================================
# 1. 완벽한 경로 자동 설정 및 환경 로드
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
save_dir = os.path.join(BASE_DIR, 'live_images')
os.makedirs(save_dir, exist_ok=True)

model_path = os.path.join(BASE_DIR, 'best_0504.pt')
best_model = YOLO(model_path)

cap1 = cv2.VideoCapture(3) # Side 1
cap2 = cv2.VideoCapture(0) # Top View
cap3 = cv2.VideoCapture(2) # Side 2

for cap in [cap1, cap2, cap3]:
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

print("\n 2초 주기 검사 ")
print("-통신망 연결 완료")
print("- [ESC]를 누르면  종료됩니다.\n")

last_inspection_time = 0
inspection_interval = 2.0 
set_index = 0

while True:
    ret1, frame1 = cap1.read()
    ret2, frame2 = cap2.read()
    ret3, frame3 = cap3.read()

    if not (ret1 and ret2 and ret3):
        continue

    # 카메라 회전 복구
    frame1 = cv2.rotate(frame1, cv2.ROTATE_180)
    frame3 = cv2.rotate(frame3, cv2.ROTATE_180)

    # 모니터링 화면
    disp1 = cv2.resize(frame1, (320, 180)) # 비율에 맞춰 모니터링 창 조절
    disp2 = cv2.resize(frame2, (320, 180))
    disp3 = cv2.resize(frame3, (320, 180))
    combined_frame = np.hstack((disp1, disp2, disp3))
    cv2.putText(combined_frame, "AUTO INSPECTING...", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    cv2.imshow("Edge AI Node", combined_frame)

    current_time = time.time()
    
    # 2초마다 추론 및 전송
    if current_time - last_inspection_time >= inspection_interval:
        last_inspection_time = current_time
        set_index += 1
        
        payload = {
            "device_id": "Edge_01",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "index": str(set_index),
            "screw_present": False, 
            "cam1_gap_mm": 0.0,
            "cam3_gap_mm": 0.0,
            "final_status": "PASS"
        }

        saved_imgs = {'cam1': frame1, 'cam2': frame2, 'cam3': frame3}

        # ------------------------------------------------
        # [STEP A] Cam2 (Top View) - 나사 유무 검사
        # ------------------------------------------------
        res2 = best_model.predict(source=frame2, conf=0.6, imgsz=1024, show=False, save=False)[0]
        saved_imgs['cam2'] = res2.plot() 
        
        if getattr(res2, 'obb', None) is not None:
            for i, cls_idx in enumerate(res2.obb.cls):
                class_name = best_model.names[int(cls_idx.item())].lower()
                
                if class_name == 'screw_target':
                    cy = res2.obb.xywhr[i][1].item()
                    conf_score = res2.obb.conf[i].item()
                    
                    if cy > 80:
                        payload["screw_present"] = True 
                        break

        # ------------------------------------------------
        # [STEP B] Cam1, Cam3 - 미세 단차 측정
        # ------------------------------------------------
        camera_frames = {'cam1': frame1, 'cam3': frame3}
        for cam_name, frame in camera_frames.items():
            res = best_model.predict(source=frame, conf=0.25, imgsz=1024, show=False, save=False)[0]
            
            hinge_center_x, hinge_center_y = None, None
            if getattr(res, 'obb', None) is not None:
                for i in range(len(res.obb)):
                    if best_model.names[int(res.obb.cls[i].item())] == 'Ref_Hinge_Stack':
                        hinge_center_x, hinge_center_y = int(res.obb.xywhr[i][0].item()), int(res.obb.xywhr[i][1].item())
                        break
            
            if hinge_center_x is not None:
                crop_size = 800 
                img_h, img_w = frame.shape[:2]
                x1, y1 = max(0, hinge_center_x - crop_size//2), max(0, hinge_center_y - crop_size//2)
                x2, y2 = min(img_w, hinge_center_x + crop_size//2), min(img_h, hinge_center_y + crop_size//2)
                roi_img = frame[y1:y2, x1:x2]
                
                lab = cv2.cvtColor(roi_img, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                cl = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)).apply(l)
                roi_img_clahe = cv2.cvtColor(cv2.merge((cl,a,b)), cv2.COLOR_LAB2BGR)
                
                roi_res = best_model.predict(source=roi_img_clahe, conf=0.1, imgsz=1024, show=False, save=False)[0]
                saved_imgs[cam_name] = roi_res.plot() 
                
                hinge_cy, gap_candidates = None, []
                if getattr(roi_res, 'obb', None) is not None:
                    for i in range(len(roi_res.obb)):
                        cls_name = best_model.names[int(roi_res.obb.cls[i].item())]
                        if cls_name == 'Ref_Hinge_Stack': hinge_cy = roi_res.obb.xywhr[i][1].item()
                        elif cls_name == 'Gap': gap_candidates.append({'h': roi_res.obb.xywhr[i][3].item(), 'cy': roi_res.obb.xywhr[i][1].item()})
                
                gap_pixel_h = None
                if gap_candidates and hinge_cy is not None:
                    gap_pixel_h = min(gap_candidates, key=lambda g: abs(g['cy'] - hinge_cy))['h']
                
                if gap_pixel_h is not None:
                    FIXED_SF = 0.146171 if cam_name == 'cam1' else 0.113928
                    calib_a = 1.1493 if cam_name == 'cam1' else 2.0907
                    calib_b = -0.0519 if cam_name == 'cam1' else -0.5100
                    final_gap_mm = ((gap_pixel_h * FIXED_SF) * calib_a) + calib_b
                    payload[f"{cam_name}_gap_mm"] = round(final_gap_mm, 2)
            else:
                saved_imgs[cam_name] = res.plot()

        # ------------------------------------------------
        # [STEP C] 교차 검증 판정
        # ------------------------------------------------
        if payload["cam1_gap_mm"] > 0.1 or payload["cam3_gap_mm"] > 0.1:
            payload["screw_present"] = True 
            payload["final_status"] = "NG (단차 불량)"
        elif not payload["screw_present"]:
            payload["final_status"] = "ERROR (나사 누락)"
        else:
            payload["final_status"] = "PASS"

        # ------------------------------------------------
        # [STEP D] 파일 저장
        # ------------------------------------------------
        for c_name, c_img in saved_imgs.items():
            temp_path = os.path.join(save_dir, f"temp_{c_name}.jpg")
            final_path = os.path.join(save_dir, f"live_{c_name}.jpg")
            cv2.imwrite(temp_path, c_img)
            os.replace(temp_path, final_path)

        # MQTT 발행
        client.publish(MQTT_TOPIC, json.dumps(payload))
        print(f"📤 [{set_index}번] {payload['timestamp']} -> {payload['final_status']} | 수치: {max(payload['cam1_gap_mm'], payload['cam3_gap_mm'])}mm")

    if cv2.waitKey(1) & 0xFF == 27:
        break

reset_payload = {
    "timestamp": "-", "index": "0", "screw_present": True,
    "cam1_gap_mm": 0.0, "cam3_gap_mm": 0.0, "final_status": "SYSTEM_OFF"
}
client.publish(MQTT_TOPIC, json.dumps(reset_payload))
time.sleep(0.5) 

cap1.release()
cap2.release()
cap3.release()
cv2.destroyAllWindows()
client.loop_stop()
print("👋 종료되었습니다.")