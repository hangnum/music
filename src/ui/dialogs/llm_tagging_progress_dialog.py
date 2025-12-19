"""
LLM 标签标注进度对话框

显示 LLM 批量标签标注任务的进度，支持启用网络搜索增强。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QCheckBox, QGroupBox,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

if TYPE_CHECKING:
    from services.llm_tagging_service import LLMTaggingService, TaggingJobStatus

logger = logging.getLogger(__name__)


class LLMTaggingProgressDialog(QDialog):
    """
    LLM 标签标注进度对话框
    
    用于启动和监控 LLM 批量标签标注任务。
    支持网络搜索增强功能。
    """
    
    # 任务完成信号
    tagging_completed = pyqtSignal(dict)
    
    def __init__(
        self,
        llm_tagging_service: "LLMTaggingService",
        parent=None,
    ):
        super().__init__(parent)
        
        self._service = llm_tagging_service
        self._current_job_id: Optional[str] = None
        self._poll_timer: Optional[QTimer] = None
        
        self.setWindowTitle("AI 标签标注")
        self.setMinimumWidth(450)
        self.setModal(True)
        
        self._setup_ui()
        self._update_stats()
    
    def _setup_ui(self):
        """设置 UI 布局"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # === 统计信息 ===
        stats_group = QGroupBox("标注统计")
        stats_layout = QVBoxLayout(stats_group)
        
        self._stats_label = QLabel("正在加载...")
        self._stats_label.setWordWrap(True)
        stats_layout.addWidget(self._stats_label)
        
        layout.addWidget(stats_group)
        
        # === 设置选项 ===
        options_group = QGroupBox("标注选项")
        options_layout = QVBoxLayout(options_group)
        
        self._web_search_checkbox = QCheckBox("启用网络搜索增强")
        self._web_search_checkbox.setToolTip(
            "使用 DuckDuckGo 搜索获取歌曲额外信息，\n"
            "可以更准确地判断音乐风格和特征。\n"
            "注意：这会增加标注时间。"
        )
        options_layout.addWidget(self._web_search_checkbox)
        
        layout.addWidget(options_group)
        
        # === 进度信息 ===
        progress_group = QGroupBox("标注进度")
        progress_layout = QVBoxLayout(progress_group)
        
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        progress_layout.addWidget(self._progress_bar)
        
        self._progress_label = QLabel("就绪")
        self._progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self._progress_label)
        
        layout.addWidget(progress_group)
        
        # === 按钮 ===
        button_layout = QHBoxLayout()
        
        self._start_btn = QPushButton("开始标注")
        self._start_btn.clicked.connect(self._on_start_clicked)
        self._start_btn.setDefault(True)
        button_layout.addWidget(self._start_btn)
        
        self._stop_btn = QPushButton("停止")
        self._stop_btn.clicked.connect(self._on_stop_clicked)
        self._stop_btn.setEnabled(False)
        button_layout.addWidget(self._stop_btn)
        
        self._close_btn = QPushButton("关闭")
        self._close_btn.clicked.connect(self.close)
        button_layout.addWidget(self._close_btn)
        
        layout.addLayout(button_layout)
    
    def _update_stats(self):
        """更新统计信息"""
        try:
            stats = self._service.get_tagging_stats()
            tagged = stats.get("tagged_tracks", 0)
            total = stats.get("total_tracks", 0)
            llm_tags = stats.get("llm_tags", 0)
            untagged = total - tagged
            
            self._stats_label.setText(
                f"总曲目: {total} | "
                f"已标注: {tagged} | "
                f"待标注: {untagged}\n"
                f"AI 生成标签数: {llm_tags}"
            )
            
            # 如果没有待标注曲目，禁用开始按钮
            if untagged == 0:
                self._start_btn.setEnabled(False)
                self._start_btn.setText("已全部标注")
            else:
                self._start_btn.setEnabled(True)
                self._start_btn.setText(f"开始标注 ({untagged} 首)")
                
        except Exception as e:
            logger.warning("获取统计信息失败: %s", e)
            self._stats_label.setText("获取统计信息失败")
    
    def _on_start_clicked(self):
        """点击开始按钮"""
        use_web_search = self._web_search_checkbox.isChecked()
        
        try:
            # 进度回调（在后台线程调用，通过 QTimer 更新 UI）
            def progress_callback(current: int, total: int):
                # 这个回调在后台线程，不能直接更新 UI
                pass
            
            # 启动任务
            job_id = self._service.start_tagging_job(
                progress_callback=progress_callback,
                batch_size=30,  # 如果启用搜索，用较小的批次
                tags_per_track=5,
                use_web_search=use_web_search,
            )
            
            if not job_id:
                QMessageBox.information(
                    self, "提示",
                    "没有需要标注的曲目"
                )
                return
            
            self._current_job_id = job_id
            
            # 更新 UI 状态
            self._start_btn.setEnabled(False)
            self._stop_btn.setEnabled(True)
            self._web_search_checkbox.setEnabled(False)
            self._progress_label.setText("正在标注...")
            
            # 启动轮询定时器
            self._poll_timer = QTimer(self)
            self._poll_timer.timeout.connect(self._poll_progress)
            self._poll_timer.start(1000)  # 每秒更新
            
        except Exception as e:
            logger.error("启动标注任务失败: %s", e)
            QMessageBox.critical(
                self, "错误",
                f"启动标注任务失败：{e}"
            )
    
    def _on_stop_clicked(self):
        """点击停止按钮"""
        if self._current_job_id:
            self._service.stop_job(self._current_job_id)
            self._progress_label.setText("正在停止...")
            self._stop_btn.setEnabled(False)
    
    def _poll_progress(self):
        """轮询任务进度"""
        if not self._current_job_id:
            return
        
        status = self._service.get_job_status(self._current_job_id)
        if not status:
            return
        
        # 更新进度
        progress_percent = int(status.progress * 100)
        self._progress_bar.setValue(progress_percent)
        self._progress_label.setText(
            f"{status.processed_tracks} / {status.total_tracks} "
            f"({progress_percent}%)"
        )
        
        # 检查是否完成
        if status.status in ("completed", "failed", "stopped"):
            self._on_job_finished(status)
    
    def _on_job_finished(self, status: "TaggingJobStatus"):
        """任务完成处理"""
        # 停止定时器
        if self._poll_timer:
            self._poll_timer.stop()
            self._poll_timer = None
        
        # 更新 UI
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._web_search_checkbox.setEnabled(True)
        
        # 显示结果
        if status.status == "completed":
            self._progress_label.setText("标注完成！")
            self._progress_bar.setValue(100)
            QMessageBox.information(
                self, "完成",
                f"标注完成！\n共处理 {status.processed_tracks} 首曲目"
            )
        elif status.status == "stopped":
            self._progress_label.setText("已停止")
            QMessageBox.information(
                self, "已停止",
                f"任务已停止\n已处理 {status.processed_tracks} / {status.total_tracks} 首曲目"
            )
        elif status.status == "failed":
            self._progress_label.setText("标注失败")
            error_msg = status.error_message or "未知错误"
            QMessageBox.critical(
                self, "失败",
                f"标注失败：{error_msg}"
            )
        
        # 更新统计
        self._update_stats()
        
        # 发送完成信号
        self.tagging_completed.emit({
            "job_id": status.job_id,
            "status": status.status,
            "processed": status.processed_tracks,
            "total": status.total_tracks,
        })
        
        self._current_job_id = None
    
    def closeEvent(self, event):
        """关闭事件"""
        # 如果任务正在运行，询问是否停止
        if self._current_job_id:
            reply = QMessageBox.question(
                self, "确认",
                "标注任务正在运行，确定要关闭吗？\n任务将在后台继续运行。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
        
        # 停止定时器
        if self._poll_timer:
            self._poll_timer.stop()
        
        event.accept()
