import datetime
from sqlalchemy.orm import Session

from backend.app.models.models import Video, CrawlJob
from backend.app.services.crawler.search_scheduler import execute_next_search
from backend.app.services.crawler.crawl_worker import process_channel_crawl_job
from backend.app.services.transcripts.transcript_service import TranscriptService
from backend.app.services.nlp.language_validation import LanguageValidationService
from backend.app.services.nlp.phrase_extraction import PhraseExtractionService
from backend.app.services.ranking.phrase_scorer import PhraseScorerService
from backend.app.services.generator.query_generator import QueryGeneratorService
from backend.app.services.logging.logger import sys_logger


class LearningLoopOrchestrator:
    def __init__(self, formula_version: str = "1.0.0", quality_threshold: float = 0.4):
        self.transcript_service = TranscriptService()
        self.language_service = LanguageValidationService()
        self.phrase_service = PhraseExtractionService()
        self.scorer_service = PhraseScorerService(formula_version=formula_version)
        self.query_generator = QueryGeneratorService(quality_threshold=quality_threshold)

    def run_complete_learning_cycle(self, db: Session) -> dict:
        """
        Executes the autonomous continuous feedback loop (Module 9):
        1. Search & Discover (execute_next_search)
        2. Process any pending channel crawl jobs to gather videos
        3. Retrieve transcripts for newly found videos
        4. Validate language (title, description, transcript)
        5. Extract candidate phrases and relationships for German content
        6. Aggregate phrase stats & score phrases
        7. Generate new candidate search queries from high-quality phrases
        8. Evaluate query performance metrics
        """
        sys_logger.info("Starting complete autonomous feedback learning cycle...")
        summary = {
            "search_result": None,
            "crawl_jobs_processed": 0,
            "videos_processed": 0,
            "transcripts_retrieved": 0,
            "phrases_extracted": 0,
            "queries_generated": 0,
            "queries_evaluated": 0,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }

        # Step 1: Execute next search (Search & Discover)
        search_res = execute_next_search(db)
        summary["search_result"] = search_res

        # Step 2: Process a batch of pending channel crawls to populate videos
        pending_jobs = db.query(CrawlJob).filter(CrawlJob.status == "pending").order_by(
            CrawlJob.priority.desc()
        ).limit(3).all()

        for job in pending_jobs:
            job.status = "running"
            db.commit()
            success = process_channel_crawl_job(db, job)
            if success:
                summary["crawl_jobs_processed"] += 1

        # Step 3: Process unprocessed videos
        unprocessed_videos = db.query(Video).filter(Video.processed == False).limit(10).all()  # noqa: E712

        for video in unprocessed_videos:
            sys_logger.info(f"Processing Video ID: {video.video_id} in learning cycle.")

            # Retrieve transcript (with caching and non-re-attempt policies)
            transcript_record = self.transcript_service.get_and_cache_transcript(db, video.video_id)
            transcript_text = transcript_record.text if transcript_record else None
            if transcript_record:
                summary["transcripts_retrieved"] += 1

            # Language validation
            validation = self.language_service.validate_language(
                title=video.title,
                description=video.description,
                transcript_text=transcript_text
            )

            # Update video language/confidence
            video.language = validation["detected_language"]
            video.language_confidence = validation["confidence_score"]
            video.transcript_available = (transcript_record is not None)
            video.transcript_attempted = True
            db.commit()

            # If German, process German NLP pipeline and extract phrases
            if validation["detected_language"] == "de":
                phrases = self.phrase_service.extract_and_store_phrases(db, video.video_id, transcript_text)
                summary["phrases_extracted"] += len(phrases)

            # Mark video as fully processed
            video.processed = True
            video.last_processed = datetime.datetime.utcnow()
            db.commit()
            summary["videos_processed"] += 1

        # Step 4: Phrase Aggregation & Scoring
        scored_count = self.scorer_service.aggregate_and_score_all_phrases(db)

        # Step 5: Query Generation
        new_queries = self.query_generator.generate_candidate_queries(db)
        summary["queries_generated"] = len(new_queries)

        # Step 6: Query Evaluation
        evaluated_count = self.query_generator.evaluate_query_performance(db)
        summary["queries_evaluated"] = evaluated_count

        sys_logger.info(f"Complete autonomous feedback learning cycle finished. Summary: {summary}")
        return summary
