import cv2
import os
import numpy as np  

# ---------------------------------------------------------
# 1. GT 폴더 자동 생성 (정상, 1mm, 1.5mm, 2.5mm)
# ---------------------------------------------------------
gt0_path = "dataset/GT_0mm"    # 정상(Normal)
gt1_path = "dataset/GT_1mm"
gt15_path = "dataset/GT_1.5mm" # 블라인드 테스트용 1.5mm
gt2_path = "dataset/GT_2.5mm"

os.makedirs(gt0_path, exist_ok=True)
os.makedirs(gt1_path, exist_ok=True)
os.makedirs(gt15_path, exist_ok=True)
os.makedirs(gt2_path, exist_ok=True)

# ---------------------------------------------------------
# 2. 카메라 세팅 
# ---------------------------------------------------------
cap1 = cv2.VideoCapture(3) # Side View 1 (뒤집은 카메라)
cap2 = cv2.VideoCapture(0) # Top View (정방향)
cap3 = cv2.VideoCapture(2) # Side View 2 (뒤집은 카메라)

count_0 = 0
count_1 = 0
count_15 = 0
count_2 = 0

print("==============================================")

print("[0] 누르면 -> 정상 0mm (GT_0mm) 저장")
print("[1] 누르면 -> 1.0mm (GT_1mm) 저장")
print("[3] 누르면 -> 1.5mm (GT_1.5mm) 저장")
print("[2] 누르면 -> 2.5mm (GT_2.5mm) 저장")
print("[ESC] 누르면 -> 프로그램 종료")
print("==============================================")

while True:
    ret1, frame1 = cap1.read()
    ret2, frame2 = cap2.read()
    ret3, frame3 = cap3.read()

    if not (ret1 and ret2 and ret3):
        print("카메라 연결 상태를 확인해주세요.")
        break

    # 측면 카메라 뒤집기 복구
    frame1 = cv2.rotate(frame1, cv2.ROTATE_180)
    frame3 = cv2.rotate(frame3, cv2.ROTATE_180)

    # 모니터링용 화면 리사이즈
    disp1 = cv2.resize(frame1, (480, 360))
    disp2 = cv2.resize(frame2, (480, 360))
    disp3 = cv2.resize(frame3, (480, 360))

    combined_frame = np.hstack((disp1, disp2, disp3))

    cv2.putText(combined_frame, "Side 1", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(combined_frame, "Top View", (480 + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(combined_frame, "Side 2", (960 + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.imshow("Multi-Cam Smart Monitoring", combined_frame)

    key = cv2.waitKey(1) & 0xFF

    if key == 27: # ESC
        print("데이터 수집을 종료합니다.")
        break
        
    elif key == ord('0'):
        cv2.imwrite(f"{gt0_path}/0mm_{count_0:03d}_cam1.jpg", frame1)
        cv2.imwrite(f"{gt0_path}/0mm_{count_0:03d}_cam2.jpg", frame2)
        cv2.imwrite(f"{gt0_path}/0mm_{count_0:03d}_cam3.jpg", frame3)
        print(f"✅ [정상 0mm] {count_0}번째 세트 저장 완료!")
        count_0 += 1

    elif key == ord('1'):
        cv2.imwrite(f"{gt1_path}/1mm_{count_1:03d}_cam1.jpg", frame1)
        cv2.imwrite(f"{gt1_path}/1mm_{count_1:03d}_cam2.jpg", frame2)
        cv2.imwrite(f"{gt1_path}/1mm_{count_1:03d}_cam3.jpg", frame3)
        print(f"🟢 [1.0mm] {count_1}번째 세트 저장 완료!")
        count_1 += 1
        
    elif key == ord('3'):
        cv2.imwrite(f"{gt15_path}/1.5mm_{count_15:03d}_cam1.jpg", frame1)
        cv2.imwrite(f"{gt15_path}/1.5mm_{count_15:03d}_cam2.jpg", frame2)
        cv2.imwrite(f"{gt15_path}/1.5mm_{count_15:03d}_cam3.jpg", frame3)
        print(f"🔵 [1.5mm] {count_15}번째 세트 저장 완료!")
        count_15 += 1

    elif key == ord('2'):
        cv2.imwrite(f"{gt2_path}/2.5mm_{count_2:03d}_cam1.jpg", frame1)
        cv2.imwrite(f"{gt2_path}/2.5mm_{count_2:03d}_cam2.jpg", frame2)
        cv2.imwrite(f"{gt2_path}/2.5mm_{count_2:03d}_cam3.jpg", frame3)
        print(f"🟡 [2.5mm] {count_2}번째 세트 저장 완료!")
        count_2 += 1

cap1.release()
cap2.release()
cap3.release()
cv2.destroyAllWindows()