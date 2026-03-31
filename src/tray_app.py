"""System tray application — native Win32 tray icon + tkinter popup.

Uses ctypes to talk directly to Shell_NotifyIconW so we get
reliable single-click detection (WM_LBUTTONUP).
Tkinter runs on the main thread; tray icon messages are dispatched
via a hidden win32 window running in a background thread.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import os
import queue
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import ttk

import sv_ttk
from PIL import Image, ImageDraw, ImageTk

from peak_hours_manager import PeakHoursManager, PeakState, PeakStatus
from strings import (
    AUTOSTART_WARN,
    FULL_POWER_DESC,
    FULL_POWER_HEADER,
    LAUNCH_AT_LOGIN,
    NOTIFICATIONS,
    QUIT,
    RESTRICTED_DESC,
    RESTRICTED_HEADER,
    RESTRICTION_HOURS,
    WORKDAYS,
    WORKDAYS_VALUE,
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
user32.DestroyIcon.argtypes = [wt.HICON]
user32.DestroyIcon.restype = wt.BOOL
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

FG_SECONDARY = "#6e6e73"


# ---------------------------------------------------------------------------
# Icon helpers
# ---------------------------------------------------------------------------

def _pil_to_hicon(pil_image: Image.Image) -> int:
    """Convert a PIL Image to a win32 HICON via a unique temp .ico file."""
    fd, tmp = tempfile.mkstemp(suffix=".ico", prefix="_claude_peak_")
    os.close(fd)
    try:
        pil_image.save(tmp, format="ICO", sizes=[(32, 32)])
        hicon = user32.LoadImageW(
            None, tmp, IMAGE_ICON, 32, 32,
            LR_LOADFROMFILE | LR_DEFAULTSIZE
        )
        return hicon
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


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


def _is_unstable_location() -> bool:
    """Check if the exe is running from Downloads, Desktop, or Temp."""
    if not getattr(sys, "frozen", False):
        return False  # running as script — dev mode, skip check
    exe = os.path.normpath(sys.executable).lower()
    unstable = [
        os.path.normpath(os.path.expanduser("~/Downloads")).lower(),
        os.path.normpath(os.path.expanduser("~/Desktop")).lower(),
        os.path.normpath(tempfile.gettempdir()).lower(),
    ]
    return any(exe.startswith(p) for p in unstable)


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
        return f'"{sys.executable}"'
    else:
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
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE
        )
        try:
            if enabled:
                cmd = _get_launch_command()
                winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, _APP_NAME)
                except FileNotFoundError:
                    pass
        finally:
            winreg.CloseKey(key)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Popup Window — Windows 11 style via sv-ttk
# ---------------------------------------------------------------------------

class PopupWindow:

    def __init__(self, root: tk.Tk, manager: PeakHoursManager,
                 on_quit: callable):
        self.root = root
        self.manager = manager
        self._on_quit_callback = on_quit
        self._win: tk.Toplevel | None = None
        self._refs: list = []

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

        if self._win:
            self._win.destroy()

        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg="#fafafa")
        self._win = win

        state = self.manager.state
        accent = HEX_ACCENT[state.status]

        frame = ttk.Frame(win, padding=16)
        frame.pack(fill="both", expand=True)
        self._frame = frame
        self._warn_label = None

        # --- Status dot (PIL anti-aliased) + Header ---
        hdr = ttk.Frame(frame)
        hdr.pack(anchor="w", fill="x")

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
        ttk.Label(hdr, text=header_text,
                  font=("Segoe UI", 13, "bold"),
                  foreground=accent).pack(side="left")

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

        # --- Native toggle switches ---
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
        if self._autostart_var.get() and _is_unstable_location():
            self._show_autostart_warning()
            self._autostart_var.set(False)
            return
        _set_autostart(self._autostart_var.get())

    def _show_autostart_warning(self):
        """Show warning label under the autostart toggle."""
        if self._warn_label:
            return
        self._warn_label = ttk.Label(
            self._frame, text=AUTOSTART_WARN,
            font=("Segoe UI", 8),
            foreground="#c44",
            wraplength=260,
        )
        self._warn_label.pack(anchor="w", pady=(2, 0))

    def _on_notifications(self):
        self.manager.notifications_enabled = self._notif_var.get()

    def close(self):
        if self._win:
            self._win.destroy()
            self._win = None

    def _quit(self):
        self.close()
        self._on_quit_callback()


# ---------------------------------------------------------------------------
# Native Win32 Tray Icon
# ---------------------------------------------------------------------------

class Win32TrayIcon:
    """Manages a native tray icon using Shell_NotifyIconW."""

    def __init__(self, on_click: callable):
        self._on_click = on_click
        self._hwnd = None
        self._nid = None
        self._hicon = None
        self._wndproc_ref = None  # prevent GC of ctypes callback
        self._thread: threading.Thread | None = None

    def start(self, status: PeakStatus, tooltip: str):
        self._thread = threading.Thread(target=self._run, args=(status, tooltip),
                                        daemon=True)
        self._thread.start()

    def update(self, status: PeakStatus, tooltip: str):
        if not self._hwnd or not self._nid:
            return
        new_hicon = _pil_to_hicon(_make_circle_image(status))
        old_hicon = self._hicon
        self._nid.hIcon = new_hicon
        self._nid.szTip = tooltip[:127]
        shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self._nid))
        if old_hicon:
            user32.DestroyIcon(old_hicon)
        self._hicon = new_hicon

    def _run(self, status: PeakStatus, tooltip: str):
        hinst = kernel32.GetModuleHandleW(None)

        # Store reference to prevent GC
        self._wndproc_ref = WNDPROC(self._wndproc)

        wc = WNDCLASS()
        wc.lpfnWndProc = self._wndproc_ref
        wc.hInstance = hinst
        wc.lpszClassName = "ClaudePeakHoursTray"
        user32.RegisterClassW(ctypes.byref(wc))

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

        msg = wt.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def _wndproc(self, hwnd, msg, wparam, lparam):
        if msg == WM_TRAYICON:
            if lparam in (WM_LBUTTONUP, WM_RBUTTONUP):
                self._on_click()
                return 0
        elif msg == WM_DESTROY:
            if self._nid:
                shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._nid))
            if self._hicon:
                user32.DestroyIcon(self._hicon)
                self._hicon = None
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

        # Apply Windows 11 theme once at startup
        sv_ttk.set_theme("light")
        style = ttk.Style()
        style.configure("Switch.TCheckbutton", background="#fafafa")
        style.configure("TFrame", background="#fafafa")
        style.configure("TLabel", background="#fafafa")
        style.configure("TButton", background="#fafafa")

        # Thread-safe click queue (Win32 thread -> tkinter main thread)
        self._click_queue: queue.Queue[tuple[int, int]] = queue.Queue()

        self.popup = PopupWindow(self.root, self.manager,
                                 on_quit=self._shutdown)

        self.tray = Win32TrayIcon(on_click=self._on_tray_click)

        # Route state changes to main thread
        self.manager.set_on_change(
            lambda state: self.root.after(0, self._handle_state_change, state)
        )
        self.manager.set_on_notify(self._send_notification)

        self._last_status: PeakStatus | None = None

    def run(self):
        state = self.manager.state
        tooltip = f"{state.status_bar_text} - {state.countdown_text}"

        self.tray.start(state.status, tooltip)
        self.manager.start()

        self._poll()
        self.root.mainloop()

    def _poll(self):
        try:
            x, y = self._click_queue.get_nowait()
            self.popup.toggle(x, y)
        except queue.Empty:
            pass
        self.root.after(50, self._poll)

    def _on_tray_click(self):
        pt = wt.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        self._click_queue.put((pt.x, pt.y))

    def _handle_state_change(self, state: PeakState):
        """Handle state change on main thread."""
        tooltip = f"{state.status_bar_text} - {state.countdown_text}"

        if (self._last_status is not None and
                self._last_status != state.status and
                state.status != PeakStatus.WARNING):
            self._flash_icon(state.status)
        else:
            self.tray.update(state.status, tooltip)
        self._last_status = state.status

    def _flash_icon(self, new_status: PeakStatus, count: int = 6):
        """Blink tray icon between dim and new color."""
        if count <= 0:
            s = self.manager.state
            tooltip = f"{s.status_bar_text} - {s.countdown_text}"
            self.tray.update(new_status, tooltip)
            return

        if count % 2 == 0:
            blank = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
            draw = ImageDraw.Draw(blank)
            draw.ellipse([2, 2, 30, 30], fill=(128, 128, 128, 80))
            hicon = _pil_to_hicon(blank)
            if self.tray._nid:
                old = self.tray._nid.hIcon
                self.tray._nid.hIcon = hicon
                shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self.tray._nid))
                if old:
                    user32.DestroyIcon(old)
                self.tray._hicon = hicon
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

    def _shutdown(self):
        """Clean shutdown — remove tray icon, stop timers, exit."""
        self.manager.stop()
        self.tray.stop()
        self.root.after(100, self.root.destroy)

    def _on_quit(self):
        self._shutdown()
