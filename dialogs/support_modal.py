"""
Donation & Support modal with clean QR display and punchy copywriting.
"""

import os
from PIL import Image
import customtkinter as ctk

from constants import IMAGES_DIR


class SupportModal(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Support the Dev")
        self.geometry("540x510")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        ico_path = os.path.join(IMAGES_DIR, "app_icon.ico")
        if os.path.exists(ico_path):
            try:
                self.after(200, lambda: self.iconbitmap(ico_path))
            except Exception:
                pass

        # Center relative to parent window
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        self.geometry(f"+{max(0, parent_x + 160)}+{max(0, parent_y + 110)}")

        # Load QR images
        bmc_path = os.path.join(IMAGES_DIR, "qrcode-bmc.png")
        gcash_path = os.path.join(IMAGES_DIR, "qrcode-gcash.JPG")

        self.ctk_bmc = None
        self.ctk_gcash = None

        if os.path.exists(bmc_path):
            try:
                im_bmc = Image.open(bmc_path)
                self.ctk_bmc = ctk.CTkImage(light_image=im_bmc, dark_image=im_bmc, size=(145, 145))
            except Exception as e:
                print(f"Error loading BMC QR: {e}")

        if os.path.exists(gcash_path):
            try:
                im_gcash = Image.open(gcash_path)
                self.ctk_gcash = ctk.CTkImage(light_image=im_gcash, dark_image=im_gcash, size=(145, 145))
            except Exception as e:
                print(f"Error loading GCash QR: {e}")

        # Modal Title
        ctk.CTkLabel(
            self,
            text="Buy Me a Coffee",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#38bdf8",
        ).pack(pady=(20, 6))

        # Short & punchy copywriting
        copy_text = (
            "Saved you some time? Buying a coffee won't hurt.\n"
            "Totally optional, but always appreciated!"
        )

        ctk.CTkLabel(
            self,
            text=copy_text,
            font=ctk.CTkFont(size=12),
            text_color="#cbd5e1",
            wraplength=460,
            justify="center",
        ).pack(pady=(0, 14), padx=20)

        # 2-Column QR Code Cards Container
        qr_frame = ctk.CTkFrame(self, fg_color="transparent")
        qr_frame.pack(fill="x", padx=20, pady=4)
        qr_frame.grid_columnconfigure(0, weight=1)
        qr_frame.grid_columnconfigure(1, weight=1)

        # Card 1: Buy Me a Coffee
        card_bmc = ctk.CTkFrame(qr_frame, fg_color="#1e293b", corner_radius=10)
        card_bmc.grid(row=0, column=0, padx=8, sticky="nsew")

        ctk.CTkLabel(
            card_bmc,
            text="Buy Me a Coffee",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#fde047",
        ).pack(pady=(12, 2))

        ctk.CTkLabel(
            card_bmc,
            text="International",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        ).pack(pady=(0, 6))

        if self.ctk_bmc:
            ctk.CTkLabel(card_bmc, text="", image=self.ctk_bmc).pack(pady=2)

        ctk.CTkLabel(
            card_bmc,
            text="Scan to donate",
            font=ctk.CTkFont(size=11),
            text_color="#64748b",
        ).pack(pady=(6, 12))

        # Card 2: GCash
        card_gcash = ctk.CTkFrame(qr_frame, fg_color="#1e293b", corner_radius=10)
        card_gcash.grid(row=0, column=1, padx=8, sticky="nsew")

        ctk.CTkLabel(
            card_gcash,
            text="GCash",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#38bdf8",
        ).pack(pady=(12, 2))

        ctk.CTkLabel(
            card_gcash,
            text="Philippines",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        ).pack(pady=(0, 6))

        if self.ctk_gcash:
            ctk.CTkLabel(card_gcash, text="", image=self.ctk_gcash).pack(pady=2)

        ctk.CTkLabel(
            card_gcash,
            text="Scan to donate",
            font=ctk.CTkFont(size=11),
            text_color="#64748b",
        ).pack(pady=(6, 12))

        # Subtle footer
        ctk.CTkLabel(
            self,
            text="Optional • Thanks for your support!",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="#64748b",
        ).pack(pady=(12, 8))

        # Dismiss button
        ctk.CTkButton(
            self,
            text="Close",
            width=140,
            height=34,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#334155",
            hover_color="#475569",
            command=self.destroy,
        ).pack(pady=(0, 16))
