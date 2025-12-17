"""
标签管理对话框

用于为曲目添加和管理标签。
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QColorDialog, QMessageBox, QWidget, QCheckBox,
    QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from typing import List, Optional

from models.track import Track
from models.tag import Tag
from services.tag_service import TagService
from core.database import DatabaseManager


class TagChip(QWidget):
    """标签芯片组件"""
    
    toggled = pyqtSignal(str, bool)  # tag_id, is_checked
    
    def __init__(self, tag: Tag, checked: bool = False, parent=None):
        super().__init__(parent)
        self.tag = tag
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(checked)
        self.checkbox.stateChanged.connect(self._on_state_changed)
        layout.addWidget(self.checkbox)
        
        # 颜色指示器
        color_dot = QLabel("●")
        color_dot.setStyleSheet(f"color: {tag.color}; font-size: 12px;")
        layout.addWidget(color_dot)
        
        # 标签名
        name_label = QLabel(tag.name)
        name_label.setStyleSheet("color: #E0E0E0;")
        layout.addWidget(name_label)
        
        layout.addStretch()
    
    def _on_state_changed(self):
        self.toggled.emit(self.tag.id, self.checkbox.isChecked())
    
    def set_checked(self, checked: bool):
        self.checkbox.setChecked(checked)


class TagDialog(QDialog):
    """
    标签管理对话框
    
    用于管理选中曲目的标签。
    """
    
    tags_updated = pyqtSignal()  # 标签更新后发出信号
    
    def __init__(self, tracks: List[Track], 
                 tag_service: Optional[TagService] = None,
                 parent=None):
        super().__init__(parent)
        
        self.tracks = tracks
        self.tag_service = tag_service or TagService(DatabaseManager())
        
        # 记录每个标签的选中状态：tag_id -> bool
        self._tag_states: dict[str, bool] = {}
        # 记录初始状态，用于检测变化
        self._initial_states: dict[str, bool] = {}
        
        self._setup_ui()
        self._load_tags()
    
    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("管理标签")
        self.setMinimumWidth(400)
        self.setMinimumHeight(500)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # 标题
        if len(self.tracks) == 1:
            title_text = f"为 \"{self.tracks[0].title}\" 管理标签"
        else:
            title_text = f"为 {len(self.tracks)} 首曲目管理标签"
        
        title = QLabel(title_text)
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #E0E0E0;")
        title.setWordWrap(True)
        layout.addWidget(title)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #333;")
        layout.addWidget(line)
        
        # 标签列表区域
        tags_label = QLabel("选择标签:")
        tags_label.setStyleSheet("color: #B0B0B0;")
        layout.addWidget(tags_label)
        
        # 可滚动的标签列表
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { 
                border: 1px solid #333; 
                border-radius: 8px;
                background-color: #1A1A1A;
            }
        """)
        
        self.tags_container = QWidget()
        self.tags_layout = QVBoxLayout(self.tags_container)
        self.tags_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.tags_layout.setSpacing(8)
        scroll.setWidget(self.tags_container)
        
        layout.addWidget(scroll, 1)
        
        # 分隔线
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet("background-color: #333;")
        layout.addWidget(line2)
        
        # 创建新标签区域
        create_label = QLabel("创建新标签:")
        create_label.setStyleSheet("color: #B0B0B0;")
        layout.addWidget(create_label)
        
        create_row = QHBoxLayout()
        
        self.new_tag_input = QLineEdit()
        self.new_tag_input.setPlaceholderText("输入标签名...")
        self.new_tag_input.setStyleSheet("""
            QLineEdit {
                background-color: #2A2A2A;
                border: 1px solid #404040;
                border-radius: 6px;
                padding: 8px 12px;
                color: #E0E0E0;
            }
            QLineEdit:focus {
                border-color: #0A84FF;
            }
        """)
        create_row.addWidget(self.new_tag_input, 1)
        
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(36, 36)
        self._current_color = "#808080"
        self._update_color_button()
        self.color_btn.clicked.connect(self._pick_color)
        create_row.addWidget(self.color_btn)
        
        self.add_btn = QPushButton("添加")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #0A84FF;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #006ADB;
            }
        """)
        self.add_btn.clicked.connect(self._create_tag)
        create_row.addWidget(self.add_btn)
        
        layout.addLayout(create_row)
        
        # 底部按钮
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A3A3A;
                color: #E0E0E0;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
            }
            QPushButton:hover {
                background-color: #4A4A4A;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("保存")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #30D158;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #28B84C;
            }
        """)
        save_btn.clicked.connect(self._save)
        buttons_layout.addWidget(save_btn)
        
        layout.addLayout(buttons_layout)
        
        # 设置对话框样式
        self.setStyleSheet("""
            QDialog {
                background-color: #1C1C1E;
            }
        """)
    
    def _update_color_button(self):
        """更新颜色按钮显示"""
        self.color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._current_color};
                border: 2px solid #555;
                border-radius: 18px;
            }}
            QPushButton:hover {{
                border-color: #888;
            }}
        """)
    
    def _pick_color(self):
        """打开颜色选择器"""
        color = QColorDialog.getColor(
            QColor(self._current_color), 
            self, 
            "选择标签颜色"
        )
        if color.isValid():
            self._current_color = color.name()
            self._update_color_button()
    
    def _load_tags(self):
        """加载所有标签并显示"""
        # 清空现有标签
        while self.tags_layout.count():
            item = self.tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        all_tags = self.tag_service.get_all_tags()
        
        if not all_tags:
            empty = QLabel("暂无标签，请先创建")
            empty.setStyleSheet("color: #666; padding: 20px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tags_layout.addWidget(empty)
            return
        
        # 获取选中曲目已有的标签
        track_tag_ids = set()
        for track in self.tracks:
            tags = self.tag_service.get_track_tags(track.id)
            for tag in tags:
                track_tag_ids.add(tag.id)
        
        # 创建标签芯片
        for tag in all_tags:
            is_checked = tag.id in track_tag_ids
            chip = TagChip(tag, is_checked, self)
            chip.toggled.connect(self._on_tag_toggled)
            self.tags_layout.addWidget(chip)
            
            self._tag_states[tag.id] = is_checked
            self._initial_states[tag.id] = is_checked
    
    def _on_tag_toggled(self, tag_id: str, is_checked: bool):
        """标签选中状态变化"""
        self._tag_states[tag_id] = is_checked
    
    def _create_tag(self):
        """创建新标签"""
        name = self.new_tag_input.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入标签名称")
            return
        
        # 检查是否已存在
        existing = self.tag_service.get_tag_by_name(name)
        if existing:
            QMessageBox.warning(self, "提示", f"标签 \"{name}\" 已存在")
            return
        
        # 创建标签
        tag = self.tag_service.create_tag(name, self._current_color)
        if tag:
            self.new_tag_input.clear()
            self._current_color = "#808080"
            self._update_color_button()
            
            # 重新加载标签列表
            self._load_tags()
            
            # 自动选中新创建的标签
            self._tag_states[tag.id] = True
            self._update_chip_state(tag.id, True)
    
    def _update_chip_state(self, tag_id: str, checked: bool):
        """更新指定标签芯片的选中状态"""
        for i in range(self.tags_layout.count()):
            widget = self.tags_layout.itemAt(i).widget()
            if isinstance(widget, TagChip) and widget.tag.id == tag_id:
                widget.set_checked(checked)
                break
    
    def _save(self):
        """保存标签变更"""
        # 找出需要添加和移除的标签
        tags_to_add = []
        tags_to_remove = []
        
        for tag_id, is_checked in self._tag_states.items():
            initial = self._initial_states.get(tag_id, False)
            if is_checked and not initial:
                tags_to_add.append(tag_id)
            elif not is_checked and initial:
                tags_to_remove.append(tag_id)
        
        # 为每个曲目应用变更
        for track in self.tracks:
            for tag_id in tags_to_add:
                self.tag_service.add_tag_to_track(track.id, tag_id)
            for tag_id in tags_to_remove:
                self.tag_service.remove_tag_from_track(track.id, tag_id)
        
        self.tags_updated.emit()
        self.accept()
