from dataclasses import dataclass

@dataclass(frozen=True)
class DesignTokens:
    """Design tokens for Deep Ocean 2025 theme."""
    
    # --- Colors ---
    # Primary (Teal Accent) - Brand Color
    PRIMARY_500: str = "#3FB7A6"  # Main brand color
    PRIMARY_600: str = "#5BC0B0"  # Hover (lighter)
    PRIMARY_700: str = "#24877A"  # Pressed/Active (darker)
    PRIMARY_BORDER: str = "#2FA191"  # Button border
    PRIMARY_BG_LIGHT: str = "rgba(63, 183, 166, 0.1)"  # Light background for active items
    PRIMARY_BG_MEDIUM: str = "rgba(63, 183, 166, 0.16)"  # Medium background for selection

    # Neutral (Deep Ocean Dark Palette)
    NEUTRAL_900: str = "#0E1116"  # Main Background (Darkest)
    NEUTRAL_850: str = "#111620"  # Sidebar/Surface
    NEUTRAL_800: str = "#141923"  # Input background
    NEUTRAL_750: str = "#18202C"  # Hover surface
    NEUTRAL_700: str = "#1E2633"  # Borders/Dividers
    NEUTRAL_600: str = "#263041"  # Input border
    NEUTRAL_500: str = "#9AA2AF"  # Secondary Text
    NEUTRAL_400: str = "#A1A8B3"  # Placeholder/Icon
    NEUTRAL_300: str = "#7B8595"  # Muted text
    NEUTRAL_200: str = "#E6E8EC"  # Primary Text (Light)
    NEUTRAL_100: str = "#DFF6F3"  # Highlighted text
    NEUTRAL_50: str = "#FFFFFF"   # High Emphasis Text
    
    # Semantic
    ERROR_500: str = "#EF4444"
    SUCCESS_500: str = "#22C55E"
    WARNING_500: str = "#F59E0B"

    # --- Spacing (4px base) ---
    SPACING_1: int = 4   # xs
    SPACING_2: int = 8   # sm
    SPACING_3: int = 12  # md
    SPACING_4: int = 16  # lg
    SPACING_6: int = 24  # xl
    SPACING_8: int = 32  # 2xl

    # --- Typography ---
    FONT_FAMILY: str = '"Segoe UI Variable", "Segoe UI", "Microsoft YaHei", sans-serif'
    
    # Font sizes
    FONT_SIZE_MINI: int = 11   # Category labels
    FONT_SIZE_XS: int = 12     # Captions
    FONT_SIZE_SM: int = 13     # Small text
    FONT_SIZE_BASE: int = 14   # Body text
    FONT_SIZE_LG: int = 16     # Large body
    FONT_SIZE_XL: int = 18     # H2
    FONT_SIZE_2XL: int = 24    # H1
    FONT_SIZE_DISPLAY: int = 28  # Display/Page title

    # --- Borders ---
    RADIUS_SM: int = 4
    RADIUS_MD: int = 8
    RADIUS_LG: int = 12
    RADIUS_FULL: int = 9999

    BORDER_WIDTH_1: int = 1

tokens = DesignTokens()
