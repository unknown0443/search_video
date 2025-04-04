import json

# 영상 관련 파라미터 (실제 값으로 수정 필요)
original_fps = 29.97   # 영상의 원본 FPS (예: 29.97)
desired_fps = 4        # 캡션 생성 시 사용한 desired fps

# 샘플링 간격: 원본 FPS를 desired FPS로 나눈 값을 반올림
sampling_interval = round(original_fps / desired_fps)

# 보정 인자 계산: (sampling_interval * desired_fps) / original_fps
scaling_factor = (sampling_interval * desired_fps) / original_fps

print(f"Original FPS: {original_fps}")
print(f"Desired FPS: {desired_fps}")
print(f"Sampling interval: {sampling_interval}")
print(f"Scaling factor: {scaling_factor}")

# 파일 경로 (프로젝트 루트 기준)
input_path = "data/video_caption(1).json"
output_path = "data/video_caption_adjusted.json"

# JSON 데이터 불러오기
with open(input_path, "r", encoding="utf-8") as infile:
    metadata = json.load(infile)

# 각 캡션의 시작 및 종료 타임스탬프 보정
for seg in metadata:
    seg["start_time"] = seg["start_time"] * scaling_factor
    seg["end_time"] = seg["end_time"] * scaling_factor

# 보정된 결과를 새 JSON 파일로 저장
with open(output_path, "w", encoding="utf-8") as outfile:
    json.dump(metadata, outfile, indent=4, ensure_ascii=False)

print("캡션 타임스탬프가 실제 영상 시간에 맞게 보정되었습니다.")
