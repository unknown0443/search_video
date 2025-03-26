import json
import re
import numpy as np
import psycopg2
from flask import Flask, send_from_directory, request, jsonify
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from flask import send_file
import requests
import os

app = Flask(__name__, static_folder="static")

def get_db_connection():
    return psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="1234",  # 실제 비밀번호
        host="localhost",
        port="5432"
    )

# SBERT 임베딩 모델 (검색용)
search_model = SentenceTransformer("bongsoo/kpf-sbert-128d-v1")

# Gemini API 설정
genai.configure(api_key="AIzaSyA0K7zgOVeUIlH2TGABbP-s-0lgLKKkrv8")

@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/video")
def serve_video():
    # 파일 경로를 절대 경로로 지정해도 됩니다.
    return send_file("FuJ1RiLoq-M.mp4", mimetype="video/mp4")

@app.route("/gif/<gif_filename>")
def serve_gif(gif_filename):
    gif_path = os.path.join("gif", gif_filename)
    return send_file(gif_path, mimetype="image/gif")

@app.route("/video_player")
def serve_video_player():
    start_time = request.args.get("t", default="0")
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>Video Player</title>
    </head>
    <body>
      <video id="myVideo" width="640" height="360" controls autoplay>
        <source src="/video" type="video/mp4">
      </video>
      <script>
        const startTime = {start_time};
        const video = document.getElementById('myVideo');
        video.addEventListener('loadedmetadata', () => {{
          video.currentTime = startTime;
        }});
      </script>
    </body>
    </html>
    """

@app.route("/slack/interactions", methods=["POST"])
def slack_interactions():
    payload_str = request.form.get("payload")
    payload = json.loads(payload_str)

    # 1) 이벤트 종류 확인
    if payload["type"] == "block_actions":
        action = payload["actions"][0]
        if action["action_id"] == "modify_click":
            segment_id = action["value"]   # 예: "141"
            trigger_id = payload["trigger_id"]

            # 2) 모달 열기
            open_modal_view = {
                "trigger_id": trigger_id,
                "view": {
                    "type": "modal",
                    "callback_id": "modify_modal_submit",
                    "private_metadata": segment_id,  # 모달 제출 시 세그먼트 ID를 전달하기 위해 저장
                    "title": {
                        "type": "plain_text",
                        "text": "자막 수정"
                    },
                    "blocks": [
                        {
                            "type": "input",
                            "block_id": "caption_input_block",
                            "element": {
                                "type": "plain_text_input",
                                "action_id": "caption_input",
                                "placeholder": {
                                    "type": "plain_text",
                                    "text": "새 자막을 입력하세요"
                                }
                            },
                            "label": {
                                "type": "plain_text",
                                "text": "자막"
                            }
                        }
                    ],
                    "submit": {
                        "type": "plain_text",
                        "text": "완료"
                    }
                }
            }

            # Slack API 호출 (views.open)
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                # 아래에 사용자님이 주신 Bot User OAuth Token을 그대로 사용
                "Authorization": "Bearer xoxb-8644784457382-8644972662886-XGU55oyDL8QFxD9gNczJDMXO"
            }
            response = requests.post(
                "https://slack.com/api/views.open",
                headers=headers,
                data=json.dumps(open_modal_view)
            )

            # 디버깅용: API 응답을 확인해보세요
            print("views.open response:", response.json())

            # 3) Slack은 200 OK 응답을 바로 받아야 함
            return "", 200

    # 4) 모달 제출(view_submission) 처리
    if payload["type"] == "view_submission" and payload["view"]["callback_id"] == "modify_modal_submit":
        segment_id = payload["view"]["private_metadata"]
        new_caption = payload["view"]["state"]["values"]["caption_input_block"]["caption_input"]["value"]

    try:
        seg_id = int(segment_id)
        # 수정된 자막에 대해 임베딩 재계산
        new_emb = search_model.encode(new_caption)
        new_emb_str = str(new_emb.tolist())
        
        conn = get_db_connection()
        cur = conn.cursor()
        update_sql = """
        UPDATE njz_segments
        SET manual_caption = %s,
            embedding = %s
        WHERE id = %s
        """
        cur.execute(update_sql, (new_caption, new_emb_str, seg_id))
        conn.commit()
        cur.close()
        conn.close()
        print(f"세그먼트 {seg_id} 자막 수정 완료")
    except Exception as e:
        print("DB 업데이트 에러:", e)
    
    # 제출 후 모달을 닫는 응답 반환
    return jsonify({"response_action": "clear"}), 200


@app.route("/slack/playvideo", methods=["POST"])
def slack_video():
    user_text = request.form.get("text", "").strip()

    # 수정 명령인 경우: "수정: 세그먼트ID=xx 내용=..."
    if user_text.startswith("수정:"):
        override_pattern = r'^수정:\s*세그먼트ID=(\d+)\s*내용=(.*)'
        match = re.match(override_pattern, user_text)
        if match:
            seg_id_str = match.group(1)
            override_text = match.group(2).strip()
            try:
                seg_id = int(seg_id_str)
            except ValueError:
                seg_id = None

            if not seg_id or not override_text:
                return jsonify({"response_type": "ephemeral", "text": "교정 명령 구문이 잘못되었습니다."})
            
            # 기존 수정 로직 실행 (DB 업데이트 등)
            new_emb = search_model.encode(override_text)
            new_emb_str = str(new_emb.tolist())
            conn = get_db_connection()
            cur = conn.cursor()
            update_sql = """
            UPDATE njz_segments
            SET manual_caption = %s,
                embedding = %s
            WHERE id = %s
            """
            cur.execute(update_sql, (override_text, new_emb_str, seg_id))
            conn.commit()
            cur.close()
            conn.close()

            return jsonify({
                "response_type": "in_channel",
                "text": f"세그먼트 {seg_id} 캡션이 수정되었습니다."
            })
        else:
            return jsonify({"response_type": "ephemeral", "text": "수정 명령 형식이 올바르지 않습니다."})
    
    else:
        # 수정 명령이 아니면, 기존 검색 로직을 사용
        user_emb = search_model.encode(user_text)
        user_emb_str = str(user_emb.tolist())
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
            for row in rows:
                seg_id = row[0]
                start_time = row[2]
                end_time = row[3]
                auto_cap = row[4] or ""
                manual_cap = row[5] or ""
                final_cap = manual_cap.strip() if manual_cap.strip() else auto_cap
                time_slot = f"{int(start_time)}-{int(end_time)} sec"

                # 세그먼트 정보 섹션 블록
                section_block = {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*세그먼트ID={seg_id}* (start={start_time})\n{time_slot}: \"{final_cap}\""
                    }
                }
                # 이미지 블록: 해당 세그먼트의 GIF 파일을 보여줌
                image_block = {
                    "type": "image",
                    "image_url": f"https://027e-58-72-151-123.ngrok-free.app/gif/output_segment_{seg_id}.gif",
                    "alt_text": f"세그먼트 {seg_id} GIF"
                }
                # 액션 블록: 영상 보러가기 및 수정하기 버튼
                actions_block = {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "영상 보러가기"},
                            "url": f"https://027e-58-72-151-123.ngrok-free.app/video_player?t={start_time}"
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "수정하기"},
                            "value": str(seg_id),
                            "action_id": "modify_click"
                        }
                    ]
                }
                blocks.extend([section_block, image_block, actions_block])
        
        slack_response = {
            "response_type": "in_channel",
            "blocks": blocks
        }
        return jsonify(slack_response)




@app.route("/chat", methods=["POST"])
def unified_chat():
    data = request.get_json()
    user_msg = data.get("message", "").strip()
    if not user_msg:
        return jsonify({"error": "No message provided"}), 400

    # 1) 교정 명령? ("수정: 세그먼트ID=xx 내용=...")
    override_pattern = r'^수정:\s*세그먼트ID=(\d+)\s*내용=(.*)'
    match = re.match(override_pattern, user_msg)
    if match:
        seg_id_str = match.group(1)
        override_text = match.group(2).strip()
        try:
            seg_id = int(seg_id_str)
        except ValueError:
            seg_id = None

        if not seg_id or not override_text:
            return jsonify({"response": "교정 명령 구문이 잘못되었습니다."})

        # NEW: 수정된 텍스트로 임베딩 재계산
        new_emb = search_model.encode(override_text)
        new_emb_str = str(new_emb.tolist())

        conn = get_db_connection()
        cur = conn.cursor()
        update_sql = """
        UPDATE njz_segments
        SET manual_caption = %s,
            embedding = %s
        WHERE id = %s
        """
        cur.execute(update_sql, (override_text, new_emb_str, seg_id))
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"response": f"세그먼트 {seg_id} 캡션이 수정되었습니다."})

    # 2) 교정 명령이 아니면 → DB 임베딩 검색 + Gemini 모델
    # distance와 무관하게 상위 3개를 모두 표시
    user_emb = search_model.encode(user_msg)
    user_emb_str = str(user_emb.tolist())

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

    if not rows:
        relevant_info = "DB에서 검색 결과가 없습니다.\n"
    else:
        relevant_info = ""
        for row in rows:
            seg_id = row[0]
            start_time = row[2]
            end_time = row[3]
            auto_cap = row[4] or ""
            manual_cap = row[5] or ""
            final_cap = manual_cap.strip() if manual_cap.strip() else auto_cap
            dist = row[7]

            time_slot = f"{int(start_time)}-{int(end_time)} sec"
            # 보기 좋게 여러 줄로 분리
            relevant_info += (
            f"[세그먼트ID={seg_id} start={start_time}]\n"
            f"{time_slot}: \"{final_cap}\"\n"
            f"(dist={dist:.2f}) [수정하기={seg_id}]\n\n"
            )
    from google.generativeai import GenerativeModel
    gemini_model = GenerativeModel("models/gemini-2.0-flash")

    # LLM에 강력 지시
    prompt = f"""
아래 내용(검색 결과)은 절대 삭제하거나 줄바꿈을 없애지 말고, 최종 답변에 그대로 포함시켜라:
{relevant_info}

사용자 입력: "{user_msg}"

주의: 세그먼트ID와 start=..., [수정하기=xx] 부분을 절대 제거하거나 변형하지 말 것.


간단한 요약을 가장먼저 말해주고 결과를 띄워주는데 줄넘김을 반드시 해주고 위 결과를 절대 지우지 말라.
내용에 띄누는 caption이 영어라면 한국어로 번역해서 알려 줘 번역은 영어뒤에 ()를 붙여서 한국어를 넣어 줘.
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

if __name__ == "__main__":
    app.run(debug=True)
