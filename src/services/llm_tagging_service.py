"""
LLM Batch Tagging Service (Facade Pattern)

Performs batch tagging on the music library, supporting batch processing, 
progress callbacks, and interrupt/resume functionality.

Refactored into a facade pattern, coordinating the following sub-modules:
- LLMTaggingJobManager: Task lifecycle management
- LLMTaggingEngine: Tag generation engine
- LLMTaggingBatchProcessor: Batch processing logic
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from core.database import DatabaseManager
from models.llm_tagging import LLMTaggingError, TaggingJobStatus
from services.config_service import ConfigService
from services.tag_service import TagService

from .llm_tagging_job_manager import LLMTaggingJobManager
from .llm_tagging_engine import LLMTaggingEngine
from .llm_tagging_batch_processor import LLMTaggingBatchProcessor

if TYPE_CHECKING:
    from core.llm_provider import LLMProvider
    from services.library_service import LibraryService
    from services.web_search_service import WebSearchService

logger = logging.getLogger(__name__)


class LLMTaggingService:
    """
    LLM Batch Tagging Service (Facade Pattern)
    
    Coordinates various sub-modules to provide a unified tagging service interface.
    
    Usage Example:
        tagging_service = LLMTaggingService(config, db, tag_service, library_service)
        
        # Start a tagging job
        job_id = tagging_service.start_tagging_job(
            progress_callback=lambda curr, total: print(f"{curr}/{total}")
        )
        
        # Query job status
        status = tagging_service.get_job_status(job_id)
    """
    
    def __init__(
        self,
        config: Optional[ConfigService] = None,
        db: Optional[DatabaseManager] = None,
        tag_service: Optional[TagService] = None,
        library_service: Optional["LibraryService"] = None,
        client: Optional["LLMProvider"] = None,
        web_search: Optional["WebSearchService"] = None,
    ):
        """
        Initialize the LLM tagging service.
        
        Args:
            config: Configuration service
            db: Database manager
            tag_service: Tag service
            library_service: Music library service
            client: LLM provider (optional, created from config by default)
            web_search: Web search service (optional, for enhanced tagging)
        """
        import warnings
        
        if db is None:
            warnings.warn(
                "Creating DatabaseManager internally in LLMTaggingService is deprecated. "
                "Use AppContainerFactory.create() to get a properly configured LLMTaggingService instance. "
                "This fallback will be removed in a future version.",
                FutureWarning,
                stacklevel=2
            )
            db = DatabaseManager()
        
        self._config = config or ConfigService()
        self._db = db
        self._tag_service = tag_service or TagService(self._db)
        self._library_service = library_service
        self._web_search = web_search
        
        if client is not None:
            self._client = client
        else:
            from services.llm_providers import create_llm_provider
            self._client = create_llm_provider(self._config)
        
        # Initialize sub-modules
        self._job_manager = LLMTaggingJobManager(self._db)
        self._engine = LLMTaggingEngine(self._client, self._config, self._web_search)
        self._batch_processor = LLMTaggingBatchProcessor(
            engine=self._engine,
            tag_service=self._tag_service,
            library_service=self._library_service,
        )
    
    def start_tagging_job(
        self,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        batch_size: int = 50,
        tags_per_track: int = 5,
        use_web_search: bool = False,
    ) -> str:
        """
        Start a batch tagging job.
        
        Args:
            progress_callback: Progress callback function (current, total)
            batch_size: Number of tracks per batch
            tags_per_track: Maximum number of tags per track
            use_web_search: Whether to enhance tagging with web search
            
        Returns:
            Job ID
        """
        if self._job_manager.is_shutdown:
            raise LLMTaggingError("Tagging service is shut down")
        if self._library_service is None:
            raise LLMTaggingError("LibraryService not initialized")
        
        # Get tracks that haven't been tagged
        untagged_ids = self._tag_service.get_untagged_tracks(source="llm", limit=100000)
        if not untagged_ids:
            logger.info("No tracks need tagging")
            return ""
        
        # Define job processing callback
        def job_callback(job_id: str, track_ids: List[str], 
                        inner_progress_callback: Optional[Callable[[int, int], None]] = None):
            """Task processing callback function"""
            # Process batch task
            stopped = self._batch_processor.process_batch_job(
                job_id=job_id,
                track_ids=track_ids,
                batch_size=batch_size,
                tags_per_track=tags_per_track,
                progress_callback=inner_progress_callback,
                use_web_search=use_web_search,
                stop_flag_getter=lambda jid: self._job_manager._stop_flag.get(jid, False),
                progress_updater=self._job_manager.update_job_progress,
            )
            
            # Update job status based on completion or stop
            if stopped:
                self._job_manager._db.update(
                    "llm_tagging_jobs",
                    {"status": "stopped", "completed_at": self._get_current_iso_time()},
                    "id = ?",
                    (job_id,)
                )
            else:
                self._job_manager._db.update(
                    "llm_tagging_jobs",
                    {"status": "completed", "completed_at": self._get_current_iso_time()},
                    "id = ?",
                    (job_id,)
                )
        
        # Create job
        job_id = self._job_manager.create_job(
            track_ids=untagged_ids,
            job_callback=job_callback,
            progress_callback=progress_callback,
            job_name="Batch Tagging",
        )
        
        return job_id
    
    def get_job_status(self, job_id: str) -> Optional[TaggingJobStatus]:
        """
        Get job status.
        
        Args:
            job_id: Job ID
            
        Returns:
            TaggingJobStatus object, or None if not found.
        """
        return self._job_manager.get_job_status(job_id)
    
    def stop_job(self, job_id: str) -> bool:
        """
        Stop a running job.
        
        Args:
            job_id: Job ID
            
        Returns:
            True if stop flag was successfully set.
        """
        return self._job_manager.stop_job(job_id)
    
    def wait_for_job(self, job_id: str, timeout: Optional[float] = None) -> bool:
        """Wait for a job to complete."""
        return self._job_manager.wait_for_job(job_id, timeout)
    
    def get_tagging_stats(self) -> Dict[str, Any]:
        """
        Get tagging statistics.
        
        Returns:
            Dictionary of statistics.
        """
        # Get stats from batch processor
        stats = self._batch_processor.get_processing_stats()
        
        # Supplement with DB stats if processor doesn't provide complete data
        if stats["total_tracks"] == 0:
            total_count = self._db.fetch_one(
                "SELECT COUNT(*) as count FROM tracks"
            )
            if total_count:
                stats["total_tracks"] = total_count["count"]
        
        if stats["tagged_tracks"] == 0:
            tagged_count = self._db.fetch_one(
                "SELECT COUNT(*) as count FROM llm_tagged_tracks"
            )
            if tagged_count:
                stats["tagged_tracks"] = tagged_count["count"]
        
        if stats["llm_tags"] == 0:
            llm_tag_count = self._db.fetch_one(
                "SELECT COUNT(*) as count FROM tags WHERE source = 'llm'"
            )
            if llm_tag_count:
                stats["llm_tags"] = llm_tag_count["count"]
        
        return stats
    
    def tag_single_track_detailed(
        self,
        track: Any,
        save_tags: bool = True,
    ) -> Dict[str, Any]:
        """
        Perform detailed tagging for a single track.
        
        Uses web search for in-depth info, then calls LLM to generate high-quality tags.
        
        Args:
            track: Track object
            save_tags: Whether to save tags to the database
            
        Returns:
            {
                "tags": ["tag1", "tag2", ...],
                "search_context": "Found context info",
                "analysis": "LLM analysis explanation",
            }
        """
        result = self._engine.tag_single_track_detailed(track, use_web_search=True)
        
        # Save tags
        if save_tags and result.get("tags") and self._tag_service:
            self._tag_service.batch_add_tags_to_track(
                track_id=track.id,
                tag_names=result["tags"],
                source="llm_detailed",
            )
            self._tag_service.mark_track_as_tagged(track.id)
        
        return result
    
    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the tagging service."""
        self._job_manager.shutdown(wait)
    
    def get_all_jobs(self, limit: int = 100) -> List[TaggingJobStatus]:
        """
        Get all jobs.
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of job statuses.
        """
        return self._job_manager.get_all_jobs(limit)
    
    def cleanup_old_jobs(self, days: int = 30) -> int:
        """
        Cleanup old jobs.
        
        Args:
            days: Days to keep
            
        Returns:
            Number of deleted jobs.
        """
        return self._job_manager.cleanup_old_jobs(days)
    
    @staticmethod
    def _get_current_iso_time() -> str:
        """Get current time as ISO format string."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    @property
    def job_manager(self) -> LLMTaggingJobManager:
        """Get job manager."""
        return self._job_manager
    
    @property
    def engine(self) -> LLMTaggingEngine:
        """Get tagging engine."""
        return self._engine
    
    @property
    def batch_processor(self) -> LLMTaggingBatchProcessor:
        """Get batch processor."""
        return self._batch_processor
    
    @property
    def client(self) -> Any:
        """Get LLM client."""
        return self._client