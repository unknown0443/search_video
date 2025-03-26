import os
import sys
import django
import yt_dlp

# ✅ Django 환경 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
BACKEND_DIR = os.path.join(BASE_DIR, "backend")

sys.path.insert(0, BASE_DIR)
sys.path.insert(0, PROJECT_DIR)
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

# ✅ Django 모델 import
from ai_model.models import YouTubeVideo  

# ✅ 영상 다운로드 경로
DOWNLOAD_PATH = os.path.join(BASE_DIR, "videos(idol)")
os.makedirs(DOWNLOAD_PATH, exist_ok=True)


def download_video(video_id):
    """유튜브 영상 다운로드 (yt-dlp 사용)"""
    url = f"https://www.youtube.com/watch?v={video_id}"
    file_path = os.path.join(DOWNLOAD_PATH, f"{video_id}.mp4")

    ydl_opts = {
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "outtmpl": file_path,
        "merge_output_format": "mp4",
        "quiet": False,
        "noplaylist": True,  # ✅ 재생목록 방지
        "socket_timeout": 10,  # ✅ 10초 동안 응답 없으면 타임아웃
        "retries": 3,  # ✅ 실패 시 3번 재시도
        "ignoreerrors": True,  # ✅ 오류 발생해도 프로그램이 멈추지 않음
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # ✅ 다운로드된 파일이 너무 작은 경우 삭제 후 실패 처리
        if os.path.exists(file_path) and os.path.getsize(file_path) < 1024 * 1024:  # 1MB 이하일 경우
            os.remove(file_path)
            print(f"⚠️ {video_id}: 파일이 너무 작아 삭제됨! 다운로드 실패로 처리")
            return None

        print(f"✅ 다운로드 완료: {file_path}")
        return file_path

    except Exception as e:
        print(f"❌ 다운로드 실패 ({video_id}): {str(e)}")
        return None  # ✅ 실패 시 None 반환하여 무한 루프 방지


def download_all_videos():
    """DB에서 아직 다운로드되지 않은 영상만 가져와서 다운로드"""
    videos = YouTubeVideo.objects.all()

    for video in videos:
        file_path = os.path.join(DOWNLOAD_PATH, f"{video.video_id}.mp4")

        # ✅ 이미 다운로드된 파일 건너뛰기
        if os.path.exists(file_path):
            print(f"⏭️ 이미 다운로드됨: {file_path}")
            continue  # ✅ 다음 영상으로 넘어감

        # ✅ 다운로드 실행
        result = download_video(video.video_id)

        # ✅ 다운로드 실패한 경우 해당 영상 건너뛰기
        if result is None:
            print(f"⚠️ {video.video_id}: 다운로드 실패, 건너뜀.")
            continue  # ✅ 다음 영상으로 진행


if __name__ == "__main__":
    print("🚀 유튜브 영상 다운로드 시작...")
    download_all_videos()
    print("🎉 모든 다운로드 완료!")
