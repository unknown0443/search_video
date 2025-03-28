# app.py
from flask import Flask, send_from_directory, send_file, request
import os

# Blueprint import
from routes_slack import slack_bp
from routes_chat import chat_bp
from routes_segments import segments_bp

app = Flask(__name__, static_folder="static")

@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/video")
def serve_video():
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

# Blueprint 등록
app.register_blueprint(slack_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(segments_bp)

if __name__ == "__main__":
    app.run(debug=True)
