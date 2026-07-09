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
        self.is_mock_mode = (self.api_key == "mock_api_key_for_now" or not self.api_key)
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
        if self.is_mock_mode:
            self._log_quota_usage(cost)
            return {}

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

        if self.is_mock_mode:
            self._log_quota_usage(cost)
            return self._generate_mock_search_results(query, max_results, page_token)

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

        if self.is_mock_mode:
            self._log_quota_usage(cost)
            return self._generate_mock_channel_details(channel_id)

        params = {
            "id": channel_id,
            "part": "snippet,statistics,brandingSettings",
        }
        return self._make_request("channels", params, cost=cost)

    def get_video_details(self, video_id: str) -> Dict[str, Any]:
        """Get video details via videos.list (Cost: 1)."""
        cost = 1

        if self.is_mock_mode:
            self._log_quota_usage(cost)
            return self._generate_mock_video_details(video_id)

        params = {
            "id": video_id,
            "part": "snippet,statistics,contentDetails",
        }
        return self._make_request("videos", params, cost=cost)

    # Mock Generators for Local/Testing Mode
    def _generate_mock_search_results(self, query: str, max_results: int, page_token: Optional[str]) -> Dict[str, Any]:
        """Generates realistic mock search responses containing German trading terms/videos."""
        sys_logger.info(f"[MOCK MODE] Generating mock search results for query: '{query}'")

        # Consistent mock videos based on some German trading seeds
        mock_items = [
            {
                "id": {"videoId": "mock_vid_1"},
                "snippet": {
                    "title": "Trading lernen für Anfänger | Live DAX Analyse & Strategien",
                    "description": "Erfahre wie du mit dem DAX Trading startest. Lerne Chartanalyse und Risikomanagement für erfolgreiches Trading im deutschen Markt.",
                    "channelId": "mock_chan_1",
                    "channelTitle": "German Trader Elite",
                    "publishedAt": "2026-07-01T12:00:00Z"
                }
            },
            {
                "id": {"videoId": "mock_vid_2"},
                "snippet": {
                    "title": "Krypto Trading Strategie 2026 - So machst du Profite",
                    "description": "Bitcoin und Ethereum Chartanalyse auf Deutsch. Schließe dich unserer Telegram-Community unter t.me/cryptotradingde an!",
                    "channelId": "mock_chan_2",
                    "channelTitle": "Crypto Insider DE",
                    "publishedAt": "2026-07-02T15:30:00Z"
                }
            },
            {
                "id": {"videoId": "mock_vid_3"},
                "snippet": {
                    "title": "Aktien kaufen für Dividenden - Mein deutsches Depot Update",
                    "description": "Heute besprechen wir die besten deutschen Aktien für Dividenden-Investoren. Mehr auf patreon.com/aktiencommunity.",
                    "channelId": "mock_chan_3",
                    "channelTitle": "Aktien mit Kopf & Verstand",
                    "publishedAt": "2026-07-03T18:00:00Z"
                }
            }
        ]

        # Slice to max_results requested
        items = mock_items[:max_results]

        return {
            "kind": "youtube#searchListResponse",
            "nextPageToken": "mock_next_token_abc123" if not page_token else None,
            "items": items
        }

    def _generate_mock_channel_details(self, channel_id: str) -> Dict[str, Any]:
        """Generates realistic mock channel details based on ID."""
        sys_logger.info(f"[MOCK MODE] Generating mock channel details for: {channel_id}")

        names_map = {
            "mock_chan_1": "German Trader Elite",
            "mock_chan_2": "Crypto Insider DE",
            "mock_chan_3": "Aktien mit Kopf & Verstand"
        }
        desc_map = {
            "mock_chan_1": "Deutscher Kanal für Daytrading, Swingtrading und DAX Analysen. Tritt unserer Discord-Community bei: discord.gg/germantrader!",
            "mock_chan_2": "Krypto Analysen, Hebel-Trading und Altcoin News für den deutschsprachigen Raum.",
            "mock_chan_3": "Langfristiges Investieren in Aktien, ETFs und Dividenden-Werte. Besuche meine Webseite: https://aktien-mit-verstand.de"
        }

        name = names_map.get(channel_id, "Sample German Trading Channel")
        desc = desc_map.get(channel_id, "Ein Kanal über Finanzen und Börse in Deutschland.")

        return {
            "items": [
                {
                    "id": channel_id,
                    "snippet": {
                        "title": name,
                        "description": desc,
                        "publishedAt": "2021-01-10T14:22:18Z",
                        "country": "DE",
                        "thumbnails": {
                            "default": {"url": "https://example.com/avatar.jpg"},
                            "high": {"url": "https://example.com/banner.jpg"}
                        },
                        "customUrl": f"@{channel_id}"
                    },
                    "statistics": {
                        "subscriberCount": "25000",
                        "videoCount": "320",
                        "viewCount": "1250000"
                    }
                }
            ]
        }

    def _generate_mock_video_details(self, video_id: str) -> Dict[str, Any]:
        """Generates realistic mock video details based on ID."""
        sys_logger.info(f"[MOCK MODE] Generating mock video details for: {video_id}")

        titles_map = {
            "mock_vid_1": "Trading lernen für Anfänger | Live DAX Analyse & Strategien",
            "mock_vid_2": "Krypto Trading Strategie 2026 - So machst du Profite",
            "mock_vid_3": "Aktien kaufen für Dividenden - Mein deutsches Depot Update"
        }
        channel_map = {
            "mock_vid_1": "mock_chan_1",
            "mock_vid_2": "mock_chan_2",
            "mock_vid_3": "mock_chan_3"
        }

        title = titles_map.get(video_id, "Standard German Trading Video")
        channel_id = channel_map.get(video_id, "mock_chan_1")

        return {
            "items": [
                {
                    "id": video_id,
                    "snippet": {
                        "title": title,
                        "description": "Detaillierte Beschreibung des Videos mit nützlichen Links. Schließe dich unserem Skool-Netzwerk an: skool.com/tradingde",
                        "publishedAt": "2026-07-01T12:00:00Z",
                        "channelId": channel_id,
                        "thumbnails": {
                            "high": {"url": "https://example.com/thumbnail.jpg"}
                        }
                    },
                    "statistics": {
                        "viewCount": "4500",
                        "likeCount": "230",
                        "commentCount": "45"
                    },
                    "contentDetails": {
                        "duration": "PT15M30S"  # 15 mins 30 secs
                    }
                }
            ]
        }
