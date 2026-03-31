"""Claude Peak Hours — Windows system tray application.

Shows peak/off-peak status for Claude AI usage limits.
Peak hours: weekdays 5:00–11:00 AM PT (14:00–20:00 CET).
"""

import ctypes

# Enable System DPI awareness — sharp rendering without per-monitor complexity.
try:
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

from tray_app import TrayApp


def main() -> None:
    app = TrayApp()
    app.run()


if __name__ == "__main__":
    main()
