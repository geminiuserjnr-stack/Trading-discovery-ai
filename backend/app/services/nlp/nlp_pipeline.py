import re
from typing import List, Dict, Any, Set
import spacy

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


TRADING_ACRONYMS: Set[str] = {
    "DAX", "BTC", "ETH", "VWAP", "EMA", "SMA", "CFD", "ETF", "RSI", "MACD",
    "NASDAQ", "DOW", "S&P", "FOREX", "BULL", "BEAR", "SEC", "FED", "USD", "EUR"
}


class GermanNLPPipeline:
    def __init__(self):
        self.nlp = get_nlp_model()

    def clean_text(self, text: str) -> str:
        """
        Cleans the input text by:
        1. Normalizing spacing
        2. Removing HTML tags
        3. Removing URLs
        4. Removing Emojis
        """
        if not text:
            return ""

        # Remove HTML
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"&[a-zA-Z0-9#]+;", " ", text)

        # Remove URLs
        text = re.sub(r"https?://\S+|www\.\S+", " ", text)

        # Remove Emojis and other non-BMP characters
        text = re.sub(r"[\U00010000-\U0010ffff]", " ", text)

        # Normalize spaces
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def process_text(self, text: str) -> Dict[str, Any]:
        """
        Processes German text through the NLP pipeline:
        - Cleans text
        - Tokenizes & Lemmatizes (preserving trading acronyms)
        - Removes German stop words
        - Extracts noun phrases
        - Builds n-grams (2-5 words)
        """
        cleaned_text = self.clean_text(text)
        if not cleaned_text:
            return {
                "tokens": [],
                "noun_phrases": [],
                "ngrams": []
            }

        doc = self.nlp(cleaned_text)

        # 1. Tokenize & Lemmatize (preserving trading acronyms & removing stop words/punctuation)
        processed_tokens: List[str] = []
        for token in doc:
            # Check if token is a trading acronym (case-insensitive check but preserve case in output)
            upper_token = token.text.upper()
            if upper_token in TRADING_ACRONYMS:
                processed_tokens.append(upper_token)
                continue

            # Skip punctuation, stop words, whitespace, numbers, and URLs
            if token.is_punct or token.is_space or token.like_num or token.is_stop:
                continue

            # Lemmatize normal words
            lemma = token.lemma_.lower().strip()
            # If lemma is too short or empty, skip
            if len(lemma) > 1 and lemma.isalpha():
                processed_tokens.append(lemma)

        # 2. Extract Noun Phrases
        noun_phrases: List[str] = []
        if doc.noun_chunks:
            for chunk in doc.noun_chunks:
                chunk_text = chunk.text.strip()
                # Clean up noun phrase
                chunk_clean = " ".join([
                    t.text.upper() if t.text.upper() in TRADING_ACRONYMS else t.text.lower()
                    for t in chunk
                    if not t.is_stop and not t.is_punct and not t.is_space
                ]).strip()
                if len(chunk_clean) > 2:
                    noun_phrases.append(chunk_clean)

        # 3. Build N-grams (2 to 5 words)
        ngrams: List[str] = []
        for n in range(2, 6):
            for i in range(len(processed_tokens) - n + 1):
                ngram_slice = processed_tokens[i:i + n]
                ngram_str = " ".join(ngram_slice)
                ngrams.append(ngram_str)

        return {
            "tokens": processed_tokens,
            "noun_phrases": list(set(noun_phrases)),
            "ngrams": list(set(ngrams))
        }
