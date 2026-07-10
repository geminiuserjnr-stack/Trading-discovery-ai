import os
import sys
from backend.app.services.youtube.youtube_service import YouTubeService

def verify_live_api():
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key or api_key == "mock_api_key_for_now":
        print("[Error] No real YOUTUBE_API_KEY environment variable detected.")
        print("Please run this script with your real YouTube API key, for example:")
        print("YOUTUBE_API_KEY=AIzaSy... python backend/app/services/youtube/verify_live_api.py")
        sys.exit(1)

    print(f"Initializing YouTubeService with key: {api_key[:8]}...[REDACTED]")
    yt = YouTubeService(api_key=api_key)

    # Force mock mode to false
    yt.is_mock_mode = False

    print("\nRunning a LIVE search on YouTube Data API for query: 'aktien trading'...")
    try:
        results = yt.search_videos("aktien trading", max_results=3)
        items = results.get("items", [])

        if not items:
            print("No items returned from the YouTube API.")
            return

        print(f"\n[Success] Retrieved {len(items)} live results from YouTube Data API:")
        for idx, item in enumerate(items):
            snippet = item.get("snippet", {})
            video_id = item.get("id", {}).get("videoId")
            channel_title = snippet.get("channelTitle")
            title = snippet.get("title")
            print(f"\n{idx + 1}. Video Title: {title}")
            print(f"   Video ID: {video_id}")
            print(f"   Channel Title: {channel_title}")

    except Exception as e:
        print(f"\n[Failure] Live request to YouTube API failed: {e}")

if __name__ == "__main__":
    verify_live_api()
