import cv2
import os
import requests
from tqdm import tqdm

# ✅ 모델 다운로드 경로 (GitHub)
MODEL_URL = "https://github.com/Saafke/EDSR_Tensorflow/raw/master/models/EDSR_x4.pb"
MODEL_PATH = "EDSR_x4.pb"

# ✅ 모델 다운로드 함수
def download_model():
    if not os.path.exists(MODEL_PATH):
        print(f"📥 모델 다운로드 중: {MODEL_URL}")
        response = requests.get(MODEL_URL, stream=True)
        if response.status_code == 200:
            with open(MODEL_PATH, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"✅ 모델 다운로드 완료: {MODEL_PATH}")
        else:
            raise Exception(f"❌ 모델 다운로드 실패! (Status Code: {response.status_code})")
    else:
        print(f"✅ 모델이 이미 존재합니다: {MODEL_PATH}")

# ✅ 모델 다운로드 실행
download_model()

# ✅ OpenCV Super Resolution 모델 로드
sr = cv2.dnn_superres.DnnSuperResImpl_create()

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"❌ 모델 파일을 찾을 수 없습니다: {MODEL_PATH}")

sr.readModel(MODEL_PATH)
sr.setModel("edsr", 4)  # ✅ 4배 확대

# ✅ GPU 사용 여부 확인 후 적용
use_cuda = cv2.cuda.getCudaEnabledDeviceCount() > 0
if use_cuda:
    sr.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
    sr.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
    print("🚀 GPU 가속이 활성화되었습니다!")
else:
    sr.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    sr.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    print("⚠️ GPU 사용 불가능 → CPU 모드로 실행")

print("✅ 모델 로드 완료!\n")


# ✅ 화질 개선 함수 (이미지 크기 1000px 초과 시 건너뜀)
def enhance_image(image_path, save_path):
    print(f"🔍 처리 중: {image_path}")  # 디버깅 메시지

    img = cv2.imread(image_path)
    if img is None:
        print(f"⚠️ 이미지 로드 실패 (손상된 파일): {image_path}")
        return False
    
    # ✅ 이미지 크기 확인
    h, w, _ = img.shape
    print(f"📏 원본 이미지 크기: {w}x{h}")

    # ✅ 크기가 700px을 초과하면 건너뜀
    if max(h, w) > 700:
        print(f"⏩ 이미지 크기 초과, 업스케일링 건너뜀: {image_path}")
        return False

    try:
        print(f"🚀 업스케일링 시작: {image_path}")  
        enhanced_img = sr.upsample(img)  # ✅ 화질 개선 실행
        print(f"✅ 업스케일링 완료: {image_path}")

        cv2.imwrite(save_path, enhanced_img)  # ✅ 저장
        return True  # 성공한 경우
    except Exception as e:
        print(f"❌ 업스케일링 실패: {image_path} - {e}")
        return False


# ✅ 업스케일링할 이미지 폴더 리스트 (여러 개 가능)
image_folders = [
    "NJZ/harin",
    "NJZ/dani",
    "NJZ/minji",
    "RED/seulgi",
    "RED/irene",
    "RED/joy",
    "RED/wendy",
    "IVE/an",
    "IVE/jang",
    "EXO/back",
    "EXO/dio",
    "EXO/kai",
    "SK/hyun",
    "SK/pil"
]

# ✅ 모든 폴더를 순회하며 업스케일링 실행
for image_folder in image_folders:
    enhanced_folder = f"{image_folder}_enhanced"
    os.makedirs(enhanced_folder, exist_ok=True)

    # ✅ 폴더 내 이미지 목록 가져오기
    image_files = [f for f in os.listdir(image_folder) if f.endswith(('.jpg', '.png'))]
    total_images = len(image_files)

    print(f"\n📂 폴더 '{image_folder}' 처리 중... 총 {total_images}개의 이미지 발견!\n")

    # ✅ 진행 상태 표시
    success_count = 0
    skip_count = 0
    for img_file in tqdm(image_files, desc=f"📸 {image_folder} 업스케일링 진행 중"):
        img_path = os.path.join(image_folder, img_file)
        save_path = os.path.join(enhanced_folder, img_file)

        # ✅ 이미 업스케일된 파일은 건너뛰기
        if os.path.exists(save_path):
            print(f"⏩ 이미 처리된 이미지: {save_path}")
            continue

        if enhance_image(img_path, save_path):
            success_count += 1
        else:
            skip_count += 1

    # ✅ 폴더별 결과 출력
    print(f"\n🎉 폴더 '{image_folder}' 업스케일링 완료! ({success_count}/{total_images}개 성공, {skip_count}개 건너뜀)")
    print(f"📂 저장 경로: {enhanced_folder}\n")

# ✅ 전체 결과 출력
print("\n🚀 모든 폴더의 업스케일링 작업 완료!")
