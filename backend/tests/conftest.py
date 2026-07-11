import os
import pytest
from sqlalchemy import create_engine
from unittest.mock import patch

# Set test database URL and YouTube Key before any other imports to override Pydantic Settings
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@127.0.0.1:5432/trading_discovery_test"
os.environ["YOUTUBE_API_KEY"] = "dummy_api_key_for_tests"

from backend.app.config.settings import settings
from backend.app.database.base import Base

class MockResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        return self._json_data


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    # Setup test database schema
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    # Optionally drop after session completes
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def mock_youtube_requests():
    """Autouse fixture to mock external Google/YouTube API network calls cleanly within tests directory."""
    def mock_get(url, params=None, timeout=None):
        if "search" in url:
            return MockResponse({
                "kind": "youtube#searchListResponse",
                "items": [
                    {
                        "id": {"videoId": "mock_vid_1"},
                        "snippet": {
                            "title": "Trading lernen für Anfänger | Live DAX Analyse & Strategien",
                            "description": "Erfahre wie du mit dem DAX Trading startest. Join Discord: discord.gg/germantrader",
                            "channelId": "mock_chan_1",
                            "channelTitle": "German Trader Elite",
                            "publishedAt": "2026-07-01T12:00:00Z"
                        }
                    }
                ]
            })
        elif "channels" in url:
            return MockResponse({
                "items": [
                    {
                        "id": params.get("id") if (params and "id" in params) else "mock_chan_1",
                        "snippet": {
                            "title": "German Trader Elite",
                            "description": "Daytrading und DAX Analysen. Join Discord: discord.gg/germantrader",
                            "publishedAt": "2021-01-10T14:22:18Z",
                            "country": "DE",
                            "thumbnails": {
                                "default": {"url": "https://example.com/avatar.jpg"},
                                "high": {"url": "https://example.com/banner.jpg"}
                            },
                            "customUrl": "@mock_chan_1"
                        },
                        "statistics": {
                            "subscriberCount": "25000",
                            "videoCount": "320",
                            "viewCount": "1250000"
                        }
                    }
                ]
            })
        elif "videos" in url:
            return MockResponse({
                "items": [
                    {
                        "id": params.get("id") if (params and "id" in params) else "mock_vid_1",
                        "snippet": {
                            "title": "Trading lernen für Anfänger | Live DAX Analyse & Strategien",
                            "description": "Detaillierte Beschreibung des Videos.",
                            "publishedAt": "2026-07-01T12:00:00Z",
                            "channelId": "mock_chan_1",
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
                            "duration": "PT15M30S"
                        }
                    }
                ]
            })
        return MockResponse({}, 404)

    with patch("backend.app.services.youtube.youtube_service.requests.get", side_effect=mock_get):
        yield
