import imageio
import os

# 영상 파일 경로 (프로젝트 루트 기준)
video_path = "FuJ1RiLoq-M.mp4"

# 영상 읽기: ffmpeg backend 사용
reader = imageio.get_reader(video_path, 'ffmpeg')
meta = reader.get_meta_data()

# FPS와 영상 길이(초)를 가져옴
fps = meta.get('fps', 30)  # fps 정보가 없으면 기본값 30 사용
duration = meta.get('duration', None)
if duration is None:
    # duration 정보가 없으면, 총 프레임 수를 이용해 계산
    nframes = reader.count_frames()
    duration = nframes / fps

print(f"Video FPS: {fps}")
print(f"Video duration: {duration:.2f} seconds")

# 추출된 프레임 저장 폴더 생성
output_dir = "extracted_frames"
os.makedirs(output_dir, exist_ok=True)

# 0초부터 영상 길이까지, 정수 초 단위로 프레임 추출
for sec in range(int(duration)):
    # 해당 초에 해당하는 프레임 인덱스 계산 (예: sec 0 -> 0, sec 1 -> int(fps), ...)
    frame_index = int(sec * fps)
    try:
        frame = reader.get_data(frame_index)
    except Exception as e:
        print(f"Failed to get frame at {sec} sec (frame {frame_index}): {e}")
        continue
    
    # 저장 파일명: 예) frame_0000.png, frame_0001.png, ...
    output_file = os.path.join(output_dir, f"frame_{sec:04d}.png")
    imageio.imwrite(output_file, frame)
    print(f"Extracted frame at {sec} second -> {output_file}")

print("모든 프레임 추출 완료.")
