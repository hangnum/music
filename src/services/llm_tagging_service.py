"""
LLM 批量标签标注服务

对音乐库进行批量标签标注，支持分批处理、进度回调、可中断/恢复。
"""

from __future__ import annotations

import json
import logging
import time
import uuid
import concurrent.futures
import weakref
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from core.database import DatabaseManager
from models.llm_tagging import LLMTaggingError, TaggingJobStatus
from services.config_service import ConfigService
from services.tag_service import TagService
from services.llm_response_parser import (
    strip_code_fences,
    try_parse_json,
    parse_tags_from_content,
    LLMParseError,
)

if TYPE_CHECKING:
    from core.llm_provider import LLMProvider
    from services.library_service import LibraryService
    from services.web_search_service import WebSearchService

logger = logging.getLogger(__name__)


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
        web_search: Optional["WebSearchService"] = None,
    ):
        """
        初始化 LLM 标注服务
        
        Args:
            config: 配置服务
            db: 数据库管理器
            tag_service: 标签服务
            library_service: 音乐库服务
            client: LLM 提供商（可选，默认根据配置创建）
            web_search: 网络搜索服务（可选，用于增强标注）
        """
        self._config = config or ConfigService()
        self._db = db or DatabaseManager()
        self._tag_service = tag_service or TagService(self._db)
        self._library_service = library_service
        self._web_search = web_search
        
        if client is not None:
            self._client = client
        else:
            from services.llm_providers import create_llm_provider
            self._client = create_llm_provider(self._config)
        
        # 从配置读取批次参数（带范围校验）
        raw_batch_size = self._config.get("llm.tagging.batch_request_size", 12)
        self._batch_request_size = max(1, min(50, int(raw_batch_size)))
        
        raw_batch_size_ws = self._config.get(
            "llm.tagging.batch_request_size_with_web_search", 6
        )
        self._batch_request_size_with_web_search = max(1, min(20, int(raw_batch_size_ws)))
        
        raw_delay = self._config.get("llm.tagging.batch_delay_seconds", 0.5)
        self._batch_delay_seconds = max(0.0, min(10.0, float(raw_delay)))
        
        raw_retries = self._config.get("llm.tagging.max_retries", 3)
        self._max_retries = max(0, min(10, int(raw_retries)))
        
        if raw_batch_size != self._batch_request_size:
            logger.warning(
                "llm.tagging.batch_request_size=%s clamped to %d",
                raw_batch_size, self._batch_request_size
            )
        
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
        try:
            executor.shutdown(wait=wait, cancel_futures=True)
        except TypeError:
            executor.shutdown(wait=wait)

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the tagging worker executor."""
        if self._shutdown:
            return
        self._shutdown = True
        if self._finalizer.alive:
            self._finalizer.detach()
        self._shutdown_executor(self._executor, wait=wait)
    
    def start_tagging_job(
        self,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        batch_size: int = 50,
        tags_per_track: int = 5,
        use_web_search: bool = False,
    ) -> str:
        """
        启动批量标注任务
        
        Args:
            progress_callback: 进度回调函数 (current, total)
            batch_size: 每批处理的曲目数量
            tags_per_track: 每首曲目的最大标签数量
            use_web_search: 是否使用网络搜索增强标注
            
        Returns:
            任务 ID
        """
        if self._shutdown:
            raise LLMTaggingError("Tagging service is shut down")
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
            use_web_search,
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
        use_web_search: bool = False,
    ) -> None:
        """Run tagging job in a background thread."""
        try:
            stopped = self._process_tagging_job(
                job_id=job_id,
                track_ids=track_ids,
                batch_size=batch_size,
                tags_per_track=tags_per_track,
                progress_callback=progress_callback,
                use_web_search=use_web_search,
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
        use_web_search: bool = False,
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
                tags_result = self._request_tags_for_batch(
                    batch_tracks, tags_per_track, use_web_search
                )
            except Exception as e:
                logger.warning(
                    "Batch processing failed, attempting per-track retry: %s", e
                )
                # 批次失败时进行单曲逐一重试
                tags_result = self._retry_tracks_individually(
                    batch_tracks, tags_per_track, use_web_search
                )

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

    def _retry_tracks_individually(
        self,
        tracks: List[Any],
        tags_per_track: int,
        use_web_search: bool = False,
    ) -> Dict[str, List[str]]:
        """
        对批次中的曲目进行单曲逐一重试
        
        当批次处理失败时调用，尝试对每首曲目单独请求标签。
        这样可以最大化标注覆盖率，避免因单个曲目问题导致整批跳过。
        
        Args:
            tracks: 需要重试的曲目列表
            tags_per_track: 每首曲目的最大标签数量
            use_web_search: 是否使用网络搜索增强
            
        Returns:
            成功标注的曲目标签字典
        """
        result: Dict[str, List[str]] = {}
        failed_count = 0
        
        for track in tracks:
            try:
                # 对单首曲目调用批量方法（批大小为1）
                single_result = self._request_tags_for_batch(
                    [track], tags_per_track, use_web_search
                )
                result.update(single_result)
            except Exception as e:
                failed_count += 1
                track_id = getattr(track, 'id', 'unknown')
                logger.warning(
                    "Per-track retry failed for track %s: %s",
                    track_id, e
                )
                # 单曲失败后继续处理下一首
                continue
            
            # 单曲之间短暂延迟，避免过于频繁的 API 调用
            time.sleep(self._batch_delay_seconds * 0.5)
        
        if failed_count > 0:
            logger.info(
                "Per-track retry completed: %d/%d succeeded",
                len(tracks) - failed_count, len(tracks)
            )
        
        return result

    def _request_tags_for_batch(
        self,
        tracks: List[Any],
        tags_per_track: int,
        use_web_search: bool = False,
    ) -> Dict[str, List[str]]:
        """
        Request tags for tracks in smaller LLM batches.
        """
        result: Dict[str, List[str]] = {}
        if not tracks:
            return result

        max_request_tracks = (
            self._batch_request_size_with_web_search 
            if use_web_search 
            else self._batch_request_size
        )

        for start in range(0, len(tracks), max_request_tracks):
            batch = tracks[start:start + max_request_tracks]
            track_briefs: List[Dict[str, str]] = []
            known_ids = set()

            for track in batch:
                artist = getattr(track, "artist_name", "") or ""
                title = track.title or ""
                album = getattr(track, "album_name", "") or ""
                genre = getattr(track, "genre", "") or ""

                brief: Dict[str, str] = {
                    "id": track.id,
                    "title": title,
                    "artist": artist,
                    "album": album,
                    "genre": genre,
                }
                known_ids.add(track.id)

                if use_web_search and self._web_search:
                    try:
                        search_context = self._web_search.get_music_context(
                            artist=artist,
                            title=title,
                            album=album,
                            max_total_chars=300,
                        )
                        if search_context:
                            brief["web_context"] = search_context
                    except Exception as e:
                        logger.warning(
                            "Batch tagging search failed (track %s): %s",
                            track.id,
                            e,
                        )

                track_briefs.append(brief)

            messages = self._build_tagging_messages(
                track_briefs,
                tags_per_track,
                use_web_search,
            )

            content = None
            for retry in range(self._max_retries):
                try:
                    content = self._client.chat_completions(messages)
                    break
                except Exception as e:
                    if retry < self._max_retries - 1:
                        wait_time = 2 * (retry + 1)
                        logger.warning(
                            "Batch LLM call failed (retry %d): %s; waiting %d sec",
                            retry + 1,
                            e,
                            wait_time,
                        )
                        time.sleep(wait_time)
                    else:
                        logger.warning("Batch LLM call failed, skipping batch: %s", e)

            if not content:
                continue

            batch_result = self._parse_tagging_response(content, known_ids)
            if not batch_result:
                logger.warning(
                    "Batch LLM returned empty/invalid result: tracks=%d",
                    len(batch),
                )
            result.update(batch_result)

            time.sleep(self._batch_delay_seconds)

        return result

    def _build_tagging_messages(
        self,
        tracks: List[Dict[str, str]],
        tags_per_track: int,
        use_web_search: bool = False,
    ) -> List[Dict[str, str]]:
        """构建标注请求消息"""
        # 构建示例输出
        example_output = '{"tags": {"track_id_1": ["流行", "华语", "周杰伦"], "track_id_2": ["摇滚", "英文"]}}'
        
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
            "response_format": {
                "type": "json_object",
                "schema": {"tags": {"<track_id>": ["tag1", "tag2"]}},
                "example": example_output,
            },
            "rules": [
                "【重要】只输出纯 JSON，不要任何 markdown 代码块（禁止 ```）。",
                "【重要】输出必须是合法 JSON，确保引号匹配、无尾部逗号。",
                f"每首曲目生成 1-{tags_per_track} 个标签。",
                "标签应该简洁（2-10字），具有描述性。",
                "如果无法判断某个分类的标签，可以省略。",
                "优先使用中文标签，保留常见英文风格名（如 Rock, Pop, R&B）。",
            ],
        }
        
        # 根据是否使用网络搜索调整 system prompt
        base_instruction = (
            "你是专业的音乐标签标注助手。你的任务是为音乐曲目生成准确的描述性标签。\n\n"
            "【输出格式要求】\n"
            "- 只输出纯 JSON 对象\n"
            "- 禁止使用 markdown 代码块（不要写 ```）\n"
            "- 禁止在 JSON 外添加任何解释文字\n\n"
            f"【输出示例】\n{example_output}"
        )
        
        if use_web_search:
            system = (
                f"{base_instruction}\n\n"
                "【数据来源】\n"
                "你将收到歌曲的标题、艺术家、专辑信息，以及从网络搜索获取的上下文（web_context）。"
                "请综合这些信息生成准确的标签。"
            )
        else:
            system = (
                f"{base_instruction}\n\n"
                "【数据来源】\n"
                "根据歌曲的标题、艺术家、专辑和流派信息生成标签。"
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
        """解析 LLM 标注响应（增强版）"""
        try:
            return parse_tags_from_content(content, known_ids)
        except LLMParseError as e:
            raise LLMTaggingError(str(e)) from e
    
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
    
    def tag_single_track_detailed(
        self,
        track: Any,
        save_tags: bool = True,
    ) -> Dict[str, Any]:
        """
        对单首曲目进行精细标注
        
        使用网络搜索获取详细信息，然后调用 LLM 生成高质量标签。
        
        Args:
            track: 曲目对象
            save_tags: 是否保存标签到数据库
            
        Returns:
            {
                "tags": ["标签1", "标签2", ...],
                "search_context": "搜索到的上下文信息",
                "analysis": "LLM 分析说明",
            }
        """
        artist = getattr(track, "artist_name", "") or ""
        title = track.title or ""
        album = getattr(track, "album_name", "") or ""
        genre = getattr(track, "genre", "") or ""
        
        # 获取详细的搜索上下文
        search_results = []
        if self._web_search:
            try:
                # 搜索歌曲信息
                song_info = self._web_search.search_music_info(
                    artist=artist, title=title, max_results=5
                )
                search_results.extend(song_info)
                
                # 搜索艺术家信息
                if artist:
                    artist_info = self._web_search.search_artist_info(
                        artist=artist, max_results=3
                    )
                    search_results.extend(artist_info)
                
                # 搜索专辑信息
                if album:
                    album_info = self._web_search.search_album_info(
                        artist=artist, album=album, max_results=2
                    )
                    search_results.extend(album_info)
            except Exception as e:
                logger.warning("精细标注搜索失败: %s", e)
        
        search_context = " | ".join(search_results[:10]) if search_results else ""
        
        # 构建精细标注请求
        messages = self._build_detailed_tagging_messages(
            title=title,
            artist=artist,
            album=album,
            genre=genre,
            search_context=search_context,
        )
        
        try:
            content = self._client.chat_completions(messages)
            result = self._parse_detailed_response(content)
        except Exception as e:
            logger.error("精细标注 LLM 调用失败: %s", e)
            return {
                "tags": [],
                "search_context": search_context,
                "analysis": f"标注失败: {e}",
            }
        
        # 保存标签
        if save_tags and result.get("tags") and self._tag_service:
            self._tag_service.batch_add_tags_to_track(
                track_id=track.id,
                tag_names=result["tags"],
                source="llm_detailed",
            )
            self._tag_service.mark_track_as_tagged(track.id)
        
        result["search_context"] = search_context
        return result
    
    def _build_detailed_tagging_messages(
        self,
        title: str,
        artist: str,
        album: str,
        genre: str,
        search_context: str,
    ) -> List[Dict[str, str]]:
        """构建精细标注请求"""
        track_info = {
            "title": title,
            "artist": artist,
            "album": album,
            "genre": genre,
        }
        
        if search_context:
            track_info["web_search_results"] = search_context
        
        payload = {
            "task": "detailed_music_tagging",
            "track": track_info,
            "request": [
                "根据歌曲信息和网络搜索结果，生成 5-10 个高质量标签",
                "标签应覆盖：风格/流派、情绪/氛围、年代、语言、艺术家特点",
                "提供简短的分析说明为什么选择这些标签",
            ],
            "response_schema": {
                "tags": ["标签1", "标签2", "..."],
                "analysis": "分析说明",
            },
        }
        
        system = (
            "你是专业的音乐分类专家。根据歌曲的元数据和从网络搜索获取的信息，"
            "为这首歌曲生成准确、详细的标签。"
            "网络搜索结果可以帮助你了解艺术家风格、专辑特点、歌曲背景等。"
            "只输出 JSON，不要输出其他内容。"
        )
        
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
    
    def _parse_detailed_response(self, content: str) -> Dict[str, Any]:
        """解析精细标注响应"""
        raw = strip_code_fences(content).strip()
        
        try:
            data = json.loads(raw)
        except Exception as e:
            logger.warning("精细标注 LLM 返回非 JSON: %s", raw[:200])
            return {"tags": [], "analysis": f"解析失败: {e}"}
        
        tags = data.get("tags", [])
        if not isinstance(tags, list):
            tags = []
        
        # 过滤有效标签
        valid_tags = []
        for tag in tags:
            if isinstance(tag, str):
                tag = tag.strip()
                if tag and len(tag) <= 50:
                    valid_tags.append(tag)
        
        return {
            "tags": valid_tags,
            "analysis": data.get("analysis", ""),
        }
