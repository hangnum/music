"""
Create Playlist Dialog

Used for creating new playlists by entering name and description.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QPushButton, QFormLayout
)
from PyQt6.QtCore import Qt


class CreatePlaylistDialog(QDialog):
    """
    Create Playlist Dialog

    Provides a form for creating playlists.

    Usage Example:
        dialog = CreatePlaylistDialog(parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = dialog.get_name()
            description = dialog.get_description()
    """
    
    def __init__(self, parent=None, edit_mode: bool = False,
                 initial_name: str = "", initial_description: str = ""):
        """
        Initialize dialog

        Args:
            parent: Parent window
            edit_mode: Whether in edit mode
            initial_name: Initial name (used in edit mode)
            initial_description: Initial description (used in edit mode)
        """
        super().__init__(parent)
        
        self._edit_mode = edit_mode
        self._initial_name = initial_name
        self._initial_description = initial_description
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up UI"""
        title = "Edit Playlist" if self._edit_mode else "Create New Playlist"
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Form
        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        # Name input
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter playlist name")
        self.name_input.setText(self._initial_name)
        form_layout.addRow("Name:", self.name_input)

        # Description input
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Add description (optional)")
        self.desc_input.setMaximumHeight(100)
        self.desc_input.setPlainText(self._initial_description)
        form_layout.addRow("Description:", self.desc_input)
        
        layout.addLayout(form_layout)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.confirm_btn = QPushButton("Confirm")
        self.confirm_btn.setDefault(True)
        self.confirm_btn.clicked.connect(self._on_confirm)
        button_layout.addWidget(self.confirm_btn)

        layout.addLayout(button_layout)

        # Connect signals
        self.name_input.textChanged.connect(self._update_confirm_state)
        self._update_confirm_state()
    
    def _update_confirm_state(self):
        """Update confirm button state"""
        has_name = bool(self.name_input.text().strip())
        self.confirm_btn.setEnabled(has_name)
    
    def _on_confirm(self):
        """Confirm button clicked"""
        if self.name_input.text().strip():
            self.accept()

    def get_name(self) -> str:
        """Get entered name"""
        return self.name_input.text().strip()

    def get_description(self) -> str:
        """Get entered description"""
        return self.desc_input.toPlainText().strip()
