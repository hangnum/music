"""
新建歌单对话框

用于创建新播放列表，输入名称和描述。
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QPushButton, QFormLayout
)
from PyQt6.QtCore import Qt


class CreatePlaylistDialog(QDialog):
    """
    新建歌单对话框
    
    提供创建播放列表的表单。
    
    使用示例:
        dialog = CreatePlaylistDialog(parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = dialog.get_name()
            description = dialog.get_description()
    """
    
    def __init__(self, parent=None, edit_mode: bool = False, 
                 initial_name: str = "", initial_description: str = ""):
        """
        初始化对话框
        
        Args:
            parent: 父窗口
            edit_mode: 是否为编辑模式
            initial_name: 初始名称（编辑模式使用）
            initial_description: 初始描述（编辑模式使用）
        """
        super().__init__(parent)
        
        self._edit_mode = edit_mode
        self._initial_name = initial_name
        self._initial_description = initial_description
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置 UI"""
        title = "编辑歌单" if self._edit_mode else "新建歌单"
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # 表单
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        # 名称输入
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("输入歌单名称")
        self.name_input.setText(self._initial_name)
        form_layout.addRow("名称:", self.name_input)
        
        # 描述输入
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("添加描述（可选）")
        self.desc_input.setMaximumHeight(100)
        self.desc_input.setPlainText(self._initial_description)
        form_layout.addRow("描述:", self.desc_input)
        
        layout.addLayout(form_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.confirm_btn = QPushButton("确定")
        self.confirm_btn.setDefault(True)
        self.confirm_btn.clicked.connect(self._on_confirm)
        button_layout.addWidget(self.confirm_btn)
        
        layout.addLayout(button_layout)
        
        # 连接信号
        self.name_input.textChanged.connect(self._update_confirm_state)
        self._update_confirm_state()
    
    def _update_confirm_state(self):
        """更新确认按钮状态"""
        has_name = bool(self.name_input.text().strip())
        self.confirm_btn.setEnabled(has_name)
    
    def _on_confirm(self):
        """确认按钮点击"""
        if self.name_input.text().strip():
            self.accept()
    
    def get_name(self) -> str:
        """获取输入的名称"""
        return self.name_input.text().strip()
    
    def get_description(self) -> str:
        """获取输入的描述"""
        return self.desc_input.toPlainText().strip()
