import os
import cv2
import glob
import re
import numpy as np
import csv 
from collections import defaultdict
from ultralytics import YOLO

# ==========================================
# 1. 환경 설정 및 모델 로드
# ==========================================
model_path = 'C:/Users/lhj/cap_1/best_0504.pt' 
test_images_path = '"C:/Users/lhj/cap_1/dataset/GT_0mm"' 

base_output_dir = 'C:/Users/lhj/cap_1/GT'
output_dir = base_output_dir

counter = 1
while os.path.exists(output_dir):
    output_dir = f"{base_output_dir}({counter})"
    counter += 1

dir_pass = os.path.join(output_dir, 'PASS')
dir_ng = os.path.join(output_dir, 'NG')
dir_error = os.path.join(output_dir, 'ERROR')

os.makedirs(dir_pass, exist_ok=True)
os.makedirs(dir_ng, exist_ok=True)
os.makedirs(dir_error, exist_ok=True)

# 💡 CSV 파일 생성 및 헤더 작성
csv_file_path = os.path.join(output_dir, 'calibration_data.csv')
with open(csv_file_path, mode='w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['GT_Folder', 'Actual_GT_MM', 'Index', 'Camera', 'Gap_Pixel_H', 'AI_Raw_MM']) 

print(f"📁 결과 폴더: [{output_dir}]")
print(f"📊 엑셀 파일(CSV)이 팀장님 실측 GT와 함께 자동 저장됩니다!")

best_model = YOLO(model_path)

# ==========================================
# 2. 데이터셋 파싱 및 그룹화
# ==========================================
print("🔍 파일 분류 중...")
image_files = glob.glob(os.path.join(test_images_path, "**", "*.jpg"), recursive=True)
image_sets = defaultdict(dict)

for filepath in image_files:
    filename = os.path.basename(filepath)
    match = re.search(r'(\d+)_cam([123])', filename)
    if match:
        file_index = match.group(1)
        cam_num = f"cam{match.group(2)}"
        image_sets[file_index][cam_num] = filepath

selected_indexes = list(image_sets.keys())
selected_indexes.sort(key=int)

print(f"✅ 총 {len(selected_indexes)}개의 세트 검사 시작...")

# ==========================================
# 3. 메인 추론 파이프라인 
# ==========================================
for idx in selected_indexes:
    cam_dict = image_sets[idx]
    
    is_defective = False
    base_results = {}

    for cam_name in ['cam1', 'cam2', 'cam3']:
        if cam_name in cam_dict:
            img_path = cam_dict[cam_name]
            img = cv2.imread(img_path)
            
            if cam_name == 'cam2':
                base_results[cam_name] = {'img': img, 'res': None, 'path': img_path}
                continue

            res = best_model.predict(source=img, conf=0.25, imgsz=1024, show=False, save=False)[0]
            base_results[cam_name] = {'img': img, 'res': res, 'path': img_path}

            if getattr(res, 'obb', None) is not None:
                for cls_idx in res.obb.cls:
                    if best_model.names[int(cls_idx.item())] == 'Gap':
                        is_defective = True
                        break

    # ------------------------------------------------
    # [STEP 2] 최종 판별 및 현미경(ROI) 수치화
    # ------------------------------------------------
    for cam_name, data in base_results.items():
        img = data['img']
        res = data['res']
        img_path_for_csv = data['path']
        formatted_idx = f"{int(idx):03d}"

        if cam_name == 'cam2':
            continue

        if not is_defective:
            continue

        else:
            hinge_center_x, hinge_center_y = None, None

            if getattr(res, 'obb', None) is not None:
                for i in range(len(res.obb)):
                    if best_model.names[int(res.obb.cls[i].item())] == 'Ref_Hinge_Stack':
                        hinge_center_x = int(res.obb.xywhr[i][0].item())
                        hinge_center_y = int(res.obb.xywhr[i][1].item())
                        break

            if hinge_center_x is not None:
                crop_size = 800 
                img_h, img_w = img.shape[:2]
                x1 = max(0, hinge_center_x - crop_size // 2)
                y1 = max(0, hinge_center_y - crop_size // 2)
                x2 = min(img_w, hinge_center_x + crop_size // 2)
                y2 = min(img_h, hinge_center_y + crop_size // 2)
                
                roi_img = img[y1:y2, x1:x2]

                lab = cv2.cvtColor(roi_img, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                cl = clahe.apply(l)
                limg = cv2.merge((cl,a,b))
                roi_img_clahe = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

                roi_res = best_model.predict(source=roi_img_clahe, conf=0.1, imgsz=1024, show=False, save=False)[0]
                annotated_roi = roi_res.plot()

                ref_pixel_h = None
                hinge_cy = None
                gap_candidates = [] 

                if getattr(roi_res, 'obb', None) is not None and len(roi_res.obb) > 0:
                    for i in range(len(roi_res.obb)):
                        cls_name = best_model.names[int(roi_res.obb.cls[i].item())]
                        if cls_name == 'Ref_Hinge_Stack': 
                            ref_pixel_h = roi_res.obb.xywhr[i][3].item()
                            hinge_cy = roi_res.obb.xywhr[i][1].item()
                        elif cls_name == 'Gap': 
                            gap_candidates.append({
                                'h': roi_res.obb.xywhr[i][3].item(),
                                'cy': roi_res.obb.xywhr[i][1].item()
                            })

                gap_pixel_h = None
                
                if gap_candidates and hinge_cy is not None:
                    real_gap = min(gap_candidates, key=lambda g: abs(g['cy'] - hinge_cy))
                    gap_pixel_h = real_gap['h']

                if ref_pixel_h is not None and gap_pixel_h is None:
                    gamma = 0.6 
                    lookUpTable = np.empty((1,256), np.uint8)
                    for i in range(256):
                        lookUpTable[0,i] = np.clip(pow(i / 255.0, gamma) * 255.0, 0, 255)
                    roi_img_gamma = cv2.LUT(roi_img, lookUpTable)

                    gamma_res = best_model.predict(source=roi_img_gamma, conf=0.1, imgsz=1024, show=False, save=False)[0]
                    
                    if getattr(gamma_res, 'obb', None) is not None:
                        gamma_gap_cands = []
                        for i in range(len(gamma_res.obb)):
                            cls_name = best_model.names[int(gamma_res.obb.cls[i].item())]
                            if cls_name == 'Gap':
                                gamma_gap_cands.append({
                                    'h': gamma_res.obb.xywhr[i][3].item(),
                                    'cy': gamma_res.obb.xywhr[i][1].item()
                                })
                        
                        if gamma_gap_cands and hinge_cy is not None:
                            real_gap_c = min(gamma_gap_cands, key=lambda g: abs(g['cy'] - hinge_cy))
                            gap_pixel_h = real_gap_c['h']
                            annotated_roi = gamma_res.plot()

                # ------------------------------------------------
                # 수치 계산  실측 GT 자동 매핑
                # ------------------------------------------------
                if gap_pixel_h is not None:
                    CAMERA_SF = {
                        'cam1': 0.146171,
                        'cam3': 0.113928,
                    }
                    FIXED_SF = CAMERA_SF[cam_name]
                    raw_mm = gap_pixel_h * FIXED_SF
                    
                    folder_name = os.path.basename(os.path.dirname(img_path_for_csv))
                    
                    # 실제 GT 딕셔너리 
                    REAL_GT_DICT = {
                        'GT_1mm': {
                            'cam1': 0.90,
                            'cam3': 1.00
                        },
                        'GT_2.5mm': {
                            'cam1': 2.25,
                            'cam3': 2.50
                        }
                    }
                    
                    # 폴더명과 카메라 이름을 보고 GT적용
                    if folder_name in REAL_GT_DICT and cam_name in REAL_GT_DICT[folder_name]:
                        actual_gt_mm = REAL_GT_DICT[folder_name][cam_name]
                    else:
                        actual_gt_mm = "Unknown"
                    
                    # CSV에 한 줄씩 기록
                    with open(csv_file_path, mode='a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow([folder_name, actual_gt_mm, formatted_idx, cam_name, f"{gap_pixel_h:.2f}", f"{raw_mm:.2f}"])
                    
                    text = f"Raw Gap: {raw_mm:.2f} mm"
                    cv2.putText(annotated_roi, text, (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3, cv2.LINE_AA)
                    
                    new_filename = f"NG_{formatted_idx}_{cam_name}.jpg"
                    cv2.imwrite(os.path.join(dir_ng, new_filename), annotated_roi)

print(f"\n✅ 엑셀 데이터 추출 완료! [{output_dir}/calibration_data.csv] 파일을 열어보세요.")