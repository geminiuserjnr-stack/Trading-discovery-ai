import datetime
from sqlalchemy.orm import Session
from backend.app.database.session import SessionLocal
from backend.app.models.models import Query, Channel, CrawlJob, QueryHistory
from backend.app.services.discovery.youtube_search import YouTubeChannelDiscovery
from backend.app.services.logging.logger import sys_logger

def run_discovery_cycle():
    """
    Main entry point for the discovery worker.
    Picks the next query and performs channel-centric discovery.
    """
    db = SessionLocal()
    try:
        # 1. Pick next active query
        query = db.query(Query).filter(Query.status == "active").order_by(
            Query.last_executed.asc().nulls_first(),
            Query.search_count.asc()
        ).first()

        if not query:
            sys_logger.info("No active queries for discovery.")
            return

        sys_logger.info(f"Starting discovery cycle for query: {query.query_text}")
        discovery_service = YouTubeChannelDiscovery()
        
        # 2. Perform discovery
        discovery_data = discovery_service.discover_channels(query.query_text, max_results=20)
        channels = discovery_data.get("channels", [])
        
        new_channels_count = 0
        
        # 3. Process discovered channels
        for chan_data in channels:
            chan_id = chan_data.get("id")
            snippet = chan_data.get("snippet", {})
            stats = chan_data.get("statistics", {})
            
            # Deduplication
            existing_chan = db.query(Channel).filter(Channel.channel_id == chan_id).first()
            if not existing_chan:
                # Create new channel record
                new_chan = Channel(
                    channel_id=chan_id,
                    channel_name=snippet.get("title", "Unknown"),
                    description=snippet.get("description", ""),
                    subscribers=int(stats.get("subscriberCount", 0)),
                    country=snippet.get("country"),
                    avatar=snippet.get("thumbnails", {}).get("default", {}).get("url"),
                    discovery_query=query.query_text,
                    investigation_status="pending", # Ready for Phase 3
                    last_seen=datetime.datetime.utcnow()
                )
                db.add(new_chan)
                db.flush() # Get ID if needed
                new_channels_count += 1
                
                # Trigger investigation immediately for new channels
                # In Phase 3, we'll use investigation_worker.py, but for now we queue it
                # We reuse CrawlJob for compatibility or create InvestigationJob later
                investigation_job = CrawlJob(
                    channel_id=chan_id,
                    priority=10,
                    reason="new_discovery",
                    status="pending"
                )
                db.add(investigation_job)

        # 4. Update Query metrics
        query.search_count += 1
        query.last_executed = datetime.datetime.utcnow()
        query.channels_discovered = (query.channels_discovered or 0) + new_channels_count
        
        # Track history
        history = QueryHistory(
            query_id=query.id,
            results_count=len(channels),
            new_channels_count=new_channels_count
        )
        db.add(history)
        
        db.commit()
        sys_logger.info(f"Discovery cycle complete. Found {new_channels_count} new channels.")
        
    except Exception as e:
        sys_logger.error(f"Discovery cycle failed: {e}")
        db.rollback()
    finally:
        db.close()
