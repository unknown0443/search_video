import os
import json
from googleapiclient.discovery import build
from datetime import datetime

# API 키 설정 (현재 작업 디렉토리 내 config.json 파일을 읽습니다)
with open("config.json", "r") as config_file:
    config = json.load(config_file)
    YOUTUBE_API_KEY = config["YOUTUBE_API_KEY"]

# 검색할 그룹 리스트 (각각 5개씩 영상 가져옴)
queries = ["레드벨벳", "뉴진스", "아이브", "엑소", "스트레이키즈"]

def search_youtube_videos(query, max_results=5):
    """
    Use the YouTube API to fetch video information for a given query.
    """
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
            continue

        video_id = item["id"]["videoId"]
        title = item["snippet"].get("title", "Unknown Title")
        channel_name = item["snippet"].get("channelTitle", "Unknown Channel")
        published_at = item["snippet"].get("publishedAt", None)
        description = item["snippet"].get("description", "")
        thumbnail_url = item["snippet"]["thumbnails"]["high"]["url"]

        if published_at:
            # Parse published_at and convert to ISO format with Z suffix (UTC)
            published_at_dt = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
            published_at_str = published_at_dt.isoformat() + "Z"
        else:
            published_at_str = datetime.now().isoformat() + "Z"

        video_list.append({
            "video_id": video_id,
            "title": title,
            "channel_name": channel_name,
            "published_at": published_at_str,
            "description": description,
            "thumbnail_url": thumbnail_url
        })

    return video_list

def save_videos_to_file(video_list, filename="youtube_videos.json"):
    """
    Save the fetched video information to a JSON file.
    """
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(video_list, f, indent=4, ensure_ascii=False)
    print(f"✅ {len(video_list)} videos saved to {filename}!")

if __name__ == "__main__":
    print("🚀 Starting YouTube video search...")

    all_videos = []  # 전체 검색 결과 저장
    for query in queries:
        print(f"🔍 Searching for '{query}'...")
        videos = search_youtube_videos(query, max_results=5)
        all_videos.extend(videos)

    save_videos_to_file(all_videos)
    print("🎉 YouTube video IDs have been saved!")
