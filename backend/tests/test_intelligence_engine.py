import pytest
import datetime
from datetime import timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.config.settings import settings
from backend.app.database.base import Base
from backend.app.models.models import Channel, Video, Query, Phrase, VideoPhrase, PhraseScore, PhraseRelationship, QueryHistory
from backend.app.services.transcripts.transcript_service import TranscriptService
from backend.app.services.nlp.language_validation import LanguageValidationService
from backend.app.services.nlp.nlp_pipeline import GermanNLPPipeline
from backend.app.services.nlp.phrase_extraction import PhraseExtractionService
from backend.app.services.ranking.phrase_scorer import PhraseScorerService
from backend.app.services.generator.query_generator import QueryGeneratorService
from backend.app.services.crawler.learning_loop import LearningLoopOrchestrator

engine = create_engine(settings.DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


from backend.app.models.models import Transcript, CommunityLink, CrawlJob

@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    # Clear tables in dependency order
    db.query(CommunityLink).delete()
    db.query(CrawlJob).delete()
    db.query(Transcript).delete()
    db.query(PhraseRelationship).delete()
    db.query(PhraseScore).delete()
    db.query(VideoPhrase).delete()
    db.query(Phrase).delete()
    db.query(QueryHistory).delete()
    db.query(Query).delete()
    db.query(Video).delete()
    db.query(Channel).delete()
    db.commit()
    yield db
    db.close()


def test_transcript_service_caching_and_fallback(clean_db):
    # Insert mock channel and video
    channel = Channel(channel_id="chan_id_123", channel_name="Test Channel", active=True)
    video = Video(
        video_id="mock_vid_test_1",
        channel_id="chan_id_123",
        title="Trading DAX",
        description="Daytrading",
        published_at=datetime.datetime.utcnow(),
        processed=False
    )
    clean_db.add(channel)
    clean_db.add(video)
    clean_db.commit()

    service = TranscriptService(is_mock_mode=True)

    # 1. Retrieve first time (should generate and cache mock transcript)
    transcript_record = service.get_and_cache_transcript(clean_db, "mock_vid_test_1")
    assert transcript_record is not None
    assert transcript_record.video_id == "mock_vid_test_1"
    assert "Daytrading" in transcript_record.text or "Heute" in transcript_record.text
    assert transcript_record.source == "mock"

    # Refresh Video from DB
    clean_db.refresh(video)
    assert video.transcript_available is True
    assert video.transcript_attempted is True

    # 2. Retrieve again (should hit cache)
    cached_record = service.get_and_cache_transcript(clean_db, "mock_vid_test_1")
    assert cached_record.retrieved_at == transcript_record.retrieved_at

    # 3. Retrieve non-existent transcript (no mock ID, and not mock mode)
    # Turn off mock mode
    service_strict = TranscriptService(is_mock_mode=False)
    video_no_trans = Video(
        video_id="real_no_transcript_id_999",
        channel_id="chan_id_123",
        title="Unrelated Video",
        description="No transcript",
        published_at=datetime.datetime.utcnow(),
        processed=False
    )
    clean_db.add(video_no_trans)
    clean_db.commit()

    res = service_strict.get_and_cache_transcript(clean_db, "real_no_transcript_id_999")
    assert res is None

    # Check that transcript_attempted is recorded to avoid repeated downloads
    clean_db.refresh(video_no_trans)
    assert video_no_trans.transcript_attempted is True
    assert video_no_trans.transcript_available is False


def test_language_validation(clean_db):
    service = LanguageValidationService()

    # German text
    res_de = service.validate_language(
        title="Daytrading lernen mit Hebel und Chartanalyse",
        description="Wir zeigen euch wie ihr am deutschen Aktien Markt investiert."
    )
    assert res_de["detected_language"] == "de"
    assert res_de["confidence_score"] > 0.40
    assert res_de["needs_manual_review"] is False

    # English text
    res_en = service.validate_language(
        title="Learn Daytrading and forex strategy with stocks",
        description="In this video we talk about standard options portfolio and investment."
    )
    assert res_en["detected_language"] == "en"

    # Uncertain case with mixed terms
    res_mixed = service.validate_language(
        title="Trading setup",
        description="Brief text de."
    )
    assert res_mixed["needs_manual_review"] is True


def test_german_nlp_pipeline_token_preservation():
    pipeline = GermanNLPPipeline()

    # Test html/url/emoji removal
    dirty_text = "<b>Lerne Trading</b> heute! 🚀 Link: https://example.com/join"
    cleaned = pipeline.clean_text(dirty_text)
    assert "🚀" not in cleaned
    assert "https" not in cleaned
    assert "<b>" not in cleaned

    # Test processing & acronym preservation
    text = "Heute besprechen wir Live den DAX und Trading mit BTC, Hebel und Optionen."
    res = pipeline.process_text(text)

    # Trading acronyms should be preserved in uppercase form
    assert "DAX" in res["tokens"]
    assert "BTC" in res["tokens"]

    # N-grams (2-5 words)
    assert len(res["ngrams"]) > 0
    # Any ngram should be space-separated tokens
    assert any(len(ng.split()) >= 2 for ng in res["ngrams"])


def test_phrase_extraction_and_topic_classification(clean_db):
    # Insert video/channel
    channel = Channel(channel_id="chan_1", channel_name="Crypto Pro", active=True)
    video = Video(
        video_id="vid_1",
        channel_id="chan_1",
        title="Bitcoin live Analyse und Krypto Daytrading",
        description="Bitcoin chartanalyse auf Deutsch. Wir traden live.",
        published_at=datetime.datetime.utcnow(),
        processed=False
    )
    clean_db.add(channel)
    clean_db.add(video)
    clean_db.commit()

    service = PhraseExtractionService()

    # Topic Classification check
    assert service.classify_topic("Bitcoin ethereum altcoins") == "Crypto"
    assert service.classify_topic("DAX Nasdaq s&p500 index") == "Indices"

    # Extraction and storing check
    phrases = service.extract_and_store_phrases(clean_db, "vid_1", "Tritt unserer BTC community bei.")
    assert len(phrases) > 0

    # Verify that VideoPhrase and Phrase records are inserted in DB
    db_phrase = clean_db.query(Phrase).filter(Phrase.phrase == "bitcoin live").first()
    if not db_phrase:
        db_phrase = clean_db.query(Phrase).first()
    assert db_phrase is not None

    db_vp = clean_db.query(VideoPhrase).filter(VideoPhrase.video_id == "vid_1").all()
    assert len(db_vp) > 0
    assert any(vp.phrase == db_phrase.phrase for vp in db_vp)

    # Relationships check (at least some co-occurrences recorded)
    relationships = clean_db.query(PhraseRelationship).all()
    assert len(relationships) > 0
    assert relationships[0].relationship_type == "co_occurrence"


def test_phrase_aggregation_and_scoring_versioning(clean_db):
    # Setup data
    channel = Channel(channel_id="c_1", channel_name="Daytrader", subscribers=10000)
    video = Video(
        video_id="v_1",
        channel_id="c_1",
        title="Daytrading Live",
        description="DAX",
        published_at=datetime.datetime.utcnow() - timedelta(days=10),
        processed=True
    )
    clean_db.add(channel)
    clean_db.add(video)
    clean_db.commit()

    vp = VideoPhrase(
        video_id="v_1",
        phrase="dax trading",
        count=3,
        channel_id="c_1",
        source="title,description",
        first_seen=datetime.datetime.utcnow() - timedelta(days=10),
        last_seen=datetime.datetime.utcnow()
    )
    phrase = Phrase(phrase="dax trading", language="de", frequency=0, quality_score=0.0)
    clean_db.add(vp)
    clean_db.add(phrase)
    clean_db.commit()

    scorer = PhraseScorerService(formula_version="1.0.0")

    # 1. Test aggregation stats
    stats = scorer.aggregate_phrase_statistics(clean_db, "dax trading")
    assert stats["frequency"] == 3
    assert stats["unique_channels"] == 1
    assert stats["unique_videos"] == 1
    assert stats["average_subscribers"] == 10000.0

    # 2. Test score calculation
    score = scorer.compute_quality_score("dax trading", stats)
    assert 0.0 <= score <= 1.0

    # 3. Test running across DB with version scoring history
    scorer.aggregate_and_score_all_phrases(clean_db)

    # Verify Phrase table is updated
    updated_phrase = clean_db.query(Phrase).filter(Phrase.phrase == "dax trading").first()
    assert updated_phrase.quality_score > 0.0
    assert updated_phrase.average_subscribers == 10000.0

    # Verify PhraseScore table has the versioned historical record
    history = clean_db.query(PhraseScore).filter(PhraseScore.phrase == "dax trading").all()
    assert len(history) == 1
    assert history[0].version == "1.0.0"
    assert history[0].score == updated_phrase.quality_score


def test_query_generation_and_evaluation(clean_db):
    # Seed high-quality phrases
    p = Phrase(
        phrase="daytrading dax",
        language="de",
        quality_score=0.85, # very high quality
        frequency=10,
        unique_channels=3
    )
    clean_db.add(p)
    clean_db.commit()

    generator = QueryGeneratorService(quality_threshold=0.5)

    # 1. Generate candidate queries
    new_queries = generator.generate_candidate_queries(clean_db)
    assert "daytrading dax" in new_queries

    # Verify Query database insertion
    q = clean_db.query(Query).filter(Query.query_text == "daytrading dax").first()
    assert q is not None
    assert q.parent_phrase == "daytrading dax"
    assert q.confidence_score == 0.85

    # 2. Add performance history and evaluate
    hist = QueryHistory(
        query_id=q.id,
        results_count=10,
        new_channels_count=0,  # 0 new channels discovered -> bad performance!
        new_videos_count=2
    )
    clean_db.add(hist)
    # Add a second search with 0 new channels
    hist2 = QueryHistory(
        query_id=q.id,
        results_count=10,
        new_channels_count=0,
        new_videos_count=1
    )
    clean_db.add(hist2)
    clean_db.commit()

    generator.evaluate_query_performance(clean_db)

    # Refresh and check modified modifier
    clean_db.refresh(q)
    assert q.new_channels_discovered == 0
    assert q.duplicate_rate > 0.0
    assert q.priority_modifier < 1.0  # priority decayed!


def test_complete_learning_loop(clean_db):
    # Setup seed queries
    q = Query(query_text="krypto trading deutsch", language="de", status="active")
    clean_db.add(q)
    clean_db.commit()

    orchestrator = LearningLoopOrchestrator(quality_threshold=0.2)

    # Run the continuous cycle
    result = orchestrator.run_complete_learning_cycle(clean_db)

    assert result is not None
    # We should have successfully executed a search, parsed findings, and generated query records
    assert result["videos_processed"] > 0
    assert result["phrases_extracted"] > 0
    assert result["queries_generated"] >= 0
