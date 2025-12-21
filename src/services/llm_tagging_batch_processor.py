"""
LLM Batch Tagging Processor Module

Responsible for batch processing logic, including batch splitting, retries, and progress updates.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional

from models.llm_tagging import LLMTaggingError

logger = logging.getLogger(__name__)


class LLMTaggingBatchProcessor:
    """
    LLM Batch Tagging Processor
    
    Handles batch tagging logic, coordinating the job manager, tagging engine, and tag service.
    """
    
    def __init__(
        self,
        engine: Any,
        tag_service: Any,
        library_service: Any,
    ):
        """
        Initialize the batch processor.
        
        Args:
            engine: Tag generation engine
            tag_service: Tag service
            library_service: Media library service
        """
        self._engine = engine
        self._tag_service = tag_service
        self._library_service = library_service
    
    def process_batch_job(
        self,
        job_id: str,
        track_ids: List[str],
        batch_size: int,
        tags_per_track: int,
        progress_callback: Optional[Callable[[int, int], None]],
        use_web_search: bool = False,
        stop_flag_getter: Optional[Callable[[str], bool]] = None,
        progress_updater: Optional[Callable[[str, int], None]] = None,
    ) -> bool:
        """
        Process a batch tagging job.
        
        Args:
            job_id: Job ID
            track_ids: List of track IDs
            batch_size: Batch size
            tags_per_track: Number of tags per track
            progress_callback: Progress callback function
            use_web_search: Whether to use web search enhancement
            stop_flag_getter: Function to get the stop flag
            progress_updater: Function to update progress
            
        Returns:
            True if stopped prematurely.
        """
        total = len(track_ids)
        processed = 0
        
        for i in range(0, total, batch_size):
            # Check stop flag
            if stop_flag_getter and stop_flag_getter(job_id):
                logger.info("Tagging job stopped: %s", job_id)
                return True
            
            batch_ids = track_ids[i:i + batch_size]
            batch_tracks = list(self._library_service.get_tracks_by_ids(batch_ids))
            
            if not batch_tracks:
                continue
            
            try:
                # Request batch tags
                tags_result = self._engine.request_tags_for_batch(
                    batch_tracks, tags_per_track, use_web_search
                )
            except Exception as e:
                logger.warning(
                    "Batch processing failed, attempting individual retries: %s", e
                )
                # Retry tracks individually if the batch fails
                tags_result = self._engine.retry_tracks_individually(
                    batch_tracks, tags_per_track, use_web_search
                )
            
            # Process batch results
            for track_id in batch_ids:
                # Re-check stop flag
                if stop_flag_getter and stop_flag_getter(job_id):
                    logger.info("Tagging job stopped: %s", job_id)
                    if progress_updater:
                        progress_updater(job_id, processed)
                    if progress_callback:
                        progress_callback(processed, total)
                    return True
                
                tags = tags_result.get(track_id, [])
                if tags:
                    # Add tags to track
                    self._tag_service.batch_add_tags_to_track(
                        track_id=track_id,
                        tag_names=tags,
                        source="llm"
                    )
                    # Mark track as tagged
                    self._tag_service.mark_track_as_tagged(track_id, job_id)
                
                processed += 1
            
            # Update progress
            if progress_updater:
                progress_updater(job_id, processed)
            
            if progress_callback:
                progress_callback(processed, total)
        
        return False
    
    def process_tracks_directly(
        self,
        tracks: List[Any],
        tags_per_track: int,
        use_web_search: bool = False,
    ) -> Dict[str, List[str]]:
        """
        Process a list of tracks directly (no job management).
        
        Args:
            tracks: List of track objects
            tags_per_track: Number of tags per track
            use_web_search: Whether to use web search
            
        Returns:
            Dictionary mapping track IDs to tags.
        """
        if not tracks:
            return {}
        
        try:
            # Try batch processing
            return self._engine.request_tags_for_batch(
                tracks, tags_per_track, use_web_search
            )
        except Exception as e:
            logger.warning(
                "Direct batch processing failed, attempting individual retries: %s", e
            )
            # Retry individually if the batch fails
            return self._engine.retry_tracks_individually(
                tracks, tags_per_track, use_web_search
            )
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """
        Get processing statistics.
        
        Returns:
            Dictionary of statistics.
        """
        # Count of tagged tracks
        tagged_count = self._tag_service.get_tagged_track_count() if hasattr(
            self._tag_service, 'get_tagged_track_count'
        ) else 0
        
        # Total tracks
        total_count = self._library_service.get_track_count() if hasattr(
            self._library_service, 'get_track_count'
        ) else 0
        
        # Count of tags generated by LLM
        llm_tag_count = self._tag_service.get_llm_tag_count() if hasattr(
            self._tag_service, 'get_llm_tag_count'
        ) else 0
        
        return {
            "tagged_tracks": tagged_count,
            "total_tracks": total_count,
            "llm_tags": llm_tag_count,
        }
    
    @property
    def engine(self) -> Any:
        """Get tagging engine."""
        return self._engine
    
    @property
    def tag_service(self) -> Any:
        """Get tag service."""
        return self._tag_service
    
    @property
    def library_service(self) -> Any:
        """Get library service."""
        return self._library_service