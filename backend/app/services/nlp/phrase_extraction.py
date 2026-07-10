import re
import datetime
from typing import List, Dict, Any, Optional, Tuple, Set
from sqlalchemy.orm import Session

from backend.app.models.models import Video, Channel, Phrase, VideoPhrase, PhraseRelationship
from backend.app.services.nlp.nlp_pipeline import GermanNLPPipeline
from backend.app.services.logging.logger import sys_logger


TOPIC_KEYWORDS = {
    "Futures": ["futures", "kontrakte", "future-kontrakte", "micro futures", "fnd"],
    "Forex": ["forex", "devisen", "währungen", "eurusd", "fx", "pips"],
    "Crypto": ["crypto", "krypto", "bitcoin", "ethereum", "btc", "eth", "altcoin", "solana"],
    "Indices": ["dax", "nasdaq", "dow", "s&p", "indizes", "sp500", "ndx"],
    "Commodities": ["commodities", "rohstoffe", "gold", "silber", "öl", "crude oil", "wti"],
    "Options": ["optionen", "options", "stillhalter", "calls", "puts", "leaps"],
    "General trading": ["trading", "daytrading", "aktien", "börse", "depot", "finanzen", "chartanalyse", "investieren"]
}


class PhraseExtractionService:
    def __init__(self):
        self.pipeline = GermanNLPPipeline()

    def classify_topic(self, text: str) -> str:
        """
        Classifies the dominant topic based on simple keyword matches.
        Topics: Futures, Forex, Crypto, Indices, Commodities, Options, General trading.
        """
        if not text:
            return "General trading"

        text_lower = text.lower()
        topic_scores = {topic: 0 for topic in TOPIC_KEYWORDS}

        for topic, keywords in TOPIC_KEYWORDS.items():
            for kw in keywords:
                # Word-boundary or exact pattern matches
                pattern = rf"\b{re.escape(kw)}\b"
                matches = re.findall(pattern, text_lower)
                topic_scores[topic] += len(matches)

        best_topic, max_score = max(topic_scores.items(), key=lambda x: x[1])
        if max_score == 0:
            return "General trading"
        return best_topic

    def extract_and_store_phrases(self, db: Session, video_id: str, transcript_text: Optional[str] = None) -> List[str]:
        """
        Extracts phrases from Title, Description, and Transcript, classifies topics,
        updates model fields, stores Phrase and VideoPhrase records, and records relationships.
        """
        video = db.query(Video).filter(Video.video_id == video_id).first()
        if not video:
            sys_logger.error(f"Video {video_id} not found for phrase extraction.")
            return []

        now = datetime.datetime.utcnow()

        # 1. Topic Classification
        combined_all_text = f"{video.title} {video.description or ''}"
        if transcript_text:
            combined_all_text += f" {transcript_text}"

        video_topic = self.classify_topic(combined_all_text)
        video.topic = video_topic
        db.commit()

        # Update Channel topic based on the channel's video topics if applicable
        channel = db.query(Channel).filter(Channel.channel_id == video.channel_id).first()
        if channel:
            channel.topic = video_topic
            db.commit()

        # 2. Extract Candidate Phrases using NLP pipeline
        # Process Title
        title_res = self.pipeline.process_text(video.title)
        # Process Description
        desc_res = self.pipeline.process_text(video.description or "")
        # Process Transcript
        trans_res = self.pipeline.process_text(transcript_text or "")

        # Collect phrase candidates & map to their source
        phrase_source_map: Dict[str, Set[str]] = {}
        phrase_freq_map: Dict[str, int] = {}

        # Add title phrases (both noun phrases and ngrams)
        for ph in title_res["noun_phrases"] + title_res["ngrams"]:
            ph = ph.strip()
            if ph:
                phrase_source_map.setdefault(ph, set()).add("title")
                phrase_freq_map[ph] = phrase_freq_map.get(ph, 0) + 1

        # Add description phrases
        for ph in desc_res["noun_phrases"] + desc_res["ngrams"]:
            ph = ph.strip()
            if ph:
                phrase_source_map.setdefault(ph, set()).add("description")
                phrase_freq_map[ph] = phrase_freq_map.get(ph, 0) + 1

        # Add transcript phrases
        for ph in trans_res["noun_phrases"] + trans_res["ngrams"]:
            ph = ph.strip()
            if ph:
                phrase_source_map.setdefault(ph, set()).add("transcript")
                phrase_freq_map[ph] = phrase_freq_map.get(ph, 0) + 1

        # Filter out phrases that are purely stop words or single letters
        extracted_phrases = []
        for phrase_text, sources in phrase_source_map.items():
            if len(phrase_text) < 3:
                continue

            # Ensure we have Phrase table record
            existing_phrase = db.query(Phrase).filter(Phrase.phrase == phrase_text).first()
            if not existing_phrase:
                existing_phrase = Phrase(
                    phrase=phrase_text,
                    language="de",
                    frequency=0,
                    unique_videos=0,
                    unique_channels=0,
                    first_seen=now,
                    last_seen=now
                )
                db.add(existing_phrase)
                db.flush()

            # Record / Update VideoPhrase
            source_str = ",".join(sorted(list(sources)))
            freq = phrase_freq_map[phrase_text]

            existing_vp = db.query(VideoPhrase).filter(
                VideoPhrase.video_id == video_id,
                VideoPhrase.phrase == phrase_text
            ).first()

            if not existing_vp:
                new_vp = VideoPhrase(
                    video_id=video_id,
                    phrase=phrase_text,
                    count=freq,
                    channel_id=video.channel_id,
                    source=source_str,
                    first_seen=now,
                    last_seen=now
                )
                db.add(new_vp)
            else:
                # Update existing
                existing_vp.count += freq
                current_sources = set(existing_vp.source.split(",")) if existing_vp.source else set()
                current_sources.update(sources)
                existing_vp.source = ",".join(sorted(list(current_sources)))
                existing_vp.last_seen = now

            extracted_phrases.append(phrase_text)

        db.commit()

        # 3. Store Phrase Relationships (Co-occurrence inside this video)
        self._record_co_occurrences(db, extracted_phrases[:30])

        sys_logger.info(f"Extracted and stored {len(extracted_phrases)} phrases for Video {video_id}.")
        return extracted_phrases

    def _record_co_occurrences(self, db: Session, phrases: List[str]):
        """Records co-occurrence relationships between phrases in a video."""
        if len(phrases) < 2:
            return

        now = datetime.datetime.utcnow()
        pairs_added = 0

        for i in range(len(phrases)):
            for j in range(i + 1, len(phrases)):
                p1, p2 = phrases[i], phrases[j]
                p_a, p_b = (p1, p2) if p1 < p2 else (p2, p1)

                existing_rel = db.query(PhraseRelationship).filter(
                    PhraseRelationship.phrase_a == p_a,
                    PhraseRelationship.phrase_b == p_b,
                    PhraseRelationship.relationship_type == "co_occurrence"
                ).first()

                if not existing_rel:
                    rel = PhraseRelationship(
                        phrase_a=p_a,
                        phrase_b=p_b,
                        relationship_type="co_occurrence",
                        strength=1.0,
                        created_at=now,
                        updated_at=now
                    )
                    db.add(rel)
                else:
                    existing_rel.strength += 1.0
                    existing_rel.updated_at = now

                pairs_added += 1
                if pairs_added >= 100:
                    break
            if pairs_added >= 100:
                break

        db.commit()
