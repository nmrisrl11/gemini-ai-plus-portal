"""
Centralized Design System & Theme Tokens for Gemini AI Plus Portal.
Provides a cohesive neutral-dark desktop palette, typography scale,
spacing constants, and Windows 11 DWM titlebar integration.
"""

import os
import sys
import ctypes
import customtkinter as ctk


# =============================================================================
# Color Palette — Cohesive Neutral-Dark Desktop System
# =============================================================================

# Surfaces (layered dark elevation)
BG_WINDOW = "#0B0D11"           # Root window canvas (matches Win11 dark titlebar)
BG_TOPBAR = "#0E1117"           # Slim top app chrome
BG_CARD = "#131720"             # Primary elevated card surface
BG_SUBCARD = "#0F131B"          # Recessed nested container / summary bar
BG_INPUT = "#0C0F15"            # Input field fill
BG_INPUT_DISABLED = "#11151E"   # Locked input field fill
BG_CONSOLE = "#090B10"          # Activity log viewport
BG_HOVER = "#1C2230"            # Subtle hover highlight for ghost elements
BG_BADGE = "#181E2B"            # Neutral pill / version badge fill

# Hairline Borders (1px borders define structure cleanly)
BORDER_SUBTLE = "#1E2430"       # Card & divider border
BORDER_INPUT = "#273042"        # Default text entry border
BORDER_FOCUS = "#3B82F6"        # Focused text entry border
BORDER_ERROR = "#EF4444"        # Validation error border
BORDER_GHOST = "#2A3345"        # Secondary / ghost button border

# Typography Colors
TEXT_PRIMARY = "#F1F5F9"        # High-contrast headings & values
TEXT_SECONDARY = "#94A3B8"      # Body descriptions & helper copy
TEXT_MUTED = "#64748B"          # Micro-labels, timestamps, captions
TEXT_FAINT = "#475569"          # Dividers & keyboard shortcut hints
TEXT_DISABLED = "#526075"       # Disabled button / field text

# Accent (Single Disciplined Brand Blue)
ACCENT = "#2563EB"              # Primary CTA fill
ACCENT_HOVER = "#1D4ED8"        # Primary CTA hover
ACCENT_SOFT = "#15223C"         # Soft blue pill background
ACCENT_TEXT = "#60A5FA"         # Links & subtle active text

# Semantic: Success (Emerald)
SUCCESS = "#10B981"
SUCCESS_BG = "#0D1F17"          # Result card background
SUCCESS_SUBCARD = "#091711"     # Result URL & notice inset
SUCCESS_BORDER = "#166534"      # Result card hairline border
SUCCESS_INNER_BORDER = "#14532D"
SUCCESS_TEXT = "#6EE7B7"        # Soft readable emerald text
SUCCESS_BTN = "#15803D"
SUCCESS_BTN_HOVER = "#166534"

# Semantic: Warning / Waiting (Amber)
WARNING = "#F59E0B"
WARNING_BG = "#221A0B"
WARNING_BORDER = "#574014"
WARNING_TEXT = "#FCD34D"

# Semantic: Danger / Error (Crimson)
DANGER = "#DC2626"
DANGER_HOVER = "#B91C1C"
DANGER_BG = "#241014"
DANGER_BORDER = "#5C1E26"
DANGER_TEXT = "#F87171"

# Secondary / Utility Buttons
BTN_SECONDARY = "#1A202D"
BTN_SECONDARY_HOVER = "#232B3B"
BTN_DISABLED_BG = "#161B26"

# Console Log Tag Colors
LOG_TIMESTAMP = "#475569"
LOG_INFO_BADGE = "#60A5FA"
LOG_SUCCESS_BADGE = "#34D399"
LOG_WARNING_BADGE = "#FBBF24"
LOG_ERROR_BADGE = "#F87171"
LOG_WAITING_BADGE = "#FBBF24"
LOG_BODY = "#CBD5E1"
LOG_BODY_MUTED = "#94A3B8"


# =============================================================================
# Typography Helpers
# =============================================================================

UI_FONT_FAMILY = "Segoe UI" if sys.platform == "win32" else "Inter"
MONO_FONT_FAMILY = "Consolas" if sys.platform == "win32" else "Menlo"


def ui_font(size: int = 12, weight: str = "normal", slant: str = "roman") -> ctk.CTkFont:
    """Returns a consistent native UI font."""
    return ctk.CTkFont(family=UI_FONT_FAMILY, size=size, weight=weight, slant=slant)


def mono_font(size: int = 11, weight: str = "normal") -> ctk.CTkFont:
    """Returns a consistent monospace font for console logs, URLs, and OTP codes."""
    return ctk.CTkFont(family=MONO_FONT_FAMILY, size=size, weight=weight)


# =============================================================================
# Window Chrome & Geometry Helpers
# =============================================================================

def _hex_to_colorref(hex_color: str) -> int:
    """Converts '#RRGGBB' to Windows COLORREF (0x00BBGGRR)."""
    h = hex_color.lstrip("#")
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return (b << 16) | (g << 8) | r


def apply_win11_titlebar(window, bg_hex: str = BG_TOPBAR, text_hex: str = TEXT_PRIMARY) -> None:
    """
    Matches the Windows 11 native titlebar background to the app chrome using DWM.
    Safely no-ops on Windows 10 or non-Windows platforms.
    """
    if sys.platform != "win32":
        return
    try:
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        if not hwnd:
            hwnd = window.winfo_id()

        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        DWMWA_CAPTION_COLOR = 35
        DWMWA_TEXT_COLOR = 36

        dark = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(dark), ctypes.sizeof(dark)
        )

        caption_color = ctypes.c_int(_hex_to_colorref(bg_hex))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_CAPTION_COLOR, ctypes.byref(caption_color), ctypes.sizeof(caption_color)
        )

        title_color = ctypes.c_int(_hex_to_colorref(text_hex))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_TEXT_COLOR, ctypes.byref(title_color), ctypes.sizeof(title_color)
        )
    except Exception:
        pass


def apply_modal_icon(modal, images_dir: str) -> None:
    """Applies the native .ico icon to a Toplevel modal safely."""
    ico_path = os.path.join(images_dir, "app_icon.ico")
    if os.path.exists(ico_path):
        try:
            modal.after(180, lambda: modal.iconbitmap(ico_path))
        except Exception:
            pass


def center_modal(modal, parent, width: int, height: int) -> None:
    """Centers a modal dialog accurately over its parent window, clamped to screen bounds."""
    try:
        parent.update_idletasks()
        px = parent.winfo_x()
        py = parent.winfo_y()
        pw = parent.winfo_width()
        ph = parent.winfo_height()

        x = px + (pw - width) // 2
        y = py + (ph - height) // 2

        screen_w = modal.winfo_screenwidth()
        screen_h = modal.winfo_screenheight()
        x = max(16, min(x, screen_w - width - 16))
        y = max(16, min(y, screen_h - height - 48))

        modal.geometry(f"{width}x{height}+{x}+{y}")
    except Exception:
        modal.geometry(f"{width}x{height}")


def bind_entry_focus(entry: ctk.CTkEntry, default_border: str = BORDER_INPUT, focus_border: str = BORDER_FOCUS) -> None:
    """Adds subtle focus-ring border highlighting to a CTkEntry."""
    def _on_in(_event):
        if str(entry.cget("state")) != "disabled":
            entry.configure(border_color=focus_border)

    def _on_out(_event):
        entry.configure(border_color=default_border)

    entry.bind("<FocusIn>", _on_in, add="+")
    entry.bind("<FocusOut>", _on_out, add="+")
