"""
LLM 播放队列管理服务

通过调用 LLM（支持多个服务商）对播放队列进行动态管理，
例如：根据自然语言指令对队列进行重排、去重、截断等。
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING
import json
import logging

from services.config_service import ConfigService
from models.track import Track

if TYPE_CHECKING:
    from core.llm_provider import LLMProvider
    from services.tag_service import TagService
    from services.tag_query_parser import TagQueryParser, TagQuery

logger = logging.getLogger(__name__)


class LLMQueueError(RuntimeError):
    pass


@dataclass(frozen=True)
class LibraryQueueRequest:
    mode: str = "replace"  # replace|append
    query: str = ""
    genre: str = ""
    artist: str = ""
    album: str = ""
    limit: int = 30
    shuffle: bool = True
    semantic_fallback: bool = True


@dataclass(frozen=True)
class QueueReorderPlan:
    ordered_track_ids: List[str]
    reason: str = ""
    clear_queue: bool = False
    library_request: Optional[LibraryQueueRequest] = None
    instruction: str = ""

class LLMQueueService:
    """
    将自然语言指令转换为队列变更计划，并应用到播放器队列。

    支持多个 LLM 提供商（SiliconFlow、Gemini 等）。
    """

    def __init__(
        self,
        config: Optional[ConfigService] = None,
        client: Optional["LLMProvider"] = None,
        tag_service: Optional["TagService"] = None,
    ):
        """初始化 LLM 队列服务
        
        Args:
            config: 配置服务实例
            client: LLM 提供商实例（可选，默认根据配置创建）
            tag_service: 标签服务实例（可选，用于标签预筛选）
        """
        self._config = config or ConfigService()
        self._tag_service = tag_service
        self._tag_query_parser: Optional["TagQueryParser"] = None
        
        if client is not None:
            self._client = client
        else:
            from services.llm_providers import create_llm_provider
            self._client = create_llm_provider(self._config)

    def suggest_reorder(
        self,
        instruction: str,
        queue: Sequence[Track],
        current_track_id: Optional[str] = None,
        library_context: Optional[Dict[str, Any]] = None,
    ) -> QueueReorderPlan:
        max_items = int(self._config.get("llm.queue_manager.max_items", 50))
        items = list(queue)[: max(0, max_items)]

        known_ids = {t.id for t in items}
        if current_track_id and current_track_id not in known_ids:
            current_track_id = None

        messages = self._build_reorder_messages(instruction, items, current_track_id, library_context)
        content = self._client.chat_completions(messages)
        plan = self._parse_reorder_plan(content, known_ids)
        plan = replace(plan, instruction=instruction)

        if plan.clear_queue:
            return plan
        if plan.library_request is not None:
            return plan

        # 保底：如果 LLM 给了空列表，或没有有效 id，则不变更
        if not plan.ordered_track_ids:
            return QueueReorderPlan([t.id for t in items], reason="LLM 未给出有效队列，保持原顺序")

        return plan

    def suggest_and_apply_reorder(self, player: Any, instruction: str) -> QueueReorderPlan:
        """便捷方法：基于当前播放器队列生成重排计划并立即应用。"""
        queue = list(getattr(player, "queue", []))
        current = getattr(player, "current_track", None)
        current_id = getattr(current, "id", None) if current else None

        plan = self.suggest_reorder(instruction=instruction, queue=queue, current_track_id=current_id)
        self.apply_reorder_plan(player, plan)
        return plan

    def apply_reorder_plan(
        self,
        player: Any,
        plan: QueueReorderPlan,
    ) -> Tuple[List[Track], int]:
        """
        应用重排计划到 PlayerService。

        Args:
            player: PlayerService（duck typing：需要 current_track, queue, set_queue）
            plan: QueueReorderPlan

        Returns:
            (new_queue, new_index)
        """
        if plan.clear_queue:
            if hasattr(player, "clear_queue"):
                player.clear_queue()
            else:
                player.set_queue([], 0)
            return [], -1
        if plan.library_request is not None:
            raise LLMQueueError("该计划包含 library_request，请使用 apply_plan 并传入 LibraryService。")

        current = getattr(player, "current_track", None)
        current_id = getattr(current, "id", None) if current else None
        queue: List[Track] = list(getattr(player, "queue", []))
        id_to_track = {t.id: t for t in queue}

        new_queue: List[Track] = []
        for track_id in plan.ordered_track_ids:
            track = id_to_track.get(track_id)
            if track:
                new_queue.append(track)

        # 把未提及曲目追加到末尾（默认行为）
        for t in queue:
            if t.id not in set(plan.ordered_track_ids):
                new_queue.append(t)

        new_index = 0
        if current_id:
            for i, t in enumerate(new_queue):
                if t.id == current_id:
                    new_index = i
                    break

        player.set_queue(new_queue, new_index)
        return new_queue, new_index

    def apply_plan(self, player: Any, plan: QueueReorderPlan, library: Any = None) -> Tuple[List[Track], int]:
        """
        应用队列计划（支持清空、从音乐库调取、以及对当前队列重排）。

        Args:
            player: PlayerService（duck typing：需要 current_track, queue, set_queue, clear_queue(可选)）
            plan: QueueReorderPlan
            library: LibraryService（duck typing：需要 query_tracks）

        Returns:
            (new_queue, new_index)
        """
        current = getattr(player, "current_track", None)
        current_id = getattr(current, "id", None) if current else None
        queue: List[Track] = list(getattr(player, "queue", []))

        # clear_queue 可以与后续 library_request 组合：先停止/清空，再设置新队列。
        # 纯清空（且没有其他动作）直接快速返回，避免额外 set_queue。
        if plan.clear_queue and plan.library_request is None and not plan.ordered_track_ids:
            if hasattr(player, "clear_queue"):
                player.clear_queue()
            else:
                player.set_queue([], 0)
            return [], -1

        new_queue, new_index = self.resolve_plan(
            plan=plan,
            queue=queue,
            current_track_id=current_id,
            library=library,
        )

        if plan.clear_queue and hasattr(player, "clear_queue"):
            player.clear_queue()

        player.set_queue(new_queue, new_index if new_queue else -1)
        return new_queue, new_index if new_queue else -1

    def resolve_plan(
        self,
        plan: QueueReorderPlan,
        queue: Sequence[Track],
        current_track_id: Optional[str] = None,
        library: Any = None,
    ) -> Tuple[List[Track], int]:
        """
        将计划解析为具体队列，不直接修改 PlayerService。

        - 可能会查询 LibraryService
        - 当启用 semantic_fallback 时，可能会再次调用 LLM 做语义筛选
        """
        base_queue: List[Track] = list(queue)
        current_id = current_track_id

        if plan.clear_queue:
            base_queue = []
            current_id = None

        if plan.library_request is not None:
            if library is None or not hasattr(library, "query_tracks"):
                raise LLMQueueError("缺少 LibraryService（需要提供 query_tracks）")

            req = plan.library_request
            limit = int(req.limit) if isinstance(req.limit, int) else 30
            limit = max(1, min(200, limit))
            shuffle = bool(req.shuffle)
            tracks: List[Track] = list(
                library.query_tracks(
                    query=str(req.query or ""),
                    genre=str(req.genre or ""),
                    artist=str(req.artist or ""),
                    album=str(req.album or ""),
                    limit=limit,
                    shuffle=shuffle,
                )
            )
            if not tracks and bool(req.semantic_fallback):
                # 尝试使用标签预筛选（两阶段优化）
                tracks = self._try_tag_prefilter(
                    instruction=plan.instruction or "",
                    library=library,
                    limit=limit,
                )
                
                # 如果标签预筛选失败，回退到原有的语义筛选
                if not tracks:
                    tracks = self._semantic_select_tracks_from_library(
                        instruction=plan.instruction or "",
                        library=library,
                        request=req,
                        limit=limit,
                    )

            if not tracks:
                q = req.genre or req.query or req.artist or req.album or "（未指定条件）"
                raise LLMQueueError(f"音乐库中未找到符合条件的曲目：{q}")

            mode = (req.mode or "replace").strip().lower()
            if mode not in {"replace", "append"}:
                mode = "replace"

            if mode == "replace":
                return tracks, 0 if tracks else -1

            seen = {t.id for t in base_queue}
            merged = base_queue + [t for t in tracks if t.id not in seen]

            new_index = 0
            if current_id:
                for i, t in enumerate(merged):
                    if t.id == current_id:
                        new_index = i
                        break
            return merged, new_index if merged else -1

        if plan.ordered_track_ids:
            id_to_track = {t.id: t for t in base_queue}
            ordered_ids = list(plan.ordered_track_ids)
            ordered_set = set(ordered_ids)

            new_queue: List[Track] = []
            for track_id in ordered_ids:
                track = id_to_track.get(track_id)
                if track:
                    new_queue.append(track)

            for t in base_queue:
                if t.id not in ordered_set:
                    new_queue.append(t)

            new_index = 0
            if current_id:
                for i, t in enumerate(new_queue):
                    if t.id == current_id:
                        new_index = i
                        break
            return new_queue, new_index if new_queue else -1

        # No-op：保持原队列。
        new_index = 0
        if current_id:
            for i, t in enumerate(base_queue):
                if t.id == current_id:
                    new_index = i
                    break
        return base_queue, new_index if base_queue else -1

    def _semantic_select_tracks_from_library(
        self,
        instruction: str,
        library: Any,
        request: LibraryQueueRequest,
        limit: int,
    ) -> List[Track]:
        if not instruction.strip():
            return []

        max_catalog_items = int(self._config.get("llm.queue_manager.semantic_fallback.max_catalog_items", 1500))
        batch_size = int(self._config.get("llm.queue_manager.semantic_fallback.batch_size", 250))
        per_batch_pick = int(self._config.get("llm.queue_manager.semantic_fallback.per_batch_pick", 8))
        max_catalog_items = max(50, min(20000, max_catalog_items))
        batch_size = max(50, min(800, batch_size))
        per_batch_pick = max(1, min(30, per_batch_pick))

        if not hasattr(library, "iter_tracks_brief") or not hasattr(library, "get_tracks_by_ids"):
            raise LLMQueueError("LibraryService 缺少 iter_tracks_brief/get_tracks_by_ids，无法进行语义筛选。")

        candidate_briefs: List[Dict[str, str]] = []
        selected_ids: List[str] = []
        seen = set()
        total_sent = 0

        for batch in library.iter_tracks_brief(batch_size=batch_size, limit=max_catalog_items):
            if not batch:
                break
            total_sent += len(batch)

            known = {str(r.get("id", "")) for r in batch if r.get("id")}
            messages = self._build_semantic_select_messages(
                instruction=instruction,
                request=request,
                candidates=batch,
                max_select=per_batch_pick,
                total_sent=total_sent,
                total_limit=max_catalog_items,
            )
            content = self._client.chat_completions(messages)
            ids = self._parse_selected_track_ids(content, known)
            for track_id in ids:
                if track_id not in seen:
                    seen.add(track_id)
                    selected_ids.append(track_id)

            # 记录 brief 便于最终挑选
            for r in batch:
                rid = str(r.get("id", ""))
                if rid and rid in seen:
                    candidate_briefs.append(
                        {
                            "id": rid,
                            "title": str(r.get("title", "") or ""),
                            "artist_name": str(r.get("artist_name", "") or ""),
                            "album_name": str(r.get("album_name", "") or ""),
                        }
                    )

        if not selected_ids:
            return []

        final_ids = selected_ids[:limit]
        if len(selected_ids) > limit:
            known_ids = {c["id"] for c in candidate_briefs}
            messages = self._build_semantic_finalize_messages(
                instruction=instruction,
                request=request,
                candidates=candidate_briefs,
                limit=limit,
            )
            content = self._client.chat_completions(messages)
            plan = self._parse_reorder_plan(content, known_ids)
            if plan.ordered_track_ids:
                final_ids = plan.ordered_track_ids[:limit]

        tracks = list(library.get_tracks_by_ids(final_ids))
        # 保持 final_ids 顺序
        id_to_track = {t.id: t for t in tracks}
        return [id_to_track[i] for i in final_ids if i in id_to_track]

    def _build_semantic_select_messages(
        self,
        instruction: str,
        request: LibraryQueueRequest,
        candidates: List[Dict[str, Any]],
        max_select: int,
        total_sent: int,
        total_limit: int,
    ) -> List[Dict[str, str]]:
        payload = {
            "instruction": instruction,
            "library_request": {
                "query": request.query,
                "genre": request.genre,
                "artist": request.artist,
                "album": request.album,
                "limit": request.limit,
            },
            "note": f"当前这批是音乐库的一个切片（已发送 {total_sent}/{total_limit} 首的简要信息）。",
            "max_select": max_select,
            "candidates": [
                {
                    "id": str(r.get("id", "")),
                    "title": str(r.get("title", "") or ""),
                    "artist_name": str(r.get("artist_name", "") or ""),
                    "album_name": str(r.get("album_name", "") or ""),
                }
                for r in candidates
                if r.get("id")
            ],
            "response_schema": {"selected_track_ids": ["<track_id>"], "reason": "简短说明（可选）"},
            "rules": [
                "只输出 JSON（不要 markdown，不要代码块）。",
                "selected_track_ids 必须来自 candidates 的 id。",
                f"最多选择 {max_select} 首；如果这一批没有合适的，可以返回空列表。",
                "如果用户表达的是风格/情绪（如“摇滚/放松/节奏快”），请根据标题/歌手/专辑等线索进行推断（可模糊匹配）。",
            ],
        }

        system = (
            "你是本地音乐播放器的音乐库语义筛选助手。"
            "用户的音乐库可能没有流派标签，请根据可见信息做模糊推断并挑选候选曲目。"
            "严格按 schema 输出 JSON，且不要输出除 JSON 外的任何内容。"
        )

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]

    def _build_semantic_finalize_messages(
        self,
        instruction: str,
        request: LibraryQueueRequest,
        candidates: List[Dict[str, str]],
        limit: int,
    ) -> List[Dict[str, str]]:
        payload = {
            "instruction": instruction,
            "library_request": {
                "query": request.query,
                "genre": request.genre,
                "artist": request.artist,
                "album": request.album,
            },
            "limit": limit,
            "candidates": candidates,
            "response_schema": {"ordered_track_ids": ["<track_id>"], "reason": "简短说明（可选）"},
            "rules": [
                "只输出 JSON（不要 markdown，不要代码块）。",
                "ordered_track_ids 只能使用 candidates 中出现过的 id。",
                f"返回不超过 {limit} 个 id，并按你认为最符合的顺序排列。",
            ],
        }

        system = (
            "你在候选曲目集合中做最终选择。"
            "严格按 schema 输出 JSON，且不要输出除 JSON 外的任何内容。"
        )

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]

    def _parse_selected_track_ids(self, content: str, known_ids: set[str]) -> List[str]:
        raw = self._strip_code_fences(content).strip()
        try:
            data = json.loads(raw)
        except Exception as e:
            raise LLMQueueError(f"LLM 返回非 JSON: {raw[:200]}") from e

        ids = data.get("selected_track_ids", [])
        if not isinstance(ids, list):
            return []

        out: List[str] = []
        seen = set()
        for v in ids:
            if not isinstance(v, str):
                continue
            if v in known_ids and v not in seen:
                seen.add(v)
                out.append(v)
        return out

    def _build_reorder_messages(
        self,
        instruction: str,
        queue: Sequence[Track],
        current_track_id: Optional[str],
        library_context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        def to_item(t: Track) -> Dict[str, Any]:
            return {
                "id": t.id,
                "title": t.title,
                "artist": t.artist_name,
                "album": t.album_name,
                "duration_ms": t.duration_ms,
            }

        schema = {
            "clear_queue": False,
            "library_request": {
                "mode": "replace|append",
                "query": "可选，关键词（会匹配歌名/歌手/专辑/流派）",
                "genre": "可选，例如：摇滚 / Rock",
                "artist": "可选",
                "album": "可选",
                "limit": 30,
                "shuffle": True,
                "semantic_fallback": True,
            },
            "ordered_track_ids": ["<track_id>", "<track_id>"],
            "reason": "简短说明（可选）",
        }

        user_payload = {
            "instruction": instruction,
            "current_track_id": current_track_id,
            "queue": [to_item(t) for t in queue],
            "library_context": library_context or {},
            "response_schema": schema,
            "rules": [
                "只输出 JSON（不要 markdown，不要代码块）。",
                "如果指令是清空队列，请设置 clear_queue=true 并且 ordered_track_ids 为空列表。",
                "如果指令是“从音乐库调取/加入/播放某类音乐进队列”，请设置 library_request（并让 ordered_track_ids 为空列表）。",
                "当 library_context.has_genre_tags=false 时，音乐库可能没有流派标签：如果按 genre/query 直接筛选不到，请保持 library_request.semantic_fallback=true（让客户端进行语义筛选）。",
                "ordered_track_ids 只能使用 queue 中出现过的 id。",
                "可以通过减少 ordered_track_ids 来表示移除曲目；未提及的曲目将由客户端追加到队尾。",
                "如果无法判断，返回原始顺序。",
            ],
        }

        system = (
            "你是本地音乐播放器的播放队列管家。"
            "请严格按给定 schema 输出 JSON。"
            "不要输出除 JSON 之外的任何内容。"
        )

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ]

    def _parse_reorder_plan(self, content: str, known_ids: set[str]) -> QueueReorderPlan:
        raw = self._strip_code_fences(content).strip()

        try:
            data = json.loads(raw)
        except Exception as e:
            raise LLMQueueError(f"LLM 返回非 JSON: {raw[:200]}") from e

        clear_queue = bool(data.get("clear_queue", False))

        library_request = None
        lr = data.get("library_request", None)
        if isinstance(lr, dict):
            mode = str(lr.get("mode", "replace") or "replace").strip().lower()
            if mode not in {"replace", "append"}:
                mode = "replace"

            def _s(key: str) -> str:
                v = lr.get(key, "")
                return v.strip() if isinstance(v, str) else ""

            limit = lr.get("limit", 30)
            try:
                limit = int(limit)
            except Exception:
                limit = 30
            limit = max(1, min(200, limit))

            shuffle = bool(lr.get("shuffle", True))
            semantic_fallback = bool(lr.get("semantic_fallback", True))

            q = _s("query")
            genre = _s("genre")
            artist = _s("artist")
            album = _s("album")
            if any([q, genre, artist, album]):
                library_request = LibraryQueueRequest(
                    mode=mode,
                    query=q,
                    genre=genre,
                    artist=artist,
                    album=album,
                    limit=limit,
                    shuffle=shuffle,
                    semantic_fallback=semantic_fallback,
                )

        ordered = data.get("ordered_track_ids", [])
        if not isinstance(ordered, list):
            ordered = []

        normalized: List[str] = []
        seen = set()
        for v in ordered:
            if not isinstance(v, str):
                continue
            if v in known_ids and v not in seen:
                normalized.append(v)
                seen.add(v)

        reason = data.get("reason", "")
        if not isinstance(reason, str):
            reason = ""

        return QueueReorderPlan(
            ordered_track_ids=normalized,
            reason=reason,
            clear_queue=clear_queue,
            library_request=library_request,
        )
    
    def _try_tag_prefilter(
        self,
        instruction: str,
        library: Any,
        limit: int,
    ) -> List[Track]:
        """
        尝试使用标签预筛选获取候选曲目
        
        两阶段优化：
        1. 将用户指令解析为标签查询
        2. 用标签查询预筛选曲目
        
        Args:
            instruction: 用户自然语言指令
            library: LibraryService
            limit: 结果数量限制
            
        Returns:
            候选曲目列表，如果预筛选失败则返回空列表
        """
        if not self._tag_service:
            logger.debug("TagService 未初始化，跳过标签预筛选")
            return []
        
        # 检查是否有足够的 LLM 标签
        llm_tags = self._tag_service.get_all_tag_names(source="llm")
        if len(llm_tags) < 5:
            logger.debug("LLM 标签数量不足 (%d)，跳过标签预筛选", len(llm_tags))
            return []
        
        # 初始化 TagQueryParser（懒加载）
        if self._tag_query_parser is None:
            from services.tag_query_parser import TagQueryParser
            self._tag_query_parser = TagQueryParser(
                client=self._client,
                tag_service=self._tag_service,
            )
        
        # 解析指令为标签查询
        try:
            tag_query = self._tag_query_parser.parse(instruction, llm_tags)
        except Exception as e:
            logger.warning("标签查询解析失败: %s", e)
            return []
        
        if not tag_query.is_valid:
            logger.debug("未匹配到有效标签: %s", tag_query.reason)
            return []
        
        if tag_query.confidence < 0.5:
            logger.debug("标签匹配置信度过低 (%.2f)，跳过预筛选", tag_query.confidence)
            return []
        
        logger.info(
            "标签预筛选: 匹配标签=%s, 模式=%s, 置信度=%.2f",
            tag_query.tags, tag_query.match_mode, tag_query.confidence
        )
        
        # 用标签查询曲目
        track_ids = self._tag_service.get_tracks_by_tags(
            tag_names=tag_query.tags,
            match_mode=tag_query.match_mode,
            limit=limit * 2,  # 多取一些以便后续精选
        )
        
        if not track_ids:
            logger.debug("标签查询无结果")
            return []
        
        # 获取曲目详情
        if not hasattr(library, "get_tracks_by_ids"):
            return []
        
        tracks = list(library.get_tracks_by_ids(track_ids))
        
        if len(tracks) <= limit:
            return tracks
        
        # 如果结果太多，用 LLM 精选
        return self._llm_select_from_candidates(
            instruction=instruction,
            candidates=tracks,
            limit=limit,
        )
    
    def _llm_select_from_candidates(
        self,
        instruction: str,
        candidates: List[Track],
        limit: int,
    ) -> List[Track]:
        """
        从候选曲目中用 LLM 精选
        
        Args:
            instruction: 用户指令
            candidates: 候选曲目列表
            limit: 结果数量限制
            
        Returns:
            精选后的曲目列表
        """
        candidate_briefs = [
            {
                "id": t.id,
                "title": t.title or "",
                "artist_name": getattr(t, "artist_name", "") or "",
                "album_name": getattr(t, "album_name", "") or "",
            }
            for t in candidates
        ]
        
        known_ids = {c["id"] for c in candidate_briefs}
        messages = self._build_semantic_finalize_messages(
            instruction=instruction,
            request=LibraryQueueRequest(),
            candidates=candidate_briefs,
            limit=limit,
        )
        
        try:
            content = self._client.chat_completions(messages)
            plan = self._parse_reorder_plan(content, known_ids)
            if plan.ordered_track_ids:
                id_to_track = {t.id: t for t in candidates}
                return [
                    id_to_track[tid] 
                    for tid in plan.ordered_track_ids[:limit] 
                    if tid in id_to_track
                ]
        except Exception as e:
            logger.warning("LLM 精选失败: %s", e)
        
        # 失败时返回前 limit 个
        return candidates[:limit]

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        t = text.strip()
        if t.startswith("```"):
            lines = t.splitlines()
            if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
                return "\n".join(lines[1:-1])
        return t

