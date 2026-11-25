"""
About Modal dialog for Google AI Plus Portal.
Explains application overview, workflow, limitations, expectations, and privacy.
"""

import os
import webbrowser
from PIL import Image
import customtkinter as ctk

from app.config import APP_VERSION, DEVELOPER_GITHUB_URL, IMAGES_DIR
from app.ui import theme as T


class AboutModal(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("About — Google AI Plus Portal")
        self.resizable(False, False)
        self.configure(fg_color=T.BG_WINDOW)
        self.transient(parent)
        self.grab_set()

        T.center_modal(self, parent, 590, 580)
        T.apply_modal_icon(self, IMAGES_DIR)
        self.after(60, lambda: T.apply_win11_titlebar(self, T.BG_TOPBAR, T.TEXT_PRIMARY))

        # Top Identity Header Bar
        header = ctk.CTkFrame(self, fg_color=T.BG_TOPBAR, corner_radius=0)
        header.pack(fill="x")

        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(fill="x", padx=22, pady=16)

        icon_path = os.path.join(IMAGES_DIR, "app_icon.png")
        if os.path.exists(icon_path):
            try:
                raw_logo = Image.open(icon_path)
                self.logo_img = ctk.CTkImage(light_image=raw_logo, dark_image=raw_logo, size=(42, 42))
                ctk.CTkLabel(header_inner, text="", image=self.logo_img).pack(side="left", padx=(0, 14))
            except Exception:
                pass

        title_stack = ctk.CTkFrame(header_inner, fg_color="transparent")
        title_stack.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            title_stack,
            text="Google AI Plus — 1-Year Access Portal",
            font=T.ui_font(16, "bold"),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_stack,
            text=f"{APP_VERSION}  ·  Desktop Edition  ·  Developed by @nmrisrl11",
            font=T.ui_font(11),
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        ctk.CTkFrame(self, fg_color=T.BORDER_SUBTLE, height=1, corner_radius=0).pack(fill="x")

        # Tabview for Organized Information
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=T.BG_CARD,
            border_width=1,
            border_color=T.BORDER_SUBTLE,
            corner_radius=10,
            segmented_button_fg_color=T.BG_SUBCARD,
            segmented_button_selected_color=T.ACCENT,
            segmented_button_selected_hover_color=T.ACCENT_HOVER,
            segmented_button_unselected_color=T.BG_SUBCARD,
            segmented_button_unselected_hover_color=T.BG_HOVER,
            text_color=T.TEXT_PRIMARY,
            text_color_disabled=T.TEXT_MUTED,
        )
        self.tabview.pack(padx=20, pady=(14, 14), fill="both", expand=True)

        tab_overview = self.tabview.add("What It Does")
        tab_limits = self.tabview.add("Usage & Limits")
        tab_privacy = self.tabview.add("Privacy & Terms")

        # ------------------------------------------------------------------
        # Tab 1: What It Does
        # ------------------------------------------------------------------
        scroll_overview = ctk.CTkScrollableFrame(
            tab_overview,
            fg_color="transparent",
            scrollbar_button_color="#222938",
            scrollbar_button_hover_color="#333E54",
        )
        scroll_overview.pack(fill="both", expand=True, padx=6, pady=4)

        self._add_section_header(scroll_overview, "Purpose & Automation")
        self._add_paragraph(
            scroll_overview,
            "An automated desktop utility designed to streamline the student promotional onboarding and link acquisition process for Google AI Plus (12 months of free Gemini Advanced & 2TB cloud storage).",
        )

        self._add_section_header(scroll_overview, "Why Use This Tool?")
        self._add_paragraph(
            scroll_overview,
            "Manually registering, formatting regional contact information, navigating multi-step verification pages, and locating the redemption endpoint can be tedious and time-consuming.\n\n"
            "This tool automates the entire navigation and form-filling flow in the background, prompting you only when your 6-digit email OTP arrives.",
        )

        self._add_section_header(scroll_overview, "How The Workflow Works")
        self._add_paragraph(
            scroll_overview,
            "1. Profile Generation: Prepares valid, randomized Indian student credentials.\n"
            "2. Automated Registration: Navigates the promotional registration portal.\n"
            "3. OTP Prompt: Safely requests your 6-digit email verification code.\n"
            "4. Link Extraction: Extracts your unique Google One promotional redemption link.\n"
            "5. Local Backup: Saves generated credentials and your offer link in results/.",
        )

        # ------------------------------------------------------------------
        # Tab 2: Usage & Limits
        # ------------------------------------------------------------------
        scroll_limits = ctk.CTkScrollableFrame(
            tab_limits,
            fg_color="transparent",
            scrollbar_button_color="#222938",
            scrollbar_button_hover_color="#333E54",
        )
        scroll_limits.pack(fill="both", expand=True, padx=6, pady=4)

        self._add_section_header(scroll_limits, "Google Account Compatibility")
        self._add_paragraph(
            scroll_limits,
            "The generated offer link is redeemed directly on Google One. Your target Google account must be in good standing and not currently enrolled in a conflicting Google Workspace enterprise plan or active promotional tier.",
        )

        self._add_section_header(scroll_limits, "Payment Method Linking on Google")
        self._add_paragraph(
            scroll_limits,
            "Google's standard policy requires attaching a valid payment method (Credit/Debit Card, PayPal, etc.) to verify identity and activate promotional trial subscriptions.\n\n"
            "• You are NOT charged during the free 12-month period ($0.00 due today).\n"
            "• You can manage or cancel auto-renewal anytime in your Google One account settings before the 1-year period ends.",
        )

        self._add_section_header(scroll_limits, "Single-Use Promotional Links")
        self._add_paragraph(
            scroll_limits,
            "Each generated link is a unique single-use promotional grant bound to the registration session. Once redeemed on a Google account, it cannot be transferred or reused.",
        )

        self._add_section_header(scroll_limits, "Promotion Availability")
        self._add_paragraph(
            scroll_limits,
            "This promotion is provided by external educational partners and Google. Availability, regional eligibility, and program quotas are subject to change at the provider's discretion.",
        )

        # ------------------------------------------------------------------
        # Tab 3: Privacy & Terms
        # ------------------------------------------------------------------
        scroll_privacy = ctk.CTkScrollableFrame(
            tab_privacy,
            fg_color="transparent",
            scrollbar_button_color="#222938",
            scrollbar_button_hover_color="#333E54",
        )
        scroll_privacy.pack(fill="both", expand=True, padx=6, pady=4)

        self._add_section_header(scroll_privacy, "100% Local Execution")
        self._add_paragraph(
            scroll_privacy,
            "All automation executes locally on your machine using standard Chromium browser automation (Playwright). No cloud relays, external proxies, or third-party servers are used.",
        )

        self._add_section_header(scroll_privacy, "Zero Telemetry & Zero Data Collection")
        self._add_paragraph(
            scroll_privacy,
            "This application contains no tracking, telemetry, or analytics.\n\n"
            "Your passwords, email addresses, and verification codes are never transmitted to the developer or any external server. All session reports are saved strictly on your local disk in the results/ folder.",
        )

        self._add_section_header(scroll_privacy, "Disclaimer & Affiliation")
        self._add_paragraph(
            scroll_privacy,
            "This is an independent desktop automation utility provided for personal convenience and educational purposes.\n\n"
            "This software is NOT affiliated with, sponsored by, or endorsed by Google LLC, Alphabet Inc., or Internshala. All trademarks, service marks, and company names belong to their respective owners.",
        )

        # ------------------------------------------------------------------
        # Bottom Action Bar
        # ------------------------------------------------------------------
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=20, pady=(0, 16))

        ctk.CTkButton(
            bottom_frame,
            text="GitHub",
            width=88,
            height=34,
            font=T.ui_font(12, "bold"),
            fg_color="transparent",
            hover_color=T.BG_HOVER,
            border_width=1,
            border_color=T.BORDER_GHOST,
            text_color=T.TEXT_SECONDARY,
            corner_radius=7,
            command=lambda: webbrowser.open(DEVELOPER_GITHUB_URL),
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            bottom_frame,
            text="Support Dev",
            width=112,
            height=34,
            font=T.ui_font(12, "bold"),
            fg_color="transparent",
            hover_color=T.WARNING_BG,
            border_width=1,
            border_color=T.BORDER_GHOST,
            text_color=T.WARNING_TEXT,
            corner_radius=7,
            command=self._open_support_modal,
        ).pack(side="left")

        ctk.CTkButton(
            bottom_frame,
            text="Close",
            width=96,
            height=34,
            font=T.ui_font(12, "bold"),
            fg_color=T.ACCENT,
            hover_color=T.ACCENT_HOVER,
            text_color="#FFFFFF",
            corner_radius=7,
            command=self.destroy,
        ).pack(side="right")

        self.bind("<Escape>", lambda e: self.destroy())

    def _open_support_modal(self):
        from app.ui.dialogs.support_modal import SupportModal
        self.destroy()
        if hasattr(self.parent, "_show_support_modal"):
            self.parent._show_support_modal()
        else:
            SupportModal(self.parent)

    def _add_section_header(self, parent, text: str):
        ctk.CTkLabel(
            parent,
            text=text,
            font=T.ui_font(13, "bold"),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x", pady=(10, 3))

    def _add_paragraph(self, parent, text: str):
        ctk.CTkLabel(
            parent,
            text=text,
            font=T.ui_font(12),
            text_color=T.TEXT_SECONDARY,
            justify="left",
            anchor="w",
            wraplength=490,
        ).pack(fill="x", pady=(0, 6))
