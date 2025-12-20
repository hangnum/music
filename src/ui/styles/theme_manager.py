from ui.resources.design_tokens import tokens


class ThemeManager:
    """Manages application themes and generates stylesheets based on DesignTokens."""

    @staticmethod
    def get_global_stylesheet() -> str:
        """Returns the global stylesheet for the application."""
        return f"""
        /* Global Reset & Base Styles */
        QMainWindow, QDialog, QWidget {{
            background-color: {tokens.NEUTRAL_900};
            color: {tokens.NEUTRAL_200};
            font-family: {tokens.FONT_FAMILY};
            font-size: {tokens.FONT_SIZE_BASE}px;
        }}

        /* --- Scrollbars --- */
        QScrollBar:vertical {{
            border: none;
            background: {tokens.NEUTRAL_900};
            width: 12px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {tokens.NEUTRAL_700};
            min-height: 40px;
            border-radius: 6px;
            border: 3px solid {tokens.NEUTRAL_900};
        }}
        QScrollBar::handle:vertical:hover {{
            background: {tokens.NEUTRAL_600};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
        
        QScrollBar:horizontal {{
            border: none;
            background: {tokens.NEUTRAL_900};
            height: 12px;
            margin: 0px;
        }}
        QScrollBar::handle:horizontal {{
            background: {tokens.NEUTRAL_700};
            min-width: 40px;
            border-radius: 6px;
            border: 3px solid {tokens.NEUTRAL_900};
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {tokens.NEUTRAL_600};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}


        /* --- Splitter --- */
        QSplitter::handle {{
            background-color: {tokens.NEUTRAL_700};
            width: 1px;
        }}

        /* --- ToolTips --- */
        QToolTip {{
            background-color: {tokens.NEUTRAL_800};
            color: {tokens.NEUTRAL_200};
            border: 1px solid {tokens.NEUTRAL_700};
            padding: 4px 8px;
            border-radius: {tokens.RADIUS_SM}px;
            font-size: {tokens.FONT_SIZE_XS}px;
        }}
        
        /* --- Menu Bar --- */
        QMenuBar {{
            background-color: {tokens.NEUTRAL_900};
            border-bottom: 1px solid {tokens.NEUTRAL_700};
        }}
        QMenuBar::item {{
            spacing: 3px; 
            padding: 4px 8px;
            background: transparent;
            border-radius: {tokens.RADIUS_SM}px;
        }}
        QMenuBar::item:selected {{ 
            background-color: {tokens.NEUTRAL_750};
        }}

        QMenu {{
            background-color: {tokens.NEUTRAL_850};
            border: 1px solid {tokens.NEUTRAL_600};
            border-radius: {tokens.RADIUS_MD}px;
            padding: 6px 0px;
        }}
        QMenu::item {{
            padding: 6px 24px 6px 12px;
            border-radius: {tokens.RADIUS_SM}px;
            margin: 0px 4px;
        }}
        QMenu::item:selected {{
            background-color: {tokens.PRIMARY_500};
            color: {tokens.NEUTRAL_50};
        }}
        QMenu::separator {{
            height: 1px;
            background: {tokens.NEUTRAL_700};
            margin: 4px 0px;
        }}

        /* --- QLabel --- */
        QLabel {{
            color: {tokens.NEUTRAL_200};
        }}
        QLabel#sidebarHeader {{
            color: {tokens.NEUTRAL_300};
            font-size: {tokens.FONT_SIZE_MINI}px;
            font-weight: 700;
            padding: 18px 24px 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        /* --- Buttons (Generic) --- */
        QPushButton {{
            background-color: transparent;
            border: 1px solid {tokens.NEUTRAL_700};
            border-radius: {tokens.RADIUS_MD}px;
            color: {tokens.NEUTRAL_200};
            padding: 6px 12px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {tokens.NEUTRAL_750};
            border-color: {tokens.NEUTRAL_600};
        }}
        QPushButton:pressed {{
            background-color: {tokens.NEUTRAL_800};
        }}
        QPushButton:focus {{
            border: 2px solid {tokens.PRIMARY_500};
        }}
        QPushButton:disabled {{
            background-color: transparent;
            color: {tokens.NEUTRAL_500};
            border-color: transparent;
        }}
        
        /* --- Input Fields --- */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {tokens.NEUTRAL_800};
            border: 1px solid {tokens.NEUTRAL_600};
            border-radius: {tokens.RADIUS_MD}px;
            padding: 8px 12px;
            color: {tokens.NEUTRAL_200};
            selection-background-color: {tokens.PRIMARY_500};
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border: 1px solid {tokens.PRIMARY_500};
            background-color: {tokens.NEUTRAL_750};
        }}
        
        /* --- Lists/Trees/Tables --- */
        QListWidget, QTreeWidget, QTableWidget, QTableView {{
            background-color: {tokens.NEUTRAL_900};
            border: none;
            outline: none;
            gridline-color: transparent;
            selection-background-color: {tokens.PRIMARY_BG_MEDIUM};
            selection-color: {tokens.NEUTRAL_50};
        }}
        QListWidget::item, QTreeWidget::item {{
            padding: 6px;
            border-radius: {tokens.RADIUS_MD}px;
        }}
        QListWidget::item:selected, QTreeWidget::item:selected {{
            background-color: {tokens.PRIMARY_BG_MEDIUM};
            color: {tokens.NEUTRAL_100};
        }}
        QListWidget::item:hover, QTreeWidget::item:hover {{
            background-color: {tokens.NEUTRAL_750};
        }}
        QHeaderView::section {{
            background-color: {tokens.NEUTRAL_900};
            color: {tokens.NEUTRAL_500};
            padding: 8px 12px;
            border: none;
            border-bottom: 1px solid {tokens.NEUTRAL_700};
            font-weight: 600;
            font-size: {tokens.FONT_SIZE_XS}px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        QTableView::item {{
            padding: 6px 12px;
            border-bottom: 1px solid {tokens.NEUTRAL_750};
            color: {tokens.NEUTRAL_200};
        }}
        QTableView::item:hover {{
            background-color: {tokens.NEUTRAL_750};
        }}
        QTableView::item:selected {{
            background-color: {tokens.PRIMARY_BG_MEDIUM};
            color: {tokens.NEUTRAL_100};
            border: none;
        }}
        
        /* --- GroupBox --- */
        QGroupBox {{
            border: 1px solid {tokens.NEUTRAL_700};
            border-radius: {tokens.RADIUS_LG}px;
            margin-top: 1.5em; 
            padding-top: 10px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 5px;
            left: 10px;
            color: {tokens.NEUTRAL_200}; 
            font-weight: 600;
        }}

        /* --- Sliders --- */
        QSlider::groove:horizontal {{
            border: none;
            height: 4px;
            background: {tokens.NEUTRAL_700};
            margin: 0px 0;
            border-radius: 2px;
        }}
        QSlider::sub-page:horizontal {{
            background: {tokens.PRIMARY_500};
            border-radius: 2px;
        }}
        QSlider::handle:horizontal {{
            background: {tokens.NEUTRAL_200};
            border: none;
            width: 12px;
            height: 12px;
            margin: -4px 0;
            border-radius: 6px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {tokens.NEUTRAL_50};
            width: 14px;
            height: 14px;
            margin: -5px 0;
        }}
        
        /* --- Specific Components --- */
        QWidget#sidebar {{
            background-color: {tokens.NEUTRAL_850};
            border-right: 1px solid {tokens.NEUTRAL_700};
        }}
        
        QWidget#playerBar {{
            background-color: {tokens.NEUTRAL_850};
            border-top: 1px solid {tokens.NEUTRAL_700};
        }}
        """

    @staticmethod
    def get_sidebar_button_style() -> str:
        """Returns style for sidebar navigation buttons."""
        return f"""
        QPushButton {{
            text-align: left;
            background-color: transparent;
            border: none;
            border-radius: {tokens.RADIUS_MD}px;
            padding: 10px 16px;
            color: {tokens.NEUTRAL_400};
            font-size: {tokens.FONT_SIZE_BASE}px;
            font-weight: 500;
            margin: 2px 8px;
        }}
        QPushButton:hover {{
            background-color: {tokens.NEUTRAL_750};
            color: {tokens.NEUTRAL_50};
        }}
        QPushButton:checked {{
            background-color: {tokens.NEUTRAL_750};
            color: {tokens.NEUTRAL_100};
            border-left: 3px solid {tokens.PRIMARY_500};
            font-weight: 600;
        }}
        """

    @staticmethod
    def get_primary_button_style() -> str:
        """Returns style for primary action buttons (e.g. Play button)."""
        return f"""
        QPushButton {{
            background-color: {tokens.PRIMARY_500};
            color: {tokens.NEUTRAL_50};
            border: 1px solid {tokens.PRIMARY_BORDER};
            border-radius: {tokens.RADIUS_FULL}px;
            padding: 0px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {tokens.PRIMARY_600};
            border-color: {tokens.PRIMARY_500};
        }}
        QPushButton:pressed {{
            background-color: {tokens.PRIMARY_700};
        }}
        QPushButton:disabled {{
            background-color: {tokens.NEUTRAL_700};
            color: {tokens.NEUTRAL_500};
            border-color: transparent;
        }}
        """

    @staticmethod
    def get_control_button_style() -> str:
        """Returns style for player control buttons (prev, next, shuffle, etc.)."""
        return f"""
        QPushButton {{
            border-radius: {tokens.RADIUS_MD}px;
            padding: 8px;
            background-color: transparent;
            border: 1px solid transparent;
            color: {tokens.NEUTRAL_200};
        }}
        QPushButton:hover {{
            background-color: {tokens.NEUTRAL_750};
            border-color: {tokens.NEUTRAL_600};
        }}
        QPushButton:checked {{
            color: {tokens.PRIMARY_500};
            background-color: {tokens.PRIMARY_BG_MEDIUM};
        }}
        QPushButton:disabled {{
            color: {tokens.NEUTRAL_500};
        }}
        """

    @staticmethod
    def get_cover_style() -> str:
        """Returns style for album cover placeholders."""
        return f"""
        QLabel {{
            background-color: {tokens.NEUTRAL_750};
            border-radius: {tokens.RADIUS_MD}px;
            border: 1px solid {tokens.NEUTRAL_600};
        }}
        """

    @staticmethod
    def get_track_title_style() -> str:
        """Returns style for track title labels."""
        return f"""
        QLabel {{
            font-weight: 600;
            font-size: {tokens.FONT_SIZE_BASE}px;
            color: {tokens.NEUTRAL_200};
            background-color: transparent;
        }}
        """

    @staticmethod
    def get_track_artist_style() -> str:
        """Returns style for track artist labels."""
        return f"""
        QLabel {{
            color: {tokens.NEUTRAL_500};
            font-size: {tokens.FONT_SIZE_XS}px;
            background-color: transparent;
        }}
        """

    @staticmethod
    def get_time_label_style() -> str:
        """Returns style for time display labels."""
        return f"""
        QLabel {{
            color: {tokens.NEUTRAL_500};
            font-size: {tokens.FONT_SIZE_MINI}px;
            font-family: monospace;
            background-color: transparent;
        }}
        """

    @staticmethod
    def get_secondary_label_style() -> str:
        """Returns style for secondary/muted labels."""
        return f"""
        QLabel {{
            color: {tokens.NEUTRAL_500};
            font-size: {tokens.FONT_SIZE_XS}px;
        }}
        """

    @staticmethod
    def get_title_label_style() -> str:
        """Returns style for page/section titles."""
        return f"""
        QLabel {{
            font-size: {tokens.FONT_SIZE_DISPLAY}px;
            font-weight: 700;
            color: {tokens.NEUTRAL_50};
        }}
        """

    @staticmethod
    def get_section_title_style() -> str:
        """Returns style for section/widget titles (e.g., 播放队列, 我的歌单)."""
        return f"""
        QLabel {{
            font-size: {tokens.FONT_SIZE_XL}px;
            font-weight: 700;
            color: {tokens.NEUTRAL_200};
            background-color: transparent;
        }}
        """

    @staticmethod
    def get_info_label_style() -> str:
        """Returns style for info/stats labels (e.g., '0 首曲目')."""
        return f"""
        QLabel {{
            color: {tokens.NEUTRAL_500};
            font-size: {tokens.FONT_SIZE_XS}px;
            background-color: transparent;
        }}
        """

    @staticmethod
    def get_accent_color() -> str:
        """Returns the primary accent color for dynamic styling."""
        return tokens.PRIMARY_500
