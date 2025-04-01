import json
import psycopg2
from sentence_transformers import SentenceTransformer

# 1. 모델 로드 (Hugging Face API 사용)
model = SentenceTransformer("bongsoo/kpf-sbert-128d-v1")

# 2. 결합된 메타데이터 JSON 로드 (예: timeline_merged_njz.json)
json_path = "data/timeline_merged_njz.json"  # 실제 경로에 맞게 수정
with open(json_path, "r", encoding="utf-8") as f:
    combined_data = json.load(f)

# 3. PostgreSQL 연결 설정 (필요한 정보로 수정)
conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="1234",
    host="localhost",
    port="5432"
)
cur = conn.cursor()

# 4. 새 테이블 생성: njz_segments (PGVector 확장 사용)
# faces 컬럼을 JSONB 타입으로 추가
create_table_sql = """
CREATE EXTENSION IF NOT EXISTS vector;

DROP TABLE IF EXISTS njz_segments;
CREATE TABLE njz_segments (
    id SERIAL PRIMARY KEY,
    video_id TEXT,
    start_time FLOAT,
    end_time FLOAT,
    caption TEXT,
    faces JSONB,
    embedding vector(128)
);
"""
cur.execute(create_table_sql)
conn.commit()

# 5. 데이터 삽입 SQL 문
insert_sql = """
INSERT INTO njz_segments (video_id, start_time, end_time, caption, faces, embedding)
VALUES (%s, %s, %s, %s, %s, %s);
"""

# 6. 각 세그먼트에 대해 임베딩 계산 후 데이터 삽입
for seg in combined_data:
    video_id = seg.get("video_id", "FuJ1RiLoq-M")
    start_time = seg.get("start_time", 0)
    end_time = seg.get("end_time", 0)
    # caption 필드가 있으면 사용, 없으면 combined_caption 사용
    caption = seg.get("caption", seg.get("combined_caption", ""))
    
    # faces 필드: 리스트 형태이면 JSON 문자열로 변환
    faces = seg.get("faces", [])
    faces_str = json.dumps(faces, ensure_ascii=False)
    
    # 임베딩 계산 (128차원)
    embedding = model.encode(caption)
    # PGVector는 문자열 형식의 벡터를 사용 (예: "[0.1,0.2,...]")
    embedding_str = str(embedding.tolist())
    
    cur.execute(insert_sql, (video_id, start_time, end_time, caption, faces_str, embedding_str))
    conn.commit()

cur.close()
conn.close()

print("Embeddings (with faces) inserted into PGVector table 'njz_segments' successfully.")