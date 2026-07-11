import time
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.app.config.settings import settings
from backend.app.services.logging.logger import sys_logger
from backend.app.database.session import SessionLocal
from backend.app.models.models import ApiQuotaLog


class YouTubeService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.YOUTUBE_API_KEY
        if not self.api_key or self.api_key == "mock_api_key_for_now":
            raise ValueError("YouTube API Key is missing or invalid. Set YOUTUBE_API_KEY in the configuration or environment.")
        self.base_url = "https://www.googleapis.com/youtube/v3"

    def _log_quota_usage(self, cost: int):
        """Log quota consumed and keep trace in the api_quota_logs table."""
        db = SessionLocal()
        try:
            today = datetime.utcnow().date()
            quota_log = db.query(ApiQuotaLog).filter(ApiQuotaLog.created_at >= datetime.combine(today, datetime.min.time())).first()
            if not quota_log:
                quota_log = ApiQuotaLog(
                    daily_quota_consumed=0,
                    remaining_quota_estimate=10000,
                    requests_made=0,
                    failed_requests=0
                )
                db.add(quota_log)

            quota_log.daily_quota_consumed += cost
            quota_log.remaining_quota_estimate = max(0, quota_log.remaining_quota_estimate - cost)
            quota_log.requests_made += 1
            db.commit()
            sys_logger.info(f"API Quota used: {cost}. Total today: {quota_log.daily_quota_consumed}. Remaining: {quota_log.remaining_quota_estimate}")
        except Exception as e:
            sys_logger.error(f"Failed to log API quota usage in DB: {e}")
            db.rollback()
        finally:
            db.close()

    def _log_failed_request(self):
        """Log failed requests for quota analytics."""
        db = SessionLocal()
        try:
            today = datetime.utcnow().date()
            quota_log = db.query(ApiQuotaLog).filter(ApiQuotaLog.created_at >= datetime.combine(today, datetime.min.time())).first()
            if not quota_log:
                quota_log = ApiQuotaLog(
                    daily_quota_consumed=0,
                    remaining_quota_estimate=10000,
                    requests_made=0,
                    failed_requests=0
                )
                db.add(quota_log)
            quota_log.requests_made += 1
            quota_log.failed_requests += 1
            db.commit()
        except Exception as e:
            sys_logger.error(f"Failed to log failed API request in DB: {e}")
            db.rollback()
        finally:
            db.close()

    def _make_request(self, endpoint: str, params: Dict[str, Any], cost: int, max_retries: int = 3) -> Dict[str, Any]:
        """Make YouTube v3 API request with retry backoff and quota tracking."""
        url = f"{self.base_url}/{endpoint}"
        params["key"] = self.api_key

        retry_delay = 1.0
        for attempt in range(max_retries):
            try:
                sys_logger.info(f"Calling YouTube API: {url} with params {params} (Attempt {attempt + 1})")
                response = requests.get(url, params=params, timeout=10)

                if response.status_code == 200:
                    self._log_quota_usage(cost)
                    return response.json()

                # Handle standard rate limits or quota exceeded
                if response.status_code == 403:
                    sys_logger.warning(f"YouTube API quota exceeded or forbidden: {response.text}")
                    break

                sys_logger.warning(f"YouTube API returned error status {response.status_code}: {response.text}")
            except Exception as e:
                sys_logger.error(f"Transient error occurred during YouTube API request: {e}")

            # Backoff before retrying
            time.sleep(retry_delay)
            retry_delay *= 2.0

        self._log_failed_request()
        raise Exception(f"Failed to fetch data from YouTube API after {max_retries} attempts.")

    def search_videos(self, query: str, max_results: int = 25, page_token: Optional[str] = None) -> Dict[str, Any]:
        """Search videos using YouTube API search.list (Cost: 100)."""
        cost = 100

        params = {
            "q": query,
            "part": "snippet",
            "type": "video",
            "maxResults": max_results,
            "relevanceLanguage": "de",
        }
        if page_token:
            params["pageToken"] = page_token

        return self._make_request("search", params, cost=cost)

    def get_channel_details(self, channel_id: str) -> Dict[str, Any]:
        """Get channel details via channels.list (Cost: 1)."""
        cost = 1

        params = {
            "id": channel_id,
            "part": "snippet,statistics,brandingSettings",
        }
        return self._make_request("channels", params, cost=cost)

    def get_video_details(self, video_id: str) -> Dict[str, Any]:
        """Get video details via videos.list (Cost: 1)."""
        cost = 1

        params = {
            "id": video_id,
            "part": "snippet,statistics,contentDetails",
        }
        return self._make_request("videos", params, cost=cost)
