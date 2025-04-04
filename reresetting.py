import json

# 파일 경로 (프로젝트 루트 기준)
input_path = "data/video_caption_adjusted.json"
output_path = "data/video_caption_int_rounded.json"

# JSON 데이터 불러오기
with open(input_path, "r", encoding="utf-8") as infile:
    segments = json.load(infile)

# 초 단위로 반올림 후, 동일 초끼리 캡션 병합
# 여기서는 각 세그먼트의 start_time을 기준으로 합니다.
grouped = {}
for seg in segments:
    # 소수점 이하 반올림: 예) 1.3 -> 1, 1.7 -> 2, 2.2 -> 2
    second = round(seg["start_time"])
    
    # 동일 초에 이미 캡션이 있으면 이어 붙임 (문장 사이에 공백 추가)
    if second in grouped:
        grouped[second] += " " + seg["caption"]
    else:
        grouped[second] = seg["caption"]

# 그룹별 데이터를 리스트로 정리 (시간 순 정렬)
rounded_segments = [{"time": t, "caption": grouped[t]} for t in sorted(grouped.keys())]

# 결과 JSON 파일로 저장
with open(output_path, "w", encoding="utf-8") as outfile:
    json.dump(rounded_segments, outfile, indent=4, ensure_ascii=False)

print(f"반올림된 타임스탬프와 병합된 캡션 정보를 '{output_path}'에 저장하였습니다.")
