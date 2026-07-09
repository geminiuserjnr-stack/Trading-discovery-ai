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
    status = Column(String, default="active")  # active, exhausted, etc.
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


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


class VideoPhrase(Base):
    __tablename__ = "video_phrases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(String, ForeignKey("videos.video_id"), nullable=False)
    phrase = Column(String, ForeignKey("phrases.phrase"), nullable=False)
    count = Column(Integer, default=1)
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
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


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
