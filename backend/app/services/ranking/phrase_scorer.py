import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models.models import Phrase, VideoPhrase, Video, Channel, PhraseScore
from backend.app.services.logging.logger import sys_logger

MARKETING_BLOCKLIST = {
    "gewinnspiel", "gratis", "rabatt", "link", "beschreibung", "abo", "kanal",
    "video", "hallo", "freunde", "kommentar", "social", "media", "link in der",
    "abonnieren", "glocke", "danke", "unterstützen", "werbung"
}


class PhraseScorerService:
    def __init__(self, formula_version: str = "1.0.0"):
        self.formula_version = formula_version

    def aggregate_phrase_statistics(self, db: Session, phrase_text: str) -> Dict[str, Any]:
        """
        Aggregates stats for a phrase across the database (unique channels, unique videos,
        total frequency, average recency, average subscribers of channels).
        """
        now = datetime.datetime.utcnow()

        vps = db.query(VideoPhrase).filter(VideoPhrase.phrase == phrase_text).all()
        if not vps:
            return {
                "frequency": 0,
                "unique_videos": 0,
                "unique_channels": 0,
                "average_recency": 0.0,
                "average_subscribers": 0.0,
                "title_occurrences": 0,
                "first_seen": now,
                "last_seen": now
            }

        total_frequency = sum(vp.count for vp in vps)
        video_ids = list(set(vp.video_id for vp in vps))
        channel_ids = list(set(vp.channel_id for vp in vps if vp.channel_id))

        unique_videos_count = len(video_ids)
        unique_channels_count = len(channel_ids)

        title_occurrences = sum(1 for vp in vps if vp.source and "title" in vp.source)

        first_seen = min(vp.first_seen for vp in vps)
        last_seen = max(vp.last_seen for vp in vps)

        # Average Recency (average age of videos in days)
        videos = db.query(Video).filter(Video.video_id.in_(video_ids)).all()
        if videos:
            total_age_days = sum(max(1, (now - v.published_at).days) for v in videos)
            average_recency = total_age_days / len(videos)
        else:
            average_recency = 0.0

        # Average Subscribers
        channels = db.query(Channel).filter(Channel.channel_id.in_(channel_ids)).all()
        if channels:
            total_subs = sum(c.subscribers or 0 for c in channels)
            average_subscribers = total_subs / len(channels)
        else:
            average_subscribers = 0.0

        return {
            "frequency": total_frequency,
            "unique_videos": unique_videos_count,
            "unique_channels": unique_channels_count,
            "average_recency": average_recency,
            "average_subscribers": average_subscribers,
            "title_occurrences": title_occurrences,
            "first_seen": first_seen,
            "last_seen": last_seen
        }

    def compute_quality_score(self, phrase_text: str, stats: Dict[str, Any]) -> float:
        """
        Computes the configurable, versioned quality score for a phrase.
        Returns a score between 0.0 and 1.0 (or higher).
        """
        if self.formula_version == "1.0.0":
            score = 0.0

            unique_channels = stats["unique_channels"]
            title_occurrences = stats["title_occurrences"]
            first_seen = stats["first_seen"]
            last_seen = stats["last_seen"]
            average_recency = stats["average_recency"]
            frequency = stats["frequency"]

            # 1. Independent Channels distribution (Positive)
            if unique_channels > 1:
                score += min(4.0, unique_channels * 0.8)
            else:
                score += 0.2

            # 2. Appears in titles (Positive)
            if title_occurrences > 0:
                score += min(2.5, title_occurrences * 0.6)

            # 3. Consistency over time (Positive)
            span_days = (last_seen - first_seen).days
            if span_days > 7:
                score += min(1.5, span_days * 0.05)

            # 4. Recent uploads (Positive)
            if average_recency > 0:
                if average_recency < 30:
                    score += 2.0
                elif average_recency < 90:
                    score += 1.0
                elif average_recency > 180:
                    score -= 1.0  # Old usage penalty (Negative)

            # 5. Non-trading / Marketing language (Negative)
            has_marketing = any(word in phrase_text.lower() for word in MARKETING_BLOCKLIST)
            if has_marketing:
                score -= 3.0

            # 6. Dominated by single creator (Negative)
            if unique_channels == 1 and frequency > 3:
                score -= 1.5

            # Normalize final score safely to 0.0 - 1.0
            final_score = max(0.0, min(1.0, score / 10.0))
            return round(final_score, 4)

        return 0.1

    def aggregate_and_score_all_phrases(self, db: Session) -> int:
        """
        Updates statistics and quality scores for all phrases in the DB,
        saving the scoring history for version tracking.
        """
        phrases = db.query(Phrase).all()
        count = 0

        for p in phrases:
            stats = self.aggregate_phrase_statistics(db, p.phrase)

            # Update aggregated stats on Phrase
            p.frequency = stats["frequency"]
            p.unique_videos = stats["unique_videos"]
            p.unique_channels = stats["unique_channels"]
            p.average_recency = stats["average_recency"]
            p.average_subscribers = stats["average_subscribers"]
            p.last_seen = stats["last_seen"]

            # Compute quality score
            score = self.compute_quality_score(p.phrase, stats)

            # Save previous score history to PhraseScore
            historical_score = PhraseScore(
                phrase=p.phrase,
                score=score,
                version=self.formula_version
            )
            db.add(historical_score)

            p.quality_score = score
            count += 1

        db.commit()
        sys_logger.info(f"Aggregated and scored {count} phrases in DB using version '{self.formula_version}'.")
        return count
