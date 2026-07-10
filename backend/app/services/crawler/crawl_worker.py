import re
import datetime
from sqlalchemy.orm import Session
from typing import Optional

from backend.app.database.session import SessionLocal
from backend.app.models.models import Channel, Video, CrawlJob, CommunityLink, Query
from backend.app.services.youtube.youtube_service import YouTubeService
from backend.app.services.utils.parsers import evaluate_channel_quality, extract_community_links
from backend.app.services.logging.logger import sys_logger


def get_channel_refresh_interval_days(channel: Channel) -> int:
    """
    Returns the refresh interval in days based on channel status (Module 8).
    - Newly discovered: 0 days (refresh immediately)
    - Active & high quality: 1 day
    - Review needed / low relevance: 7 days
    - Others: 30 days
    """
    if not channel.last_crawled:
        return 0
    if channel.is_german and channel.is_trading and not channel.needs_manual_review:
        return 1
    if channel.needs_manual_review:
        return 7
    return 30


def schedule_channel_refreshes(db: Session) -> int:
    """
    Scans the existing channels, applies the Refresh Policy (Module 8),
    and enqueues necessary CrawlJobs for those due for a refresh.
    """
    now = datetime.datetime.utcnow()
    channels = db.query(Channel).filter(Channel.active == True).all()  # noqa: E712
    jobs_created = 0

    for chan in channels:
        interval_days = get_channel_refresh_interval_days(chan)
        due = False
        if not chan.last_crawled:
            due = True
        else:
            delta = now - chan.last_crawled
            if delta.days >= interval_days:
                due = True

        if due:
            # Check if there is already an active/pending job in the queue to avoid duplication (Module 7)
            existing_job = db.query(CrawlJob).filter(
                CrawlJob.channel_id == chan.channel_id,
                CrawlJob.status == "pending"
            ).first()

            if not existing_job:
                job = CrawlJob(
                    channel_id=chan.channel_id,
                    priority=5,  # refresh jobs have normal priority
                    reason="scheduled_refresh",
                    status="pending"
                )
                db.add(job)
                jobs_created += 1

    db.commit()
    sys_logger.info(f"Refresh Scheduler: Queued {jobs_created} channels for scheduled metadata refresh.")
    return jobs_created


def process_channel_crawl_job(db: Session, job: CrawlJob) -> bool:
    """
    Executes a queued CrawlJob for a specific channel ID (Module 10):
    1. Fetches detailed channel metadata and updates the DB.
    2. Fetches recent video uploads for that channel.
    3. Scans channel descriptions & video descriptions for community links and registers them.
    4. Evaluates Quality Flags for the channel.
    5. Marks the job complete.
    """
    if not job.channel_id:
        job.status = "failed"
        job.error_message = "No channel ID specified in job."
        db.commit()
        return False

    sys_logger.info(f"Starting crawl for Channel ID: {job.channel_id} (Reason: {job.reason})")

    yt_service = YouTubeService()
    now = datetime.datetime.utcnow()
    job.started_at = now

    try:
        # 1. Fetch detailed channel metadata (Module 6)
        channel_data = yt_service.get_channel_details(job.channel_id)
        items = channel_data.get("items", [])
        if not items:
            raise Exception("Channel details not found in YouTube Data API.")

        item = items[0]
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})

        title = snippet.get("title", "Unknown Channel")
        desc = snippet.get("description", "")
        subscribers = int(stats.get("subscriberCount", 0))
        video_count = int(stats.get("videoCount", 0))
        total_views = int(stats.get("viewCount", 0))
        country = snippet.get("country")
        custom_url = snippet.get("customUrl")

        # Safe birth date parse
        created_date_str = snippet.get("publishedAt")
        created_dt = None
        if created_date_str:
            try:
                if created_date_str.endswith("Z"):
                    created_date_str = created_date_str[:-1]
                created_dt = datetime.datetime.fromisoformat(created_date_str)
            except:
                pass

        thumbnails = snippet.get("thumbnails", {})
        avatar = thumbnails.get("default", {}).get("url")
        banner = thumbnails.get("high", {}).get("url")

        # 2. Fetch existing channel record or create new (Deduplication engine: Module 7)
        channel = db.query(Channel).filter(Channel.channel_id == job.channel_id).first()
        if not channel:
            channel = Channel(channel_id=job.channel_id, channel_name=title)
            db.add(channel)

        channel.channel_name = title
        channel.description = desc
        channel.subscribers = subscribers
        channel.upload_count = video_count
        channel.total_views = total_views
        channel.created_date = created_dt
        channel.country = country
        channel.custom_url = custom_url
        channel.avatar = avatar
        channel.banner = banner
        channel.last_crawled = now
        channel.last_seen = now

        # Evaluate quality flags & lightweight German estimation (Module 12, 13)
        quality = evaluate_channel_quality(title, desc, subscribers, video_count)
        channel.is_german = quality["is_german"]
        channel.language_confidence = quality["language_confidence"]
        channel.is_trading = quality["is_trading"]
        channel.has_recent_uploads = quality["has_recent_uploads"]
        channel.needs_manual_review = quality["needs_manual_review"]
        channel.active = quality["active"]

        # Parse & store community links in channel description (Module 14)
        chan_links = extract_community_links(desc)
        for link in chan_links:
            # Check duplicate link to prevent pollution
            existing_link = db.query(CommunityLink).filter(
                CommunityLink.channel_id == channel.channel_id,
                CommunityLink.url == link["url"]
            ).first()
            if not existing_link:
                comm_link = CommunityLink(
                    channel_id=channel.channel_id,
                    platform=link["platform"],
                    url=link["url"],
                    detected_at=now
                )
                db.add(comm_link)

        if chan_links:
            channel.has_community_links = True

        # Ensure the main channel is flushed to database so foreign key checks on child videos succeed
        db.flush()

        # 3. Fetch recent uploads & store new videos (Module 5)
        # Search for channel's videos using relevanceLanguage
        search_videos_res = yt_service.search_videos(query=f"channel_id:{job.channel_id}", max_results=5)
        video_items = search_videos_res.get("items", [])

        new_vids_added = 0
        for vid_item in video_items:
            vid_id = vid_item.get("id", {}).get("videoId")
            if not vid_id:
                continue

            vid_snippet = vid_item.get("snippet", {})
            vid_title = vid_snippet.get("title", "")
            vid_desc = vid_snippet.get("description", "")

            # Safe publish date
            pub_date_str = vid_snippet.get("publishedAt")
            pub_dt = now
            if pub_date_str:
                try:
                    if pub_date_str.endswith("Z"):
                        pub_date_str = pub_date_str[:-1]
                    pub_dt = datetime.datetime.fromisoformat(pub_date_str)
                except:
                    pass

            # Safe Channel ID extraction for the video item
            v_channel_id = vid_snippet.get("channelId", job.channel_id)

            # Ensure the channel exists to satisfy foreign key constraints
            if v_channel_id != job.channel_id:
                chan_exists = db.query(Channel).filter(Channel.channel_id == v_channel_id).first()
                if not chan_exists:
                    placeholder_chan = Channel(
                        channel_id=v_channel_id,
                        channel_name=vid_snippet.get("channelTitle", "Placeholder Channel"),
                        active=True
                    )
                    db.add(placeholder_chan)
                    db.flush()

            # Deduplication Check (Module 7): Skip if exists, update stats if needed
            existing_vid = db.query(Video).filter(Video.video_id == vid_id).first()
            if not existing_vid:
                # Retrieve video stats & duration details from v3 API
                vid_details = yt_service.get_video_details(vid_id)
                details_items = vid_details.get("items", [])

                v_views, v_likes, v_comments = 0, 0, 0
                v_duration = 0
                v_thumb = None

                if details_items:
                    det = details_items[0]
                    det_stats = det.get("statistics", {})
                    det_content = det.get("contentDetails", {})

                    v_views = int(det_stats.get("viewCount", 0))
                    v_likes = int(det_stats.get("likeCount", 0))
                    v_comments = int(det_stats.get("commentCount", 0))

                    # Convert simple PT15M30S format (or keep 0 for simplicity)
                    v_duration_str = det_content.get("duration", "")
                    if "M" in v_duration_str:
                        # Fallback parsing
                        match = re.search(r"PT(\d+)M", v_duration_str)
                        if match:
                            v_duration = int(match.group(1)) * 60

                    v_thumbnails = det.get("snippet", {}).get("thumbnails", {})
                    v_thumb = v_thumbnails.get("high", {}).get("url")

                # Lightweight Video language confidence
                vid_text = f"{vid_title} {vid_desc}"
                vid_lang_conf = evaluate_channel_quality(vid_title, vid_desc, 0, 0)["language_confidence"]

                new_vid = Video(
                    video_id=vid_id,
                    channel_id=v_channel_id,
                    title=vid_title,
                    description=vid_desc,
                    published_at=pub_dt,
                    duration=v_duration,
                    view_count=v_views,
                    like_count=v_likes,
                    comment_count=v_comments,
                    processed=False,
                    thumbnail_url=v_thumb,
                    language_confidence=vid_lang_conf
                )
                db.add(new_vid)
                db.flush()
                new_vids_added += 1

                # Parse & store community links in video descriptions (Module 14)
                vid_links = extract_community_links(vid_desc)
                for lk in vid_links:
                    existing_lk = db.query(CommunityLink).filter(
                        CommunityLink.video_id == vid_id,
                        CommunityLink.url == lk["url"]
                    ).first()
                    if not existing_lk:
                        comm_lk = CommunityLink(
                            channel_id=v_channel_id,
                            video_id=vid_id,
                            platform=lk["platform"],
                            url=lk["url"],
                            detected_at=now
                        )
                        db.add(comm_lk)

        # Update metrics on job
        job.status = "completed"
        job.completed_at = datetime.datetime.utcnow()
        job.channels_found = 1
        job.videos_found = new_vids_added

        db.commit()
        sys_logger.info(f"Crawl worker successfully finished channel crawl for {job.channel_id}. Added {new_vids_added} new videos.")
        return True

    except Exception as e:
        sys_logger.error(f"Crawl worker failed processing job {job.id} for channel {job.channel_id}: {e}")
        db.rollback()

        # Exponential backoff/retry (Module 10)
        job.retry_count += 1
        if job.retry_count >= 3:
            job.status = "failed"
            job.error_message = f"Max retries exceeded. Last error: {e}"
        else:
            job.status = "pending"  # return back to pending
            job.error_message = f"Attempt {job.retry_count} failed: {e}"

        db.commit()
        return False
