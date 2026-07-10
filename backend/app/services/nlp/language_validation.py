import re
from typing import Dict, Any, Optional
import spacy
from sqlalchemy.orm import Session

from backend.app.models.models import Video, Channel
from backend.app.services.logging.logger import sys_logger

_nlp_model = None

def get_nlp_model():
    global _nlp_model
    if _nlp_model is None:
        try:
            _nlp_model = spacy.load("de_core_news_lg")
        except Exception as e:
            sys_logger.warning(f"Failed to load de_core_news_lg, falling back to blank de: {e}")
            _nlp_model = spacy.blank("de")
    return _nlp_model


# Standard German and English stopwords/indicators for language scoring
GERMAN_INDICATORS = {
    "der", "die", "das", "und", "ist", "für", "mit", "von", "auf", "nicht", "ein", "eine",
    "zu", "in", "den", "dem", "im", "des", "es", "dass", "sind", "wir", "sie", "ich",
    "aber", "oder", "auch", "als", "an", "bei", "nach", "um", "vor", "durch", "über",
    "aus", "so", "wie", "nur", "noch", "was", "wenn", "da", "uns", "sich", "ihr", "ihre",
    "aktien", "depot", "dax", "krypto", "börse", "chart", "hebel", "dividenden"
}

ENGLISH_INDICATORS = {
    "the", "and", "of", "to", "in", "is", "you", "that", "it", "he", "was", "for", "on",
    "are", "as", "with", "his", "they", "i", "at", "be", "this", "have", "from", "or",
    "one", "had", "by", "word", "but", "not", "what", "all", "were", "we", "when", "your",
    "can", "there", "use", "an", "each", "which", "she", "do", "how", "stock", "portfolio",
    "crypto", "leverage", "dividends"
}


class LanguageValidationService:
    def validate_language(self, title: str, description: str, transcript_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Determines the dominant language and confidence score based on title, description, and transcript.
        Assigns confidence score from 0.0 to 1.0.
        """
        combined_text = f"{title or ''} {description or ''}"
        if transcript_text:
            combined_text += f" {transcript_text}"

        combined_text_clean = combined_text.strip()
        if not combined_text_clean:
            return {
                "detected_language": "un",
                "confidence_score": 0.0,
                "needs_manual_review": True
            }

        # Tokenize using spaCy
        nlp = get_nlp_model()
        doc = nlp(combined_text_clean[:20000])  # limit length for performance

        german_count = 0
        english_count = 0

        for token in doc:
            token_text = token.text.lower()
            if token_text in GERMAN_INDICATORS:
                german_count += 1
            elif token_text in ENGLISH_INDICATORS:
                english_count += 1

        # Check for special German characters (ä, ö, ü, ß)
        german_chars_match = re.findall(r"[äöüßÄÖÜ]", combined_text_clean)
        german_count += len(german_chars_match) * 2  # strong signal

        total_signal = german_count + english_count
        if total_signal == 0:
            # Fallback to simple word check
            words = re.findall(r"\b[a-zäöüß]+\b", combined_text_clean.lower())
            german_count = sum(1 for w in words if w in GERMAN_INDICATORS)
            english_count = sum(1 for w in words if w in ENGLISH_INDICATORS)
            total_signal = german_count + english_count

        if total_signal == 0:
            confidence = 0.0
            detected_lang = "un"
        else:
            confidence = german_count / total_signal
            detected_lang = "de" if confidence >= 0.50 else "en"

        # Mark uncertain cases for review (e.g. score between 0.15 and 0.55)
        needs_review = (0.15 <= confidence <= 0.55) or (detected_lang == "de" and confidence < 0.35) or detected_lang == "un"

        return {
            "detected_language": detected_lang,
            "confidence_score": round(confidence, 4),
            "needs_manual_review": needs_review
        }

    def process_and_update_video_language(self, db: Session, video_id: str, transcript_text: Optional[str] = None) -> bool:
        """
        Validates the language of a video, updates its language/confidence fields,
        and marks needs_manual_review on its parent channel if language detection is uncertain.
        """
        video = db.query(Video).filter(Video.video_id == video_id).first()
        if not video:
            sys_logger.error(f"Video {video_id} not found in database for language validation.")
            return False

        validation = self.validate_language(video.title, video.description, transcript_text)

        video.language = validation["detected_language"]
        video.language_confidence = validation["confidence_score"]
        db.commit()

        # If language is uncertain, mark parent channel for review
        channel = db.query(Channel).filter(Channel.channel_id == video.channel_id).first()
        if channel:
            # Keep previous manual review flags if true, otherwise set based on validation
            if validation["needs_manual_review"]:
                channel.needs_manual_review = True
                channel.is_german = (validation["detected_language"] == "de")
                channel.language_confidence = validation["confidence_score"]
                db.commit()

        sys_logger.info(f"Language validation completed for Video {video_id}: language={video.language}, confidence={video.language_confidence}")
        return True
