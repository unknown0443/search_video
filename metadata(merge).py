import json

# 파일 경로 (프로젝트 루트 기준)
metadata_file = "data/metadata.json"
caption_file = "data/video_caption_int_rounded.json"
output_file = "data/combined_metadata.json"

# JSON 데이터 불러오기
with open(metadata_file, "r", encoding="utf-8") as f:
    metadata_list = json.load(f)

with open(caption_file, "r", encoding="utf-8") as f:
    caption_list = json.load(f)

# metadata_list를 timestamp별로 그룹화 (여러 얼굴 정보가 있을 수 있으므로 리스트로 저장)
metadata_grouped = {}
for entry in metadata_list:
    ts = entry["timestamp"]
    face_info = {
        "group": entry.get("group"),
        "member": entry.get("member"),
        "confidence": entry.get("confidence"),
        "bbox": entry.get("bbox")
    }
    if ts in metadata_grouped:
        metadata_grouped[ts].append(face_info)
    else:
        metadata_grouped[ts] = [face_info]

# caption_list를 time을 key로 하는 딕셔너리로 변환
caption_dict = {entry["time"]: entry["caption"] for entry in caption_list}

# 두 파일의 타임스탬프(정수 초)의 union을 구함
all_timestamps = set(metadata_grouped.keys()) | set(caption_dict.keys())

combined = []
for ts in sorted(all_timestamps):
    combined_entry = {
        "timestamp": ts,
        "video_id": "FuJ1RiLoq-M",
        "caption": caption_dict.get(ts, ""),
        # 얼굴 정보가 없으면 빈 리스트, 있으면 해당 리스트 사용
        "faces": metadata_grouped.get(ts, [])
    }
    combined.append(combined_entry)

# 결합된 데이터를 새로운 JSON 파일로 저장
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(combined, f, indent=4, ensure_ascii=False)

print(f"Combined metadata saved to {output_file}")
