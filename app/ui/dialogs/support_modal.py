"""
Donation & Support modal with clean QR display and punchy copywriting.
"""

import os
from PIL import Image
import customtkinter as ctk

from app.config import IMAGES_DIR
from app.ui import theme as T


class SupportModal(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Support the Dev")
        self.resizable(False, False)
        self.configure(fg_color=T.BG_WINDOW)
        self.transient(parent)
        self.grab_set()

        T.center_modal(self, parent, 530, 495)
        T.apply_modal_icon(self, IMAGES_DIR)
        self.after(60, lambda: T.apply_win11_titlebar(self, T.BG_WINDOW, T.TEXT_PRIMARY))

        # Load QR images
        bmc_path = os.path.join(IMAGES_DIR, "qrcode-bmc.png")
        gcash_path = os.path.join(IMAGES_DIR, "qrcode-gcash.JPG")

        self.ctk_bmc = None
        self.ctk_gcash = None

        if os.path.exists(bmc_path):
            try:
                im_bmc = Image.open(bmc_path)
                self.ctk_bmc = ctk.CTkImage(light_image=im_bmc, dark_image=im_bmc, size=(142, 142))
            except Exception as e:
                print(f"Error loading BMC QR: {e}")

        if os.path.exists(gcash_path):
            try:
                im_gcash = Image.open(gcash_path)
                self.ctk_gcash = ctk.CTkImage(light_image=im_gcash, dark_image=im_gcash, size=(142, 142))
            except Exception as e:
                print(f"Error loading GCash QR: {e}")

        wrapper = ctk.CTkFrame(self, fg_color="transparent")
        wrapper.pack(fill="both", expand=True, padx=22, pady=20)

        # Modal Header
        ctk.CTkLabel(
            wrapper,
            text="Buy Me a Coffee",
            font=T.ui_font(18, "bold"),
            text_color=T.TEXT_PRIMARY,
        ).pack(pady=(0, 4))

        copy_text = (
            "Saved you some time? Buying a coffee won't hurt.\n"
            "Totally optional, always appreciated."
        )
        ctk.CTkLabel(
            wrapper,
            text=copy_text,
            font=T.ui_font(12),
            text_color=T.TEXT_SECONDARY,
            wraplength=440,
            justify="center",
        ).pack(pady=(0, 16))

        # 2-Column QR Code Cards Container
        qr_frame = ctk.CTkFrame(wrapper, fg_color="transparent")
        qr_frame.pack(fill="x", pady=(0, 14))
        qr_frame.grid_columnconfigure(0, weight=1, uniform="qr_col")
        qr_frame.grid_columnconfigure(1, weight=1, uniform="qr_col")

        # Card 1: Buy Me a Coffee
        card_bmc = ctk.CTkFrame(
            qr_frame,
            fg_color=T.BG_CARD,
            border_width=1,
            border_color=T.BORDER_SUBTLE,
            corner_radius=12,
        )
        card_bmc.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        ctk.CTkLabel(
            card_bmc,
            text="Buy Me a Coffee",
            font=T.ui_font(13, "bold"),
            text_color=T.WARNING_TEXT,
        ).pack(pady=(14, 1))

        ctk.CTkLabel(
            card_bmc,
            text="International",
            font=T.ui_font(11),
            text_color=T.TEXT_MUTED,
        ).pack(pady=(0, 10))

        if self.ctk_bmc:
            qr_plate_1 = ctk.CTkFrame(card_bmc, fg_color="#FFFFFF", corner_radius=8)
            qr_plate_1.pack(pady=2)
            ctk.CTkLabel(qr_plate_1, text="", image=self.ctk_bmc).pack(padx=6, pady=6)

        ctk.CTkLabel(
            card_bmc,
            text="Scan QR to support",
            font=T.ui_font(11),
            text_color=T.TEXT_MUTED,
        ).pack(pady=(8, 14))

        # Card 2: GCash
        card_gcash = ctk.CTkFrame(
            qr_frame,
            fg_color=T.BG_CARD,
            border_width=1,
            border_color=T.BORDER_SUBTLE,
            corner_radius=12,
        )
        card_gcash.grid(row=0, column=1, padx=(8, 0), sticky="nsew")

        ctk.CTkLabel(
            card_gcash,
            text="GCash",
            font=T.ui_font(13, "bold"),
            text_color=T.ACCENT_TEXT,
        ).pack(pady=(14, 1))

        ctk.CTkLabel(
            card_gcash,
            text="Philippines",
            font=T.ui_font(11),
            text_color=T.TEXT_MUTED,
        ).pack(pady=(0, 10))

        if self.ctk_gcash:
            qr_plate_2 = ctk.CTkFrame(card_gcash, fg_color="#FFFFFF", corner_radius=8)
            qr_plate_2.pack(pady=2)
            ctk.CTkLabel(qr_plate_2, text="", image=self.ctk_gcash).pack(padx=6, pady=6)

        ctk.CTkLabel(
            card_gcash,
            text="Scan QR to support",
            font=T.ui_font(11),
            text_color=T.TEXT_MUTED,
        ).pack(pady=(8, 14))

        # Subtle footer + Close button
        ctk.CTkLabel(
            wrapper,
            text="Optional  ·  Thanks for using Google AI Plus Portal",
            font=T.ui_font(11),
            text_color=T.TEXT_MUTED,
        ).pack(pady=(2, 12))

        ctk.CTkButton(
            wrapper,
            text="Close",
            width=124,
            height=34,
            font=T.ui_font(12, "bold"),
            fg_color=T.BTN_SECONDARY,
            hover_color=T.BTN_SECONDARY_HOVER,
            border_width=1,
            border_color=T.BORDER_GHOST,
            text_color=T.TEXT_PRIMARY,
            corner_radius=7,
            command=self.destroy,
        ).pack()

        self.bind("<Escape>", lambda e: self.destroy())
