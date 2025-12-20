"""
每日歌单对话框

用于生成基于标签的今日歌单。
"""

from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from models.track import Track
from services.config_service import ConfigService
from services.daily_playlist_service import DailyPlaylistResult, DailyPlaylistService
from services.library_service import LibraryService
from services.player_service import PlayerService
from services.playlist_service import PlaylistService
from services.tag_service import TagService
from services.llm_providers import create_llm_provider


class _GenerateWorker(QObject):
    """后台生成歌单的工作线程"""
    
    finished = pyqtSignal(object, object)  # result, error
    
    def __init__(
        self,
        service: DailyPlaylistService,
        tags: List[str],
        limit: int,
    ):
        super().__init__()
        self._service = service
        self._tags = tags
        self._limit = limit
    
    def run(self) -> None:
        try:
            result = self._service.generate(self._tags, limit=self._limit)
            self.finished.emit(result, None)
        except Exception as e:
            self.finished.emit(None, e)


class DailyPlaylistDialog(QDialog):
    """
    每日歌单对话框
    
    允许用户选择标签或输入描述，生成今日歌单。
    """
    
    playlist_generated = pyqtSignal(list)  # List[Track]
    
    def __init__(
        self,
        tag_service: TagService,
        library_service: LibraryService,
        config_service: ConfigService,
        player_service: Optional[PlayerService] = None,
        playlist_service: Optional[PlaylistService] = None,
        parent=None,
    ):
        super().__init__(parent)
        
        self._tag_service = tag_service
        self._library_service = library_service
        self._config_service = config_service
        self._player_service = player_service
        self._playlist_service = playlist_service
        
        self._result: Optional[DailyPlaylistResult] = None
        self._thread: Optional[QThread] = None
        self._worker: Optional[_GenerateWorker] = None
        
        self.setWindowTitle("每日歌单")
        self.setMinimumSize(700, 600)
        
        self._setup_styles()
        self._setup_ui()
        self._load_tags()
    
    def _setup_styles(self):
        """设置现代化样式"""
        self.setStyleSheet("""
            DailyPlaylistDialog {
                background-color: #121722;
            }
            QGroupBox {
                color: #E6E8EC;
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #253043;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
            QLabel {
                color: #9AA2AF;
            }
            QLabel#titleLabel {
                color: #E6E8EC;
                font-size: 20px;
                font-weight: bold;
            }
            QLabel#subtitleLabel {
                color: #6C7686;
                font-size: 13px;
            }
            QLabel#summaryLabel {
                color: #3FB7A6;
                font-size: 13px;
            }
            QLineEdit {
                background-color: #141923;
                border: 1px solid #263041;
                border-radius: 6px;
                padding: 10px;
                color: #E6E8EC;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #3FB7A6;
            }
            QSpinBox {
                background-color: #141923;
                border: 1px solid #263041;
                border-radius: 6px;
                padding: 8px;
                color: #E6E8EC;
            }
            QCheckBox {
                color: #9AA2AF;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #3A465C;
                background-color: #1C2734;
            }
            QCheckBox::indicator:checked {
                background-color: #3FB7A6;
                border-color: #3FB7A6;
            }
            QCheckBox:hover {
                color: #E6E8EC;
            }
            QPushButton#generateBtn {
                background-color: #3FB7A6;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 14px 32px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton#generateBtn:hover {
                background-color: #5BC0B0;
            }
            QPushButton#generateBtn:pressed {
                background-color: #2FA191;
            }
            QPushButton#generateBtn:disabled {
                background-color: #3A465C;
                color: #7B8595;
            }
            QPushButton#actionBtn {
                background-color: #1C2734;
                color: #E6E8EC;
                border: 1px solid #3A465C;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
            }
            QPushButton#actionBtn:hover {
                background-color: #263041;
            }
            QPushButton#actionBtn:disabled {
                color: #5A6473;
            }
            QListWidget {
                background-color: #151B26;
                border: 1px solid #253043;
                border-radius: 8px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-radius: 4px;
                color: #E6E8EC;
            }
            QListWidget::item:hover {
                background-color: #1C2734;
            }
            QListWidget::item:selected {
                background-color: #3FB7A6;
            }
            QProgressBar {
                border: none;
                background-color: #1C2734;
                border-radius: 4px;
                height: 6px;
            }
            QProgressBar::chunk {
                background-color: #3FB7A6;
                border-radius: 4px;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
    
    def _setup_ui(self):
        """设置 UI 布局"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # 标题区
        title = QLabel("🎵 今天想听什么？")
        title.setObjectName("titleLabel")
        
        subtitle = QLabel("选择标签或输入描述，生成专属今日歌单")
        subtitle.setObjectName("subtitleLabel")
        
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(8)
        
        # 标签输入区
        tag_group = QGroupBox("选择标签")
        tag_layout = QVBoxLayout(tag_group)
        
        # 搜索过滤
        self._tag_filter = QLineEdit()
        self._tag_filter.setPlaceholderText("🔍 搜索标签...")
        self._tag_filter.textChanged.connect(self._filter_tags)
        tag_layout.addWidget(self._tag_filter)
        
        # 标签滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(180)
        
        self._tag_container = QWidget()
        self._tag_grid = QGridLayout(self._tag_container)
        self._tag_grid.setSpacing(8)
        scroll.setWidget(self._tag_container)
        
        tag_layout.addWidget(scroll)
        
        # 手动输入标签
        manual_label = QLabel("或手动输入标签（逗号分隔）:")
        manual_label.setStyleSheet("font-size: 12px;")
        self._manual_tags = QLineEdit()
        self._manual_tags.setPlaceholderText("例如: 流行, 轻松, 周杰伦")
        
        tag_layout.addWidget(manual_label)
        tag_layout.addWidget(self._manual_tags)
        
        layout.addWidget(tag_group)
        
        # 选项区
        options_layout = QHBoxLayout()
        
        limit_label = QLabel("歌单数量:")
        self._limit_spin = QSpinBox()
        self._limit_spin.setRange(10, 100)
        self._limit_spin.setValue(50)
        self._limit_spin.setSuffix(" 首")
        
        options_layout.addWidget(limit_label)
        options_layout.addWidget(self._limit_spin)
        options_layout.addStretch()
        
        layout.addLayout(options_layout)
        
        # 生成按钮
        self._generate_btn = QPushButton("✨ 生成歌单")
        self._generate_btn.setObjectName("generateBtn")
        self._generate_btn.clicked.connect(self._on_generate)
        layout.addWidget(self._generate_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # 进度条
        self._progress = QProgressBar()
        self._progress.setFixedHeight(6)
        self._progress.setRange(0, 0)  # 不确定进度
        self._progress.hide()
        layout.addWidget(self._progress)
        
        # 结果区
        self._result_group = QGroupBox("生成结果")
        result_layout = QVBoxLayout(self._result_group)
        
        self._summary_label = QLabel("")
        self._summary_label.setObjectName("summaryLabel")
        result_layout.addWidget(self._summary_label)
        
        self._track_list = QListWidget()
        self._track_list.setMinimumHeight(150)
        result_layout.addWidget(self._track_list)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        self._play_btn = QPushButton("▶ 立即播放")
        self._play_btn.setObjectName("actionBtn")
        self._play_btn.clicked.connect(self._on_play)
        self._play_btn.setEnabled(False)
        
        self._save_btn = QPushButton("💾 保存为播放列表")
        self._save_btn.setObjectName("actionBtn")
        self._save_btn.clicked.connect(self._on_save)
        self._save_btn.setEnabled(False)
        
        btn_layout.addWidget(self._play_btn)
        btn_layout.addWidget(self._save_btn)
        btn_layout.addStretch()
        
        result_layout.addLayout(btn_layout)
        
        self._result_group.hide()
        layout.addWidget(self._result_group)
        
        # 存储标签复选框
        self._tag_checkboxes: List[QCheckBox] = []
    
    def _load_tags(self):
        """加载所有标签"""
        tags = self._tag_service.get_all_tags()
        
        # 清除旧的复选框
        for cb in self._tag_checkboxes:
            cb.deleteLater()
        self._tag_checkboxes.clear()
        
        # 创建新的复选框
        row, col = 0, 0
        cols_per_row = 4
        
        for tag in tags:
            cb = QCheckBox(tag.name)
            cb.setProperty("tag_name", tag.name)
            self._tag_grid.addWidget(cb, row, col)
            self._tag_checkboxes.append(cb)
            
            col += 1
            if col >= cols_per_row:
                col = 0
                row += 1
        
        if not tags:
            no_tag_label = QLabel("暂无标签，请先为音乐添加标签")
            no_tag_label.setStyleSheet("color: #6C7686;")
            self._tag_grid.addWidget(no_tag_label, 0, 0)
    
    def _filter_tags(self, text: str):
        """过滤标签"""
        needle = text.strip().lower()
        for cb in self._tag_checkboxes:
            tag_name = cb.property("tag_name") or ""
            cb.setVisible(not needle or needle in tag_name.lower())
    
    def _get_selected_tags(self) -> List[str]:
        """获取选中的标签"""
        selected = []
        
        # 从复选框获取
        for cb in self._tag_checkboxes:
            if cb.isChecked():
                tag_name = cb.property("tag_name")
                if tag_name:
                    selected.append(tag_name)
        
        # 从手动输入获取
        manual = self._manual_tags.text().strip()
        if manual:
            parts = [p.strip() for p in manual.replace("，", ",").split(",")]
            selected.extend([p for p in parts if p and p not in selected])
        
        return selected
    
    def _on_generate(self):
        """生成歌单"""
        if self._thread and self._thread.isRunning():
            return
        
        tags = self._get_selected_tags()
        limit = self._limit_spin.value()
        
        if not tags:
            QMessageBox.warning(
                self,
                "提示",
                "请至少选择一个标签或输入标签描述"
            )
            return
        
        self._set_busy(True)
        
        # 创建 LLM Provider
        try:
            llm_provider = create_llm_provider(self._config_service)
        except Exception:
            llm_provider = None
        
        # 创建服务
        service = DailyPlaylistService(
            tag_service=self._tag_service,
            library_service=self._library_service,
            llm_provider=llm_provider,
        )
        
        # 启动后台线程
        self._thread = QThread(self)
        self._worker = _GenerateWorker(service, tags, limit)
        self._worker.moveToThread(self._thread)
        
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_generate_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()
    
    def _set_busy(self, busy: bool):
        """设置忙碌状态"""
        self._generate_btn.setEnabled(not busy)
        self._progress.setVisible(busy)
        if busy:
            self._result_group.hide()
    
    def _cleanup_thread(self):
        """清理线程"""
        if self._worker:
            self._worker.deleteLater()
        if self._thread:
            self._thread.deleteLater()
        self._worker = None
        self._thread = None
    
    def _on_generate_finished(
        self,
        result: Optional[DailyPlaylistResult],
        error: Optional[BaseException],
    ):
        """生成完成回调"""
        self._set_busy(False)
        
        if error:
            QMessageBox.critical(self, "生成失败", str(error))
            return
        
        if not result or not result.tracks:
            QMessageBox.information(
                self,
                "提示",
                "未能找到匹配的音乐，请尝试其他标签或确保音乐库中有足够的带标签曲目。"
            )
            return
        
        self._result = result
        self._display_result(result)
    
    def _display_result(self, result: DailyPlaylistResult):
        """显示生成结果"""
        self._summary_label.setText(f"共 {result.total} 首 · {result.summary}")
        
        self._track_list.clear()
        for i, track in enumerate(result.tracks, 1):
            artist = getattr(track, 'artist', '') or '未知艺术家'
            text = f"{i}. {track.title} - {artist}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, track.id)
            self._track_list.addItem(item)
        
        self._play_btn.setEnabled(True)
        self._save_btn.setEnabled(self._playlist_service is not None)
        self._result_group.show()
        
        # 发送信号
        self.playlist_generated.emit(result.tracks)
    
    def _on_play(self):
        """立即播放"""
        if not self._result or not self._result.tracks:
            return
        
        if not self._player_service:
            QMessageBox.warning(self, "提示", "播放服务不可用")
            return
        
        try:
            self._player_service.set_queue(self._result.tracks, 0)
            self._player_service.play_pause()
            self.accept()  # 关闭对话框
        except Exception as e:
            QMessageBox.critical(self, "播放失败", str(e))
    
    def _on_save(self):
        """保存为播放列表"""
        if not self._result or not self._result.tracks:
            return
        
        if not self._playlist_service:
            QMessageBox.warning(self, "提示", "播放列表服务不可用")
            return
        
        # 生成播放列表名称
        from datetime import datetime
        name = f"每日歌单 {datetime.now().strftime('%Y-%m-%d')}"
        
        try:
            playlist = self._playlist_service.create_playlist(name)
            if playlist:
                track_ids = [t.id for t in self._result.tracks]
                for track_id in track_ids:
                    self._playlist_service.add_track_to_playlist(playlist.id, track_id)
                
                QMessageBox.information(
                    self, 
                    "保存成功", 
                    f"播放列表 \"{name}\" 已创建，包含 {len(track_ids)} 首歌曲"
                )
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))
    
    def closeEvent(self, event):
        """关闭时清理"""
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(5000)
        self._cleanup_thread()
        event.accept()
