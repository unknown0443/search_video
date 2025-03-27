import os
import json
import math

# 프로젝트 루트의 data 폴더 경로 설정
data_dir = os.path.join(os.getcwd(), "data")

# 캡션 JSON 파일과 얼굴 메타데이터 JSON 파일 로드
with open(os.path.join(data_dir, "video_captions_opt(beta).json"), "r", encoding="utf-8") as f:
    captions = json.load(f)

with open(os.path.join(data_dir, "FuJ1RiLoq-M.json"), "r", encoding="utf-8") as f:
    faces = json.load(f)

# 전체 영상 길이를 결정 (캡션의 end_time과 얼굴 데이터의 timestamp 중 최댓값 사용)
max_caption_time = max(seg["end_time"] for seg in captions)
max_face_time = max(face["timestamp"] for face in faces)
video_duration = math.ceil(max(max_caption_time, max_face_time))

timeline_data = []

for t in range(video_duration):
    # 해당 시간 슬롯(예: t초 ~ t+1초)에 포함되는 캡션 세그먼트 추출
    caption_texts = [seg["caption"] for seg in captions if seg["start_time"] < (t + 1) and seg["end_time"] > t]
    
    # 해당 시간 슬롯에 속하는 얼굴 데이터 중, 그룹이 "NJZ"인 항목만 선택
    seg_faces = [face for face in faces if t <= face.get("timestamp", 0) < (t + 1) and face.get("group") == "NJZ"]
    
    # 여러 캡션이 있을 경우 하나의 문자열로 결합 (필요에 따라 수정 가능)
    combined_caption = " ".join(caption_texts)
    
    timeline_data.append({
        "time_slot": f"{t}-{t+1} sec",
        "captions": caption_texts,
        "combined_caption": combined_caption,
        "faces": seg_faces
    })

# 결합된 타임라인 데이터를 data 폴더 내의 새로운 JSON 파일로 저장
with open(os.path.join(data_dir, "timeline_merged_njz.json"), "w", encoding="utf-8") as f:
    json.dump(timeline_data, f, indent=4, ensure_ascii=False)

print("Timeline merged data (only NJZ group) saved to 'data/timeline_merged_njz.json'")
