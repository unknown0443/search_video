import os
import subprocess

# extracted_frames 폴더 내 이미지 파일이 있다고 가정 (예: frame_0000.png ~ frame_1095.png)
frames_folder = "extracted_frames"
output_folder = "gif"
os.makedirs(output_folder, exist_ok=True)

# 전체 프레임 수 (예시: 1096개)
num_frames = 1096

for i in range(num_frames):
    # 각 세그먼트에 대해 "1초 전, 현재, 1초 후"에 해당하는 프레임 번호 계산
    prev_frame = i - 1 if i - 1 >= 0 else i
    curr_frame = i
    next_frame = i + 1 if i + 1 < num_frames else i

    # 이미지 파일 경로 구성 (예: extracted_frames/frame_0000.png)
    file_prev = os.path.join(frames_folder, f"frame_{prev_frame:04d}.png")
    file_curr = os.path.join(frames_folder, f"frame_{curr_frame:04d}.png")
    file_next = os.path.join(frames_folder, f"frame_{next_frame:04d}.png")

    # 사용할 이미지 목록
    frame_files = [file_prev, file_curr, file_next]

    # 출력할 GIF 파일명 (예: gif/output_segment_0000.gif)
    output_gif = os.path.join(output_folder, f"output_segment_{i:04d}.gif")

    # ImageMagick (magick 명령어)를 사용하여 GIF 생성 (delay 조정은 필요에 따라 변경)
    command = ["magick", "-delay", "100"] + frame_files + [output_gif]
    print("Running command:", " ".join(command))
    try:
        subprocess.run(command, check=True)
        print(f"Segment {i}: GIF 생성 완료 -> {output_gif}")
    except subprocess.CalledProcessError as e:
        print(f"Segment {i}: GIF 생성 실패", e)
