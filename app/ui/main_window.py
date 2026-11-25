"""
Modern GUI for Google AI Plus (1-Year Access) Portal
Supports 1-Click Automated Provisioning and Live UI Diagnostics.
"""

import os
import sys
import ctypes
import re
import threading
import queue
import time
import random
import webbrowser
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageTk

# On Windows, assign an explicit AppUserModelID so the taskbar button displays the
# application's custom icon instead of grouping under python.exe's default Python logo.
if sys.platform == "win32":
    try:
        myappid = "nmrisrl11.googleaiplus.claimerportal.v100"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

from app.core.claimer import (
    GeminiAIClaimer,
    FIRST_NAMES,
    LAST_NAMES,
    generate_random_indian_phone,
    generate_secure_password,
    normalize_error_message,
)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

from app.config import (
    ICONS_DIR,
    IMAGES_DIR,
    RESULTS_DIR,
    APP_VERSION,
    DEVELOPER_GITHUB_URL,
    SHOW_VISUAL_BROWSER_OPTION,
    DEFAULT_ACTIVITY_TEXT,
)
from app.ui.dialogs import (
    OTPDialog,
    SupportModal,
    AboutModal,
    DiagnosticsModal,
)
from app.ui import theme as T

__all__ = [
    "GeminiClaimerApp",
    "OTPDialog",
    "SupportModal",
    "AboutModal",
    "DiagnosticsModal",
    "APP_VERSION",
    "DEVELOPER_GITHUB_URL",
    "save_result_file",
]


def save_result_file(email: str, password: str, name: str, phone: str, url: str) -> str:
    """Saves provisioning credentials and generated redemption link into results folder."""
    os.makedirs(RESULTS_DIR, exist_ok=True)

    from app.core.claimer import clean_google_one_url
    url = clean_google_one_url(url)

    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    date_display = time.strftime("%Y-%m-%d %H:%M:%S")

    safe_email = re.sub(r'[^a-zA-Z0-9_\-@.]', '_', email)
    filename = f"{safe_email}_{timestamp}.txt"
    filepath = os.path.join(RESULTS_DIR, filename)

    if url == "EMAIL_DISPATCHED":
        status_section = """--------------------------------------------------------------------------------
STATUS:
Account Setup Completed & Qualified — Activation Link Dispatched to Email
--------------------------------------------------------------------------------

ACTIVATION INSTRUCTIONS:
1. Check your email inbox (and spam/promotions folder).
2. Look for the confirmation email: 'Claim your free access'.
3. Click the activation button inside to activate your 12 months of free Google AI Plus access."""
    else:
        status_section = f"""--------------------------------------------------------------------------------
PROMOTIONAL REDEMPTION LINK:
{url}
--------------------------------------------------------------------------------

ACTIVATION INSTRUCTIONS:
1. Open the redemption link above in your browser.
2. Sign in to the corresponding Google Account.
3. Follow the on-screen steps to activate your 12 months of free Google AI Plus access."""

    content = f"""================================================================================
           GOOGLE AI PLUS (1-YEAR ACCESS) PROVISIONING REPORT
================================================================================
Generated At    : {date_display}
Account Name    : {name or 'N/A'}
Email Address   : {email}
Account Password: {password}
Contact Phone   : {phone or 'N/A'}

{status_section}

IMPORTANT NOTICE:
Please carefully review all on-screen details, requirements, and prompts before
confirming or proceeding with any steps on the destination page.
================================================================================
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath


class GeminiClaimerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"Google AI Plus Portal — {APP_VERSION}")
        self.geometry("880x780")
        self.minsize(800, 680)
        self.configure(fg_color=T.BG_WINDOW)

        self.log_queue = queue.Queue()
        self.otp_queue = queue.Queue()
        self.otp_response_queue = queue.Queue()

        self.claimer_thread = None
        self.active_claimer = None
        self.current_redemption_url = None
        self.has_logged_activity = False
        self._profile_expanded = False
        self._password_masked = False
        self._progress_running = False

        self._load_icons()
        self._build_ui()
        self._start_queue_listener()

        # Match Windows 11 native titlebar to app chrome
        self.after(60, lambda: T.apply_win11_titlebar(self, T.BG_TOPBAR, T.TEXT_PRIMARY))

        # Hotkey bindings: F1 for About/Help, F12 for Diagnostics
        self.bind("<F1>", lambda e: self._show_about_modal())
        self.bind("<F12>", lambda e: self._show_diagnostics_menu())
        self.bind("<Control-Shift-D>", lambda e: self._show_diagnostics_menu())
        self.bind("<Control-Shift-d>", lambda e: self._show_diagnostics_menu())

    def _load_icons(self):
        """Loads graphical assets from merged images directory."""
        self.icon_app_small = None
        self.icon_shuffle = None
        self.icon_check = None

        png_path = os.path.join(IMAGES_DIR, "app_icon.png")
        if os.path.exists(png_path):
            try:
                base_img = Image.open(png_path).convert("RGBA")
                self._taskbar_icons = [
                    ImageTk.PhotoImage(base_img.resize((s, s), Image.Resampling.LANCZOS))
                    for s in [256, 64, 48, 32, 24, 16]
                ]
                self.iconphoto(True, *self._taskbar_icons)
                self.icon_app_small = ctk.CTkImage(light_image=base_img, dark_image=base_img, size=(22, 22))
            except Exception:
                pass

        ico_path = os.path.join(IMAGES_DIR, "app_icon.ico")
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
                self.after(200, lambda: self.iconbitmap(ico_path))
            except Exception:
                pass

        shuffle_path = os.path.join(IMAGES_DIR, "shuffle.png")
        if os.path.exists(shuffle_path):
            try:
                img = Image.open(shuffle_path)
                self.icon_shuffle = ctk.CTkImage(light_image=img, dark_image=img, size=(14, 14))
            except Exception:
                self.icon_shuffle = None

        check_path = os.path.join(IMAGES_DIR, "check.png")
        if os.path.exists(check_path):
            try:
                img = Image.open(check_path)
                self.icon_check = ctk.CTkImage(light_image=img, dark_image=img, size=(12, 12))
            except Exception:
                self.icon_check = None

    def _build_ui(self):
        # =====================================================================
        # 1. Slim Native Top App Bar
        # =====================================================================
        topbar = ctk.CTkFrame(self, fg_color=T.BG_TOPBAR, corner_radius=0, height=54)
        topbar.pack(fill="x", padx=0, pady=0)
        topbar.pack_propagate(False)

        topbar_inner = ctk.CTkFrame(topbar, fg_color="transparent")
        topbar_inner.pack(fill="both", expand=True, padx=24)

        # Left identity cluster: icon + title + version pill
        brand_cluster = ctk.CTkFrame(topbar_inner, fg_color="transparent")
        brand_cluster.pack(side="left", fill="y")

        if self.icon_app_small:
            ctk.CTkLabel(
                brand_cluster,
                text="",
                image=self.icon_app_small,
            ).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            brand_cluster,
            text="Google AI Plus Portal",
            font=T.ui_font(15, "bold"),
            text_color=T.TEXT_PRIMARY,
        ).pack(side="left")

        ver_badge = ctk.CTkFrame(
            brand_cluster,
            fg_color=T.BG_BADGE,
            border_width=1,
            border_color=T.BORDER_SUBTLE,
            corner_radius=6,
        )
        ver_badge.pack(side="left", padx=(10, 0), pady=15)

        ctk.CTkLabel(
            ver_badge,
            text=APP_VERSION,
            font=T.mono_font(10, "bold"),
            text_color=T.TEXT_MUTED,
        ).pack(padx=7, pady=1)

        # Right utility cluster: quiet ghost actions
        nav_cluster = ctk.CTkFrame(topbar_inner, fg_color="transparent")
        nav_cluster.pack(side="right", fill="y")

        ctk.CTkButton(
            nav_cluster,
            text="Results",
            width=72,
            height=28,
            font=T.ui_font(12),
            fg_color="transparent",
            hover_color=T.BG_HOVER,
            text_color=T.TEXT_SECONDARY,
            corner_radius=6,
            command=self._open_results_folder,
        ).pack(side="left", padx=(0, 4), pady=13)

        self.btn_support = ctk.CTkButton(
            nav_cluster,
            text="Support",
            width=72,
            height=28,
            font=T.ui_font(12),
            fg_color="transparent",
            hover_color=T.BG_HOVER,
            text_color=T.TEXT_SECONDARY,
            corner_radius=6,
            command=self._show_support_modal,
        )
        self.btn_support.pack(side="left", padx=(0, 4), pady=13)

        ctk.CTkButton(
            nav_cluster,
            text="About",
            width=64,
            height=28,
            font=T.ui_font(12),
            fg_color="transparent",
            hover_color=T.BG_HOVER,
            text_color=T.TEXT_SECONDARY,
            corner_radius=6,
            command=self._show_about_modal,
        ).pack(side="left", pady=13)

        # Crisp 1px topbar divider
        ctk.CTkFrame(self, fg_color=T.BORDER_SUBTLE, height=1, corner_radius=0).pack(fill="x")

        # =====================================================================
        # 2. Minimal Native Footer Bar (Packed before main_container so it never clips)
        # =====================================================================
        footer_frame = ctk.CTkFrame(self, fg_color="transparent", height=26)
        footer_frame.pack(fill="x", side="bottom", padx=24, pady=(0, 10))

        dev_link = ctk.CTkLabel(
            footer_frame,
            text="Developed by @nmrisrl11",
            font=T.ui_font(11),
            text_color=T.TEXT_MUTED,
            cursor="hand2",
        )
        dev_link.pack(side="left")
        dev_link.bind("<Enter>", lambda e: dev_link.configure(text_color=T.ACCENT_TEXT))
        dev_link.bind("<Leave>", lambda e: dev_link.configure(text_color=T.TEXT_MUTED))
        dev_link.bind("<Button-1>", lambda e: webbrowser.open(DEVELOPER_GITHUB_URL))

        ctk.CTkLabel(footer_frame, text="  ·  ", font=T.ui_font(11), text_color=T.TEXT_FAINT).pack(side="left")

        about_link = ctk.CTkLabel(
            footer_frame,
            text="About",
            font=T.ui_font(11),
            text_color=T.TEXT_MUTED,
            cursor="hand2",
        )
        about_link.pack(side="left")
        about_link.bind("<Enter>", lambda e: about_link.configure(text_color=T.ACCENT_TEXT))
        about_link.bind("<Leave>", lambda e: about_link.configure(text_color=T.TEXT_MUTED))
        about_link.bind("<Button-1>", lambda e: self._show_about_modal())

        ctk.CTkLabel(footer_frame, text="  ·  ", font=T.ui_font(11), text_color=T.TEXT_FAINT).pack(side="left")

        support_link = ctk.CTkLabel(
            footer_frame,
            text="Buy Me a Coffee",
            font=T.ui_font(11),
            text_color=T.TEXT_MUTED,
            cursor="hand2",
        )
        support_link.pack(side="left")
        support_link.bind("<Enter>", lambda e: support_link.configure(text_color=T.WARNING_TEXT))
        support_link.bind("<Leave>", lambda e: support_link.configure(text_color=T.TEXT_MUTED))
        support_link.bind("<Button-1>", lambda e: self._show_support_modal())

        ctk.CTkLabel(
            footer_frame,
            text="F1 About  ·  F12 Diagnostics",
            font=T.mono_font(10),
            text_color=T.TEXT_FAINT,
        ).pack(side="right")

        # =====================================================================
        # 3. Main Content Workspace (No Permanent Outer Scrollbar)
        # =====================================================================
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=24, pady=(14, 8))

        # ---------------------------------------------------------------------
        # Card A: Account Setup & Controls
        # ---------------------------------------------------------------------
        self.config_card = ctk.CTkFrame(
            self.main_container,
            fg_color=T.BG_CARD,
            border_width=1,
            border_color=T.BORDER_SUBTLE,
            corner_radius=12,
        )
        self.config_card.pack(fill="x", pady=(0, 12))

        setup_inner = ctk.CTkFrame(self.config_card, fg_color="transparent")
        setup_inner.pack(fill="x", padx=20, pady=18)

        # Hero Gmail Header Row
        email_label_row = ctk.CTkFrame(setup_inner, fg_color="transparent")
        email_label_row.pack(fill="x", pady=(0, 6))

        self.card_title = ctk.CTkLabel(
            email_label_row,
            text="Target Gmail Address",
            font=T.ui_font(13, "bold"),
            text_color=T.TEXT_PRIMARY,
        )
        self.card_title.pack(side="left")

        ctk.CTkLabel(
            email_label_row,
            text="6-digit verification code will be sent here",
            font=T.ui_font(11),
            text_color=T.TEXT_MUTED,
        ).pack(side="right")

        # Hero Gmail Input
        self.entry_email = ctk.CTkEntry(
            setup_inner,
            placeholder_text="name@gmail.com",
            height=40,
            font=T.ui_font(13),
            fg_color=T.BG_INPUT,
            border_width=1,
            border_color=T.BORDER_INPUT,
            text_color=T.TEXT_PRIMARY,
            placeholder_text_color=T.TEXT_MUTED,
            corner_radius=8,
        )
        self.entry_email.pack(fill="x")
        T.bind_entry_focus(self.entry_email)
        self.entry_email.bind("<Return>", lambda e: self._start_process())
        self.entry_email.bind("<KeyRelease>", lambda e: self._clear_inline_error())

        # Inline Validation Feedback (hidden by default)
        self.lbl_inline_error = ctk.CTkLabel(
            setup_inner,
            text="",
            font=T.ui_font(11),
            text_color=T.DANGER_TEXT,
            anchor="w",
        )

        # Recessed Generated Profile Summary Strip
        self.profile_summary_box = ctk.CTkFrame(
            setup_inner,
            fg_color=T.BG_SUBCARD,
            border_width=1,
            border_color=T.BORDER_SUBTLE,
            corner_radius=8,
        )
        self.profile_summary_box.pack(fill="x", pady=(12, 0))

        summary_row = ctk.CTkFrame(self.profile_summary_box, fg_color="transparent")
        summary_row.pack(fill="x", padx=12, pady=9)

        summary_left = ctk.CTkFrame(summary_row, fg_color="transparent")
        summary_left.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            summary_left,
            text="GENERATED PROFILE",
            font=T.ui_font(10, "bold"),
            text_color=T.TEXT_MUTED,
        ).pack(anchor="w")

        self.lbl_profile_summary = ctk.CTkLabel(
            summary_left,
            text="",
            font=T.ui_font(12),
            text_color=T.TEXT_SECONDARY,
            anchor="w",
        )
        self.lbl_profile_summary.pack(anchor="w", pady=(1, 0))

        summary_actions = ctk.CTkFrame(summary_row, fg_color="transparent")
        summary_actions.pack(side="right")

        self.btn_randomize = ctk.CTkButton(
            summary_actions,
            text=" Randomize",
            image=self.icon_shuffle,
            compound="left",
            width=106,
            height=28,
            font=T.ui_font(11, "bold"),
            fg_color=T.BTN_SECONDARY,
            hover_color=T.BTN_SECONDARY_HOVER,
            border_width=1,
            border_color=T.BORDER_GHOST,
            text_color=T.TEXT_PRIMARY,
            corner_radius=6,
            command=self._randomize_credentials,
        )
        self.btn_randomize.pack(side="left", padx=(0, 6))

        self.btn_toggle_profile = ctk.CTkButton(
            summary_actions,
            text="Customize",
            width=84,
            height=28,
            font=T.ui_font(11, "bold"),
            fg_color="transparent",
            hover_color=T.BG_HOVER,
            border_width=1,
            border_color=T.BORDER_GHOST,
            text_color=T.TEXT_SECONDARY,
            corner_radius=6,
            command=self._toggle_profile_drawer,
        )
        self.btn_toggle_profile.pack(side="left")

        # Collapsible 2x2 Profile Editor Drawer (Instantiated immediately, hidden until Customize clicked)
        self.profile_drawer = ctk.CTkFrame(
            self.profile_summary_box,
            fg_color="transparent",
        )

        ctk.CTkFrame(
            self.profile_drawer,
            fg_color=T.BORDER_SUBTLE,
            height=1,
            corner_radius=0,
        ).pack(fill="x", padx=12, pady=(0, 10))

        fields_grid = ctk.CTkFrame(self.profile_drawer, fg_color="transparent")
        fields_grid.pack(fill="x", padx=12, pady=(0, 12))
        fields_grid.grid_columnconfigure(0, weight=1, uniform="profile_col")
        fields_grid.grid_columnconfigure(1, weight=1, uniform="profile_col")

        # First Name
        self.lbl_fname = ctk.CTkLabel(
            fields_grid,
            text="First Name",
            font=T.ui_font(11, "bold"),
            text_color=T.TEXT_MUTED,
        )
        self.lbl_fname.grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 3))
        self.entry_fname = ctk.CTkEntry(
            fields_grid,
            placeholder_text="First name",
            height=34,
            font=T.ui_font(12),
            fg_color=T.BG_INPUT,
            border_width=1,
            border_color=T.BORDER_INPUT,
            text_color=T.TEXT_PRIMARY,
            corner_radius=7,
        )
        self.entry_fname.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(0, 8))
        self.entry_fname.insert(0, random.choice(FIRST_NAMES))
        T.bind_entry_focus(self.entry_fname)
        self.entry_fname.bind("<KeyRelease>", lambda e: self._update_profile_summary())

        # Last Name
        self.lbl_lname = ctk.CTkLabel(
            fields_grid,
            text="Last Name",
            font=T.ui_font(11, "bold"),
            text_color=T.TEXT_MUTED,
        )
        self.lbl_lname.grid(row=0, column=1, sticky="w", padx=(8, 0), pady=(0, 3))
        self.entry_lname = ctk.CTkEntry(
            fields_grid,
            placeholder_text="Last name",
            height=34,
            font=T.ui_font(12),
            fg_color=T.BG_INPUT,
            border_width=1,
            border_color=T.BORDER_INPUT,
            text_color=T.TEXT_PRIMARY,
            corner_radius=7,
        )
        self.entry_lname.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))
        self.entry_lname.insert(0, random.choice(LAST_NAMES))
        T.bind_entry_focus(self.entry_lname)
        self.entry_lname.bind("<KeyRelease>", lambda e: self._update_profile_summary())

        # Contact (+91)
        self.lbl_phone = ctk.CTkLabel(
            fields_grid,
            text="Contact (+91)",
            font=T.ui_font(11, "bold"),
            text_color=T.TEXT_MUTED,
        )
        self.lbl_phone.grid(row=2, column=0, sticky="w", padx=(0, 8), pady=(0, 3))
        self.entry_phone = ctk.CTkEntry(
            fields_grid,
            placeholder_text="10 digit Indian number",
            height=34,
            font=T.mono_font(12),
            fg_color=T.BG_INPUT,
            border_width=1,
            border_color=T.BORDER_INPUT,
            text_color=T.TEXT_PRIMARY,
            corner_radius=7,
        )
        self.entry_phone.grid(row=3, column=0, sticky="ew", padx=(0, 8))
        self.entry_phone.insert(0, generate_random_indian_phone())
        T.bind_entry_focus(self.entry_phone)
        self.entry_phone.bind("<KeyRelease>", lambda e: self._update_profile_summary())

        # Password + Mask toggle
        pwd_label_row = ctk.CTkFrame(fields_grid, fg_color="transparent")
        pwd_label_row.grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(0, 3))

        ctk.CTkLabel(
            pwd_label_row,
            text="Account Password",
            font=T.ui_font(11, "bold"),
            text_color=T.TEXT_MUTED,
        ).pack(side="left")

        self.btn_toggle_pwd = ctk.CTkButton(
            pwd_label_row,
            text="Hide",
            width=42,
            height=18,
            font=T.ui_font(10, "bold"),
            fg_color="transparent",
            hover_color=T.BG_HOVER,
            text_color=T.ACCENT_TEXT,
            corner_radius=4,
            command=self._toggle_password_visibility,
        )
        self.btn_toggle_pwd.pack(side="right")

        self.entry_password = ctk.CTkEntry(
            fields_grid,
            placeholder_text="Minimum 6 characters",
            height=34,
            font=T.mono_font(12),
            fg_color=T.BG_INPUT,
            border_width=1,
            border_color=T.BORDER_INPUT,
            text_color=T.TEXT_PRIMARY,
            corner_radius=7,
        )
        self.entry_password.grid(row=3, column=1, sticky="ew", padx=(8, 0))
        self.entry_password.insert(0, generate_secure_password(12))
        T.bind_entry_focus(self.entry_password)
        self.entry_password.bind("<KeyRelease>", lambda e: self._clear_inline_error())

        self._update_profile_summary()

        # Action Row inside Setup Card Footer
        action_row = ctk.CTkFrame(setup_inner, fg_color="transparent")
        action_row.pack(fill="x", pady=(14, 0))

        if SHOW_VISUAL_BROWSER_OPTION:
            self.chk_browser = ctk.CTkCheckBox(
                action_row,
                text="Show visual progress window",
                font=T.ui_font(12),
                text_color=T.TEXT_SECONDARY,
                fg_color=T.ACCENT,
                hover_color=T.ACCENT_HOVER,
                border_color=T.BORDER_GHOST,
                border_width=1,
                checkbox_width=18,
                checkbox_height=18,
                corner_radius=5,
            )
            self.chk_browser.pack(side="left", pady=4)
            self.chk_browser.select()
        else:
            self.chk_browser = None
            ctk.CTkLabel(
                action_row,
                text="Runs silently in background  •  Credentials saved locally",
                font=T.ui_font(11),
                text_color=T.TEXT_MUTED,
            ).pack(side="left", pady=4)

        btn_cluster = ctk.CTkFrame(action_row, fg_color="transparent")
        btn_cluster.pack(side="right")

        self.btn_stop = ctk.CTkButton(
            btn_cluster,
            text="Reset Fields",
            width=112,
            height=38,
            font=T.ui_font(12, "bold"),
            fg_color="transparent",
            hover_color=T.BG_HOVER,
            border_width=1,
            border_color=T.BORDER_GHOST,
            text_color=T.TEXT_SECONDARY,
            corner_radius=8,
            command=self._stop_process,
        )
        self.btn_stop.pack(side="left", padx=(0, 10))

        self.btn_start = ctk.CTkButton(
            btn_cluster,
            text="Get 1-Year Access Link",
            width=206,
            height=38,
            font=T.ui_font(13, "bold"),
            fg_color=T.ACCENT,
            hover_color=T.ACCENT_HOVER,
            text_color="#FFFFFF",
            corner_radius=8,
            command=self._start_process,
        )
        self.btn_start.pack(side="left")

        # ---------------------------------------------------------------------
        # Card B: Result Banner (Initially Hidden; slides in above Stepper)
        # ---------------------------------------------------------------------
        self.result_card = ctk.CTkFrame(
            self.main_container,
            fg_color=T.SUCCESS_BG,
            border_width=1,
            border_color=T.SUCCESS_BORDER,
            corner_radius=12,
        )

        res_inner = ctk.CTkFrame(self.result_card, fg_color="transparent")
        res_inner.pack(fill="x", padx=18, pady=12)

        # Row 1: Status pill + Title (left) | Results Folder + Support (right)
        res_head = ctk.CTkFrame(res_inner, fg_color="transparent")
        res_head.pack(fill="x", pady=(0, 8))

        ready_pill = ctk.CTkFrame(
            res_head,
            fg_color=T.SUCCESS_INNER_BORDER,
            corner_radius=5,
        )
        ready_pill.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            ready_pill,
            text="READY",
            font=T.mono_font(10, "bold"),
            text_color=T.SUCCESS_TEXT,
        ).pack(padx=7, pady=2)

        self.result_title = ctk.CTkLabel(
            res_head,
            text="Success! Redemption link is ready",
            font=T.ui_font(13, "bold"),
            text_color=T.TEXT_PRIMARY,
        )
        self.result_title.pack(side="left")

        self.btn_res_support = ctk.CTkButton(
            res_head,
            text="Support Dev",
            width=98,
            height=26,
            font=T.ui_font(11, "bold"),
            fg_color=T.WARNING_BG,
            hover_color="#3B2B0F",
            border_width=1,
            border_color=T.WARNING_BORDER,
            text_color=T.WARNING_TEXT,
            corner_radius=6,
            command=self._show_support_modal,
        )
        self.btn_res_support.pack(side="right")

        self.btn_open_results = ctk.CTkButton(
            res_head,
            text="Results Folder",
            width=106,
            height=26,
            font=T.ui_font(11, "bold"),
            fg_color=T.SUCCESS_SUBCARD,
            hover_color=T.SUCCESS_INNER_BORDER,
            border_width=1,
            border_color=T.SUCCESS_BORDER,
            text_color=T.TEXT_PRIMARY,
            corner_radius=6,
            command=self._open_results_folder,
        )
        self.btn_open_results.pack(side="right", padx=(0, 6))

        # Row 2: Inline URL Pill + Primary Copy & Open Actions
        res_link_row = ctk.CTkFrame(res_inner, fg_color="transparent")
        res_link_row.pack(fill="x", pady=(0, 8))

        self.url_frame = ctk.CTkFrame(
            res_link_row,
            fg_color=T.SUCCESS_SUBCARD,
            border_width=1,
            border_color=T.SUCCESS_INNER_BORDER,
            corner_radius=8,
            height=36,
        )
        self.url_frame.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.lbl_result_url = ctk.CTkLabel(
            self.url_frame,
            text="",
            font=T.mono_font(12, "bold"),
            text_color=T.SUCCESS_TEXT,
            anchor="w",
            justify="left",
        )
        self.lbl_result_url.pack(padx=12, pady=7, fill="x")

        self.btn_copy_link = ctk.CTkButton(
            res_link_row,
            text="Copy Offer Link",
            width=128,
            height=36,
            font=T.ui_font(12, "bold"),
            fg_color=T.SUCCESS_BTN,
            hover_color=T.SUCCESS_BTN_HOVER,
            text_color="#FFFFFF",
            corner_radius=8,
            command=self._copy_link_to_clipboard,
        )
        self.btn_copy_link.pack(side="left", padx=(0, 6))

        self.btn_open_browser = ctk.CTkButton(
            res_link_row,
            text="Open in Browser",
            width=128,
            height=36,
            font=T.ui_font(12, "bold"),
            fg_color=T.ACCENT,
            hover_color=T.ACCENT_HOVER,
            text_color="#FFFFFF",
            corner_radius=8,
            command=self._open_in_browser,
        )
        self.btn_open_browser.pack(side="left")

        # Row 3: Compact 2-Column Activation & Advisory Notice
        self.notice_box = ctk.CTkFrame(
            res_inner,
            fg_color=T.SUCCESS_SUBCARD,
            border_width=1,
            border_color=T.SUCCESS_INNER_BORDER,
            corner_radius=8,
        )
        self.notice_box.pack(fill="x")
        self.notice_box.grid_columnconfigure(0, weight=1, uniform="notice_col")
        self.notice_box.grid_columnconfigure(1, weight=1, uniform="notice_col")

        ctk.CTkLabel(
            self.notice_box,
            text="How to activate",
            font=T.ui_font(11, "bold"),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=(12, 8), pady=(7, 1))

        self.lbl_activate_desc = ctk.CTkLabel(
            self.notice_box,
            text="Open the offer link in your browser and follow the on-screen steps to activate your 1-Year Google AI Plus access.",
            font=T.ui_font(11),
            text_color=T.TEXT_SECONDARY,
            justify="left",
            anchor="w",
        )
        self.lbl_activate_desc.grid(row=1, column=0, sticky="nw", padx=(12, 8), pady=(0, 8))

        ctk.CTkLabel(
            self.notice_box,
            text="Important Notice",
            font=T.ui_font(11, "bold"),
            text_color=T.WARNING_TEXT,
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=(8, 12), pady=(7, 1))

        self.lbl_notice_desc = ctk.CTkLabel(
            self.notice_box,
            text="Carefully review all on-screen details, requirements, and prompts before confirming on the destination page.",
            font=T.ui_font(11),
            text_color=T.TEXT_SECONDARY,
            justify="left",
            anchor="w",
        )
        self.lbl_notice_desc.grid(row=1, column=1, sticky="nw", padx=(8, 12), pady=(0, 8))
        self.notice_box.bind("<Configure>", self._on_notice_resize)

        # ---------------------------------------------------------------------
        # Card C: Segmented Pipeline Stepper + Live Progress Rail
        # ---------------------------------------------------------------------
        self.pipeline_card = ctk.CTkFrame(
            self.main_container,
            fg_color=T.BG_CARD,
            border_width=1,
            border_color=T.BORDER_SUBTLE,
            corner_radius=10,
        )
        self.pipeline_card.pack(fill="x", pady=(0, 12))

        pipe_inner = ctk.CTkFrame(self.pipeline_card, fg_color="transparent")
        pipe_inner.pack(fill="x", padx=20, pady=(11, 9))
        pipe_inner.grid_columnconfigure(1, weight=1)
        pipe_inner.grid_columnconfigure(3, weight=1)

        # Step 1
        step1_wrap = ctk.CTkFrame(pipe_inner, fg_color="transparent")
        step1_wrap.grid(row=0, column=0, sticky="w")

        self.step1_badge = ctk.CTkLabel(
            step1_wrap,
            text="1",
            width=22,
            height=22,
            font=T.mono_font(11, "bold"),
            fg_color=T.ACCENT_SOFT,
            text_color=T.ACCENT_TEXT,
            corner_radius=11,
        )
        self.step1_badge.pack(side="left", padx=(0, 8))

        self.step1_lbl = ctk.CTkLabel(
            step1_wrap,
            text="Profile Setup",
            font=T.ui_font(12, "bold"),
            text_color=T.TEXT_PRIMARY,
        )
        self.step1_lbl.pack(side="left")

        # Connector 1 -> 2
        self.step1_sep = ctk.CTkFrame(pipe_inner, fg_color=T.BORDER_SUBTLE, height=2, corner_radius=1)
        self.step1_sep.grid(row=0, column=1, sticky="ew", padx=14)

        # Step 2
        step2_wrap = ctk.CTkFrame(pipe_inner, fg_color="transparent")
        step2_wrap.grid(row=0, column=2)

        self.step2_badge = ctk.CTkLabel(
            step2_wrap,
            text="2",
            width=22,
            height=22,
            font=T.mono_font(11, "bold"),
            fg_color=T.BG_BADGE,
            text_color=T.TEXT_MUTED,
            corner_radius=11,
        )
        self.step2_badge.pack(side="left", padx=(0, 8))

        self.step2_lbl = ctk.CTkLabel(
            step2_wrap,
            text="Email Verification",
            font=T.ui_font(12),
            text_color=T.TEXT_MUTED,
        )
        self.step2_lbl.pack(side="left")

        # Connector 2 -> 3
        self.step2_sep = ctk.CTkFrame(pipe_inner, fg_color=T.BORDER_SUBTLE, height=2, corner_radius=1)
        self.step2_sep.grid(row=0, column=3, sticky="ew", padx=14)

        # Step 3
        step3_wrap = ctk.CTkFrame(pipe_inner, fg_color="transparent")
        step3_wrap.grid(row=0, column=4, sticky="e")

        self.step3_badge = ctk.CTkLabel(
            step3_wrap,
            text="3",
            width=22,
            height=22,
            font=T.mono_font(11, "bold"),
            fg_color=T.BG_BADGE,
            text_color=T.TEXT_MUTED,
            corner_radius=11,
        )
        self.step3_badge.pack(side="left", padx=(0, 8))

        self.step3_lbl = ctk.CTkLabel(
            step3_wrap,
            text="Access Link Ready",
            font=T.ui_font(12),
            text_color=T.TEXT_MUTED,
        )
        self.step3_lbl.pack(side="left")

        # Slim 2px integrated progress rail
        self.pipeline_progress = ctk.CTkProgressBar(
            self.pipeline_card,
            height=3,
            corner_radius=0,
            fg_color=T.BG_SUBCARD,
            progress_color=T.ACCENT,
        )
        self.pipeline_progress.pack(fill="x", padx=2, pady=(0, 2))
        self.pipeline_progress.set(0)

        # ---------------------------------------------------------------------
        # Card D: Live Activity Console (Fills remaining height cleanly)
        # ---------------------------------------------------------------------
        self.log_card = ctk.CTkFrame(
            self.main_container,
            fg_color=T.BG_CARD,
            border_width=1,
            border_color=T.BORDER_SUBTLE,
            corner_radius=12,
        )
        self.log_card.pack(fill="both", expand=True)

        log_header = ctk.CTkFrame(self.log_card, fg_color="transparent")
        log_header.pack(fill="x", padx=16, pady=(12, 8))

        ctk.CTkLabel(
            log_header,
            text="Live Activity Feed",
            font=T.ui_font(13, "bold"),
            text_color=T.TEXT_PRIMARY,
        ).pack(side="left")

        # Right status pill + Copy Log action
        log_right = ctk.CTkFrame(log_header, fg_color="transparent")
        log_right.pack(side="right")

        self.btn_copy_log = ctk.CTkButton(
            log_right,
            text="Copy Log",
            width=74,
            height=24,
            font=T.ui_font(11),
            fg_color="transparent",
            hover_color=T.BG_HOVER,
            border_width=1,
            border_color=T.BORDER_SUBTLE,
            text_color=T.TEXT_MUTED,
            corner_radius=6,
            command=self._copy_logs_to_clipboard,
        )
        self.btn_copy_log.pack(side="left", padx=(0, 10))

        self.status_pill = ctk.CTkFrame(
            log_right,
            fg_color=T.BG_SUBCARD,
            border_width=1,
            border_color=T.BORDER_SUBTLE,
            corner_radius=12,
        )
        self.status_pill.pack(side="left")

        self.lbl_status = ctk.CTkLabel(
            self.status_pill,
            text="● System Ready",
            font=T.ui_font(11, "bold"),
            text_color=T.SUCCESS,
        )
        self.lbl_status.pack(padx=10, pady=2)

        self.txt_logs = ctk.CTkTextbox(
            self.log_card,
            height=110,
            font=T.mono_font(11),
            text_color=T.LOG_BODY,
            fg_color=T.BG_CONSOLE,
            border_width=1,
            border_color=T.BORDER_SUBTLE,
            scrollbar_button_color="#222938",
            scrollbar_button_hover_color="#333E54",
            corner_radius=8,
            wrap="word",
            padx=12,
            pady=10,
        )
        self.txt_logs.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        self._configure_log_tags()
        self._insert_idle_guide()

    # =========================================================================
    # UI Helper Controls
    # =========================================================================

    def _configure_log_tags(self):
        """Sets up color-coded tags on the underlying Tk Text widget."""
        try:
            tb = self.txt_logs._textbox
            tb.tag_config("ts", foreground=T.LOG_TIMESTAMP)
            tb.tag_config("badge_INFO", foreground=T.LOG_INFO_BADGE)
            tb.tag_config("badge_SUCCESS", foreground=T.LOG_SUCCESS_BADGE)
            tb.tag_config("badge_WARNING", foreground=T.LOG_WARNING_BADGE)
            tb.tag_config("badge_ERROR", foreground=T.LOG_ERROR_BADGE)
            tb.tag_config("badge_WAITING_USER", foreground=T.LOG_WAITING_BADGE)
            tb.tag_config("body_default", foreground=T.LOG_BODY)
            tb.tag_config("body_SUCCESS", foreground=T.SUCCESS_TEXT)
            tb.tag_config("body_ERROR", foreground=T.DANGER_TEXT)
            tb.tag_config("body_WARNING", foreground=T.WARNING_TEXT)
            tb.tag_config("guide", foreground=T.LOG_BODY_MUTED)
        except Exception:
            pass

    def _insert_idle_guide(self):
        """Inserts the clean idle quick-guide text into the activity console."""
        self.txt_logs.configure(state="normal")
        self.txt_logs.delete("1.0", "end")
        try:
            self.txt_logs._textbox.insert("end", DEFAULT_ACTIVITY_TEXT.strip(), ("guide",))
        except Exception:
            self.txt_logs.insert("end", DEFAULT_ACTIVITY_TEXT.strip())
        self.txt_logs.configure(state="disabled")

    def _update_profile_summary(self):
        """Updates the single-line Generated Profile summary strip."""
        fname = self.entry_fname.get().strip() or "—"
        lname = self.entry_lname.get().strip() or ""
        full_name = f"{fname} {lname}".strip()
        phone = self.entry_phone.get().strip() or "—"
        pwd_len = len(self.entry_password.get().strip())
        pwd_desc = f"Password ({pwd_len} chars)" if pwd_len else "No password"
        self.lbl_profile_summary.configure(text=f"{full_name}   •   +91 {phone}   •   {pwd_desc}")

    def _toggle_profile_drawer(self, force_state: bool = None):
        """Expands or collapses the secondary auto-generated profile fields."""
        target = (not self._profile_expanded) if force_state is None else force_state
        if target == self._profile_expanded:
            return
        self._profile_expanded = target
        if self._profile_expanded:
            self.profile_drawer.pack(fill="x")
            self.btn_toggle_profile.configure(text="Hide", text_color=T.TEXT_PRIMARY)
        else:
            self.profile_drawer.pack_forget()
            self.btn_toggle_profile.configure(text="Customize", text_color=T.TEXT_SECONDARY)

    def _toggle_password_visibility(self):
        """Toggles masked vs plaintext view for the account password field."""
        self._password_masked = not self._password_masked
        self.entry_password.configure(show="•" if self._password_masked else "")
        self.btn_toggle_pwd.configure(text="Show" if self._password_masked else "Hide")

    def _set_inline_error(self, message: str, field: str = "email"):
        """Displays a refined inline validation message directly below the email field."""
        self.lbl_inline_error.configure(text=message)
        self.lbl_inline_error.pack(fill="x", pady=(5, 0), after=self.entry_email)
        if field == "email":
            self.entry_email.configure(border_color=T.BORDER_ERROR)
            self.entry_email.focus_set()
        elif field == "password":
            self._toggle_profile_drawer(force_state=True)
            self.entry_password.configure(border_color=T.BORDER_ERROR)
            self.entry_password.focus_set()

    def _clear_inline_error(self):
        """Clears any active inline validation message and restores default borders."""
        if self.lbl_inline_error.winfo_manager():
            self.lbl_inline_error.pack_forget()
        if str(self.entry_email.cget("border_color")) == T.BORDER_ERROR:
            self.entry_email.configure(border_color=T.BORDER_FOCUS)
        if str(self.entry_password.cget("border_color")) == T.BORDER_ERROR:
            self.entry_password.configure(border_color=T.BORDER_INPUT)

    def _set_progress_state(self, mode: str):
        """Controls the slim progress rail: 'idle', 'running', 'waiting', or 'done'."""
        if not hasattr(self, "pipeline_progress"):
            return
        if self._progress_running and mode not in ("running", "waiting"):
            self.pipeline_progress.stop()
            self._progress_running = False

        if mode == "idle":
            self.pipeline_progress.configure(mode="determinate", progress_color=T.ACCENT)
            self.pipeline_progress.set(0)
        elif mode == "running":
            self.pipeline_progress.configure(mode="indeterminate", progress_color=T.ACCENT)
            if not self._progress_running:
                self.pipeline_progress.start()
                self._progress_running = True
        elif mode == "waiting":
            self.pipeline_progress.configure(mode="indeterminate", progress_color=T.WARNING)
            if not self._progress_running:
                self.pipeline_progress.start()
                self._progress_running = True
        elif mode == "done":
            self.pipeline_progress.configure(mode="determinate", progress_color=T.SUCCESS)
            self.pipeline_progress.set(1.0)

    def _copy_logs_to_clipboard(self):
        """Copies the current activity feed contents to clipboard."""
        content = self.txt_logs.get("1.0", "end").strip()
        if not content:
            return
        self.clipboard_clear()
        self.clipboard_append(content)
        self.update()
        self.btn_copy_log.configure(text="Copied", text_color=T.SUCCESS_TEXT)
        self.after(2000, lambda: self.btn_copy_log.configure(text="Copy Log", text_color=T.TEXT_MUTED))

    # =========================================================================
    # Modals & Core Event Handlers
    # =========================================================================

    def _show_about_modal(self):
        """Displays the About application modal."""
        modal = AboutModal(self)
        self.wait_window(modal)

    def _show_support_modal(self):
        """Displays the Support & Donation modal with QR codes."""
        modal = SupportModal(self)
        self.wait_window(modal)

    def _on_notice_resize(self, event):
        """Dynamically adjusts wraplength for the 2-column notice box."""
        col_width = max(160, (event.width // 2) - 24)
        if hasattr(self, "lbl_activate_desc"):
            self.lbl_activate_desc.configure(wraplength=col_width)
        if hasattr(self, "lbl_notice_desc"):
            self.lbl_notice_desc.configure(wraplength=col_width)

    def _set_badge_completed(self, badge: ctk.CTkLabel):
        """Styles a stepper badge with the crisp white check.png icon."""
        if self.icon_check:
            badge.configure(text="", image=self.icon_check, fg_color=T.SUCCESS_BTN)
        else:
            badge.configure(text="✓", image=None, fg_color=T.SUCCESS_BTN, text_color="#FFFFFF")

    def _set_badge_number(self, badge: ctk.CTkLabel, number: str, fg_color: str, text_color: str):
        """Styles a stepper badge with a step number and clears any check icon."""
        badge.configure(image=None, text=number, fg_color=fg_color, text_color=text_color)

    def _set_pipeline_step(self, step: int):
        """Updates the visual 3-step pipeline progress stepper."""
        if not hasattr(self, "step1_lbl"):
            return

        if step == 1:
            self._set_badge_number(self.step1_badge, "1", T.ACCENT_SOFT, T.ACCENT_TEXT)
            self.step1_lbl.configure(text="Profile Setup", font=T.ui_font(12, "bold"), text_color=T.TEXT_PRIMARY)
            self.step1_sep.configure(fg_color=T.BORDER_SUBTLE)

            self._set_badge_number(self.step2_badge, "2", T.BG_BADGE, T.TEXT_MUTED)
            self.step2_lbl.configure(text="Email Verification", font=T.ui_font(12), text_color=T.TEXT_MUTED)
            self.step2_sep.configure(fg_color=T.BORDER_SUBTLE)

            self._set_badge_number(self.step3_badge, "3", T.BG_BADGE, T.TEXT_MUTED)
            self.step3_lbl.configure(text="Access Link Ready", font=T.ui_font(12), text_color=T.TEXT_MUTED)
        elif step == 2:
            self._set_badge_completed(self.step1_badge)
            self.step1_lbl.configure(text="Profile Ready", font=T.ui_font(12, "bold"), text_color=T.SUCCESS_TEXT)
            self.step1_sep.configure(fg_color=T.SUCCESS_BORDER)

            self._set_badge_number(self.step2_badge, "2", T.WARNING_BG, T.WARNING_TEXT)
            self.step2_lbl.configure(text="Awaiting Email OTP", font=T.ui_font(12, "bold"), text_color=T.WARNING_TEXT)
            self.step2_sep.configure(fg_color=T.BORDER_SUBTLE)

            self._set_badge_number(self.step3_badge, "3", T.BG_BADGE, T.TEXT_MUTED)
            self.step3_lbl.configure(text="Access Link Ready", font=T.ui_font(12), text_color=T.TEXT_MUTED)
            self._set_progress_state("waiting")
        elif step >= 3:
            self._set_badge_completed(self.step1_badge)
            self.step1_lbl.configure(text="Profile Ready", font=T.ui_font(12, "bold"), text_color=T.SUCCESS_TEXT)
            self.step1_sep.configure(fg_color=T.SUCCESS_BORDER)

            self._set_badge_completed(self.step2_badge)
            self.step2_lbl.configure(text="Email Verified", font=T.ui_font(12, "bold"), text_color=T.SUCCESS_TEXT)
            self.step2_sep.configure(fg_color=T.SUCCESS_BORDER)

            self._set_badge_completed(self.step3_badge)
            self.step3_lbl.configure(text="1-Year Link Ready", font=T.ui_font(12, "bold"), text_color=T.SUCCESS_TEXT)
            self._set_progress_state("done")

    def _reset_activity_feed(self):
        """Restores the initial clean guide in the activity textbox."""
        self.has_logged_activity = False
        self._insert_idle_guide()

    def _show_diagnostics_menu(self):
        """Allows testing edge cases without consuming a Gmail account."""
        modal = DiagnosticsModal(self)
        self.wait_window(modal)

    def _set_fields_state(self, state: str):
        """Enable or disable all configuration and profile setup fields ('normal' or 'disabled')."""
        bg = T.BG_INPUT if state == "normal" else T.BG_INPUT_DISABLED
        fg = T.TEXT_PRIMARY if state == "normal" else T.TEXT_MUTED
        border = T.BORDER_INPUT if state == "normal" else T.BORDER_SUBTLE
        for entry in (self.entry_email, self.entry_password, self.entry_fname, self.entry_lname, self.entry_phone):
            entry.configure(state=state, fg_color=bg, text_color=fg, border_color=border)
        self.btn_randomize.configure(state=state)
        if self.chk_browser:
            self.chk_browser.configure(state=state)

    def _randomize_credentials(self):
        for entry in [self.entry_fname, self.entry_lname, self.entry_password, self.entry_phone]:
            entry.configure(state="normal")

        self.entry_fname.delete(0, "end")
        self.entry_fname.insert(0, random.choice(FIRST_NAMES))

        self.entry_lname.delete(0, "end")
        self.entry_lname.insert(0, random.choice(LAST_NAMES))

        self.entry_password.delete(0, "end")
        self.entry_password.insert(0, generate_secure_password(12))

        self.entry_phone.delete(0, "end")
        self.entry_phone.insert(0, generate_random_indian_phone())

        self._update_profile_summary()

    def _append_log(self, message: str, level: str = "INFO"):
        if not self.has_logged_activity:
            self.has_logged_activity = True
            self.txt_logs.configure(state="normal")
            self.txt_logs.delete("1.0", "end")
            self.txt_logs.configure(state="disabled")

        timestamp = time.strftime("%H:%M:%S")
        badges = {
            "INFO": "[i]",
            "SUCCESS": "[OK]",
            "WARNING": "[!]",
            "ERROR": "[X]",
            "WAITING_USER": "[...]",
        }
        badge = badges.get(level, "[*]")
        badge_tag = f"badge_{level}" if level in badges else "badge_INFO"
        body_tag = f"body_{level}" if level in ("SUCCESS", "ERROR", "WARNING") else "body_default"

        self.txt_logs.configure(state="normal")
        try:
            tb = self.txt_logs._textbox
            tb.insert("end", f"[{timestamp}] ", ("ts",))
            tb.insert("end", f"{badge:<5} ", (badge_tag,))
            tb.insert("end", f"{message}\n", (body_tag,))
        except Exception:
            self.txt_logs.insert("end", f"[{timestamp}] {badge} {message}\n")
        self.txt_logs.see("end")
        self.txt_logs.configure(state="disabled")

    def _set_status(self, text: str, color: str = T.ACCENT_TEXT):
        self.lbl_status.configure(text=f"● {text}", text_color=color)

    def _start_queue_listener(self):
        """Processes logs and OTP requests from background worker thread."""
        try:
            while not self.log_queue.empty():
                msg, lvl = self.log_queue.get_nowait()
                self._append_log(msg, lvl)
                if lvl == "SUCCESS" and "Successfully acquired" in msg:
                    self._set_status("Completed Successfully", T.SUCCESS)
                    self._set_pipeline_step(3)
                elif lvl == "ERROR":
                    self._set_status("Notice", T.DANGER_TEXT)
                elif lvl == "WAITING_USER":
                    self._set_pipeline_step(2)
                    if "challenge" in msg.lower() or "verification" in msg.lower():
                        self._set_status("Awaiting Manual Verification...", T.WARNING)
                    else:
                        self._set_status("Awaiting Email OTP...", T.WARNING)

            if not self.otp_queue.empty():
                email, err_msg = self.otp_queue.get_nowait()
                dlg = OTPDialog(self, email, err_msg)
                self.wait_window(dlg)
                self.otp_response_queue.put(dlg.otp_value)

        except Exception as e:
            print("Queue listener error:", e)

        self.after(100, self._start_queue_listener)

    def _on_request_otp(self, error_message: str = None) -> str:
        """Called from claimer thread to prompt user for OTP."""
        email = self.entry_email.get().strip()
        self.otp_queue.put((email, error_message))
        self._set_pipeline_step(2)
        otp_val = self.otp_response_queue.get()
        return otp_val

    def _start_process(self):
        self._clear_inline_error()

        email = self.entry_email.get().strip()
        password = self.entry_password.get().strip()
        fname = self.entry_fname.get().strip()
        lname = self.entry_lname.get().strip()
        phone = self.entry_phone.get().strip()
        show_browser = self.chk_browser.get() if self.chk_browser else False

        if not email or "@gmail.com" not in email.lower():
            self._set_inline_error(
                "Enter a valid Gmail address (@gmail.com) to receive the 6-digit verification code.",
                field="email",
            )
            return

        if len(password) < 6:
            self._set_inline_error(
                "Account password must be at least 6 characters.",
                field="password",
            )
            return

        self.current_redemption_url = None
        self.result_card.pack_forget()
        self._set_fields_state("disabled")
        self.btn_start.configure(
            state="disabled",
            fg_color=T.BTN_DISABLED_BG,
            text_color=T.TEXT_DISABLED,
        )
        self.btn_stop.configure(
            state="normal",
            text="Stop Process",
            width=126,
            fg_color=T.DANGER,
            hover_color=T.DANGER_HOVER,
            border_width=0,
            text_color="#FFFFFF",
        )
        self._set_status("Processing...", T.ACCENT_TEXT)
        self._set_pipeline_step(1)
        self._set_progress_state("running")
        self._append_log("Initiating account registration and promo provisioning...", "INFO")

        self.active_claimer = GeminiAIClaimer(
            email=email,
            password=password,
            mode="register",
            first_name=fname,
            last_name=lname,
            phone_number=phone,
            headless=not show_browser,
            allow_manual_verification=True,
            on_log=lambda msg, lvl: self.log_queue.put((msg, lvl)),
            on_request_otp=self._on_request_otp,
            on_error=self._on_error_callback,
            on_success=self._on_success_callback,
        )

        def worker():
            try:
                self.active_claimer.run()
            finally:
                self.after(0, self._on_finish)

        self.claimer_thread = threading.Thread(target=worker, daemon=True)
        self.claimer_thread.start()

    def _stop_process(self):
        was_active = False
        if self.active_claimer:
            was_active = True
            self.active_claimer.stop()
            self.active_claimer = None

        self._clear_inline_error()

        # Reset success state & card
        self.current_redemption_url = None
        self.lbl_result_url.configure(text="")
        self.result_card.pack_forget()

        # Re-enable all fields for fresh input
        self._set_fields_state("normal")

        # Clear email and randomize credentials
        self.entry_email.delete(0, "end")
        self._randomize_credentials()
        self.entry_email.focus_set()

        # Reset action buttons, pipeline & status
        self.btn_start.configure(
            state="normal",
            fg_color=T.ACCENT,
            hover_color=T.ACCENT_HOVER,
            text_color="#FFFFFF",
        )
        self.btn_stop.configure(
            state="normal",
            text="Reset Fields",
            width=112,
            fg_color="transparent",
            hover_color=T.BG_HOVER,
            border_width=1,
            border_color=T.BORDER_GHOST,
            text_color=T.TEXT_SECONDARY,
        )
        self._set_pipeline_step(1)
        self._set_progress_state("idle")
        self._set_status("System Ready", T.SUCCESS)

        # Restore default guide in log box
        self._reset_activity_feed()

        if was_active:
            self._append_log("Process stopped by user.", "WARNING")
        else:
            self._append_log("Account session reset. Ready for new registration.", "INFO")

    def _on_finish(self):
        if self.current_redemption_url:
            # Succeeded: keep setup fields locked, offer 'Provision Another Account'
            self._set_fields_state("disabled")
            self.btn_start.configure(
                state="disabled",
                fg_color=T.BTN_DISABLED_BG,
                text_color=T.TEXT_DISABLED,
            )
            self.btn_stop.configure(
                state="normal",
                text="Provision Another Account",
                width=196,
                fg_color=T.ACCENT,
                hover_color=T.ACCENT_HOVER,
                border_width=0,
                text_color="#FFFFFF",
            )
            self._set_pipeline_step(3)
        else:
            # Failed or aborted: restore fields and allow re-trying
            self._set_fields_state("normal")
            self.btn_start.configure(
                state="normal",
                fg_color=T.ACCENT,
                hover_color=T.ACCENT_HOVER,
                text_color="#FFFFFF",
            )
            self.btn_stop.configure(
                state="normal",
                text="Reset Fields",
                width=112,
                fg_color="transparent",
                hover_color=T.BG_HOVER,
                border_width=1,
                border_color=T.BORDER_GHOST,
                text_color=T.TEXT_SECONDARY,
            )
            self._set_progress_state("idle")

    def _on_error_callback(self, err_msg: str):
        formatted = normalize_error_message(err_msg, for_log=False)
        messagebox.showerror("Notice", formatted, parent=self)

    def _on_success_callback(self, redemption_url: str):
        from app.core.claimer import clean_google_one_url
        redemption_url = clean_google_one_url(redemption_url)
        self.current_redemption_url = redemption_url
        email = self.entry_email.get().strip() or "your registered email"

        # Collapse optional drawer so Result Card + Console sit comfortably with zero clipping
        self._toggle_profile_drawer(force_state=False)

        if redemption_url == "EMAIL_DISPATCHED":
            self.result_title.configure(text="Account Completed — Activation link sent to your email")
            self.lbl_result_url.configure(text=f"Check your inbox at: {email}")
            self.btn_copy_link.configure(text="Copy Credentials")
            self.btn_open_browser.configure(text="Open Email Inbox")
            self.lbl_activate_desc.configure(
                text="Your account setup has been completed and qualified. The 12-month access activation link was sent directly to your registered email address.\n"
                     "1. Check your email inbox (and spam/promotions folder).  "
                     "2. Look for 'Claim your free access'.  "
                     "3. Click the activation button inside."
            )
            self.lbl_notice_desc.configure(
                text="Please verify your email inbox and follow the on-screen steps. If your browser previously showed an eligibility notice on the page, using the link in your email activates your access directly."
            )
        else:
            self.result_title.configure(text="Success! Redemption link is ready")
            self.lbl_result_url.configure(text=redemption_url)
            self.btn_copy_link.configure(text="Copy Offer Link")
            self.btn_open_browser.configure(text="Open in Browser")
            self.lbl_activate_desc.configure(
                text="Open the offer link in your browser and proceed with the activation directly on your screen. Follow the on-screen steps to complete your 1-Year Google AI Plus access."
            )
            self.lbl_notice_desc.configure(
                text="Please carefully review all on-screen details, requirements, and prompts before confirming or proceeding with any steps on the destination page."
            )

        self.result_card.pack(fill="x", pady=(0, 12), before=self.pipeline_card)
        self._set_pipeline_step(3)
        self._set_status("Completed Successfully", T.SUCCESS)

        # Lock configuration fields upon success and offer Provision Another
        self._set_fields_state("disabled")
        self.btn_start.configure(
            state="disabled",
            fg_color=T.BTN_DISABLED_BG,
            text_color=T.TEXT_DISABLED,
        )
        self.btn_stop.configure(
            state="normal",
            text="Provision Another Account",
            width=196,
            fg_color=T.ACCENT,
            hover_color=T.ACCENT_HOVER,
            border_width=0,
            text_color="#FFFFFF",
        )

        # Save record to results folder
        password = self.entry_password.get().strip()
        fname = self.entry_fname.get().strip()
        lname = self.entry_lname.get().strip()
        phone = self.entry_phone.get().strip()
        full_name = f"{fname} {lname}".strip() or "Google AI Plus User"

        try:
            saved_file = save_result_file(
                email=email,
                password=password,
                name=full_name,
                phone=phone,
                url=redemption_url,
            )
            filename = os.path.basename(saved_file)
            self._append_log(f"Details saved to results/{filename}", "SUCCESS")
        except Exception as e:
            self._append_log(f"Could not save result file: {e}", "WARNING")

    def _open_results_folder(self):
        os.makedirs(RESULTS_DIR, exist_ok=True)
        try:
            os.startfile(RESULTS_DIR)
        except Exception:
            webbrowser.open(RESULTS_DIR)

    def _copy_link_to_clipboard(self):
        if self.current_redemption_url:
            if self.current_redemption_url == "EMAIL_DISPATCHED":
                email = self.entry_email.get().strip()
                password = self.entry_password.get().strip()
                text_to_copy = f"Email: {email}\nPassword: {password}"
                self.clipboard_clear()
                self.clipboard_append(text_to_copy)
                self.update()
                self.btn_copy_link.configure(text="Credentials Copied!")
                self.after(2500, lambda: self.btn_copy_link.configure(text="Copy Credentials"))
            else:
                self.clipboard_clear()
                self.clipboard_append(self.current_redemption_url)
                self.update()
                self.btn_copy_link.configure(text="Copied to Clipboard!")
                self.after(2500, lambda: self.btn_copy_link.configure(text="Copy Offer Link"))

    def _open_in_browser(self):
        if self.current_redemption_url:
            if self.current_redemption_url == "EMAIL_DISPATCHED":
                webbrowser.open("https://mail.google.com")
            else:
                webbrowser.open(self.current_redemption_url)


if __name__ == "__main__":
    app = GeminiClaimerApp()
    app.mainloop()
