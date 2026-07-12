from typing import Dict, Any, List, Optional
from backend.app.services.youtube.youtube_service import YouTubeService
from backend.app.services.logging.logger import sys_logger

class YouTubeChannelDiscovery:
    def __init__(self, api_key: Optional[str] = None):
        self.yt_service = YouTubeService(api_key=api_key)

    def discover_channels(self, query: str, max_results: int = 25, page_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Search for channels related to a query. 
        Focuses on channel-level metadata rather than just videos.
        """
        sys_logger.info(f"Discovering channels for query: {query}")
        
        # 1. Search for channels directly (Cost: 100)
        params = {
            "q": query,
            "part": "snippet",
            "type": "channel",
            "maxResults": max_results,
            "relevanceLanguage": "de",
        }
        if page_token:
            params["pageToken"] = page_token
            
        search_results = self.yt_service._make_request("search", params, cost=100)
        
        # 2. Extract channel IDs
        items = search_results.get("items", [])
        channel_ids = [item.get("id", {}).get("channelId") for item in items if item.get("id", {}).get("channelId")]
        
        # 3. Enrich channel data (Cost: 1 per 50 channels)
        enriched_channels = []
        if channel_ids:
            channel_details = self.yt_service.get_channel_details(",".join(channel_ids))
            enriched_channels = channel_details.get("items", [])
            
        return {
            "channels": enriched_channels,
            "next_page_token": search_results.get("nextPageToken"),
            "total_results": search_results.get("pageInfo", {}).get("totalResults", 0)
        }

    def discover_channels_via_videos(self, query: str, max_results: int = 25) -> List[Dict[str, Any]]:
        """
        Fallback/Alternative: Search for videos and extract their channels.
        Useful when direct channel search is too broad.
        """
        sys_logger.info(f"Discovering channels via videos for query: {query}")
        video_results = self.yt_service.search_videos(query, max_results=max_results)
        
        items = video_results.get("items", [])
        channel_ids = list(set([item.get("snippet", {}).get("channelId") for item in items if item.get("snippet", {}).get("channelId")]))
        
        if not channel_ids:
            return []
            
        channel_details = self.yt_service.get_channel_details(",".join(channel_ids))
        return channel_details.get("items", [])
