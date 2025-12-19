"""
音频引擎工厂

提供音频引擎的创建和管理，支持多后端切换。
"""

import logging
from typing import List, Type, Dict, Optional

from core.audio_engine import AudioEngineBase, PygameAudioEngine

logger = logging.getLogger(__name__)

# 引擎注册表
_ENGINE_REGISTRY: Dict[str, Type[AudioEngineBase]] = {}


def register_engine(name: str, engine_class: Type[AudioEngineBase]) -> None:
    """
    注册音频引擎

    Args:
        name: 引擎名称标识
        engine_class: 引擎类
    """
    _ENGINE_REGISTRY[name] = engine_class


# 注册内置引擎
register_engine("pygame", PygameAudioEngine)

# 尝试注册可选引擎
try:
    from core.miniaudio_engine import MiniaudioEngine
    register_engine("miniaudio", MiniaudioEngine)
except Exception:
    logger.debug("miniaudio 后端不可用")

try:
    from core.vlc_engine import VLCEngine
    register_engine("vlc", VLCEngine)
except Exception:
    logger.debug("VLC 后端不可用")


class AudioEngineFactory:
    """
    音频引擎工厂

    根据配置创建合适的音频引擎实例，支持降级策略。

    使用示例:
        # 创建指定后端
        engine = AudioEngineFactory.create("miniaudio")

        # 自动选择最佳可用后端
        engine = AudioEngineFactory.create_best_available()

        # 获取可用后端列表
        backends = AudioEngineFactory.get_available_backends()
    """

    # 后端优先级（降级顺序）
    PRIORITY_ORDER = ["miniaudio", "vlc", "pygame"]

    @classmethod
    def create(cls, backend: str = "miniaudio") -> AudioEngineBase:
        """
        创建指定的音频引擎

        如果指定后端不可用，会自动降级到可用后端。

        Args:
            backend: 后端名称 ("miniaudio", "vlc", "pygame")

        Returns:
            AudioEngineBase: 音频引擎实例

        Raises:
            RuntimeError: 所有后端都不可用时抛出
        """
        # 尝试创建指定后端
        if backend in _ENGINE_REGISTRY:
            try:
                engine = _ENGINE_REGISTRY[backend]()
                logger.info("使用音频后端: %s", backend)
                return engine
            except Exception as e:
                logger.warning("创建 %s 后端失败: %s，尝试降级", backend, e)

        # 降级策略：按优先级尝试其他后端
        return cls.create_best_available(exclude=[backend])

    @classmethod
    def create_best_available(
        cls, exclude: Optional[List[str]] = None
    ) -> AudioEngineBase:
        """
        创建最佳可用音频引擎

        按优先级顺序尝试各后端。

        Args:
            exclude: 排除的后端名称列表

        Returns:
            AudioEngineBase: 音频引擎实例

        Raises:
            RuntimeError: 所有后端都不可用时抛出
        """
        exclude = exclude or []

        for backend in cls.PRIORITY_ORDER:
            if backend in exclude:
                continue
            if backend not in _ENGINE_REGISTRY:
                continue

            try:
                engine = _ENGINE_REGISTRY[backend]()
                logger.info("使用音频后端: %s", backend)
                return engine
            except Exception as e:
                logger.debug("后端 %s 不可用: %s", backend, e)

        raise RuntimeError("没有可用的音频后端。请安装 pygame、miniaudio 或 VLC。")

    @classmethod
    def get_available_backends(cls) -> List[str]:
        """
        获取可用的后端列表

        Returns:
            List[str]: 可用后端名称列表，按优先级排序
        """
        available = []

        for backend in cls.PRIORITY_ORDER:
            if backend not in _ENGINE_REGISTRY:
                continue

            engine_class = _ENGINE_REGISTRY[backend]
            
            # 检查子类是否重写了 probe() 方法（而非继承基类的默认实现）
            has_custom_probe = (
                'probe' in engine_class.__dict__ or  # 直接定义在类上
                any('probe' in base.__dict__ for base in engine_class.__mro__[1:-1] 
                    if base.__name__ != 'AudioEngineBase')  # 定义在中间父类上
            )
            
            if has_custom_probe:
                # 使用静态 probe() 方法（不触碰播放状态）
                try:
                    if engine_class.probe():
                        available.append(backend)
                except Exception:
                    pass
            else:
                # 没有 probe 方法的引擎：尝试实例化
                try:
                    engine = engine_class()
                    available.append(backend)
                    if hasattr(engine, 'cleanup'):
                        engine.cleanup()
                except Exception:
                    pass

        return available

    @classmethod
    def get_backend_info(cls, backend: str) -> Dict[str, bool]:
        """
        获取后端的特性支持信息

        Args:
            backend: 后端名称

        Returns:
            Dict[str, bool]: 特性支持情况
        """
        if backend not in _ENGINE_REGISTRY:
            return {}

        try:
            engine = _ENGINE_REGISTRY[backend]()
            info = {
                "gapless": engine.supports_gapless(),
                "crossfade": engine.supports_crossfade(),
                "equalizer": engine.supports_equalizer(),
                "replay_gain": engine.supports_replay_gain(),
            }
            if hasattr(engine, 'cleanup'):
                engine.cleanup()
            return info
        except Exception:
            return {}

    @classmethod
    def is_available(cls, backend: str) -> bool:
        """
        检查后端是否可用

        Args:
            backend: 后端名称

        Returns:
            bool: 是否可用
        """
        if backend not in _ENGINE_REGISTRY:
            return False

        engine_class = _ENGINE_REGISTRY[backend]
        
        # 检查子类是否重写了 probe() 方法
        has_custom_probe = (
            'probe' in engine_class.__dict__ or
            any('probe' in base.__dict__ for base in engine_class.__mro__[1:-1] 
                if base.__name__ != 'AudioEngineBase')
        )
        
        if has_custom_probe:
            try:
                return engine_class.probe()
            except Exception:
                return False
        
        # 没有 probe 方法的引擎：尝试实例化
        try:
            engine = engine_class()
            if hasattr(engine, 'cleanup'):
                engine.cleanup()
            return True
        except Exception:
            return False
