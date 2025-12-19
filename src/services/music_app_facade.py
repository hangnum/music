# -*- coding: utf-8 -*-
"""
音乐应用门面模块

提供 UI 层访问服务层的统一接口，收窄依赖面。

设计原则：
- UI 组件只依赖此 Facade，不直接访问底层服务
- Facade 只暴露 UI 真正需要的"用例级方法"
- 内部服务引用对外不可见
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from enum import Enum
    from app.protocols import (
        IConfigService,
        IEventBus,
        ILibraryService,
        IPlayerService,
        IPlaylistService,
    )
    from models.track import Track

logger = logging.getLogger(__name__)


class MusicAppFacade:
    """音乐应用门面
    
    UI 用例门面 - 收窄 UI 与服务层的依赖面。
    子组件应只接收此 Facade，而非 AppContainer 或单独的服务。
    
    使用示例:
        # 在 widget 中使用
        class MyWidget(QWidget):
            def __init__(self, facade: MusicAppFacade):
                self._facade = facade
                self._facade.subscribe(EventType.TRACK_STARTED, self._on_track)
                
            def play_track(self, track):
                self._facade.play(track)
    """
    
    def __init__(
        self,
        player: "IPlayerService",
        library: "ILibraryService",
        playlist_service: "IPlaylistService",
        config: "IConfigService",
        event_bus: "IEventBus",
    ):
        """初始化门面
        
        Args:
            player: 播放服务
            library: 媒体库服务
            playlist_service: 歌单服务
            config: 配置服务
            event_bus: 事件总线
        """
        self._player = player
        self._library = library
        self._playlist = playlist_service
        self._config = config
        self._event_bus = event_bus
    
    # =========================================================================
    # 播放控制
    # =========================================================================
    
    def play(self, track: Optional["Track"] = None) -> bool:
        """播放曲目
        
        Args:
            track: 要播放的曲目，None则播放当前曲目
            
        Returns:
            是否成功播放
        """
        return self._player.play(track)
    
    def pause(self) -> None:
        """暂停播放"""
        self._player.pause()
    
    def resume(self) -> None:
        """恢复播放"""
        self._player.resume()
    
    def stop(self) -> None:
        """停止播放"""
        self._player.stop()
    
    def toggle_play(self) -> None:
        """切换播放/暂停"""
        self._player.toggle_play()
    
    def next_track(self) -> Optional["Track"]:
        """下一曲"""
        return self._player.next_track()
    
    def previous_track(self) -> Optional["Track"]:
        """上一曲"""
        return self._player.previous_track()
    
    def seek(self, position_ms: int) -> None:
        """跳转到指定位置
        
        Args:
            position_ms: 目标位置（毫秒）
        """
        self._player.seek(position_ms)
    
    def set_volume(self, volume: float) -> None:
        """设置音量
        
        Args:
            volume: 音量值 (0.0 - 1.0)
        """
        self._player.set_volume(volume)
    
    def get_volume(self) -> float:
        """获取当前音量"""
        return self._player.get_volume()
    
    @property
    def is_playing(self) -> bool:
        """是否正在播放"""
        return self._player.is_playing
    
    @property
    def current_track(self) -> Optional["Track"]:
        """当前播放的曲目"""
        return self._player.current_track
    
    @property
    def queue(self) -> List["Track"]:
        """播放队列"""
        return self._player.queue
    
    def set_queue(self, tracks: List["Track"], start_index: int = 0) -> None:
        """设置播放队列
        
        Args:
            tracks: 曲目列表
            start_index: 起始索引
        """
        self._player.set_queue(tracks, start_index)
    
    # =========================================================================
    # 媒体库操作
    # =========================================================================
    
    def scan_library(self, directories: List[str]) -> None:
        """异步扫描媒体库
        
        Args:
            directories: 目录列表
        """
        self._library.scan_async(directories)
    
    def get_all_tracks(self) -> List["Track"]:
        """获取所有曲目"""
        return self._library.get_all_tracks()
    
    def get_track(self, track_id: str) -> Optional["Track"]:
        """获取单个曲目"""
        return self._library.get_track(track_id)
    
    def search(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """搜索媒体库
        
        Args:
            query: 搜索关键词
            limit: 结果数量限制
            
        Returns:
            包含 tracks, albums, artists 的搜索结果
        """
        return self._library.search(query, limit)
    
    def get_track_count(self) -> int:
        """获取曲目总数"""
        return self._library.get_track_count()
    
    # =========================================================================
    # 歌单操作
    # =========================================================================
    
    def create_playlist(self, name: str, description: str = "") -> Any:
        """创建歌单
        
        Args:
            name: 歌单名称
            description: 歌单描述
            
        Returns:
            创建的歌单对象
        """
        return self._playlist.create(name, description)
    
    def get_playlists(self) -> List[Any]:
        """获取所有歌单"""
        return self._playlist.get_all()
    
    def get_playlist(self, playlist_id: str) -> Optional[Any]:
        """获取单个歌单"""
        return self._playlist.get(playlist_id)
    
    def add_track_to_playlist(self, playlist_id: str, track_id: str) -> bool:
        """添加曲目到歌单"""
        return self._playlist.add_track(playlist_id, track_id)
    
    def remove_track_from_playlist(self, playlist_id: str, track_id: str) -> bool:
        """从歌单移除曲目"""
        return self._playlist.remove_track(playlist_id, track_id)
    
    # =========================================================================
    # 配置操作
    # =========================================================================
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self._config.get(key, default)
    
    def set_config(self, key: str, value: Any) -> None:
        """设置配置值"""
        self._config.set(key, value)
    
    def save_config(self) -> None:
        """保存配置"""
        self._config.save()
    
    # =========================================================================
    # 事件订阅
    # =========================================================================
    
    def subscribe(
        self, 
        event_type: "Enum", 
        callback: Callable[[Any], None]
    ) -> str:
        """订阅事件
        
        Args:
            event_type: 事件类型
            callback: 回调函数
            
        Returns:
            订阅ID
        """
        return self._event_bus.subscribe(event_type, callback)
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """取消订阅
        
        Args:
            subscription_id: 订阅ID
            
        Returns:
            是否成功取消
        """
        return self._event_bus.unsubscribe(subscription_id)
    
    def publish(self, event_type: "Enum", data: Any = None) -> None:
        """发布事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
        """
        self._event_bus.publish(event_type, data)
