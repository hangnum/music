# -*- coding: utf-8 -*-
"""
单实例应用管理器

使用 QLocalServer/QLocalSocket 实现单实例检测和进程间通信。
当第二个实例启动时，会向主实例发送激活消息，然后退出。

使用示例:
    from core.single_instance import SingleInstanceManager
    
    manager = SingleInstanceManager("MyApp")
    if manager.is_running():
        manager.send_activation_message()
        sys.exit(0)
    
    manager.start_server()
    manager.activation_requested.connect(window.activate_from_external)
"""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

logger = logging.getLogger(__name__)


class SingleInstanceManager(QObject):
    """单实例应用管理器
    
    使用本地套接字实现进程间通信，确保应用只运行一个实例。
    
    Attributes:
        activation_requested: 当其他实例请求激活时发射的信号
    """
    
    # 当其他实例请求激活主窗口时发射
    activation_requested = pyqtSignal()
    
    # 激活消息的内容
    _ACTIVATION_MESSAGE = b"ACTIVATE"
    
    # 连接超时时间（毫秒）
    _CONNECTION_TIMEOUT_MS = 1000
    
    def __init__(self, app_key: str, parent: Optional[QObject] = None):
        """初始化单实例管理器
        
        Args:
            app_key: 应用程序的唯一标识符，用于创建本地服务器名称
            parent: 父 QObject
        """
        super().__init__(parent)
        self._app_key = app_key
        self._server: Optional[QLocalServer] = None
        
        logger.debug("SingleInstanceManager 初始化，app_key=%s", app_key)
    
    def is_running(self) -> bool:
        """检测是否已有实例在运行
        
        通过尝试连接本地服务器来检测。如果连接成功，说明已有实例在运行。
        
        Returns:
            True 如果已有实例在运行，False 否则
        """
        socket = QLocalSocket()
        socket.connectToServer(self._app_key)
        
        is_connected = socket.waitForConnected(self._CONNECTION_TIMEOUT_MS)
        
        if is_connected:
            logger.info("检测到已有实例在运行")
            socket.disconnectFromServer()
        else:
            logger.debug("未检测到运行中的实例")
        
        return is_connected
    
    def send_activation_message(self) -> bool:
        """向主实例发送激活消息
        
        连接到主实例的服务器并发送激活请求。
        
        Returns:
            True 如果消息发送成功，False 否则
        """
        socket = QLocalSocket()
        socket.connectToServer(self._app_key)
        
        if not socket.waitForConnected(self._CONNECTION_TIMEOUT_MS):
            logger.error("无法连接到主实例: %s", socket.errorString())
            return False
        
        # 发送激活消息
        socket.write(self._ACTIVATION_MESSAGE)
        socket.flush()
        
        if not socket.waitForBytesWritten(self._CONNECTION_TIMEOUT_MS):
            logger.error("发送激活消息失败: %s", socket.errorString())
            socket.disconnectFromServer()
            return False
        
        logger.info("已向主实例发送激活请求")
        socket.disconnectFromServer()
        return True
    
    def start_server(self) -> bool:
        """启动本地服务器
        
        创建并启动本地服务器，监听来自其他实例的连接。
        
        Returns:
            True 如果服务器启动成功，False 否则
        """
        self._server = QLocalServer(self)
        
        # 移除可能残留的旧服务器（例如上次崩溃后遗留的）
        QLocalServer.removeServer(self._app_key)
        
        if not self._server.listen(self._app_key):
            logger.error(
                "无法启动本地服务器: %s", 
                self._server.errorString()
            )
            return False
        
        # 连接新连接信号
        self._server.newConnection.connect(self._on_new_connection)
        
        logger.info("本地服务器已启动，监听: %s", self._app_key)
        return True
    
    def _on_new_connection(self) -> None:
        """处理新的连接请求"""
        if self._server is None:
            return
        
        socket = self._server.nextPendingConnection()
        if socket is None:
            return
        
        # 等待接收数据
        if socket.waitForReadyRead(self._CONNECTION_TIMEOUT_MS):
            data = socket.readAll().data()
            
            if data == self._ACTIVATION_MESSAGE:
                logger.info("收到激活请求，发射 activation_requested 信号")
                self.activation_requested.emit()
            else:
                logger.warning("收到未知消息: %s", data)
        
        socket.disconnectFromServer()
    
    def cleanup(self) -> None:
        """清理资源
        
        关闭服务器并移除服务器文件。通常在应用退出时调用。
        """
        if self._server is not None:
            self._server.close()
            QLocalServer.removeServer(self._app_key)
            logger.debug("本地服务器已关闭")
