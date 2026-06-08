# 🏭 FactoryVision
**Edge AI 기반 스마트 팩토리 조립 불량 검사 및 3D 웹 관제 시스템**

다중 시점 카메라와 YOLO-OBB 기반의 센서 퓨전을 통해 제조 현장의 조립 불량(단차 등)을 측정하고, MQTT 통신을 이용해 실시간으로 3D 디지털 트윈 대시보드에 연동하는 시스템입니다.

단순한 객체 인식을 넘어, 서브 밀리미터 단위의 단차 측정을 위해 실제 Ground Truth(1mm, 2.5mm) 데이터를 활용하여 선형 회귀(Linear Regression) 분석을 통해 오차 보정 계수를 도출했습니다.



---

## 📂 프로젝트 구조 (Directory)

```text
📦 FactoryVision
┣ 📂 Edge_node/              # AI 검사 엔진 및 하드웨어 제어부 (Python)
┃ ┣ 📜 Json.py             # 다중 카메라 제어, 단차 계산, MQTT 전송 메인 로직
┃ ┣ 📜 best_0504.pt        # 자체 라벨링 데이터로 학습된 YOLOv8-OBB 모델 가중치
┃ ┗ 📂 Calibration/        # 오차 보정을 위한 캘리브레이션 연구 코드 및 결과
┃   ┣ 📜 GTreg.py          # 픽셀-물리 수치 변환용 선형 회귀 분석 스크립트
┃   ┣ 📜 GTmulticam.py     # 다중 웹캠 동기화 테스트 스크립트
┃   ┗ 🖼️ LinearRegression.png # 선형 회귀 분석 결과 그래프
┃
┗ 📂 WebDashboard/           # 실시간 3D 디지털 트윈 대시보드 (React, Three.js)
  ┣ 📂 public/             # 3D 장비 렌더링 모델(.glb) 및 정적 리소스
  ┣ 📂 src/                # 프론트엔드 메인 로직 (App.jsx, UI/UX 디자인 요소)
  ┣ 📜 package.json        # 프론트엔드 의존성 패키지 목록
  ┗ 📜 vite.config.js      # Vite 환경 설정
