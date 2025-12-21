"""
LLM Tagging Job Manager Module

Responsible for the lifecycle management of tagging jobs, including starting, stopping, and status tracking.
"""

from __future__ import annotations

import concurrent.futures
import logging
import time
import uuid
import weakref
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from core.database import DatabaseManager
from models.llm_tagging import LLMTaggingError, TaggingJobStatus

logger = logging.getLogger(__name__)


class LLMTaggingJobManager:
    """
    LLM Tagging Job Manager
    
    Handles the lifecycle and status management of tagging jobs.
    """
    
    def __init__(self, db: DatabaseManager):
        self._db = db
        self._stop_flag: Dict[str, bool] = {}
        # Run tagging jobs in a background thread to avoid blocking UI.
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="LLMTagging"
        )
        self._running_futures: Dict[str, concurrent.futures.Future] = {}
        self._shutdown = False
        self._finalizer = weakref.finalize(self, self._shutdown_executor, self._executor)
    
    @staticmethod
    def _shutdown_executor(
        executor: concurrent.futures.ThreadPoolExecutor,
        wait: bool = False,
    ) -> None:
        """Shutdown the executor."""
        try:
            executor.shutdown(wait=wait, cancel_futures=True)
        except TypeError:
            executor.shutdown(wait=wait)
    
    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the job manager."""
        if self._shutdown:
            return
        self._shutdown = True
        if self._finalizer.alive:
            self._finalizer.detach()
        self._shutdown_executor(self._executor, wait=wait)
    
    def create_job(
        self,
        track_ids: List[str],
        job_callback: Callable[[str, List[str], Optional[Callable[[int, int], None]]], None],
        progress_callback: Optional[Callable[[int, int], None]] = None,
        job_name: str = "",
    ) -> str:
        """
        Create a tagging job.
        
        Args:
            track_ids: List of track IDs to be tagged
            job_callback: Job processing callback function
            progress_callback: Progress callback function
            job_name: Name of the job
            
        Returns:
            Job ID
        """
        if self._shutdown:
            raise LLMTaggingError("Tagging service is shut down")
        
        if not track_ids:
            logger.info("No tracks need tagging")
            return ""
        
        # Create job record
        job_id = str(uuid.uuid4())
        self._db.insert("llm_tagging_jobs", {
            "id": job_id,
            "name": job_name,
            "total_tracks": len(track_ids),
            "processed_tracks": 0,
            "status": "running",
            "started_at": datetime.now().isoformat(),
        })
        self._stop_flag[job_id] = False
        
        # Wrap callback function to add error handling and status updates
        def job_wrapper():
            try:
                job_callback(job_id, track_ids, progress_callback)
                
                if self._stop_flag.get(job_id, False):
                    self._db.update(
                        "llm_tagging_jobs",
                        {"status": "stopped", "completed_at": datetime.now().isoformat()},
                        "id = ?",
                        (job_id,)
                    )
                else:
                    self._db.update(
                        "llm_tagging_jobs",
                        {"status": "completed", "completed_at": datetime.now().isoformat()},
                        "id = ?",
                        (job_id,)
                    )
            except Exception as e:
                logger.error("Tagging job failed: %s", e)
                self._db.update(
                    "llm_tagging_jobs",
                    {
                        "status": "failed",
                        "error_message": str(e),
                        "completed_at": datetime.now().isoformat(),
                    },
                    "id = ?",
                    (job_id,)
                )
            finally:
                self._stop_flag.pop(job_id, None)
                self._running_futures.pop(job_id, None)
        
        future = self._executor.submit(job_wrapper)
        self._running_futures[job_id] = future
        
        return job_id
    
    def stop_job(self, job_id: str) -> bool:
        """
        Stop a running job.
        
        Args:
            job_id: Job ID
            
        Returns:
            True if stop flag was successfully set.
        """
        if job_id in self._stop_flag:
            self._stop_flag[job_id] = True
            return True
        return False
    
    def wait_for_job(self, job_id: str, timeout: Optional[float] = None) -> bool:
        """
        Wait for a job to complete.
        
        Args:
            job_id: Job ID
            timeout: Timeout in seconds
            
        Returns:
            True if job completed within timeout.
        """
        future = self._running_futures.get(job_id)
        if future is None:
            return True
        
        try:
            future.result(timeout=timeout)
            return True
        except concurrent.futures.TimeoutError:
            return False
        except Exception:
            return True
    
    def get_job_status(self, job_id: str) -> Optional[TaggingJobStatus]:
        """
        Get job status.
        
        Args:
            job_id: Job ID
            
        Returns:
            TaggingJobStatus object, or None if not found.
        """
        row = self._db.fetch_one(
            "SELECT * FROM llm_tagging_jobs WHERE id = ?",
            (job_id,)
        )
        
        if not row:
            return None
        
        def parse_datetime(s: Optional[str]) -> Optional[datetime]:
            if not s:
                return None
            try:
                return datetime.fromisoformat(s)
            except (ValueError, TypeError):
                return None
        
        return TaggingJobStatus(
            job_id=row["id"],
            status=row["status"],
            total_tracks=row["total_tracks"],
            processed_tracks=row["processed_tracks"],
            started_at=parse_datetime(row.get("started_at")),
            completed_at=parse_datetime(row.get("completed_at")),
            error_message=row.get("error_message"),
        )
    
    def update_job_progress(self, job_id: str, processed_tracks: int) -> None:
        """
        Update job progress.
        
        Args:
            job_id: Job ID
            processed_tracks: Number of tracks processed
        """
        self._db.update(
            "llm_tagging_jobs",
            {"processed_tracks": processed_tracks},
            "id = ?",
            (job_id,)
        )
    
    def get_all_jobs(self, limit: int = 100) -> List[TaggingJobStatus]:
        """
        Get all jobs.
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of TaggingJobStatus objects.
        """
        rows = self._db.fetch_all(
            "SELECT * FROM llm_tagging_jobs ORDER BY started_at DESC LIMIT ?",
            (limit,)
        )
        
        def parse_datetime(s: Optional[str]) -> Optional[datetime]:
            if not s:
                return None
            try:
                return datetime.fromisoformat(s)
            except (ValueError, TypeError):
                return None
        
        return [
            TaggingJobStatus(
                job_id=row["id"],
                status=row["status"],
                total_tracks=row["total_tracks"],
                processed_tracks=row["processed_tracks"],
                started_at=parse_datetime(row.get("started_at")),
                completed_at=parse_datetime(row.get("completed_at")),
                error_message=row.get("error_message"),
            )
            for row in rows
        ]
    
    def cleanup_old_jobs(self, days: int = 30) -> int:
        """
        Cleanup old jobs.
        
        Args:
            days: Days to keep
            
        Returns:
            Number of deleted jobs.
        """
        try:
            days = int(days)
        except Exception:
            days = 30
        days = max(0, days)
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cursor = self._db.execute(
            "DELETE FROM llm_tagging_jobs WHERE completed_at < ?",
            (cutoff,)
        )
        return cursor.rowcount
    
    @property
    def is_shutdown(self) -> bool:
        """Check if the manager is shut down."""
        return self._shutdown
