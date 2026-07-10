import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.app.models.models import Phrase, Query, QueryHistory
from backend.app.services.logging.logger import sys_logger


class QueryGeneratorService:
    def __init__(self, quality_threshold: float = 0.4):
        self.quality_threshold = quality_threshold

    def generate_candidate_queries(self, db: Session) -> List[str]:
        """
        Generates search queries automatically from high-quality phrases.
        Avoids exact duplicates of existing queries.
        """
        # Fetch phrases with quality scores above the threshold
        high_quality_phrases = db.query(Phrase).filter(
            Phrase.quality_score >= self.quality_threshold
        ).order_by(Phrase.quality_score.desc()).limit(20).all()

        generated_queries = []
        now = datetime.datetime.utcnow()

        for p in high_quality_phrases:
            query_text = p.phrase.lower().strip()
            if not query_text or len(query_text) < 4:
                continue

            # Check if this query already exists
            existing_query = db.query(Query).filter(Query.query_text == query_text).first()
            if not existing_query:
                # Create a new candidate query from the high-quality phrase
                q = Query(
                    query_text=query_text,
                    language="de",
                    status="active",
                    parent_phrase=p.phrase,
                    generation_time=now,
                    confidence_score=p.quality_score,
                    priority_modifier=1.0
                )
                db.add(q)
                generated_queries.append(query_text)
                sys_logger.info(f"Automatically generated new query from phrase '{p.phrase}' (score={p.quality_score}).")

        if generated_queries:
            db.commit()

        sys_logger.info(f"Query Generation completed: Created {len(generated_queries)} new search queries.")
        return generated_queries

    def evaluate_query_performance(self, db: Session) -> int:
        """
        Evaluates the performance metrics for generated queries based on history.
        Decays the priority modifier of non-performing queries over time.
        """
        queries = db.query(Query).filter(Query.parent_phrase.isnot(None)).all()  # only check generated ones
        count = 0

        for q in queries:
            # Query history elements
            histories = db.query(QueryHistory).filter(QueryHistory.query_id == q.id).all()
            if not histories:
                continue

            total_searches = len(histories)
            total_new_channels = sum(h.new_channels_count for h in histories)
            total_new_videos = sum(h.new_videos_count for h in histories)
            total_results = sum(h.results_count for h in histories)

            # Update metrics
            q.new_channels_discovered = total_new_channels
            q.new_videos_discovered = total_new_videos

            # Compute duplicate rate
            if total_results > 0:
                duplicates = total_results - (total_new_channels + total_new_videos)
                q.duplicate_rate = round(max(0.0, duplicates / total_results), 4)
            else:
                q.duplicate_rate = 0.0

            # Cost per new channel (assuming search cost is 100 quota points)
            total_cost = total_searches * 100
            q.cost_per_new_channel = round(total_cost / max(1, total_new_channels), 2)

            # Performance Priority Decay:
            # If the query has been searched at least twice and found no new channels, lower priority modifier
            if total_searches >= 2 and total_new_channels == 0:
                q.priority_modifier = round(max(0.1, q.priority_modifier * 0.7), 4)
                sys_logger.info(f"Query '{q.query_text}' repeatedly failed to produce new channel discoveries. Decayed priority_modifier to {q.priority_modifier}.")

            count += 1

        db.commit()
        sys_logger.info(f"Evaluated performance for {count} generated search queries.")
        return count
