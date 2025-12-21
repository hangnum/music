# -*- coding: utf-8 -*-
"""
Single Instance Application Manager

Uses QLocalServer/QLocalSocket to implement single-instance detection and inter-process communication.
When a second instance starts, it sends an activation message to the primary instance and then exits.

Usage Example:
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
    """Single Instance Application Manager
    
    Uses local sockets for inter-process communication to ensure only one instance of the app runs.
    
    Attributes:
        activation_requested: Signal emitted when another instance requests activation.
    """
    
    # Emitted when another instance requests activation of the main window
    activation_requested = pyqtSignal()
    
    # Content of the activation message
    _ACTIVATION_MESSAGE = b"ACTIVATE"
    
    # Connection timeout (milliseconds)
    _CONNECTION_TIMEOUT_MS = 1000
    
    def __init__(self, app_key: str, parent: Optional[QObject] = None):
        """Initialize the single instance manager
        
        Args:
            app_key: Unique identifier for the application, used to create the local server name.
            parent: Parent QObject
        """
        super().__init__(parent)
        self._app_key = app_key
        self._server: Optional[QLocalServer] = None
        
        logger.debug("SingleInstanceManager initialized, app_key=%s", app_key)
    
    def is_running(self) -> bool:
        """Check if another instance is already running
        
        Detected by attempting to connect to a local server. A successful connection means an instance is already running.
        
        Returns:
            True if another instance is running, False otherwise.
        """
        socket = QLocalSocket()
        socket.connectToServer(self._app_key)
        
        is_connected = socket.waitForConnected(self._CONNECTION_TIMEOUT_MS)
        
        if is_connected:
            logger.info("Existing instance detected running")
            socket.disconnectFromServer()
        else:
            logger.debug("No running instance detected")
        
        return is_connected
    
    def send_activation_message(self) -> bool:
        """Send an activation message to the primary instance
        
        Connects to the primary instance's server and sends an activation request.
        
        Returns:
            True if the message was sent successfully, False otherwise.
        """
        socket = QLocalSocket()
        socket.connectToServer(self._app_key)
        
        if not socket.waitForConnected(self._CONNECTION_TIMEOUT_MS):
            logger.error("Could not connect to primary instance: %s", socket.errorString())
            return False
        
        # Send activation message
        socket.write(self._ACTIVATION_MESSAGE)
        socket.flush()
        
        if not socket.waitForBytesWritten(self._CONNECTION_TIMEOUT_MS):
            logger.error("Failed to send activation message: %s", socket.errorString())
            socket.disconnectFromServer()
            return False
        
        logger.info("Activation request sent to primary instance")
        socket.disconnectFromServer()
        return True
    
    def start_server(self) -> bool:
        """Start the local server
        
        Creates and starts a local server to listen for connections from other instances.
        
        Returns:
            True if server started successfully, False otherwise.
        """
        self._server = QLocalServer(self)
        
        # Remove any leftover server file (e.g., from a previous crash)
        QLocalServer.removeServer(self._app_key)
        
        if not self._server.listen(self._app_key):
            logger.error(
                "Could not start local server: %s", 
                self._server.errorString()
            )
            return False
        
        # Connect new connection signal
        self._server.newConnection.connect(self._on_new_connection)
        
        logger.info("Local server started, listening on: %s", self._app_key)
        return True
    
    def _on_new_connection(self) -> None:
        """Handle new connection requests"""
        if self._server is None:
            return
        
        socket = self._server.nextPendingConnection()
        if socket is None:
            return
        
        # Wait for data reception
        if socket.waitForReadyRead(self._CONNECTION_TIMEOUT_MS):
            data = socket.readAll().data()
            
            if data == self._ACTIVATION_MESSAGE:
                logger.info("Activation request received, emitting activation_requested signal")
                self.activation_requested.emit()
            else:
                logger.warning("Received unknown message: %s", data)
        
        socket.disconnectFromServer()
    
    def cleanup(self) -> None:
        """Clean up resources
        
        Closes the server and removes the server file. Typically called when the application exits.
        """
        if self._server is not None:
            self._server.close()
            QLocalServer.removeServer(self._app_key)
            logger.debug("Local server closed")
