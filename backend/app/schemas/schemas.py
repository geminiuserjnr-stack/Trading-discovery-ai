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
    discord_communities_count: int
    discord_coverage_percentage: float
    new_channels_today: int
    api_quota: int
    scheduler_status: str
    latest_discords: List[dict]


# Query Schemas
class QueryBase(BaseModel):
    query_text: str
    language: str = "de"
    status: str = "active"
    country: Optional[str] = None
    generation_source: Optional[str] = None


class QueryCreate(QueryBase):
    pass


class QueryResponse(QueryBase):
    id: UUID4
    search_count: int
    success_count: int
    duplicate_count: int
    phrase_count: int
    effectiveness_score: float
    channels_discovered: Optional[int] = 0
    discords_found: Optional[int] = 0
    success_rate: Optional[float] = 0.0
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

    # Trading Community Discovery fields
    investigation_status: Optional[str] = "pending"
    discord_status: Optional[str] = "none"
    discord_type: Optional[str] = "unknown"
    discord_source: Optional[str] = "unknown"
    confidence_score: Optional[float] = 0.0
    last_investigated: Optional[datetime] = None
    discord_url: Optional[str] = None


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



class DiscordLinkBase(BaseModel):
    channel_id: str
    invite_url: str
    source: Optional[str] = None
    verification_status: str = "pending"
    discord_type: str = "unknown"


class DiscordLinkCreate(DiscordLinkBase):
    pass


class DiscordLinkResponse(DiscordLinkBase):
    id: UUID4
    created_at: datetime
    verified_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ChannelInvestigationBase(BaseModel):
    channel_id: str
    status: str = "pending"
    sources_checked: Optional[str] = None
    discord_found: bool = False
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ChannelInvestigationCreate(ChannelInvestigationBase):
    pass


class ChannelInvestigationResponse(ChannelInvestigationBase):
    id: UUID4

    model_config = ConfigDict(from_attributes=True)
