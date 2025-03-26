import os
import json
import sys
import django
from googleapiclient.discovery import build
from datetime import datetime
from django.utils.timezone import make_aware

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

# ✅ API 키 설정
with open("config.json", "r") as config_file:
    config = json.load(config_file)
    YOUTUBE_API_KEY = config["YOUTUBE_API_KEY"]

# ✅ 검색할 그룹 리스트 (각각 5개씩 영상 가져옴)
queries = ["레드벨벳", "뉴진스", "아이브", "엑소", "스트레이키즈"]

def search_youtube_videos(query, max_results=5):
    """YouTube API를 사용하여 특정 검색어(query)와 관련된 영상 정보 가져오기"""
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    request = youtube.search().list(
        q=query,
        part="snippet",
        type="video",
        maxResults=max_results
    )
    response = request.execute()

    video_list = []
    for item in response["items"]:
        if "videoId" not in item["id"]:
            continue  # ✅ videoId가 없는 항목 필터링

        video_id = item["id"]["videoId"]
        title = item["snippet"].get("title", "Unknown Title")
        channel_name = item["snippet"].get("channelTitle", "Unknown Channel")
        published_at = item["snippet"].get("publishedAt", None)
        description = item["snippet"].get("description", "")
        thumbnail_url = item["snippet"]["thumbnails"]["high"]["url"]

        # ✅ "published_at"이 없을 경우 기본값 설정
        if published_at:
            published_at_dt = make_aware(datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ"))
        else:
            published_at_dt = make_aware(datetime.now())  # 현재 시간으로 기본값 설정

        video_list.append({
            "video_id": video_id,
            "title": title,
            "channel_name": channel_name,
            "published_at": published_at_dt,
            "description": description,
            "thumbnail_url": thumbnail_url
        })

    return video_list

def save_videos_to_db(video_list):
    """검색된 영상 정보를 데이터베이스에 저장"""
    for video in video_list:
        YouTubeVideo.objects.update_or_create(
            video_id=video["video_id"],
            defaults={
                "title": video["title"],
                "channel_name": video["channel_name"],
                "published_at": video["published_at"],
                "description": video["description"],
                "thumbnail_url": video["thumbnail_url"],
                "views": 0,  
                "likes": 0,  
                "comments": 0  
            }
        )
    print(f"✅ {len(video_list)}개의 영상이 데이터베이스에 저장되었습니다!")

if __name__ == "__main__":
    print("🚀 YouTube 영상 검색 시작...")

    all_videos = []  # ✅ 전체 결과 저장
    for query in queries:
        print(f"🔍 '{query}' 검색 중...")
        videos = search_youtube_videos(query, max_results=5)
        all_videos.extend(videos)

    save_videos_to_db(all_videos)
    print("🎉 YouTube 영상 ID 저장 완료!")
