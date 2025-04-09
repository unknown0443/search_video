# common_search.py
import json
from urllib.parse import quote_plus
from utils import get_db_connection, format_hhmmss
from config import search_model

def get_search_blocks(user_text):
    # 임베딩 계산
    user_emb = search_model.encode(user_text)
    user_emb_str = str(user_emb.tolist())
    
    # DB 조회
    conn = get_db_connection()
    cur = conn.cursor()
    sql = """
    SELECT
        id, video_id, start_time, end_time, caption, manual_caption, faces,
        embedding <=> %s AS distance
    FROM njz_segments
    ORDER BY embedding <=> %s
    LIMIT 3;
    """
    cur.execute(sql, (user_emb_str, user_emb_str))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    blocks = []
    if not rows:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "DB에서 검색 결과가 없습니다."}
        })
    else:
        encoded_query = quote_plus(user_text)
        for row in rows:
            seg_id = row[0]
            # 예시: 세그먼트ID 272 이하인 경우에만 GIF 파일이 있다고 가정
            if seg_id > 272:
                continue

            start_time = row[2]
            end_time = row[3]
            auto_cap = row[4] or ""
            manual_cap = row[5] or ""
            final_cap = manual_cap.strip() if manual_cap.strip() else auto_cap
            time_slot = f"{int(start_time)}-{int(end_time)} sec"

            section_block = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*세그먼트ID={seg_id}* (start={start_time})\n{time_slot}: \"{final_cap}\""
                }
            }
            image_block = {
                "type": "image",
                "image_url": f"https://7309-58-72-151-123.ngrok-free.app/gif/output_segment_{int(seg_id):04d}.gif",
                "alt_text": f"세그먼트 {seg_id} GIF"
            }
            actions_block = {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "영상 보러가기"},
                        "url": f"https://7309-58-72-151-123.ngrok-free.app/video_player?t={start_time}"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "수정하기"},
                        "value": str(seg_id),
                        "action_id": "modify_click"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Edit in Web"},
                        "url": f"https://7309-58-72-151-123.ngrok-free.app/?q={encoded_query}"
                    }
                ]
            }
            blocks.extend([section_block, image_block, actions_block])
    return blocks
