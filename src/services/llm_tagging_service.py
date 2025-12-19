"""
LLM 批量标签标注服务

对音乐库进行批量标签标注，支持分批处理、进度回调、可中断/恢复。
"""

from __future__ import annotations

import json
import logging
import uuid
import concurrent.futures
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from core.database import DatabaseManager
from services.config_service import ConfigService
from services.tag_service import TagService

if TYPE_CHECKING:
    from core.llm_provider import LLMProvider
    from services.library_service import LibraryService

logger = logging.getLogger(__name__)


class LLMTaggingError(RuntimeError):
    """LLM 标注错误"""
    pass


@dataclass
class TaggingJobStatus:
    """标注任务状态"""
    job_id: str
    status: str  # pending | running | completed | failed | stopped
    total_tracks: int
    processed_tracks: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    
    @property
    def progress(self) -> float:
        """进度百分比 (0.0 - 1.0)"""
        if self.total_tracks == 0:
            return 0.0
        return self.processed_tracks / self.total_tracks


class LLMTaggingService:
    """
    LLM 批量标签标注服务
    
    对音乐库进行批量标签标注，支持：
    - 分批处理（避免单次请求过大）
    - 进度回调
    - 可中断/恢复
    
    使用示例:
        tagging_service = LLMTaggingService(config, db, tag_service, library_service)
        
        # 启动标注任务
        job_id = tagging_service.start_tagging_job(
            progress_callback=lambda curr, total: print(f"{curr}/{total}")
        )
        
        # 查询任务状态
        status = tagging_service.get_job_status(job_id)
    """
    
    def __init__(
        self,
        config: Optional[ConfigService] = None,
        db: Optional[DatabaseManager] = None,
        tag_service: Optional[TagService] = None,
        library_service: Optional["LibraryService"] = None,
        client: Optional["LLMProvider"] = None,
    ):
        """
        初始化 LLM 标注服务
        
        Args:
            config: 配置服务
            db: 数据库管理器
            tag_service: 标签服务
            library_service: 音乐库服务
            client: LLM 提供商（可选，默认根据配置创建）
        """
        self._config = config or ConfigService()
        self._db = db or DatabaseManager()
        self._tag_service = tag_service or TagService(self._db)
        self._library_service = library_service
        
        if client is not None:
            self._client = client
        else:
            from services.llm_providers import create_llm_provider
            self._client = create_llm_provider(self._config)
        
        self._stop_flag: Dict[str, bool] = {}
        # Run tagging jobs in a background thread to avoid blocking UI.
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="LLMTagging"
        )
        self._running_futures: Dict[str, concurrent.futures.Future] = {}
    
    def start_tagging_job(
        self,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        batch_size: int = 50,
        tags_per_track: int = 5,
    ) -> str:
        """
        启动批量标注任务
        
        Args:
            progress_callback: 进度回调函数 (current, total)
            batch_size: 每批处理的曲目数量
            tags_per_track: 每首曲目的最大标签数量
            
        Returns:
            任务 ID
        """
        if self._library_service is None:
            raise LLMTaggingError("LibraryService 未初始化")
        
        # 获取未标注的曲目
        untagged_ids = self._tag_service.get_untagged_tracks(source="llm", limit=100000)
        if not untagged_ids:
            logger.info("没有需要标注的曲目")
            return ""
        
        # 创建任务记录
        job_id = str(uuid.uuid4())
        self._db.insert("llm_tagging_jobs", {
            "id": job_id,
            "total_tracks": len(untagged_ids),
            "processed_tracks": 0,
            "status": "running",
            "started_at": datetime.now().isoformat(),
        })
        self._stop_flag[job_id] = False

        future = self._executor.submit(
            self._run_tagging_job_wrapper,
            job_id,
            untagged_ids,
            batch_size,
            tags_per_track,
            progress_callback,
        )
        self._running_futures[job_id] = future

        return job_id

    def _run_tagging_job_wrapper(
        self,
        job_id: str,
        track_ids: List[str],
        batch_size: int,
        tags_per_track: int,
        progress_callback: Optional[Callable[[int, int], None]],
    ) -> None:
        """Run tagging job in a background thread."""
        try:
            stopped = self._process_tagging_job(
                job_id=job_id,
                track_ids=track_ids,
                batch_size=batch_size,
                tags_per_track=tags_per_track,
                progress_callback=progress_callback,
            )

            if stopped:
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


    
    def _process_tagging_job(
        self,
        job_id: str,
        track_ids: List[str],
        batch_size: int,
        tags_per_track: int,
        progress_callback: Optional[Callable[[int, int], None]],
    ) -> bool:
        """Process tagging job."""
        total = len(track_ids)
        processed = 0

        for i in range(0, total, batch_size):
            if self._stop_flag.get(job_id, False):
                logger.info("Tagging job stopped: %s", job_id)
                return True

            batch_ids = track_ids[i:i + batch_size]
            batch_tracks = list(self._library_service.get_tracks_by_ids(batch_ids))

            if not batch_tracks:
                continue

            try:
                tags_result = self._request_tags_for_batch(batch_tracks, tags_per_track)
            except Exception as e:
                logger.warning("Batch processing failed, skipping: %s", e)
                processed += len(batch_ids)
                self._db.update(
                    "llm_tagging_jobs",
                    {"processed_tracks": processed},
                    "id = ?",
                    (job_id,)
                )
                if progress_callback:
                    progress_callback(processed, total)
                continue

            for track_id in batch_ids:
                if self._stop_flag.get(job_id, False):
                    logger.info("Tagging job stopped: %s", job_id)
                    self._db.update(
                        "llm_tagging_jobs",
                        {"processed_tracks": processed},
                        "id = ?",
                        (job_id,)
                    )
                    if progress_callback:
                        progress_callback(processed, total)
                    return True

                tags = tags_result.get(track_id, [])
                if tags:
                    self._tag_service.batch_add_tags_to_track(
                        track_id=track_id,
                        tag_names=tags,
                        source="llm"
                    )
                    self._tag_service.mark_track_as_tagged(track_id, job_id)
                processed += 1

            self._db.update(
                "llm_tagging_jobs",
                {"processed_tracks": processed},
                "id = ?",
                (job_id,)
            )

            if progress_callback:
                progress_callback(processed, total)

        return False

    def _request_tags_for_batch(

        self,
        tracks: List[Any],
        tags_per_track: int,
    ) -> Dict[str, List[str]]:
        """
        请求 LLM 为批量曲目生成标签
        
        Args:
            tracks: 曲目列表
            tags_per_track: 每首曲目的最大标签数量
            
        Returns:
            {track_id: [tag1, tag2, ...]}
        """
        # 构建曲目摘要
        track_briefs = []
        for t in tracks:
            track_briefs.append({
                "id": t.id,
                "title": t.title or "",
                "artist": getattr(t, "artist_name", "") or "",
                "album": getattr(t, "album_name", "") or "",
                "genre": getattr(t, "genre", "") or "",
            })
        
        messages = self._build_tagging_messages(track_briefs, tags_per_track)
        content = self._client.chat_completions(messages)
        
        return self._parse_tagging_response(content, {t["id"] for t in track_briefs})
    
    def _build_tagging_messages(
        self,
        tracks: List[Dict[str, str]],
        tags_per_track: int,
    ) -> List[Dict[str, str]]:
        """构建标注请求消息"""
        payload = {
            "task": "music_tagging",
            "tracks": tracks,
            "max_tags_per_track": tags_per_track,
            "tag_categories": [
                "艺术家/歌手名",
                "音乐风格/流派（如：摇滚、流行、古典、电子、爵士、嘻哈、R&B、民谣等）",
                "情绪/氛围（如：放松、激昂、伤感、欢快、浪漫等）",
                "年代/时期（如：80年代、90年代、经典、现代等）",
                "语言（如：中文、英文、日语、韩语等）",
                "其他特征（如：纯音乐、现场版、翻唱等）",
            ],
            "response_schema": {
                "tags": {
                    "<track_id>": ["tag1", "tag2", "..."]
                }
            },
            "rules": [
                "只输出 JSON（不要 markdown，不要代码块）。",
                f"每首曲目生成 1-{tags_per_track} 个标签。",
                "标签应该简洁、具有描述性，便于后续检索。",
                "如果无法判断某个分类的标签，可以省略。",
                "优先使用中文标签，但保留常见的英文风格名称（如 Rock, Pop）。",
            ],
        }
        
        system = (
            "你是音乐标签标注助手。根据歌曲的标题、艺术家、专辑和流派信息，"
            "为每首歌曲生成描述性标签。这些标签将用于后续的音乐检索和推荐。"
            "严格按 schema 输出 JSON，且不要输出除 JSON 之外的任何内容。"
        )
        
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
    
    def _parse_tagging_response(
        self,
        content: str,
        known_ids: set,
    ) -> Dict[str, List[str]]:
        """解析 LLM 标注响应"""
        raw = self._strip_code_fences(content).strip()
        
        try:
            data = json.loads(raw)
        except Exception as e:
            logger.warning("LLM 返回非 JSON: %s", raw[:200])
            raise LLMTaggingError(f"LLM 返回非 JSON: {raw[:200]}") from e
        
        tags_data = data.get("tags", {})
        if not isinstance(tags_data, dict):
            return {}
        
        result: Dict[str, List[str]] = {}
        for track_id, tags in tags_data.items():
            if track_id not in known_ids:
                continue
            if not isinstance(tags, list):
                continue
            
            # 过滤有效标签
            valid_tags = []
            for tag in tags:
                if isinstance(tag, str):
                    tag = tag.strip()
                    if tag and len(tag) <= 50:
                        valid_tags.append(tag)
            
            if valid_tags:
                result[track_id] = valid_tags
        
        return result
    
    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """移除代码块标记"""
        t = text.strip()
        if t.startswith("```"):
            lines = t.splitlines()
            if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
                return "\n".join(lines[1:-1])
        return t
    
    def get_job_status(self, job_id: str) -> Optional[TaggingJobStatus]:
        """
        获取任务状态
        
        Args:
            job_id: 任务 ID
            
        Returns:
            任务状态对象，如果不存在则返回 None
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
    
    def stop_job(self, job_id: str) -> bool:
        """
        停止正在运行的任务
        
        Args:
            job_id: 任务 ID
            
        Returns:
            是否成功设置停止标志
        """
        if job_id in self._stop_flag:
            self._stop_flag[job_id] = True
            return True
        return False

    def wait_for_job(self, job_id: str, timeout: Optional[float] = None) -> bool:
        """Wait for a tagging job to finish."""
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
    
    def get_tagging_stats(self) -> Dict[str, Any]:
        """
        获取标注统计信息
        
        Returns:
            统计信息字典
        """
        # 已标注曲目数
        tagged_count = self._db.fetch_one(
            "SELECT COUNT(*) as count FROM llm_tagged_tracks"
        )
        
        # 总曲目数
        total_count = self._db.fetch_one(
            "SELECT COUNT(*) as count FROM tracks"
        )
        
        # LLM 生成的标签数
        llm_tag_count = self._db.fetch_one(
            "SELECT COUNT(*) as count FROM tags WHERE source = 'llm'"
        )
        
        return {
            "tagged_tracks": tagged_count["count"] if tagged_count else 0,
            "total_tracks": total_count["count"] if total_count else 0,
            "llm_tags": llm_tag_count["count"] if llm_tag_count else 0,
        }
