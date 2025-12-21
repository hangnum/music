"""
Tag Management Dialog

Used for adding and managing tags for tracks.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QColorDialog, QMessageBox, QWidget, QCheckBox,
    QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from typing import List

from models.track import Track
from models.tag import Tag
from services.tag_service import TagService
from ui.resources.design_tokens import tokens
from ui.styles.theme_manager import ThemeManager


class TagChip(QWidget):
    """Tag chip component"""
    
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
        
        # Color indicator
        color_dot = QLabel("●")
        color_dot.setStyleSheet(f"color: {tag.color}; font-size: {tokens.FONT_SIZE_XS}px;")
        layout.addWidget(color_dot)

        # Tag name
        name_label = QLabel(tag.name)
        name_label.setStyleSheet(f"color: {tokens.NEUTRAL_200};")
        layout.addWidget(name_label)
        
        layout.addStretch()
    
    def _on_state_changed(self):
        self.toggled.emit(self.tag.id, self.checkbox.isChecked())
    
    def set_checked(self, checked: bool):
        self.checkbox.setChecked(checked)


class TagDialog(QDialog):
    """
    Tag Management Dialog

    Used for managing tags of selected tracks.
    """
    
    tags_updated = pyqtSignal()  # Signal emitted when tags are updated
    
    def __init__(self, tracks: List[Track],
                 tag_service: TagService,
                 parent=None):
        """Initialize tag management dialog

        Args:
            tracks: List of tracks to manage tags for
            tag_service: Tag service (must be provided, no longer supports fallback)
            parent: Parent component
        """
        super().__init__(parent)
        
        self.tracks = tracks
        self.tag_service = tag_service
        
        # Record selection state for each tag: tag_id -> bool
        self._tag_states: dict[str, bool] = {}
        # Record initial states for change detection
        self._initial_states: dict[str, bool] = {}
        
        self._setup_ui()
        self._load_tags()
    
    def _setup_ui(self):
        """Set up UI"""
        self.setWindowTitle("Manage Tags")
        self.setMinimumWidth(400)
        self.setMinimumHeight(500)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Title
        if len(self.tracks) == 1:
            title_text = f"Manage tags for \"{self.tracks[0].title}\""
        else:
            title_text = f"Manage tags for {len(self.tracks)} tracks"
        
        title = QLabel(title_text)
        title.setStyleSheet(f"font-size: {tokens.FONT_SIZE_LG}px; font-weight: bold; color: {tokens.NEUTRAL_200};")
        title.setWordWrap(True)
        layout.addWidget(title)
        
        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background-color: {tokens.NEUTRAL_700};")
        layout.addWidget(line)

        # Tag list area
        tags_label = QLabel("Select tags:")
        tags_label.setStyleSheet(f"color: {tokens.NEUTRAL_500};")
        layout.addWidget(tags_label)

        # Scrollable tag list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{ 
                border: 1px solid {tokens.NEUTRAL_600}; 
                border-radius: {tokens.RADIUS_MD}px;
                background-color: {tokens.NEUTRAL_800};
            }}
        """)
        
        self.tags_container = QWidget()
        self.tags_layout = QVBoxLayout(self.tags_container)
        self.tags_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.tags_layout.setSpacing(8)
        scroll.setWidget(self.tags_container)
        
        layout.addWidget(scroll, 1)
        
        # Separator line
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet(f"background-color: {tokens.NEUTRAL_700};")
        layout.addWidget(line2)

        # Create new tag area
        create_label = QLabel("Create new tag:")
        create_label.setStyleSheet(f"color: {tokens.NEUTRAL_500};")
        layout.addWidget(create_label)
        
        create_row = QHBoxLayout()
        
        self.new_tag_input = QLineEdit()
        self.new_tag_input.setPlaceholderText("Enter tag name...")
        self.new_tag_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {tokens.NEUTRAL_800};
                border: 1px solid {tokens.NEUTRAL_600};
                border-radius: {tokens.RADIUS_MD}px;
                padding: 8px 12px;
                color: {tokens.NEUTRAL_200};
            }}
            QLineEdit:focus {{
                border-color: {tokens.PRIMARY_500};
            }}
        """)
        create_row.addWidget(self.new_tag_input, 1)
        
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(36, 36)
        self._current_color = tokens.NEUTRAL_500
        self._update_color_button()
        self.color_btn.clicked.connect(self._pick_color)
        create_row.addWidget(self.color_btn)
        
        self.add_btn = QPushButton("Add")
        self.add_btn.setStyleSheet(ThemeManager.get_primary_button_style())
        self.add_btn.clicked.connect(self._create_tag)
        create_row.addWidget(self.add_btn)
        
        layout.addLayout(create_row)
        
        # Bottom buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {tokens.NEUTRAL_750};
                color: {tokens.NEUTRAL_200};
                border: none;
                border-radius: {tokens.RADIUS_MD}px;
                padding: 10px 24px;
            }}
            QPushButton:hover {{
                background-color: {tokens.NEUTRAL_700};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(ThemeManager.get_primary_button_style())
        save_btn.clicked.connect(self._save)
        buttons_layout.addWidget(save_btn)
        
        layout.addLayout(buttons_layout)
        
        # Set dialog style
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {tokens.NEUTRAL_850};
            }}
        """)
    
    def _update_color_button(self):
        """Update color button display"""
        self.color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._current_color};
                border: 2px solid {tokens.NEUTRAL_700};
                border-radius: 18px;
            }}
            QPushButton:hover {{
                border-color: {tokens.NEUTRAL_600};
            }}
        """)
    
    def _pick_color(self):
        """Open color picker"""
        color = QColorDialog.getColor(
            QColor(self._current_color),
            self,
            "Select Tag Color"
        )
        if color.isValid():
            self._current_color = color.name()
            self._update_color_button()
    
    def _load_tags(self):
        """Load all tags and display"""
        # Clear existing tags
        while self.tags_layout.count():
            item = self.tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        all_tags = self.tag_service.get_all_tags()
        
        if not all_tags:
            empty = QLabel("No tags available, please create one first")
            empty.setStyleSheet(f"color: {tokens.NEUTRAL_500}; padding: 20px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tags_layout.addWidget(empty)
            return
        
        # Get existing tags for selected tracks
        track_tag_ids = set()
        for track in self.tracks:
            tags = self.tag_service.get_track_tags(track.id)
            for tag in tags:
                track_tag_ids.add(tag.id)
        
        # Create tag chips
        for tag in all_tags:
            is_checked = tag.id in track_tag_ids
            chip = TagChip(tag, is_checked, self)
            chip.toggled.connect(self._on_tag_toggled)
            self.tags_layout.addWidget(chip)
            
            self._tag_states[tag.id] = is_checked
            self._initial_states[tag.id] = is_checked
    
    def _on_tag_toggled(self, tag_id: str, is_checked: bool):
        """Tag selection state changed"""
        self._tag_states[tag_id] = is_checked
    
    def _create_tag(self):
        """Create new tag"""
        name = self.new_tag_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Tip", "Please enter a tag name")
            return

        # Check if already exists
        existing = self.tag_service.get_tag_by_name(name)
        if existing:
            QMessageBox.warning(self, "Tip", f"Tag \"{name}\" already exists")
            return

        # Create tag
        tag = self.tag_service.create_tag(name, self._current_color)
        if tag:
            self.new_tag_input.clear()
            self._current_color = tokens.NEUTRAL_500
            self._update_color_button()
            
            # Reload tag list
            self._load_tags()

            # Auto-select newly created tag
            self._tag_states[tag.id] = True
            self._update_chip_state(tag.id, True)
    
    def _update_chip_state(self, tag_id: str, checked: bool):
        """Update selection state of specified tag chip"""
        for i in range(self.tags_layout.count()):
            widget = self.tags_layout.itemAt(i).widget()
            if isinstance(widget, TagChip) and widget.tag.id == tag_id:
                widget.set_checked(checked)
                break
    
    def _save(self):
        """Save tag changes"""
        # Find tags to add and remove
        tags_to_add = []
        tags_to_remove = []
        
        for tag_id, is_checked in self._tag_states.items():
            initial = self._initial_states.get(tag_id, False)
            if is_checked and not initial:
                tags_to_add.append(tag_id)
            elif not is_checked and initial:
                tags_to_remove.append(tag_id)
        
        # Apply changes to each track
        for track in self.tracks:
            for tag_id in tags_to_add:
                self.tag_service.add_tag_to_track(track.id, tag_id)
            for tag_id in tags_to_remove:
                self.tag_service.remove_tag_from_track(track.id, tag_id)
        
        self.tags_updated.emit()
        self.accept()
