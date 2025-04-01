# routes_segments.py
from flask import Blueprint, request, jsonify
import json

from config import search_model
from utils import get_db_connection

segments_bp = Blueprint('segments_bp', __name__)

@segments_bp.route("/segment/merge", methods=["POST"])
def merge_segment():
    data = request.get_json()
    seg_ids = data.get("segment_ids", [])
    new_caption = data.get("new_caption", "").strip()

    if not seg_ids:
        return jsonify({"response": "병합할 세그먼트 ID가 필요합니다."}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1) 병합할 세그먼트들 가져오기
        select_sql = """SELECT id, video_id, start_time, end_time, caption, faces
                        FROM njz_segments
                        WHERE id = ANY(%s)
                        ORDER BY start_time ASC"""
        cur.execute(select_sql, (seg_ids,))
        rows = cur.fetchall()
        if not rows:
            return jsonify({"response": "해당 세그먼트를 찾을 수 없습니다."}), 404

        video_id = rows[0][1]
        start_time_merged = rows[0][2]
        end_time_merged   = rows[-1][3]

        # old_captions, old_faces
        old_captions = []
        old_faces_list = []
        for r in rows:
            cap = r[4] or ""
            old_captions.append(cap)

            f = r[5] or "[]"
            if isinstance(f, str):
                try:
                    f = json.loads(f)
                except:
                    f = []
            old_faces_list.append(f)

        if not new_caption:
            new_caption = " ".join(old_captions)

        # 2) 기존 세그먼트 삭제
        delete_sql = "DELETE FROM njz_segments WHERE id = ANY(%s)"
        cur.execute(delete_sql, (seg_ids,))

        # 3) 새 세그먼트 INSERT
        new_emb = search_model.encode(new_caption)
        new_emb_str = str(new_emb.tolist())

        insert_sql = """
        INSERT INTO njz_segments
        (video_id, start_time, end_time, caption, manual_caption, embedding, faces)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """
        cur.execute(insert_sql, (
            video_id, 
            start_time_merged, 
            end_time_merged,
            new_caption, 
            new_caption, 
            new_emb_str, 
            "[]"
        ))
        new_id = cur.fetchone()[0]

        # 4) 히스토리 기록
        hist_sql = """
        INSERT INTO njz_segment_operations_history
        (operation_type, segment_ids_before, segment_ids_after,
         old_captions, new_captions, old_faces, new_faces, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(hist_sql, (
            "merge",
            json.dumps(seg_ids),
            json.dumps([new_id]),
            json.dumps(old_captions),
            json.dumps([new_caption]),
            json.dumps(old_faces_list),
            json.dumps([[]]),  # 새 faces가 빈 배열로 기록됨
            "local_user"
        ))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"response": f"병합 완료! 새 세그먼트 ID={new_id}"}), 200

    except Exception as e:
        print("병합 오류:", e)
        return jsonify({"response": f"세그먼트 병합 중 오류: {e}"}), 500


@segments_bp.route("/segment/split", methods=["POST"])
def split_segment():
    data = request.get_json()
    segment_id = data.get("segment_id")
    split_time = data.get("split_time")
    captions = data.get("captions", [])  # [caption_part1, caption_part2]

    if not segment_id or split_time is None or len(captions) != 2:
        return jsonify({"response": "필수 데이터가 부족합니다."}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1) 기존 세그먼트 가져오기
        select_sql = """SELECT video_id, start_time, end_time, caption, manual_caption, faces
                        FROM njz_segments WHERE id = %s"""
        cur.execute(select_sql, (segment_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"response": f"세그먼트 {segment_id}를 찾을 수 없습니다."}), 404

        video_id, old_start, old_end, old_caption, old_manual, old_faces = row

        if not (old_start < split_time < old_end):
            return jsonify({"response": "분할 시점이 기존 세그먼트 범위 안에 있어야 합니다."}), 400

        old_final_cap = old_manual.strip() if old_manual and old_manual.strip() else (old_caption or "")
        if not old_faces:
            old_faces = "[]"
        if isinstance(old_faces, str):
            try:
                old_faces = json.loads(old_faces)
            except:
                old_faces = []

        # 2) 기존 세그먼트 삭제
        delete_sql = "DELETE FROM njz_segments WHERE id = %s"
        cur.execute(delete_sql, (segment_id,))

        # 3) 분할된 세그먼트 A
        startA = old_start
        endA   = split_time
        capA   = captions[0].strip()
        embA   = search_model.encode(capA)
        embA_str = str(embA.tolist())

        insert_sql = """
        INSERT INTO njz_segments
        (video_id, start_time, end_time, caption, manual_caption, embedding, faces)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """
        cur.execute(insert_sql, (video_id, startA, endA, capA, capA, embA_str, "[]"))
        new_idA = cur.fetchone()[0]

        # 4) 분할된 세그먼트 B
        startB = split_time
        endB   = old_end
        capB   = captions[1].strip()
        embB   = search_model.encode(capB)
        embB_str = str(embB.tolist())

        cur.execute(insert_sql, (video_id, startB, endB, capB, capB, embB_str, "[]"))
        new_idB = cur.fetchone()[0]

        # 5) 히스토리 기록
        hist_sql = """
        INSERT INTO njz_segment_operations_history
        (operation_type, segment_ids_before, segment_ids_after,
         old_captions, new_captions, old_faces, new_faces, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(hist_sql, (
            "split",
            json.dumps([segment_id]),
            json.dumps([new_idA, new_idB]),
            json.dumps([old_final_cap]),
            json.dumps([capA, capB]),
            json.dumps([old_faces]),
            json.dumps([[], []]),
            "local_user"
        ))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"response": f"분할 완료! A={new_idA}, B={new_idB}"}), 200

    except Exception as e:
        print("분할 오류:", e)
        return jsonify({"response": f"세그먼트 분할 중 오류: {e}"}), 500


@segments_bp.route("/segment/create", methods=["POST"])
def create_segment():
    data = request.get_json()
    video_id = data.get("video_id")
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    caption = data.get("caption", "").strip()

    new_emb = search_model.encode(caption)
    new_emb_str = str(new_emb.tolist())

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1) 세그먼트 INSERT
        insert_sql = """
        INSERT INTO njz_segments
        (video_id, start_time, end_time, caption, manual_caption, embedding, faces)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """
        cur.execute(insert_sql, (video_id, start_time, end_time, caption, caption, new_emb_str, "[]"))
        new_id = cur.fetchone()[0]

        # 2) 히스토리 기록 (create)
        hist_sql = """
        INSERT INTO njz_segment_operations_history
        (operation_type, segment_ids_before, segment_ids_after,
         old_captions, new_captions, old_faces, new_faces, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(hist_sql, (
            "create",
            json.dumps([]),
            json.dumps([new_id]),
            json.dumps([]),
            json.dumps([caption]),
            json.dumps([]),
            json.dumps([]),
            "local_user"
        ))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"response": "세그먼트 생성 성공!"})
    except Exception as e:
        print("세그먼트 생성 오류:", e)
        return jsonify({"response": f"세그먼트 생성 중 오류가 발생했습니다: {e}"}), 500


@segments_bp.route("/segment/<int:seg_id>", methods=["GET"])
def get_segment(seg_id):
    conn = get_db_connection()
    cur = conn.cursor()
    sql = """
    SELECT caption, manual_caption, faces
    FROM njz_segments
    WHERE id = %s
    """
    cur.execute(sql, (seg_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return jsonify({"success": False, "message": "Segment not found"}), 404

    caption = row[0] or ""
    manual_caption = row[1] or ""
    faces = row[2] or []

    if isinstance(faces, str):
        try:
            faces = json.loads(faces)
        except:
            faces = []

    return jsonify({
        "success": True,
        "data": {
            "caption": caption,
            "manual_caption": manual_caption,
            "faces": faces
        }
    })


@segments_bp.route("/segment/<int:seg_id>/history", methods=["GET"])
def get_segment_history(seg_id):
    conn = get_db_connection()
    cur = conn.cursor()
    sql = """
    SELECT id, operation_type, old_captions, new_captions, old_faces, new_faces, created_at, created_by
    FROM njz_segment_operations_history
    WHERE segment_ids_before @> %s::jsonb OR segment_ids_after @> %s::jsonb
    ORDER BY created_at DESC
    """
    seg_str = json.dumps([seg_id])
    cur.execute(sql, (seg_str, seg_str))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    history_list = []
    for r in rows:
        history_list.append({
            "history_id": r[0],
            "operation_type": r[1],
            "old_captions": r[2],
            "new_captions": r[3],
            "old_faces": r[4],
            "new_faces": r[5],
            "created_at": str(r[6]),
            "created_by": r[7]
        })

    return jsonify({"success": True, "history": history_list})

@segments_bp.route("/segment/group_info", methods=["POST"])
def group_info():
    data = request.get_json()
    segment_ids = data.get("segment_ids", [])
    if not segment_ids:
        return jsonify({"success": False, "message": "No segment_ids provided"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    # 세그먼트 조회
    select_sql = """
    SELECT id, caption, manual_caption, faces
    FROM njz_segments
    WHERE id = ANY(%s)
    ORDER BY id
    """
    cur.execute(select_sql, (segment_ids,))
    rows = cur.fetchall()

    combined_caption = []
    combined_members = set()
    for row in rows:
        seg_id = row[0]
        auto_cap = row[1] or ""
        manual_cap = row[2] or ""
        faces_json = row[3] or "[]"
        if isinstance(faces_json, str):
            try:
                faces_json = json.loads(faces_json)
            except:
                faces_json = []

        # 최종 캡션은 manual_caption이 있으면 사용, 없으면 auto_cap
        final_cap = manual_cap.strip() if manual_cap.strip() else auto_cap
        combined_caption.append(final_cap)

        # 멤버 추출
        for f in faces_json:
            if "member" in f and f["member"]:
                combined_members.add(f["member"])

    cur.close()
    conn.close()

    # 캡션 병합: 단순히 줄바꿈이나 "/" 등으로 이어붙이거나, 첫 번째만 사용해도 됨
    # 여기서는 "/"로 결합 예시
    merged_caption = " / ".join(combined_caption)

    return jsonify({
        "success": True,
        "segment_ids": segment_ids,
        "combined_caption": merged_caption,
        "combined_members": list(combined_members),
    })
