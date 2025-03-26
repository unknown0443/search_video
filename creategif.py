import os
import subprocess

# 출력 GIF 파일들을 저장할 폴더 생성 (없으면 생성)
output_folder = "gif"
os.makedirs(output_folder, exist_ok=True)

# 세그먼트 설정
segment_duration = 5      # 초 단위
overlap_duration = 1      # 초 단위
step = segment_duration - overlap_duration  # 4초씩 이동
num_segments = 273        # 0번 세그먼트부터 272번 세그먼트까지

# 각 세그먼트에 대해 GIF 생성
for n in range(num_segments):
    # 프레임 번호 계산 (1초당 1프레임으로 가정하고, 파일명이 0001부터 시작)
    start_frame = n * step + 1
    end_frame = n * step + segment_duration  # = n*4 + 5
    
    frame_files = []
    for i in range(start_frame, end_frame + 1):
        filename = os.path.join("FuJ1RiLoq-M", f"FuJ1RiLoq-M_frame_{i:04d}.jpg")
        if not os.path.exists(filename):
            print(f"파일 없음: {filename}")
        frame_files.append(filename)
    
    output_gif = os.path.join(output_folder, f"output_segment_{n}.gif")
    
    # ImageMagick 명령어 구성 (예: -delay 100; 필요에 따라 delay 조정)
    command = ["magick", "-delay", "100"] + frame_files + [output_gif]
    print("Running command:", " ".join(command))
    
    try:
        subprocess.run(command, check=True)
        print(f"Segment {n}: GIF 생성 완료 -> {output_gif}")
    except subprocess.CalledProcessError as e:
        print(f"Segment {n}: GIF 생성 실패", e)
