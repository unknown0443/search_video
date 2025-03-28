# routes_chat.py
from flask import Blueprint, request, jsonify
import json
import re

from google.generativeai import GenerativeModel
from config import search_model
from utils import get_db_connection, format_hhmmss

chat_bp = Blueprint('chat_bp', __name__)

@chat_bp.route("/chat", methods=["POST"])
def unified_chat():
    data = request.get_json()
    user_msg = data.get("message", "").strip()
    if not user_msg:
        return jsonify({"error": "No message provided"}), 400

    # 1) "수정: 세그먼트ID=xx 내용=... 멤버=..." 명령어 처리
    override_pattern = r'^수정:\s*세그먼트ID=(\d+)\s*내용=(.*?)(?:\s+멤버=(.*))?$'
    match = re.match(override_pattern, user_msg)
    if match:
        seg_id_str = match.group(1)
        override_text = match.group(2).strip()
        members_text = match.group(3)  # 선택적으로 있을 수 있음

        try:
            seg_id = int(seg_id_str)
        except ValueError:
            seg_id = None

        if not seg_id or not override_text:
            return jsonify({"response": "교정 명령 구문이 잘못되었습니다."})

        # 1) 수정 전 데이터 조회
        conn = get_db_connection()
        cur = conn.cursor()
        select_sql = """
        SELECT caption, manual_caption, faces
        FROM njz_segments
        WHERE id = %s
        """
        cur.execute(select_sql, (seg_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return jsonify({"response": f"세그먼트 {seg_id}를 찾을 수 없습니다."})

        old_auto_cap = row[0] or ""
        old_manual_cap = row[1] or ""
        old_faces = row[2] or "[]"
        old_final_cap = old_manual_cap.strip() if old_manual_cap.strip() else old_auto_cap
        if isinstance(old_faces, str):
            try:
                old_faces = json.loads(old_faces)
            except:
                old_faces = []

        # 2) 새 faces 만들기 (멤버 정보)
        if members_text:
            members_list = [m.strip() for m in members_text.split(",") if m.strip()]
            new_faces = json.dumps([{"member": m} for m in members_list])
        else:
            new_faces = json.dumps([])

        # 3) DB 업데이트
        new_emb = search_model.encode(override_text)
        new_emb_str = str(new_emb.tolist())

        if members_text:
            update_sql = """
            UPDATE njz_segments
            SET manual_caption = %s,
                embedding = %s,
                faces = %s
            WHERE id = %s
            """
            cur.execute(update_sql, (override_text, new_emb_str, new_faces, seg_id))
        else:
            update_sql = """
            UPDATE njz_segments
            SET manual_caption = %s,
                embedding = %s
            WHERE id = %s
            """
            cur.execute(update_sql, (override_text, new_emb_str, seg_id))

        # 4) 히스토리 기록
        hist_sql = """
        INSERT INTO njz_segment_operations_history
        (operation_type, segment_ids_before, segment_ids_after,
         old_captions, new_captions, old_faces, new_faces, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(hist_sql, (
            "update",
            json.dumps([seg_id]),
            json.dumps([seg_id]),
            json.dumps([old_final_cap]),
            json.dumps([override_text]),
            json.dumps([old_faces]),
            json.dumps([json.loads(new_faces)]),
            "local_user"
        ))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"response": f"세그먼트 {seg_id} 캡션이 수정되었습니다."})

    # 2) 수정 명령이 아닐 경우 검색 로직
    user_emb = search_model.encode(user_msg)
    user_emb_str = str(user_emb.tolist())

    conn = get_db_connection()
    cur = conn.cursor()
    sql = """
    SELECT
        id, video_id, start_time, end_time,
        caption, manual_caption, faces,
        embedding <=> %s AS distance
    FROM njz_segments
    ORDER BY embedding <=> %s
    LIMIT 3;
    """
    cur.execute(sql, (user_emb_str, user_emb_str))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        relevant_info = "DB에서 검색 결과가 없습니다.\n"
    else:
        relevant_info = ""
        for row in rows:
            seg_id      = row[0]
            start_sec   = row[2]
            end_sec     = row[3]
            auto_cap    = row[4] or ""
            manual_cap  = row[5] or ""
            faces_list  = row[6] or "[]"
            dist        = row[7]

            final_cap = manual_cap.strip() if manual_cap.strip() else auto_cap
            start_hms = format_hhmmss(start_sec)
            end_hms   = format_hhmmss(end_sec)
            time_slot = f"{start_hms} ~ {end_hms}"

            members_set = set()
            try:
                for f in faces_list:
                    if "member" in f:
                        members_set.add(f["member"])
            except Exception as err:
                print('Error', err)
                pass
            if members_set:
                face_line = "등장인물: " + ", ".join(sorted(members_set))
            else:
                face_line = "등장인물: 없음"

            relevant_info += (
                f"[세그먼트ID={seg_id} start={start_sec}]\n"
                f"{time_slot}: \"{final_cap}\"\n"
                f"{face_line}\n"
                f"(dist={dist:.2f}) [수정하기={seg_id}]\n\n"
            )

    from google.generativeai import GenerativeModel
    gemini_model = GenerativeModel("models/gemini-2.0-flash")

    prompt = f"""
Context:
{relevant_info}

사용자 입력: "{user_msg}"

중요:
1) 세그먼트ID=..., start=..., (dist=...) [수정하기=xx] 등의 정보는 그대로 유지할 것.
2) 등장인물 정보는 그대로 보여줄 것.
3) 각 세그먼트의 설명은 combined_caption과 등장인물 정보를 바탕으로 자연스러운 한국어 해석을 작성하는 데 사용한다.
   - 만약 combined_caption이 존재하면 해당 내용을 사용하고, 없으면 captions 배열의 설명을 사용한다.
   - 영어 멤버명을 한글로 변환할 때, 예를 들어 Gang Harin → 강해린, Kim Minji → 김민지, Pham Hanni → 팜하니, Danielle → 다니엘 등으로 변환한다.
       
요청 사항:
위 검색 결과의 세그먼트 정보에서 영어 캡션은 한국어로 번역하고 멤버의 영어이름도 한국어로 번역해.
가장위의 요약을 해줘 예시)검색어와 가장 유사한 3개의 장면입니다. 
"""

    try:
        response = gemini_model.generate_content(prompt)
        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                chat_response = candidate.content.parts[0].text.strip()
            else:
                chat_response = "No response from the model"
        else:
            chat_response = "No response from the model"
    except Exception as e:
        print("Chat endpoint error:", e)
        chat_response = "오류가 발생했습니다."

    return jsonify({"response": chat_response})
