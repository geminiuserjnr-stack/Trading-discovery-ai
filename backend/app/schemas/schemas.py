from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, UUID4, ConfigDict


# Health Schema
class HealthResponse(BaseModel):
    status: str
    database: str
    redis: str
    celery: str
    api_quota_remaining: int


# Stats Schema
class StatsResponse(BaseModel):
    total_channels: int
    total_videos: int
    german_channels: int
    processed_videos: int
    extracted_phrases: int
    generated_queries: int
    duplicate_rate: float
    success_rate: float
    api_quota: int
    scheduler_status: str
    latest_discoveries: List[dict]


# Query Schemas
class QueryBase(BaseModel):
    query_text: str
    language: str = "de"
    status: str = "active"


class QueryCreate(QueryBase):
    pass


class QueryResponse(QueryBase):
    id: UUID4
    search_count: int
    success_count: int
    duplicate_count: int
    phrase_count: int
    effectiveness_score: float
    last_executed: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Channel Schemas
class ChannelBase(BaseModel):
    channel_id: str
    channel_name: str
    description: Optional[str] = None
    subscribers: int = 0
    country: Optional[str] = None
    detected_language: Optional[str] = None
    created_date: Optional[datetime] = None
    upload_count: int = 0
    total_views: int = 0
    avatar: Optional[str] = None
    banner: Optional[str] = None
    custom_url: Optional[str] = None
    last_crawled: Optional[datetime] = None
    discovery_query: Optional[str] = None
    active: bool = True


class ChannelCreate(ChannelBase):
    pass


class ChannelResponse(ChannelBase):
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Video Schemas
class VideoBase(BaseModel):
    video_id: str
    channel_id: str
    title: str
    description: Optional[str] = None
    published_at: datetime
    duration: int = 0
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    language: Optional[str] = None
    processed: bool = False
    transcript_available: bool = False
    last_processed: Optional[datetime] = None


class VideoCreate(VideoBase):
    pass


class VideoResponse(VideoBase):
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Phrase Schemas
class PhraseBase(BaseModel):
    phrase: str
    language: str = "de"
    frequency: int = 1
    unique_channels: int = 1
    unique_videos: int = 1
    quality_score: float = 0.0
    first_seen: datetime
    last_seen: datetime


class PhraseCreate(PhraseBase):
    pass


class PhraseResponse(PhraseBase):
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Action Request / Response Schemas
class CrawlRequest(BaseModel):
    channel_id: Optional[str] = None
    query_text: Optional[str] = None
    max_results: Optional[int] = None


class CrawlResponse(BaseModel):
    status: str
    message: str
    job_id: str


class SearchRequest(BaseModel):
    query_text: str
    max_results: Optional[int] = None


class SearchResponse(BaseModel):
    status: str
    message: str
    results_found: int


class ActionRunResponse(BaseModel):
    status: str
    message: str
