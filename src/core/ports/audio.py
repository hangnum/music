# -*- coding: utf-8 -*-
"""
音频引擎端口接口

定义音频引擎的抽象接口，使播放服务不依赖具体的音频后端实现。
"""

from __future__ import annotations

from enum import Enum
from typing import Callable, Optional, Protocol, runtime_checkable


class PlayerState(Enum):
    """播放器状态"""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    LOADING = "loading"


@runtime_checkable
class IAudioEngine(Protocol):
    """音频引擎接口
    
    提供音频播放的核心功能。
    当前实现：MiniaudioEngine, PygameEngine, VLCEngine
    """
    
    @property
    def state(self) -> PlayerState:
        """当前播放状态"""
        ...
    
    @property
    def volume(self) -> float:
        """当前音量 (0.0 - 1.0)"""
        ...
    
    def load(self, file_path: str) -> bool:
        """加载音频文件
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            是否加载成功
        """
        ...
    
    def play(self) -> bool:
        """开始播放
        
        Returns:
            是否成功开始播放
        """
        ...
    
    def pause(self) -> bool:
        """暂停播放
        
        Returns:
            是否成功暂停
        """
        ...
    
    def resume(self) -> bool:
        """恢复播放
        
        Returns:
            是否成功恢复
        """
        ...
    
    def stop(self) -> bool:
        """停止播放
        
        Returns:
            是否成功停止
        """
        ...
    
    def seek(self, position_ms: int) -> bool:
        """跳转到指定位置
        
        Args:
            position_ms: 目标位置（毫秒）
            
        Returns:
            是否成功跳转
        """
        ...
    
    def get_position(self) -> int:
        """获取当前播放位置
        
        Returns:
            当前位置（毫秒）
        """
        ...
    
    def get_duration(self) -> int:
        """获取音频时长
        
        Returns:
            时长（毫秒）
        """
        ...
    
    def set_volume(self, volume: float) -> None:
        """设置音量
        
        Args:
            volume: 音量值 (0.0 - 1.0)
        """
        ...
    
    def set_on_end(self, callback: Optional[Callable]) -> None:
        """设置播放结束回调
        
        Args:
            callback: 回调函数，接收 PlaybackEndInfo
        """
        ...
    
    def set_on_error(self, callback: Optional[Callable[[str], None]]) -> None:
        """设置错误回调
        
        Args:
            callback: 回调函数，接收错误消息
        """
        ...
    
    def set_next_track(self, file_path: Optional[str]) -> None:
        """设置下一曲（用于 gapless/crossfade）
        
        Args:
            file_path: 下一曲文件路径，None 清除
        """
        ...
    
    def get_engine_name(self) -> str:
        """获取引擎名称"""
        ...
    
    def cleanup(self) -> None:
        """清理资源"""
        ...


@runtime_checkable
class IAudioEngineFactory(Protocol):
    """音频引擎工厂接口"""
    
    def create(self, backend: str = "miniaudio") -> IAudioEngine:
        """创建音频引擎
        
        Args:
            backend: 后端名称
            
        Returns:
            音频引擎实例
        """
        ...
    
    def create_best_available(self) -> IAudioEngine:
        """创建最佳可用引擎"""
        ...
    
    def get_available_backends(self) -> list:
        """获取可用后端列表"""
        ...
