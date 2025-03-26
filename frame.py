import cv2
import os

# 영상 파일 경로 (프로젝트 루트에 있음)
video_file = "FuJ1RiLoq-M.mp4"

# 추출한 프레임들을 저장할 폴더 (프로젝트 루트/FuJ1RiLoq-M)
output_folder = "FuJ1RiLoq-M"
os.makedirs(output_folder, exist_ok=True)

# 영상 열기
cap = cv2.VideoCapture(video_file)
if not cap.isOpened():
    print("Error: Could not open video file.")
    exit(1)

# 영상의 FPS를 가져옴
fps = cap.get(cv2.CAP_PROP_FPS)
# 초당 1프레임으로 추출하기 위해 프레임 간격은 영상의 FPS 값(반올림)
frame_interval = int(round(fps))
print(f"Original FPS: {fps:.2f}, Frame interval for 1fps extraction: {frame_interval}")

frame_count = 0       # 전체 프레임 카운트
saved_frame_count = 0 # 저장된 프레임 번호 (1부터 시작)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 매 frame_interval 번째 프레임 저장 (초당 1프레임)
    if frame_count % frame_interval == 0:
        saved_frame_count += 1
        # 파일명: FuJ1RiLoq-M_frame_0001.jpg, FuJ1RiLoq-M_frame_0002.jpg, ...
        filename = os.path.join(output_folder, f"FuJ1RiLoq-M_frame_{saved_frame_count:04d}.jpg")
        cv2.imwrite(filename, frame)
        print(f"Saved frame {saved_frame_count} (frame count {frame_count})")
    
    frame_count += 1

cap.release()
print(f"Extraction complete: {saved_frame_count} frames saved in '{output_folder}' folder.")
