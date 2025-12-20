"""收藏歌单服务

提供收藏歌单的管理功能，支持曲目收藏/取消收藏操作。
"""

from __future__ import annotations

import logging
from typing import Iterable, Optional, Set

from core.database import DatabaseManager
from models.playlist import Playlist
from models.track import Track
from services.playlist_service import PlaylistService

logger = logging.getLogger(__name__)


class FavoritesService:
    """收藏歌单服务"""

    FAVORITES_NAME = "我的喜欢"
    FAVORITES_DESCRIPTION = "收藏的歌曲"
    FAVORITES_KEY = "favorites.playlist_id"

    def __init__(self, db: DatabaseManager, playlist_service: PlaylistService):
        self._db = db
        self._playlist_service = playlist_service

    def get_or_create_playlist(self) -> Playlist:
        """获取或创建收藏歌单"""
        playlist_id = self._get_state_value(self.FAVORITES_KEY)
        if playlist_id:
            playlist = self._playlist_service.get(playlist_id)
            if playlist:
                return playlist

        playlist = self._playlist_service.create(
            self.FAVORITES_NAME,
            self.FAVORITES_DESCRIPTION,
        )
        self._set_state_value(self.FAVORITES_KEY, playlist.id)
        return playlist

    def get_playlist_id(self) -> str:
        """获取收藏歌单 ID"""
        return self.get_or_create_playlist().id

    def get_favorite_ids(self) -> Set[str]:
        """获取所有收藏曲目 ID 集合"""
        playlist_id = self._get_state_value(self.FAVORITES_KEY)
        if playlist_id:
            playlist = self._playlist_service.get(playlist_id)
            if playlist:
                return set(playlist.track_ids)

        playlist = self.get_or_create_playlist()
        return set(playlist.track_ids)

    def is_favorite(self, track_id: str) -> bool:
        """判断曲目是否已收藏"""
        return track_id in self.get_favorite_ids()

    def add_track(self, track: Track) -> bool:
        """添加曲目到收藏"""
        playlist = self.get_or_create_playlist()
        return self._playlist_service.add_track(playlist.id, track)

    def remove_track(self, track_id: str) -> bool:
        """从收藏移除曲目"""
        playlist = self.get_or_create_playlist()
        return self._playlist_service.remove_track(playlist.id, track_id)

    def add_tracks(self, tracks: Iterable[Track]) -> int:
        """批量添加曲目到收藏"""
        count = 0
        for track in tracks:
            if self.add_track(track):
                count += 1
        return count

    def remove_tracks(self, track_ids: Iterable[str]) -> int:
        """批量从收藏移除曲目"""
        count = 0
        for track_id in track_ids:
            if self.remove_track(track_id):
                count += 1
        return count

    def _get_state_value(self, key: str) -> Optional[str]:
        row = self._db.fetch_one("SELECT value FROM app_state WHERE key = ?", (key,))
        return row["value"] if row else None

    def _set_state_value(self, key: str, value: str) -> None:
        try:
            self._db.execute(
                "INSERT OR REPLACE INTO app_state(key, value, updated_at) VALUES(?, ?, CURRENT_TIMESTAMP)",
                (key, value),
            )
        except Exception:
            logger.warning("保存状态值失败: key=%s", key, exc_info=True)
