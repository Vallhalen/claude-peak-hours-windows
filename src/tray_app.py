"""System tray application — native Win32 tray icon + tkinter popup.

Uses ctypes to talk directly to Shell_NotifyIconW so we get
reliable single-click detection (WM_LBUTTONUP).
Tkinter runs on the main thread; tray icon messages are dispatched
via a hidden win32 window running in a background thread.
"""

from __future__ import annotations

import sys
import os
import threading
import ctypes
import ctypes.wintypes as wt
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageDraw

from peak_hours_manager import PeakHoursManager, PeakStatus, PeakState
from strings import (
    FULL_POWER_HEADER, RESTRICTED_HEADER,
    FULL_POWER_DESC, RESTRICTED_DESC,
    RESTRICTION_HOURS, WORKDAYS, WORKDAYS_VALUE,
    LAUNCH_AT_LOGIN, NOTIFICATIONS, QUIT,
)

# ---------------------------------------------------------------------------
# Win32 constants & structures
# ---------------------------------------------------------------------------
WM_USER = 0x0400
WM_TRAYICON = WM_USER + 1
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
WM_DESTROY = 0x0002

NIF_ICON = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_TIP = 0x00000004
NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002

IDI_APPLICATION = 32512
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010
LR_DEFAULTSIZE = 0x0040

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_long, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)

shell32 = ctypes.windll.shell32
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Set proper argtypes/restypes for 64-bit Windows
user32.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.DefWindowProcW.restype = ctypes.c_long

user32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.PostQuitMessage.argtypes = [ctypes.c_int]

user32.LoadImageW.argtypes = [
    wt.HINSTANCE, wt.LPCWSTR, wt.UINT, ctypes.c_int, ctypes.c_int, wt.UINT
]
user32.LoadImageW.restype = wt.HANDLE

kernel32.GetModuleHandleW.argtypes = [wt.LPCWSTR]
kernel32.GetModuleHandleW.restype = wt.HINSTANCE


class WNDCLASS(ctypes.Structure):
    _fields_ = [
        ("style", wt.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wt.HINSTANCE),
        ("hIcon", wt.HICON),
        ("hCursor", wt.HANDLE),
        ("hbrBackground", wt.HBRUSH),
        ("lpszMenuName", wt.LPCWSTR),
        ("lpszClassName", wt.LPCWSTR),
    ]


class NOTIFYICONDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.DWORD),
        ("hWnd", wt.HWND),
        ("uID", wt.UINT),
        ("uFlags", wt.UINT),
        ("uCallbackMessage", wt.UINT),
        ("hIcon", wt.HICON),
        ("szTip", ctypes.c_wchar * 128),
    ]


# ---------------------------------------------------------------------------
# Colors / UI
# ---------------------------------------------------------------------------
ICON_COLORS = {
    PeakStatus.OFF_PEAK: (0, 180, 80),
    PeakStatus.PEAK: (220, 50, 50),
    PeakStatus.WARNING: (240, 180, 0),
}

HEX_ACCENT = {
    PeakStatus.OFF_PEAK: "#00a050",
    PeakStatus.PEAK: "#dc3232",
    PeakStatus.WARNING: "#e0a000",
}

BG = "#f5f5f7"
BG_CARD = "#ffffff"
FG_PRIMARY = "#1d1d1f"
FG_SECONDARY = "#6e6e73"
FG_ICON = "#8e8e93"
SEPARATOR = "#e5e5ea"
TOGGLE_ON = "#34c759"
TOGGLE_OFF = "#c7c7cc"
TOGGLE_KNOB = "#ffffff"


# ---------------------------------------------------------------------------
# Icon helpers
# ---------------------------------------------------------------------------

def _pil_to_hicon(pil_image: Image.Image) -> int:
    """Convert a PIL Image to a win32 HICON via a temp .ico file."""
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), "_claude_peak_tray.ico")
    pil_image.save(tmp, format="ICO", sizes=[(32, 32)])
    hicon = user32.LoadImageW(
        None, tmp, IMAGE_ICON, 32, 32,
        LR_LOADFROMFILE | LR_DEFAULTSIZE
    )
    return hicon


def _make_circle_image(status: PeakStatus) -> Image.Image:
    size = 32
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = ICON_COLORS[status]
    draw.ellipse([2, 2, size - 2, size - 2], fill=(*color, 255))
    return img


# ---------------------------------------------------------------------------
# Autostart (Windows Registry)
# ---------------------------------------------------------------------------
_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME = "ClaudePeakHours"


def _get_autostart() -> bool:
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, _APP_NAME)
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def _get_launch_command() -> str:
    """Return the command to launch this app at login."""
    if getattr(sys, "frozen", False):
        # PyInstaller .exe
        return f'"{sys.executable}"'
    else:
        # Running as .pyw script — use pythonw.exe (no console)
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.exists(pythonw):
            pythonw = sys.executable
        script = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "main.pyw")
        )
        return f'"{pythonw}" "{script}"'


def _set_autostart(enabled: bool) -> None:
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE)
        if enabled:
            winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, _get_launch_command())
        else:
            try:
                winreg.DeleteValue(key, _APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Toggle Switch widget
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Popup Window — native Windows look via ttk
# ---------------------------------------------------------------------------

class PopupWindow:

    def __init__(self, root: tk.Tk, manager: PeakHoursManager):
        self.root = root
        self.manager = manager
        self._win: tk.Toplevel | None = None
        self._refs: list = []  # prevent GC of PhotoImages

    @property
    def visible(self) -> bool:
        return self._win is not None and self._win.winfo_exists()

    def toggle(self, click_x: int = 0, click_y: int = 0):
        if self.visible:
            self.close()
        else:
            self.show(click_x, click_y)

    def show(self, click_x: int = 0, click_y: int = 0):
        self._click_x = click_x
        self._click_y = click_y
        self._refs.clear()

        self.manager.update()
        self.manager._compute_local_peak_hours()

        if self._win:
            self._win.destroy()

        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        self._win = win

        # Windows 11 Fluent Design theme
        import sv_ttk
        sv_ttk.set_theme("light")

        state = self.manager.state
        accent = HEX_ACCENT[state.status]

        # Main frame with system background
        frame = ttk.Frame(win, padding=16)
        frame.pack(fill="both", expand=True)

        # --- Status dot (PIL anti-aliased) + Header ---
        hdr = ttk.Frame(frame)
        hdr.pack(anchor="w", fill="x")

        from PIL import ImageTk
        dot_size = 14
        ss = 4
        dot_img = Image.new("RGBA", (dot_size * ss, dot_size * ss), (0, 0, 0, 0))
        dot_draw = ImageDraw.Draw(dot_img)
        rgb = ICON_COLORS[state.status]
        dot_draw.ellipse([ss, ss, (dot_size - 1) * ss, (dot_size - 1) * ss],
                         fill=(*rgb, 255))
        dot_img = dot_img.resize((dot_size, dot_size), Image.LANCZOS)
        dot_photo = ImageTk.PhotoImage(dot_img)
        self._refs.append(dot_photo)

        ttk.Label(hdr, image=dot_photo).pack(side="left", padx=(0, 8))

        header_text = RESTRICTED_HEADER if state.is_peak else FULL_POWER_HEADER
        lbl_hdr = ttk.Label(hdr, text=header_text,
                            font=("Segoe UI", 13, "bold"),
                            foreground=accent)
        lbl_hdr.pack(side="left")

        # --- Description ---
        desc = RESTRICTED_DESC if state.is_peak else FULL_POWER_DESC
        ttk.Label(frame, text=desc, font=("Segoe UI", 9),
                  foreground=FG_SECONDARY, wraplength=260).pack(
            anchor="w", pady=(4, 10))

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=(0, 8))

        # --- Info rows ---
        self._info_row(frame, "\u23f1", state.next_change_label,
                       state.countdown_text)
        self._info_row(frame, "\U0001f551", RESTRICTION_HOURS,
                       state.peak_hours_local)
        self._info_row(frame, "\U0001f4c5", WORKDAYS, WORKDAYS_VALUE)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=(10, 8))

        # --- Native checkboxes ---
        self._autostart_var = tk.BooleanVar(value=_get_autostart())
        self._notif_var = tk.BooleanVar(value=self.manager.notifications_enabled)

        ttk.Checkbutton(frame, text=LAUNCH_AT_LOGIN,
                        variable=self._autostart_var,
                        command=self._on_autostart,
                        style="Switch.TCheckbutton").pack(anchor="w", pady=2)

        ttk.Checkbutton(frame, text=NOTIFICATIONS,
                        variable=self._notif_var,
                        command=self._on_notifications,
                        style="Switch.TCheckbutton").pack(anchor="w", pady=2)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=(8, 4))

        # --- Quit button (native) ---
        ttk.Button(frame, text=QUIT, command=self._quit,
                   width=8).pack(anchor="w", pady=(4, 0))

        # --- Position above the tray icon ---
        win.update_idletasks()
        w = win.winfo_reqwidth()
        h = win.winfo_reqheight()
        cx, cy = self._click_x, self._click_y
        x = cx - w // 2
        y = cy - h - 10
        screen_w = win.winfo_screenwidth()
        if x + w > screen_w:
            x = screen_w - w - 4
        if x < 0:
            x = 4
        if y < 0:
            y = cy + 10
        win.geometry(f"{w}x{h}+{x}+{y}")

        # Close on focus loss
        win.bind("<FocusOut>", self._on_focus_out)
        win.after(100, lambda: win.focus_force())

    def _on_focus_out(self, event):
        if self._win:
            self._win.after(200, self._check_focus)

    def _check_focus(self):
        if not self._win:
            return
        try:
            focused = self.root.focus_get()
            if focused and str(focused).startswith(str(self._win)):
                return
        except Exception:
            pass
        self.close()

    def _info_row(self, parent, icon: str, label: str, value: str):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=2)
        ttk.Label(row, text=icon, font=("Segoe UI", 10)).pack(
            side="left", padx=(0, 6))
        ttk.Label(row, text=label, font=("Segoe UI", 9),
                  foreground=FG_SECONDARY).pack(side="left")
        ttk.Label(row, text=value, font=("Segoe UI", 9, "bold")).pack(
            side="right")

    def _on_autostart(self):
        _set_autostart(self._autostart_var.get())

    def _on_notifications(self):
        self.manager.notifications_enabled = self._notif_var.get()

    def close(self):
        if self._win:
            self._win.destroy()
            self._win = None

    def _quit(self):
        self.close()
        os._exit(0)


# ---------------------------------------------------------------------------
# Native Win32 Tray Icon
# ---------------------------------------------------------------------------

class Win32TrayIcon:
    """Manages a native tray icon using Shell_NotifyIconW."""

    def __init__(self, on_click: callable, on_quit: callable):
        self._on_click = on_click
        self._on_quit = on_quit
        self._hwnd = None
        self._nid = None
        self._hicon = None
        self._thread: threading.Thread | None = None

    def start(self, status: PeakStatus, tooltip: str):
        self._thread = threading.Thread(target=self._run, args=(status, tooltip),
                                        daemon=True)
        self._thread.start()

    def update(self, status: PeakStatus, tooltip: str):
        if not self._hwnd or not self._nid:
            return
        new_hicon = _pil_to_hicon(_make_circle_image(status))
        self._nid.hIcon = new_hicon
        self._nid.szTip = tooltip[:127]
        shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self._nid))
        if self._hicon:
            user32.DestroyIcon(self._hicon)
        self._hicon = new_hicon

    def _run(self, status: PeakStatus, tooltip: str):
        # Register window class
        kernel32.GetModuleHandleW.restype = wt.HINSTANCE
        hinst = kernel32.GetModuleHandleW(None)

        wc = WNDCLASS()
        wc.lpfnWndProc = WNDPROC(self._wndproc)
        wc.hInstance = hinst
        wc.lpszClassName = "ClaudePeakHoursTray"
        class_atom = user32.RegisterClassW(ctypes.byref(wc))

        # Create hidden message-only window
        user32.CreateWindowExW.restype = wt.HWND
        user32.CreateWindowExW.argtypes = [
            wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            wt.HWND, wt.HANDLE, wt.HINSTANCE, ctypes.c_void_p,
        ]
        self._hwnd = user32.CreateWindowExW(
            0, "ClaudePeakHoursTray", "Claude Peak Hours", 0,
            0, 0, 0, 0, None, None, hinst, None
        )

        # Create tray icon
        self._hicon = _pil_to_hicon(_make_circle_image(status))

        nid = NOTIFYICONDATA()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
        nid.hWnd = self._hwnd
        nid.uID = 1
        nid.uFlags = NIF_ICON | NIF_MESSAGE | NIF_TIP
        nid.uCallbackMessage = WM_TRAYICON
        nid.hIcon = self._hicon
        nid.szTip = tooltip[:127]
        self._nid = nid

        shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))

        # Message loop
        msg = wt.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def _wndproc(self, hwnd, msg, wparam, lparam):
        if msg == WM_TRAYICON:
            if lparam == WM_LBUTTONUP:
                self._on_click()
                return 0
            elif lparam == WM_RBUTTONUP:
                self._on_click()
                return 0
        elif msg == WM_DESTROY:
            if self._nid:
                shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._nid))
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def stop(self):
        if self._hwnd:
            user32.PostMessageW(self._hwnd, WM_DESTROY, 0, 0)


# ---------------------------------------------------------------------------
# Main TrayApp
# ---------------------------------------------------------------------------

class TrayApp:
    def __init__(self):
        self.manager = PeakHoursManager()

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Claude Peak Hours")

        # Fix DPI scaling for tkinter — get actual monitor DPI
        try:
            dpi = ctypes.windll.user32.GetDpiForSystem()
            scale = dpi / 96.0
            self.root.tk.call('tk', 'scaling', scale * 1.333)  # tk uses 72dpi base
        except Exception:
            pass

        self.popup = PopupWindow(self.root, self.manager)
        self._pending_toggle = False

        self.tray = Win32TrayIcon(
            on_click=self._on_tray_click,
            on_quit=self._on_quit,
        )

        self.manager.set_on_change(self._on_state_change)
        self.manager.set_on_notify(self._send_notification)

    def run(self):
        state = self.manager.state
        tooltip = f"{state.status_bar_text} - {state.countdown_text}"

        self.tray.start(state.status, tooltip)
        self.manager.start()

        # Poll for tray click events (thread-safe bridge)
        self._poll()
        self.root.mainloop()

    def _poll(self):
        if self._pending_toggle:
            self._pending_toggle = False
            self.popup.toggle(
                getattr(self, '_click_x', 0),
                getattr(self, '_click_y', 0),
            )
        self.root.after(50, self._poll)

    def _on_tray_click(self):
        # Capture cursor position NOW (while over the tray icon)
        pt = wt.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        self._click_x = pt.x
        self._click_y = pt.y
        self._pending_toggle = True

    def _on_state_change(self, state: PeakState):
        tooltip = f"{state.status_bar_text} - {state.countdown_text}"

        # Flash the icon on peak/off-peak transition
        if (hasattr(self, '_last_status') and
                self._last_status != state.status and
                state.status != PeakStatus.WARNING):
            self._flash_icon(state.status)
        else:
            self.tray.update(state.status, tooltip)
        self._last_status = state.status

    def _flash_icon(self, new_status: PeakStatus, count: int = 6):
        """Blink tray icon between blank and new color."""
        if count <= 0:
            tooltip = f"{self.manager.state.status_bar_text} - {self.manager.state.countdown_text}"
            self.tray.update(new_status, tooltip)
            return

        if count % 2 == 0:
            # Show blank (transparent) icon
            blank = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
            draw = ImageDraw.Draw(blank)
            draw.ellipse([2, 2, 30, 30], fill=(128, 128, 128, 80))
            hicon = _pil_to_hicon(blank)
            if self.tray._nid:
                self.tray._nid.hIcon = hicon
                shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self.tray._nid))
        else:
            self.tray.update(new_status, "")

        self.root.after(300, lambda: self._flash_icon(new_status, count - 1))

    def _send_notification(self, title: str, body: str):
        try:
            from winotify import Notification
            toast = Notification(
                app_id="Claude Peak Hours",
                title=title,
                msg=body,
                duration="short",
            )
            toast.show()
        except Exception:
            pass

    def _on_quit(self):
        self.manager.stop()
        self.tray.stop()
        self.root.after(0, self.root.destroy)
