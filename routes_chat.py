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

    # ----------------------------------
    # 1) 수정 명령 ("수정:" 모드)
    # ----------------------------------
    override_pattern = r'^수정:\s*세그먼트ID=(\d+)\s*내용=(.*?)(?:\s+멤버=(.*))?$'
    if user_msg.startswith("수정:"):
        match = re.match(override_pattern, user_msg)
        if match:
            seg_id_str = match.group(1)
            override_text = match.group(2).strip()
            members_text = match.group(3)

            try:
                seg_id = int(seg_id_str)
            except ValueError:
                seg_id = None

            if not seg_id or not override_text:
                return jsonify({"response": "교정 명령 구문이 잘못되었습니다."})

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

            if members_text:
                members_list = [m.strip() for m in members_text.split(",") if m.strip()]
                new_faces = json.dumps([{"member": m} for m in members_list])
            else:
                new_faces = json.dumps([])

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

    # ----------------------------------
    # 2) 질문 ("질문:" 모드)
    # ----------------------------------
    elif user_msg.startswith("질문:"):
        question = user_msg[len("질문:"):].strip()

        conn = get_db_connection()
        cur = conn.cursor()
        sql = """
        SELECT id, start_time, end_time, caption, manual_caption, faces
        FROM njz_segments
        ORDER BY start_time ASC
        """
        cur.execute(sql)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        grouped_segments = []
        current_group = []
        THRESHOLD = 1.0  # 1초 임계값

        for row in rows:
            seg_id = row[0]
            start_time = row[1]
            end_time = row[2]
            auto_cap = row[3] or ""
            manual_cap = row[4] or ""
            faces_json = row[5] or "[]"
            final_cap = manual_cap.strip() if manual_cap.strip() else auto_cap

            if isinstance(faces_json, str):
                try:
                    faces_data = json.loads(faces_json)
                except:
                    faces_data = []
            else:
                faces_data = faces_json

            members = [f["member"] for f in faces_data if "member" in f]
            seg_info = {
                "id": seg_id,
                "start": start_time,
                "end": end_time,
                "cap": final_cap,
                "members": members,
            }

            if not current_group:
                current_group.append(seg_info)
            else:
                last = current_group[-1]
                time_gap = seg_info["start"] - last["end"]
                # 시간 gap이 THRESHOLD 이하면 그룹화 (캡션은 단순 결합)
                if time_gap <= THRESHOLD:
                    # 기존 캡션과 다르더라도 "/"로 결합 (추후 중요정보 추출 로직 추가 가능)
                    current_group[-1]["cap"] = f"{current_group[-1]['cap']} / {seg_info['cap']}"
                    # 멤버도 합치기
                    current_group[-1]["members"] = list(set(current_group[-1]["members"] + seg_info["members"]))
                    # 그룹의 종료 시간 업데이트
                    current_group[-1]["end"] = seg_info["end"]
                    # 그룹에 새로운 세그먼트 ID도 추가
                    current_group[-1]["ids"] = current_group[-1].get("ids", [last["id"]]) + [seg_info["id"]]
                else:
                    grouped_segments.append(current_group)
                    current_group = [seg_info]

        if current_group:
            grouped_segments.append(current_group)

        all_segments_text = ""
        for group in grouped_segments:
            if "ids" in group[0]:
                ids = group[0]["ids"]
            else:
                ids = [group[0]["id"]]
            start_hms = format_hhmmss(group[0]["start"])
            end_hms = format_hhmmss(group[-1]["end"])
            caption = group[0]["cap"]
            members = sorted({m for seg in group for m in seg["members"]})
            member_str = ", ".join(members) if members else "없음"

            if len(ids) == 1:
                seg_line = f"[세그먼트ID={ids[0]}, start_sec={group[0]['start']}, end_sec={group[-1]['end']}]\n{start_hms} ~ {end_hms}\n캡션: \"{caption}\"\n등장인물: {member_str}\n"
            else:
                seg_line = f"[세그먼트ID={ids[0]}~{ids[-1]}, start_sec={group[0]['start']}, end_sec={group[-1]['end']}]\n{start_hms} ~ {end_hms}\n캡션: \"{caption}\"\n등장인물: {member_str}\n"
            all_segments_text += seg_line + "\n"  # 문단 구분을 위해 빈 줄 추가

        prompt = f"""
아래는 영상의 세그먼트 정보 목록입니다:
{all_segments_text}

사용자의 질문: "{question}"

위 세그먼트 정보를 활용하여, 질문에 대해 구체적으로 답변해 주세요.
예) "민지가 나오는 모든 장면을 알려줘"라면, 각 세그먼트ID와 시간 정보를 나열해 주세요.
세그먼트ID가 연속적이라면 예를 들어 세그먼트ID(2~4)와 시간(세그먼트ID2의 시작시간 ~ 세그먼트ID4의 끝나는시간)으로 표기해 주세요.
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

    #  # ----------------------------------
    # 3) 기본 검색 로직 (우선순위 적용, 그룹화 제거)
    # ----------------------------------
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
        LIMIT 10;
        """
        cur.execute(sql, (user_emb_str, user_emb_str))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        # 각 세그먼트에 대해 수정된 캡션(manual_caption)이 있으면 사용, 없으면 원본 캡션을 사용하며,
        # faces.member 유무에 따라 우선순위(priority)를 부여
        segments = []
        for row in rows:
            seg_id = row[0]
            video_id = row[1]
            start_time = row[2]
            end_time = row[3]
            auto_cap = row[4] or ""
            manual_cap = row[5] or ""
            faces = row[6] or []
            dist = row[7]
            final_cap = manual_cap.strip() if manual_cap.strip() else auto_cap

            if isinstance(faces, str):
                try:
                    faces = json.loads(faces)
                except:
                    faces = []
            members = [f["member"] for f in faces if "member" in f]
            priority = 1 if members else (2 if manual_cap.strip() else 3)

            segments.append({
                "id": seg_id,
                "video_id": video_id,
                "start": start_time,
                "end": end_time,
                "cap": final_cap,
                "members": sorted(set(members)),
                "dist": dist,
                "priority": priority
            })

        # 우선순위와 유사도(distance)를 기준으로 정렬
        segments = sorted(segments, key=lambda s: (s["priority"], s["dist"]))

        # 그룹화 코드를 제거하고, 각 세그먼트를 개별 결과로 만듦
        if not segments:
            relevant_info = "DB에서 검색 결과가 없습니다.\n"
        else:
            relevant_info = ""
            for seg in segments:
                start_hms = format_hhmmss(seg["start"])
                end_hms = format_hhmmss(seg["end"])
                cap = seg["cap"]
                members = seg["members"]
                face_line = "등장인물: " + ", ".join(members) if members else "등장인물: 없음"
                relevant_info += (
                    f"[세그먼트ID={seg['id']} (start_sec={seg['start']}, end_sec={seg['end']})]\n"
                    f"{start_hms} ~ {end_hms}\n"
                    f"캡션: \"{cap}\"\n"
                    f"{face_line}\n"
                    f"(dist={seg['dist']:.2f}) [수정하기={seg['id']}]\n\n"
                )

        prompt = f"""
Context:
{relevant_info}

사용자 입력: "{user_msg}"

중요:
- 세그먼트 정보(세그먼트ID, start_sec, end_sec, (dist=...), [수정하기=xx])는 그대로 유지.
- 등장인물 정보가 영어라면 한국어로 출력.
- 각 세그먼트의 설명은 combined_caption(존재 시) 또는 captions 배열의 설명을 바탕으로 자연스러운 한국어 해석으로 작성.
  (예: Gang Harin → 강해린, Kim Minji → 김민지, Pham Hanni → 팜하니, Danielle → 다니엘)

요청:
영어 캡션과 멤버 이름을 한국어로 번역하여, "검색어와 가장 유사한 장면입니다."와 같이 요약해 주세요.
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
# ----------------------------------
# 그룹 수정 API
# ----------------------------------
@chat_bp.route("/segment/group_modify", methods=["POST"])
def group_modify():
    data = request.get_json()
    segment_ids = data.get("segment_ids")
    new_caption = data.get("new_caption", "").strip()
    new_members = data.get("new_members", [])
    if not segment_ids or not new_caption:
        return jsonify({"success": False, "message": "세그먼트 ID와 새 캡션이 필요합니다."}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    old_caps = []
    old_faces_list = []
    for seg_id in segment_ids:
        cur.execute("SELECT caption, manual_caption, faces FROM njz_segments WHERE id = %s", (seg_id,))
        row = cur.fetchone()
        if not row:
            continue
        old_auto_cap = row[0] or ""
        old_manual_cap = row[1] or ""
        old_faces = row[2] or "[]"
        old_final_cap = old_manual_cap.strip() if old_manual_cap.strip() else old_auto_cap
        if isinstance(old_faces, str):
            try:
                old_faces = json.loads(old_faces)
            except:
                old_faces = []
        old_caps.append(old_final_cap)
        old_faces_list.append(old_faces)
        new_emb = search_model.encode(new_caption)
        new_emb_str = str(new_emb.tolist())
        if new_members:
            new_faces = json.dumps([{"member": m} for m in new_members])
            cur.execute("UPDATE njz_segments SET manual_caption=%s, embedding=%s, faces=%s WHERE id=%s",
                        (new_caption, new_emb_str, new_faces, seg_id))
        else:
            cur.execute("UPDATE njz_segments SET manual_caption=%s, embedding=%s WHERE id=%s",
                        (new_caption, new_emb_str, seg_id))
    hist_sql = """
    INSERT INTO njz_segment_operations_history 
    (operation_type, segment_ids_before, segment_ids_after, old_captions, new_captions, old_faces, new_faces, created_by)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
    """
    new_faces_val = json.dumps([{"member": m} for m in new_members]) if new_members else json.dumps([])
    cur.execute(hist_sql, (
        "group_update",
        json.dumps(segment_ids),
        json.dumps(segment_ids),
        json.dumps(old_caps),
        json.dumps([new_caption] * len(segment_ids)),
        json.dumps(old_faces_list),
        json.dumps(json.loads(new_faces_val)),
        "local_user"
    ))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"success": True, "message": "그룹 수정이 완료되었습니다."})
