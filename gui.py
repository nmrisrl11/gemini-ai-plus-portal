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
import tkinter as tk
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

from claimer import (
    GeminiAIClaimer,
    FIRST_NAMES,
    LAST_NAMES,
    generate_random_indian_phone,
    generate_secure_password,
    normalize_error_message,
)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

from constants import (
    ICONS_DIR,
    IMAGES_DIR,
    RESULTS_DIR,
    APP_VERSION,
    DEVELOPER_GITHUB_URL,
    SHOW_VISUAL_BROWSER_OPTION,
    DEFAULT_ACTIVITY_TEXT,
)
from dialogs import (
    OTPDialog,
    SupportModal,
    AboutModal,
    DiagnosticsModal,
)

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

    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    date_display = time.strftime("%Y-%m-%d %H:%M:%S")

    safe_email = re.sub(r'[^a-zA-Z0-9_\-@.]', '_', email)
    filename = f"{safe_email}_{timestamp}.txt"
    filepath = os.path.join(RESULTS_DIR, filename)

    content = f"""================================================================================
           GOOGLE AI PLUS (1-YEAR ACCESS) PROVISIONING REPORT
================================================================================
Generated At    : {date_display}
Account Name    : {name or 'N/A'}
Email Address   : {email}
Account Password: {password}
Contact Phone   : {phone or 'N/A'}

--------------------------------------------------------------------------------
PROMOTIONAL REDEMPTION LINK:
{url}
--------------------------------------------------------------------------------

ACTIVATION INSTRUCTIONS:
1. Open the redemption link above in your browser.
2. Sign in to the corresponding Google Account.
3. Follow the on-screen steps to activate your 12 months of free Google AI Plus access.

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
        self.title(f"Google AI Plus (1-Year Access) Portal — {APP_VERSION}")
        self.geometry("860x780")
        self.minsize(800, 680)

        self.log_queue = queue.Queue()
        self.otp_queue = queue.Queue()
        self.otp_response_queue = queue.Queue()

        self.claimer_thread = None
        self.active_claimer = None
        self.current_redemption_url = None
        self.has_logged_activity = False

        self._load_icons()
        self._build_ui()
        self._start_queue_listener()

        # Hotkey bindings: F1 for About/Help, F12 for Diagnostics
        self.bind("<F1>", lambda e: self._show_about_modal())
        self.bind("<F12>", lambda e: self._show_diagnostics_menu())
        self.bind("<Control-Shift-D>", lambda e: self._show_diagnostics_menu())
        self.bind("<Control-Shift-d>", lambda e: self._show_diagnostics_menu())

    def _load_icons(self):
        """Loads graphical assets from merged images directory."""
        # High-DPI Window & Taskbar icon setup
        png_path = os.path.join(IMAGES_DIR, "app_icon.png")
        if os.path.exists(png_path):
            try:
                base_img = Image.open(png_path).convert("RGBA")
                # Keep references on self so Tkinter doesn't garbage collect
                self._taskbar_icons = [
                    ImageTk.PhotoImage(base_img.resize((s, s), Image.Resampling.LANCZOS))
                    for s in [256, 64, 48, 32, 24, 16]
                ]
                self.iconphoto(True, *self._taskbar_icons)
            except Exception:
                pass

        # Native Win32 window titlebar icon
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
                self.icon_shuffle = ctk.CTkImage(light_image=img, dark_image=img, size=(16, 16))
            except Exception:
                self.icon_shuffle = None
        else:
            self.icon_shuffle = None

    def _build_ui(self):
        # Header banner
        header_frame = ctk.CTkFrame(self, fg_color="#0f172a", corner_radius=0)
        header_frame.pack(fill="x", padx=0, pady=0)

        title_lbl = ctk.CTkLabel(
            header_frame,
            text="Google AI Plus — 1-Year Access Portal",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#f8fafc",
        )
        title_lbl.pack(pady=(16, 3))

        subtitle_lbl = ctk.CTkLabel(
            header_frame,
            text="Automated 12-Month Gemini Advanced & Google AI Plus Offer Link Generator",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8",
        )
        subtitle_lbl.pack(pady=(0, 16))

        # Main Scrollable Container
        main_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        main_scroll.pack(fill="both", expand=True, padx=25, pady=(5, 5))

        # Credentials Configuration Card
        self.config_card = ctk.CTkFrame(main_scroll, fg_color="#1e293b", corner_radius=10)
        self.config_card.pack(fill="x", pady=(0, 10), padx=5)

        self.config_card.grid_columnconfigure(1, weight=1)
        self.config_card.grid_columnconfigure(3, weight=1)

        # Header Row: Card Title on Left, Randomize Info on Right
        self.card_title = ctk.CTkLabel(
            self.config_card,
            text="Account Profile & Setup",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#38bdf8",
        )
        self.card_title.grid(row=0, column=0, columnspan=2, padx=15, pady=(12, 10), sticky="w")

        self.btn_randomize = ctk.CTkButton(
            self.config_card,
            text="  Randomize Info",
            image=self.icon_shuffle,
            compound="left",
            width=140,
            height=30,
            fg_color="#334155",
            hover_color="#475569",
            command=self._randomize_credentials,
        )
        self.btn_randomize.grid(row=0, column=2, columnspan=2, padx=15, pady=(12, 10), sticky="e")

        # Row 1: First Name & Last Name
        self.lbl_fname = ctk.CTkLabel(self.config_card, text="First Name:", font=ctk.CTkFont(size=13))
        self.lbl_fname.grid(row=1, column=0, padx=15, pady=6, sticky="w")
        self.entry_fname = ctk.CTkEntry(self.config_card, placeholder_text="First name")
        self.entry_fname.grid(row=1, column=1, padx=(5, 15), pady=6, sticky="ew")
        self.entry_fname.insert(0, random.choice(FIRST_NAMES))

        self.lbl_lname = ctk.CTkLabel(self.config_card, text="Last Name:", font=ctk.CTkFont(size=13))
        self.lbl_lname.grid(row=1, column=2, padx=15, pady=6, sticky="w")
        self.entry_lname = ctk.CTkEntry(self.config_card, placeholder_text="Last name")
        self.entry_lname.grid(row=1, column=3, padx=(5, 15), pady=6, sticky="ew")
        self.entry_lname.insert(0, random.choice(LAST_NAMES))

        # Row 2: Gmail Address & Password
        ctk.CTkLabel(self.config_card, text="Gmail Address:", font=ctk.CTkFont(size=13)).grid(
            row=2, column=0, padx=15, pady=6, sticky="w"
        )
        self.entry_email = ctk.CTkEntry(self.config_card, placeholder_text="example@gmail.com")
        self.entry_email.grid(row=2, column=1, padx=(5, 15), pady=6, sticky="ew")

        ctk.CTkLabel(self.config_card, text="Password:", font=ctk.CTkFont(size=13)).grid(
            row=2, column=2, padx=15, pady=6, sticky="w"
        )
        self.entry_password = ctk.CTkEntry(self.config_card, placeholder_text="Minimum 6 characters")
        self.entry_password.grid(row=2, column=3, padx=(5, 15), pady=6, sticky="ew")
        self.entry_password.insert(0, generate_secure_password(12))

        # Row 3: Phone number & Visual Progress Checkbox
        row3_pady = 6 if SHOW_VISUAL_BROWSER_OPTION else (6, 14)
        self.lbl_phone = ctk.CTkLabel(self.config_card, text="Contact (+91):", font=ctk.CTkFont(size=13))
        self.lbl_phone.grid(row=3, column=0, padx=15, pady=row3_pady, sticky="w")
        self.entry_phone = ctk.CTkEntry(self.config_card, placeholder_text="10 digit Indian number")
        self.entry_phone.grid(row=3, column=1, padx=(5, 15), pady=row3_pady, sticky="ew")
        self.entry_phone.insert(0, generate_random_indian_phone())

        if SHOW_VISUAL_BROWSER_OPTION:
            self.chk_browser = ctk.CTkCheckBox(
                self.config_card,
                text="Show visual progress window (Recommended)",
                font=ctk.CTkFont(size=12),
            )
            self.chk_browser.grid(row=3, column=2, columnspan=2, padx=15, pady=6, sticky="w")
            self.chk_browser.select()
        else:
            self.chk_browser = None

        # Action Buttons
        btn_frame = ctk.CTkFrame(main_scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(4, 10), padx=5)

        self.btn_start = ctk.CTkButton(
            btn_frame,
            text="Get 1-Year Access Link",
            width=220,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            corner_radius=8,
            command=self._start_process,
        )
        self.btn_start.pack(side="left", padx=(0, 12))

        self.btn_stop = ctk.CTkButton(
            btn_frame,
            text="Reset Fields",
            width=160,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#334155",
            hover_color="#475569",
            text_color="#cbd5e1",
            corner_radius=8,
            command=self._stop_process,
        )
        self.btn_stop.pack(side="left")

        self.btn_support = ctk.CTkButton(
            btn_frame,
            text="Support Dev",
            width=140,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#334155",
            hover_color="#f59e0b",
            text_color="#f8fafc",
            corner_radius=8,
            command=self._show_support_modal,
        )
        self.btn_support.pack(side="right")

        # Visual Pipeline Stepper
        self.pipeline_card = ctk.CTkFrame(main_scroll, fg_color="#1e293b", corner_radius=8)
        self.pipeline_card.pack(fill="x", pady=(0, 10), padx=5)

        pipe_inner = ctk.CTkFrame(self.pipeline_card, fg_color="transparent")
        pipe_inner.pack(pady=10)

        self.step1_lbl = ctk.CTkLabel(
            pipe_inner,
            text="① Profile Setup",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#38bdf8",
        )
        self.step1_lbl.pack(side="left", padx=(10, 8))

        self.step1_sep = ctk.CTkLabel(
            pipe_inner,
            text="───▶",
            font=ctk.CTkFont(size=11),
            text_color="#475569",
        )
        self.step1_sep.pack(side="left", padx=4)

        self.step2_lbl = ctk.CTkLabel(
            pipe_inner,
            text="② Email Verification",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#64748b",
        )
        self.step2_lbl.pack(side="left", padx=8)

        self.step2_sep = ctk.CTkLabel(
            pipe_inner,
            text="───▶",
            font=ctk.CTkFont(size=11),
            text_color="#475569",
        )
        self.step2_sep.pack(side="left", padx=4)

        self.step3_lbl = ctk.CTkLabel(
            pipe_inner,
            text="③ Access Link Ready",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#64748b",
        )
        self.step3_lbl.pack(side="left", padx=(8, 10))

        # Result Banner (Initially Hidden)
        self.result_card = ctk.CTkFrame(main_scroll, fg_color="#14532d", corner_radius=10)
        
        self.result_title = ctk.CTkLabel(
            self.result_card,
            text="Success! Redemption link is ready",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#86efac",
        )
        self.result_title.pack(padx=16, pady=(14, 6), anchor="w")

        # Redemption Link Pill Container (Rounded Background, Not an Input Field)
        self.url_frame = ctk.CTkFrame(
            self.result_card,
            fg_color="#064e3b",
            corner_radius=8,
            border_width=1,
            border_color="#047857",
        )
        self.url_frame.pack(fill="x", padx=16, pady=(4, 12))

        self.lbl_result_url = ctk.CTkLabel(
            self.url_frame,
            text="",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            text_color="#a7f3d0",
            anchor="w",
            justify="left",
        )
        self.lbl_result_url.pack(padx=14, pady=10, fill="x")

        res_btn_frame = ctk.CTkFrame(self.result_card, fg_color="transparent")
        res_btn_frame.pack(fill="x", padx=16, pady=(0, 12))

        self.btn_copy_link = ctk.CTkButton(
            res_btn_frame,
            text="Copy Offer Link",
            width=140,
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#16a34a",
            hover_color="#15803d",
            corner_radius=8,
            command=self._copy_link_to_clipboard,
        )
        self.btn_copy_link.pack(side="left", padx=(0, 10))

        self.btn_open_browser = ctk.CTkButton(
            res_btn_frame,
            text="Open in Browser",
            width=140,
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            corner_radius=8,
            command=self._open_in_browser,
        )
        self.btn_open_browser.pack(side="left", padx=(0, 10))

        self.btn_open_results = ctk.CTkButton(
            res_btn_frame,
            text="Open Results Folder",
            width=160,
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#334155",
            hover_color="#475569",
            corner_radius=8,
            command=self._open_results_folder,
        )
        self.btn_open_results.pack(side="left")

        self.btn_res_support = ctk.CTkButton(
            res_btn_frame,
            text="Support Dev",
            width=140,
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#d97706",
            hover_color="#b45309",
            corner_radius=8,
            command=self._show_support_modal,
        )
        self.btn_res_support.pack(side="left", padx=(10, 0))

        # Instruction & Advisory Notice Card inside Result
        self.notice_box = ctk.CTkFrame(self.result_card, fg_color="#0f3b20", corner_radius=8)
        self.notice_box.pack(fill="x", padx=16, pady=(0, 16))

        ctk.CTkLabel(
            self.notice_box,
            text="How to activate",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#f8fafc",
            anchor="w",
        ).pack(padx=16, pady=(12, 3), fill="x", anchor="w")

        self.lbl_activate_desc = ctk.CTkLabel(
            self.notice_box,
            text="Open the offer link in your browser and proceed with the activation directly on your screen. Follow the on-screen steps to complete your 1-Year Google AI Plus access.",
            font=ctk.CTkFont(size=12),
            text_color="#cbd5e1",
            justify="left",
            anchor="w",
        )
        self.lbl_activate_desc.pack(padx=16, pady=(0, 10), fill="x", anchor="w")

        ctk.CTkLabel(
            self.notice_box,
            text="Important Notice",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#fde047",
            anchor="w",
        ).pack(padx=16, pady=(0, 3), fill="x", anchor="w")

        self.lbl_notice_desc = ctk.CTkLabel(
            self.notice_box,
            text="Please carefully review all on-screen details, requirements, and prompts before confirming or proceeding with any steps on the destination page.",
            font=ctk.CTkFont(size=12),
            text_color="#cbd5e1",
            justify="left",
            anchor="w",
        )
        self.lbl_notice_desc.pack(padx=16, pady=(0, 14), fill="x", anchor="w")

        # Responsive text wrapping that consumes entire available width on resize
        self.notice_box.bind("<Configure>", self._on_notice_resize)

        # Live Activity Feed Console
        log_card = ctk.CTkFrame(main_scroll, fg_color="#0f172a", corner_radius=10)
        log_card.pack(fill="both", expand=True, pady=(0, 10), padx=5)

        log_header = ctk.CTkFrame(log_card, fg_color="transparent")
        log_header.pack(fill="x", padx=15, pady=(10, 5))

        ctk.CTkLabel(
            log_header,
            text="Live Activity Feed",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#e2e8f0",
        ).pack(side="left")

        self.lbl_status = ctk.CTkLabel(
            log_header,
            text="● System Ready",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#10b981",
        )
        self.lbl_status.pack(side="right")

        self.txt_logs = ctk.CTkTextbox(
            log_card,
            height=210,
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color="#cbd5e1",
            fg_color="#020617",
            corner_radius=6,
            wrap="word",
        )
        self.txt_logs.pack(fill="both", expand=True, padx=15, pady=(5, 12))
        self.txt_logs.insert("end", DEFAULT_ACTIVITY_TEXT.strip())
        self.txt_logs.configure(state="disabled")

        # Footer Status Bar (Interactive developer link & coffee link on left, clean version on right)
        footer_frame = ctk.CTkFrame(self, fg_color="transparent", height=24)
        footer_frame.pack(fill="x", side="bottom", padx=25, pady=(0, 8))

        dev_link = ctk.CTkLabel(
            footer_frame,
            text="Developed by @nmrisrl11",
            font=ctk.CTkFont(size=11),
            text_color="#64748b",
            cursor="hand2",
        )
        dev_link.pack(side="left")
        dev_link.bind("<Enter>", lambda e: dev_link.configure(text_color="#38bdf8"))
        dev_link.bind("<Leave>", lambda e: dev_link.configure(text_color="#64748b"))
        dev_link.bind("<Button-1>", lambda e: webbrowser.open(DEVELOPER_GITHUB_URL))

        sep1 = ctk.CTkLabel(footer_frame, text="  •  ", font=ctk.CTkFont(size=11), text_color="#334155")
        sep1.pack(side="left")

        about_link = ctk.CTkLabel(
            footer_frame,
            text="About",
            font=ctk.CTkFont(size=11),
            text_color="#64748b",
            cursor="hand2",
        )
        about_link.pack(side="left")
        about_link.bind("<Enter>", lambda e: about_link.configure(text_color="#38bdf8"))
        about_link.bind("<Leave>", lambda e: about_link.configure(text_color="#64748b"))
        about_link.bind("<Button-1>", lambda e: self._show_about_modal())

        sep2 = ctk.CTkLabel(footer_frame, text="  •  ", font=ctk.CTkFont(size=11), text_color="#334155")
        sep2.pack(side="left")

        support_link = ctk.CTkLabel(
            footer_frame,
            text="Buy Me a Coffee",
            font=ctk.CTkFont(size=11),
            text_color="#64748b",
            cursor="hand2",
        )
        support_link.pack(side="left")
        support_link.bind("<Enter>", lambda e: support_link.configure(text_color="#f59e0b"))
        support_link.bind("<Leave>", lambda e: support_link.configure(text_color="#64748b"))
        support_link.bind("<Button-1>", lambda e: self._show_support_modal())

        lbl_ver = ctk.CTkLabel(
            footer_frame,
            text=f"{APP_VERSION}",
            font=ctk.CTkFont(size=11),
            text_color="#475569",
        )
        lbl_ver.pack(side="right")

    def _show_about_modal(self):
        """Displays the About application modal."""
        modal = AboutModal(self)
        self.wait_window(modal)

    def _show_support_modal(self):
        """Displays the Support & Donation modal with QR codes."""
        modal = SupportModal(self)
        self.wait_window(modal)

    def _on_notice_resize(self, event):
        """Dynamically adjusts wraplength to consume the entire available card width without premature wrapping."""
        available_width = max(200, event.width - 36)
        if hasattr(self, "lbl_activate_desc"):
            self.lbl_activate_desc.configure(wraplength=available_width)
        if hasattr(self, "lbl_notice_desc"):
            self.lbl_notice_desc.configure(wraplength=available_width)

    def _set_pipeline_step(self, step: int):
        """Updates the visual 3-step pipeline progress stepper."""
        if not hasattr(self, "step1_lbl"):
            return

        if step == 1:
            self.step1_lbl.configure(text="① Profile Setup", text_color="#38bdf8")
            self.step1_sep.configure(text_color="#475569")
            self.step2_lbl.configure(text="② Email Verification", text_color="#64748b")
            self.step2_sep.configure(text_color="#475569")
            self.step3_lbl.configure(text="③ Access Link Ready", text_color="#64748b")
        elif step == 2:
            self.step1_lbl.configure(text="✓ Profile Ready", text_color="#10b981")
            self.step1_sep.configure(text_color="#10b981")
            self.step2_lbl.configure(text="② Awaiting Email OTP", text_color="#f59e0b")
            self.step2_sep.configure(text_color="#475569")
            self.step3_lbl.configure(text="③ Access Link Ready", text_color="#64748b")
        elif step >= 3:
            self.step1_lbl.configure(text="✓ Profile Ready", text_color="#10b981")
            self.step1_sep.configure(text_color="#10b981")
            self.step2_lbl.configure(text="✓ Email Verified", text_color="#10b981")
            self.step2_sep.configure(text_color="#10b981")
            self.step3_lbl.configure(text="✓ 1-Year Link Ready", text_color="#10b981")

    def _reset_activity_feed(self):
        """Restores the initial clean guide in the activity textbox."""
        self.has_logged_activity = False
        self.txt_logs.configure(state="normal")
        self.txt_logs.delete("1.0", "end")
        self.txt_logs.insert("end", DEFAULT_ACTIVITY_TEXT.strip())
        self.txt_logs.configure(state="disabled")

    def _show_diagnostics_menu(self):
        """Allows testing edge cases without consuming a Gmail account."""
        modal = DiagnosticsModal(self)
        self.wait_window(modal)

    def _set_fields_state(self, state: str):
        """Enable or disable all configuration and profile setup fields ('normal' or 'disabled')."""
        self.entry_email.configure(state=state)
        self.entry_password.configure(state=state)
        self.entry_fname.configure(state=state)
        self.entry_lname.configure(state=state)
        self.entry_phone.configure(state=state)
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
        formatted = f"[{timestamp}] {badge} {message}\n"

        self.txt_logs.configure(state="normal")
        self.txt_logs.insert("end", formatted)
        self.txt_logs.see("end")
        self.txt_logs.configure(state="disabled")

    def _set_status(self, text: str, color: str = "#38bdf8"):
        self.lbl_status.configure(text=f"● {text}", text_color=color)

    def _start_queue_listener(self):
        """Processes logs and OTP requests from background worker thread."""
        try:
            while not self.log_queue.empty():
                msg, lvl = self.log_queue.get_nowait()
                self._append_log(msg, lvl)
                if lvl == "SUCCESS" and "Successfully acquired" in msg:
                    self._set_status("Completed Successfully", "#10b981")
                    self._set_pipeline_step(3)
                elif lvl == "ERROR":
                    self._set_status("Notice", "#ef4444")
                elif lvl == "WAITING_USER":
                    self._set_pipeline_step(2)
                    if "challenge" in msg.lower() or "verification" in msg.lower():
                        self._set_status("Awaiting Manual Verification...", "#f59e0b")
                    else:
                        self._set_status("Awaiting Email OTP...", "#f59e0b")

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
        email = self.entry_email.get().strip()
        password = self.entry_password.get().strip()
        fname = self.entry_fname.get().strip()
        lname = self.entry_lname.get().strip()
        phone = self.entry_phone.get().strip()
        show_browser = self.chk_browser.get() if self.chk_browser else False

        if not email or "@gmail.com" not in email:
            messagebox.showerror(
                "Invalid Email",
                "Please enter a valid Gmail address (@gmail.com) for the Google AI Plus promotion.",
                parent=self,
            )
            return

        if len(password) < 6:
            messagebox.showerror(
                "Invalid Password",
                "Password must be at least 6 characters.",
                parent=self,
            )
            return

        self.current_redemption_url = None
        self.result_card.pack_forget()
        self._set_fields_state("disabled")
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(
            state="normal",
            text="Stop Process",
            fg_color="#dc2626",
            hover_color="#b91c1c",
            text_color="#ffffff",
        )
        self._set_status("Processing...", "#38bdf8")
        self._set_pipeline_step(1)
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

        # Reset success state & card
        self.current_redemption_url = None
        self.lbl_result_url.configure(text="")
        self.result_card.pack_forget()

        # Re-enable all fields for fresh input
        self._set_fields_state("normal")

        # Clear email and randomize credentials
        self.entry_email.delete(0, "end")
        self._randomize_credentials()
        self.entry_email.focus()

        # Reset action buttons, pipeline & status
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(
            state="normal",
            text="Reset Fields",
            fg_color="#334155",
            hover_color="#475569",
            text_color="#cbd5e1",
        )
        self._set_pipeline_step(1)
        self._set_status("System Ready", "#10b981")

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
            self.btn_start.configure(state="disabled")
            self.btn_stop.configure(
                state="normal",
                text="Provision Another Account",
                fg_color="#0284c7",
                hover_color="#0369a1",
                text_color="#ffffff",
            )
            self._set_pipeline_step(3)
        else:
            # Failed or aborted: restore fields and allow re-trying
            self._set_fields_state("normal")
            self.btn_start.configure(state="normal")
            self.btn_stop.configure(
                state="normal",
                text="Reset Fields",
                fg_color="#334155",
                hover_color="#475569",
                text_color="#cbd5e1",
            )

    def _on_error_callback(self, err_msg: str):
        formatted = normalize_error_message(err_msg, for_log=False)
        messagebox.showerror("Notice", formatted, parent=self)

    def _on_success_callback(self, redemption_url: str):
        self.current_redemption_url = redemption_url
        self.lbl_result_url.configure(text=redemption_url)
        self.result_card.pack(fill="x", pady=10, padx=5, before=self.pipeline_card)
        self._set_pipeline_step(3)

        # Lock configuration fields upon success and offer Provision Another
        self._set_fields_state("disabled")
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(
            state="normal",
            text="Provision Another Account",
            fg_color="#0284c7",
            hover_color="#0369a1",
            text_color="#ffffff",
        )

        # Save record to results folder
        email = self.entry_email.get().strip() or "account@gmail.com"
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
            self.clipboard_clear()
            self.clipboard_append(self.current_redemption_url)
            self.update()
            self.btn_copy_link.configure(text="Copied to Clipboard!")
            self.after(2500, lambda: self.btn_copy_link.configure(text="Copy Offer Link"))

    def _open_in_browser(self):
        if self.current_redemption_url:
            webbrowser.open(self.current_redemption_url)


if __name__ == "__main__":
    app = GeminiClaimerApp()
    app.mainloop()
