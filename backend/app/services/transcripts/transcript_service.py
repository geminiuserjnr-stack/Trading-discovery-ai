import datetime
from typing import Optional
from sqlalchemy.orm import Session
from youtube_transcript_api import YouTubeTranscriptApi

from backend.app.models.models import Video, Transcript
from backend.app.services.logging.logger import sys_logger


class TranscriptService:
    def __init__(self):
        pass

    def get_and_cache_transcript(self, db: Session, video_id: str) -> Optional[Transcript]:
        """
        Retrieves transcript for a video, caches it in the transcripts table,
        and ensures no repeated downloads are attempted if it was already processed.
        """
        # 1. Check if already cached
        cached = db.query(Transcript).filter(Transcript.video_id == video_id).first()
        if cached:
            sys_logger.info(f"Transcript for video {video_id} found in cache.")
            return cached

        # 2. Check if we already attempted and failed
        video = db.query(Video).filter(Video.video_id == video_id).first()
        if video and video.transcript_attempted:
            sys_logger.info(f"Transcript for video {video_id} was already attempted and is not available. Skipping.")
            return None

        sys_logger.info(f"Retrieving transcript for video {video_id}...")

        text = None
        language = "de"
        source = "api"

        try:
            # Attempt to fetch real transcript (preferring German)
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=["de", "en"])
            text = " ".join([entry["text"] for entry in transcript_list])
            # Guess language from api list
            try:
                transcript_metadata = YouTubeTranscriptApi.list_transcripts(video_id)
                german_transcripts = [t for t in transcript_metadata if t.language_code == "de"]
                if german_transcripts:
                    language = "de"
                    source = "manual" if german_transcripts[0].is_manual else "generated"
                else:
                    active_t = transcript_metadata.find_transcript(["de", "en"])
                    language = active_t.language_code
                    source = "manual" if active_t.is_manual else "generated"
            except Exception as meta_err:
                sys_logger.warning(f"Could not retrieve transcript metadata details: {meta_err}")
                language = "de"  # Default fallback
                source = "api"
        except Exception as e:
            sys_logger.warning(f"Failed to retrieve transcript from YouTube API for video {video_id}: {e}")

        if text:
            # Save to database cache
            transcript_record = Transcript(
                video_id=video_id,
                language=language,
                text=text,
                source=source,
                retrieved_at=datetime.datetime.utcnow()
            )
            db.add(transcript_record)

            if video:
                video.transcript_available = True
                video.transcript_attempted = True
                video.language = language
            db.commit()
            db.refresh(transcript_record)
            sys_logger.info(f"Successfully retrieved and cached transcript for video {video_id}.")
            return transcript_record
        else:
            if video:
                video.transcript_available = False
                video.transcript_attempted = True
            db.commit()
            sys_logger.info(f"Recorded that transcript is not available for video {video_id}.")
            return None
