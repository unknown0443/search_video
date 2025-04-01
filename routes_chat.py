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

    # -------------------------
    # 1) "수정:" 명령어 처리
    # -------------------------
    override_pattern = r'^수정:\s*세그먼트ID=(\d+)\s*내용=(.*?)(?:\s+멤버=(.*))?$'
    if user_msg.startswith("수정:"):
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

            # (1) 수정 전 데이터 조회
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

            # (2) 새 faces 만들기
            if members_text:
                members_list = [m.strip() for m in members_text.split(",") if m.strip()]
                new_faces = json.dumps([{"member": m} for m in members_list])
            else:
                new_faces = json.dumps([])

            # (3) DB 업데이트
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

            # (4) 히스토리 기록
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
        else:
            return jsonify({"response": "수정 명령 형식이 올바르지 않습니다."})

    # -------------------------
    # 2) "질문:" 모드 처리
    # -------------------------
    elif user_msg.startswith("질문:"):
        question = user_msg[len("질문:"):].strip()

        # (1) DB에서 전체 세그먼트(또는 원하는 범위) 조회
        conn = get_db_connection()
        cur = conn.cursor()
        # 모든 세그먼트 또는 조건부로 특정 영상만
        sql = """
        SELECT id, start_time, end_time, caption, manual_caption, faces
        FROM njz_segments
        ORDER BY start_time ASC
        """
        cur.execute(sql)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        # (2) DB에서 가져온 세그먼트 정보 -> LLM에게 전달할 텍스트로 변환
        # 예: [세그먼트ID=101, start=60, end=65, 캡션="민지가 웃고 있다."]
        all_segments_text = ""
        for row in rows:
            seg_id = row[0]
            start_sec = row[1]
            end_sec = row[2]
            auto_cap = row[3] or ""
            manual_cap = row[4] or ""
            faces_json = row[5] or "[]"

            final_cap = manual_cap.strip() if manual_cap.strip() else auto_cap
            # 멤버들
            try:
                faces_data = json.loads(faces_json) if isinstance(faces_json, str) else faces_json
            except:
                faces_data = []
            members = [f["member"] for f in faces_data if "member" in f]
            members_str = ", ".join(members) if members else "없음"

            start_hms = format_hhmmss(start_sec)
            end_hms = format_hhmmss(end_sec)
            all_segments_text += (
                f"[세그먼트ID={seg_id}, start={start_hms}, end={end_hms}, 멤버={members_str}, 캡션=\"{final_cap}\"]\n"
            )

        # (3) 질문 모드 프롬프트 구성
        prompt = f"""
아래는 영상의 세그먼트 정보 목록입니다:
{all_segments_text}

사용자의 질문: "{question}"

위 세그먼트 정보를 활용하여, 질문에 대해 구체적으로 답변해 주세요.
예) "민지가 나오는 모든 장면을 알려줘"라면, 각 세그먼트ID와 시간 정보를 나열해 주세요.
세그먼트ID가 2, 3, 4 이런식으로 연속적이라면 답을 세그먼트ID(2~4) 시간(세그먼트ID2의 시작시간 ~ 세그먼트ID4의 끝나는시간)이런식으로 표기해줘.
세그먼트ID가 계속 붙어있다면 붙어있는 부분까지 다 묶어주고 세그먼트 시작시간과 끝나는 시간은 start_sec, end_sec을 참고해서 시간만 대답해줘.
"""
        try:
            gemini_model = GenerativeModel("models/gemini-2.0-flash")
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

    # -------------------------
    # 3) 기본 영상 검색 로직
    # -------------------------
    else:
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
                    # faces_list가 str일 수 있으니 파싱
                    if isinstance(faces_list, str):
                        faces_list = json.loads(faces_list)
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

        prompt = f"""
Context:
{relevant_info}

사용자 입력: "{user_msg}"

중요:
- 세그먼트 정보(세그먼트ID, start, (dist=...), [수정하기=xx])는 그대로 유지.
- 등장인물 정보가 영어라면 한국어로 출력.
- 각 세그먼트의 설명은 combined_caption (존재 시) 또는 captions 배열의 설명을 바탕으로 자연스러운 한국어 해석으로 작성.
  (예: Gang Harin → 강해린, Kim Minji → 김민지, Pham Hanni → 팜하니, Danielle → 다니엘)

요청:
영어 캡션과 멤버 이름을 한국어로 번역하여, "검색어와 가장 유사한 3개의 장면입니다."와 같이 요약해 주세요.
"""
        try:
            gemini_model = GenerativeModel("models/gemini-2.0-flash")
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
