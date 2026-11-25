"""
Email verification OTP input dialog with strict 6-digit keystroke validation.
"""

import customtkinter as ctk

from constants import IMAGES_DIR
import theme as T


class OTPDialog(ctk.CTkToplevel):
    def __init__(self, parent, email: str, error_message: str = None):
        super().__init__(parent)
        self.title("Email Verification")
        width = 450
        height = 385 if error_message else 335
        self.resizable(False, False)
        self.configure(fg_color=T.BG_WINDOW)
        self.transient(parent)
        self.grab_set()

        T.center_modal(self, parent, width, height)
        T.apply_modal_icon(self, IMAGES_DIR)
        self.after(60, lambda: T.apply_win11_titlebar(self, T.BG_WINDOW, T.TEXT_PRIMARY))

        self.otp_value = None

        # Outer container
        wrapper = ctk.CTkFrame(self, fg_color="transparent")
        wrapper.pack(fill="both", expand=True, padx=22, pady=20)

        # Header
        self.lbl_title = ctk.CTkLabel(
            wrapper,
            text="Verify Your Email",
            font=T.ui_font(18, "bold"),
            text_color=T.TEXT_PRIMARY,
        )
        self.lbl_title.pack(anchor="w")

        self.lbl_desc = ctk.CTkLabel(
            wrapper,
            text="Enter the 6-digit verification code sent to:",
            font=T.ui_font(12),
            text_color=T.TEXT_SECONDARY,
        )
        self.lbl_desc.pack(anchor="w", pady=(3, 8))

        # Target Email Pill
        email_pill = ctk.CTkFrame(
            wrapper,
            fg_color=T.BG_CARD,
            border_width=1,
            border_color=T.BORDER_SUBTLE,
            corner_radius=7,
        )
        email_pill.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            email_pill,
            text=email,
            font=T.mono_font(12, "bold"),
            text_color=T.ACCENT_TEXT,
            anchor="w",
        ).pack(padx=12, pady=7, fill="x")

        # Optional Error Alert Banner
        if error_message:
            err_box = ctk.CTkFrame(
                wrapper,
                fg_color=T.DANGER_BG,
                border_width=1,
                border_color=T.DANGER_BORDER,
                corner_radius=7,
            )
            err_box.pack(fill="x", pady=(0, 10))
            self.lbl_err = ctk.CTkLabel(
                err_box,
                text=f"Notice: {error_message}",
                font=T.ui_font(11, "bold"),
                text_color=T.DANGER_TEXT,
                wraplength=380,
                justify="left",
                anchor="w",
            )
            self.lbl_err.pack(padx=12, pady=7, fill="x")

        # Main OTP Input Card
        input_card = ctk.CTkFrame(
            wrapper,
            fg_color=T.BG_CARD,
            border_width=1,
            border_color=T.BORDER_SUBTLE,
            corner_radius=10,
        )
        input_card.pack(fill="x", pady=(0, 14))

        vcmd = (self.register(self._validate_otp_input), "%P")
        self.entry_otp = ctk.CTkEntry(
            input_card,
            placeholder_text="• • • • • •",
            height=50,
            justify="center",
            font=T.mono_font(24, "bold"),
            fg_color=T.BG_INPUT,
            border_width=1,
            border_color=T.BORDER_INPUT,
            text_color=T.TEXT_PRIMARY,
            placeholder_text_color=T.TEXT_FAINT,
            corner_radius=8,
            validate="key",
            validatecommand=vcmd,
        )
        self.entry_otp.pack(fill="x", padx=16, pady=(14, 6))
        T.bind_entry_focus(self.entry_otp)

        self.lbl_counter = ctk.CTkLabel(
            input_card,
            text="0 / 6 digits entered",
            font=T.ui_font(11),
            text_color=T.TEXT_MUTED,
        )
        self.lbl_counter.pack(pady=(0, 12))

        # Action Bar
        btn_row = ctk.CTkFrame(wrapper, fg_color="transparent")
        btn_row.pack(fill="x", side="bottom")

        ctk.CTkButton(
            btn_row,
            text="Cancel",
            width=96,
            height=38,
            font=T.ui_font(12, "bold"),
            fg_color="transparent",
            hover_color=T.BG_HOVER,
            border_width=1,
            border_color=T.BORDER_GHOST,
            text_color=T.TEXT_SECONDARY,
            corner_radius=8,
            command=self._on_close,
        ).pack(side="left")

        self.btn_submit = ctk.CTkButton(
            btn_row,
            text="Verify Code & Proceed",
            height=38,
            font=T.ui_font(13, "bold"),
            state="disabled",
            fg_color=T.BTN_DISABLED_BG,
            hover_color=T.ACCENT_HOVER,
            text_color=T.TEXT_DISABLED,
            corner_radius=8,
            command=self._on_submit,
        )
        self.btn_submit.pack(side="right", fill="x", expand=True, padx=(10, 0))

        # Event bindings
        self.entry_otp.bind("<Return>", lambda e: self._on_submit())
        self.entry_otp.bind("<Control-v>", self._handle_paste)
        self.entry_otp.bind("<Control-V>", self._handle_paste)
        self.entry_otp.bind("<<Paste>>", self._handle_paste)
        self.bind("<Escape>", lambda e: self._on_close())
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.after(100, lambda: self.entry_otp.focus_set())

    def _validate_otp_input(self, proposed: str) -> bool:
        """Restricts input strictly to numeric digits only and maximum 6 characters."""
        if len(proposed) > 6:
            return False
        if proposed != "" and not proposed.isdigit():
            return False
        self._update_counter_and_button(proposed)
        return True

    def _update_counter_and_button(self, val: str):
        if not hasattr(self, "lbl_counter") or not hasattr(self, "btn_submit"):
            return
        length = len(val)
        if length == 0:
            self.lbl_counter.configure(text="0 / 6 digits entered", text_color=T.TEXT_MUTED)
            self.btn_submit.configure(state="disabled", fg_color=T.BTN_DISABLED_BG, text_color=T.TEXT_DISABLED)
        elif length < 6:
            self.lbl_counter.configure(text=f"{length} / 6 digits entered", text_color=T.WARNING_TEXT)
            self.btn_submit.configure(state="disabled", fg_color=T.BTN_DISABLED_BG, text_color=T.TEXT_DISABLED)
        else:
            self.lbl_counter.configure(text="6 / 6 digits entered — ready to verify", text_color=T.SUCCESS_TEXT)
            self.btn_submit.configure(state="normal", fg_color=T.ACCENT, text_color="#FFFFFF")

    def _handle_paste(self, event=None):
        """Filters pasted text to only extract digits and limit to 6 digits."""
        try:
            raw = self.clipboard_get()
        except Exception:
            return "break"

        digits = "".join(ch for ch in raw if ch.isdigit())[:6]
        if digits:
            self.entry_otp.delete(0, "end")
            self.entry_otp.insert(0, digits)
            self._update_counter_and_button(digits)
        return "break"

    def _on_close(self):
        self.otp_value = None
        self.destroy()

    def _on_submit(self):
        val = self.entry_otp.get().strip()
        if len(val) != 6 or not val.isdigit():
            self.lbl_counter.configure(text="Exactly 6 digits required to verify", text_color=T.DANGER_TEXT)
            return
        self.otp_value = val
        self.destroy()
