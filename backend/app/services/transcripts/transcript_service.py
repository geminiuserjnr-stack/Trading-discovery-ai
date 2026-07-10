import datetime
from typing import Optional
from sqlalchemy.orm import Session
from youtube_transcript_api import YouTubeTranscriptApi

from backend.app.models.models import Video, Transcript
from backend.app.services.logging.logger import sys_logger


class TranscriptService:
    def __init__(self, is_mock_mode: bool = False):
        self.is_mock_mode = is_mock_mode

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

        # Check for mock video IDs or mock mode
        if self.is_mock_mode or video_id.startswith("mock_") or "mock" in video_id:
            text = self._generate_mock_transcript(video_id)
            source = "mock"
            language = "de"
        else:
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

    def _generate_mock_transcript(self, video_id: str) -> str:
        """Helper to generate mock trading transcripts in German."""
        mock_templates = {
            "mock_vid_1": (
                "Hallo liebe Trading Freunde! Heute schauen wir uns eine Live DAX Analyse an. "
                "Der DAX hat am Widerstand bei 16000 Punkten gedreht. Wir nutzen für den Einstieg "
                "eine klassische Daytrading Strategie mit Hebel. Wichtig ist das Risikomanagement. "
                "Zuerst bestimmen wir den Stop Loss unter dem letzten Verlaufstief. Wenn der Chart "
                "nach oben ausbricht, suchen wir ein Long Setup. Viel Erfolg beim Trading!"
            ),
            "mock_vid_2": (
                "Willkommen zurück beim Krypto Insider! Bitcoin konsolidiert gerade. "
                "In diesem Video zeige ich euch meine Hebel-Trading Strategie für Ethereum. "
                "Wir analysieren den 4-Stunden Chart und suchen nach Unterstützungen. "
                "Wenn ihr Lust auf Austausch habt, schaut in unsere Telegram-Community unter t.me/cryptotradingde vorbei! "
                "Denkt dran, Krypto Trading birgt hohe Risiken."
            ),
            "mock_vid_3": (
                "Hallo zusammen! Heute gibt es ein deutsches Depot Update. "
                "Wir besprechen die besten Dividenden Aktien für langfristigen Vermögensaufbau. "
                "Ich habe diesen Monat Allianz und BASF nachgekauft. "
                "Das Ziel ist ein passiver Cashflow durch Dividenden. "
                "Lest auch meinen neuen Blogbeitrag unter aktien-mit-verstand.de!"
            )
        }
        return mock_templates.get(
            video_id,
            "Heute lernen wir Daytrading an der Börse mit Hebel und Chartanalyse auf Deutsch für Anfänger."
        )
