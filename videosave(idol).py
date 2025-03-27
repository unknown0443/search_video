import os
import yt_dlp
import json

# ✅ 영상 다운로드 경로 설정 (현재 작업 디렉토리 내 "videos(idol)" 폴더)
DOWNLOAD_PATH = os.path.join(os.getcwd(), "videos(idol)")
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

def download_video(video_id):
    """
    Download a YouTube video using yt-dlp.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    file_path = os.path.join(DOWNLOAD_PATH, f"{video_id}.mp4")

    ydl_opts = {
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "outtmpl": file_path,
        "merge_output_format": "mp4",
        "quiet": False,
        "noplaylist": True,         # 재생목록 제외
        "socket_timeout": 10,        # 10초 타임아웃
        "retries": 3,                # 실패 시 3회 재시도
        "ignoreerrors": True,        # 오류 발생 시 무시
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # 파일 크기가 1MB 이하이면 다운로드 실패로 처리
        if os.path.exists(file_path) and os.path.getsize(file_path) < 1024 * 1024:
            os.remove(file_path)
            print(f"⚠️ {video_id}: File too small, removed (download failed).")
            return None

        print(f"✅ Download complete: {file_path}")
        return file_path

    except Exception as e:
        print(f"❌ Download failed ({video_id}): {str(e)}")
        return None

def download_all_videos():
    """
    Download videos based on a JSON file or a default list.
    """
    # 시도: "youtube_videos.json" 파일에서 영상 정보를 읽음
    if os.path.exists("youtube_videos.json"):
        with open("youtube_videos.json", "r", encoding="utf-8") as f:
            videos = json.load(f)
    else:
        print("youtube_videos.json not found. Using default video list.")
        videos = [{"video_id": "dQw4w9WgXcQ"}]  # 예시: Dummy video

    for video in videos:
        video_id = video.get("video_id")
        file_path = os.path.join(DOWNLOAD_PATH, f"{video_id}.mp4")

        # 이미 다운로드된 경우 건너뜀
        if os.path.exists(file_path):
            print(f"⏭️ Already downloaded: {file_path}")
            continue

        result = download_video(video_id)
        if result is None:
            print(f"⚠️ {video_id}: Download failed, skipping.")

if __name__ == "__main__":
    print("🚀 Starting YouTube video download...")
    download_all_videos()
    print("🎉 All downloads completed!")
