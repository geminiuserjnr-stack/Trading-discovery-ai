import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from backend.app.database.base import Base


class Query(Base):
    __tablename__ = "queries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_text = Column(String, nullable=False, unique=True)
    language = Column(String, default="de")
    search_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    duplicate_count = Column(Integer, default=0)
    phrase_count = Column(Integer, default=0)
    effectiveness_score = Column(Float, default=0.0)
    last_executed = Column(DateTime, nullable=True)
    status = Column(String, default="active")  # active, exhausted, paused
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Phase 1C Fields
    parent_phrase = Column(String, nullable=True)
    generation_time = Column(DateTime, nullable=True)
    confidence_score = Column(Float, nullable=True)
    new_channels_discovered = Column(Integer, default=0)
    new_videos_discovered = Column(Integer, default=0)
    duplicate_rate = Column(Float, default=0.0)
    new_phrases_discovered = Column(Integer, default=0)
    cost_per_new_channel = Column(Float, default=0.0)
    priority_modifier = Column(Float, default=1.0)


class Channel(Base):
    __tablename__ = "channels"

    channel_id = Column(String, primary_key=True)  # YouTube channel id is a unique string
    channel_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    subscribers = Column(Integer, default=0)
    country = Column(String, nullable=True)
    detected_language = Column(String, nullable=True)
    created_date = Column(DateTime, nullable=True)  # channel creation date
    upload_count = Column(Integer, default=0)
    total_views = Column(Integer, default=0)
    avatar = Column(String, nullable=True)
    banner = Column(String, nullable=True)
    custom_url = Column(String, nullable=True)
    last_crawled = Column(DateTime, nullable=True)
    discovery_query = Column(String, nullable=True)
    active = Column(Boolean, default=True)

    # Phase 1B Quality Flags & Metrics
    is_german = Column(Boolean, default=False)
    is_trading = Column(Boolean, default=False)
    has_recent_uploads = Column(Boolean, default=False)
    has_community_links = Column(Boolean, default=False)
    needs_manual_review = Column(Boolean, default=False)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    language_confidence = Column(Float, default=0.0)

    # Phase 1C Fields
    topic = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Video(Base):
    __tablename__ = "videos"

    video_id = Column(String, primary_key=True)  # YouTube video ID
    channel_id = Column(String, ForeignKey("channels.channel_id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=False)
    duration = Column(Integer, default=0)  # duration in seconds
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    language = Column(String, nullable=True)
    processed = Column(Boolean, default=False)
    transcript_available = Column(Boolean, default=False)
    last_processed = Column(DateTime, nullable=True)

    # Phase 1B Video Metadata Extensions
    thumbnail_url = Column(String, nullable=True)
    language_confidence = Column(Float, default=0.0)

    # Phase 1C Fields
    transcript_attempted = Column(Boolean, default=False, nullable=False)
    topic = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Transcript(Base):
    __tablename__ = "transcripts"

    video_id = Column(String, ForeignKey("videos.video_id"), primary_key=True)
    language = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    source = Column(String, nullable=True)  # generated, manual, api, scraper etc
    retrieved_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Phrase(Base):
    __tablename__ = "phrases"

    phrase = Column(String, primary_key=True)
    language = Column(String, default="de")
    frequency = Column(Integer, default=1)
    unique_channels = Column(Integer, default=1)
    unique_videos = Column(Integer, default=1)
    quality_score = Column(Float, default=0.0)
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Phase 1C Fields
    average_recency = Column(Float, default=0.0)
    average_subscribers = Column(Float, default=0.0)


class VideoPhrase(Base):
    __tablename__ = "video_phrases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(String, ForeignKey("videos.video_id"), nullable=False)
    phrase = Column(String, ForeignKey("phrases.phrase"), nullable=False)
    count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Phase 1C Fields
    channel_id = Column(String, nullable=True)
    source = Column(String, nullable=True)
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)


class PhraseScore(Base):
    __tablename__ = "phrase_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phrase = Column(String, ForeignKey("phrases.phrase"), nullable=False)
    score = Column(Float, default=0.0, nullable=False)
    version = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class PhraseRelationship(Base):
    __tablename__ = "phrase_relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phrase_a = Column(String, ForeignKey("phrases.phrase"), nullable=False)
    phrase_b = Column(String, ForeignKey("phrases.phrase"), nullable=False)
    relationship_type = Column(String, nullable=False)  # co_occurrence, same_channel, same_topic
    strength = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ChannelPhrase(Base):
    __tablename__ = "channel_phrases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(String, ForeignKey("channels.channel_id"), nullable=False)
    phrase = Column(String, ForeignKey("phrases.phrase"), nullable=False)
    co_occurrence_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String, default="pending")  # pending, running, completed, failed
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    channels_found = Column(Integer, default=0)
    videos_found = Column(Integer, default=0)
    transcripts_found = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    # Phase 1B Crawl Job Queue Fields
    channel_id = Column(String, nullable=True)
    priority = Column(Integer, default=0)  # higher is higher priority
    reason = Column(String, nullable=True)  # new discovery, scheduled refresh, manual request
    retry_count = Column(Integer, default=0)
    created_time = Column(DateTime, default=datetime.utcnow, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SchedulerJob(Base):
    __tablename__ = "scheduler_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_name = Column(String, nullable=False)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    status = Column(String, default="idle")  # idle, running, failed, success
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class LanguageStatistics(Base):
    __tablename__ = "language_statistics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    language = Column(String, nullable=False, unique=True)
    channel_count = Column(Integer, default=0)
    video_count = Column(Integer, default=0)
    phrase_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class QueryHistory(Base):
    __tablename__ = "query_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id = Column(UUID(as_uuid=True), ForeignKey("queries.id"), nullable=False)
    executed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    results_count = Column(Integer, default=0)
    new_channels_count = Column(Integer, default=0)
    new_videos_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level = Column(String, nullable=False)  # INFO, WARNING, ERROR etc
    message = Column(Text, nullable=False)
    module = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# Phase 1B New Tables

class SearchResult(Base):
    __tablename__ = "search_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id = Column(UUID(as_uuid=True), nullable=True)
    search_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    returned_video_ids = Column(Text, nullable=True)  # comma separated list or JSON string
    returned_channel_ids = Column(Text, nullable=True)  # comma separated list or JSON string
    next_page_token = Column(String, nullable=True)
    api_response_status = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ApiQuotaLog(Base):
    __tablename__ = "api_quota_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    log_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    daily_quota_consumed = Column(Integer, default=0)
    remaining_quota_estimate = Column(Integer, default=10000)
    requests_made = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class CommunityLink(Base):
    __tablename__ = "community_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(String, ForeignKey("channels.channel_id"), nullable=True)
    video_id = Column(String, ForeignKey("videos.video_id"), nullable=True)
    platform = Column(String, nullable=False)  # discord, telegram, skool, patreon, website
    url = Column(String, nullable=False)
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
