"""Localization strings — Polish and English, auto-detected from system locale."""

import locale


def _is_polish() -> bool:
    try:
        lang = locale.getdefaultlocale()[0] or ""
    except Exception:
        lang = ""
    return lang.startswith("pl")


_PL = _is_polish()


# Status bar / tray tooltip
FULL_POWER = "Pełna moc" if _PL else "Full power"
RESTRICTED = "Zwiększone zużycie" if _PL else "Higher usage"

# Popup header
FULL_POWER_HEADER = "PEŁNA MOC" if _PL else "FULL POWER"
RESTRICTED_HEADER = "ZWIĘKSZONE ZUŻYCIE" if _PL else "HIGHER USAGE"

# Popup description
FULL_POWER_DESC = (
    "Claude działa na full — korzystaj!" if _PL
    else "Claude running at full capacity — go ahead!"
)
RESTRICTED_DESC = (
    "Twoje limity zużywają się szybciej niż zwykle" if _PL
    else "Your limits are being consumed faster than usual"
)

# Countdown labels
RESTRICTIONS_IN = "Zwiększone zużycie za" if _PL else "Higher usage in"
FULL_POWER_IN = "Pełna moc za" if _PL else "Full power in"

# Info rows
RESTRICTION_HOURS = "Peak hours" if _PL else "Peak hours"
WORKDAYS = "Dni robocze" if _PL else "Workdays"
WORKDAYS_VALUE = "Pon–Pt" if _PL else "Mon–Fri"

# Settings / menu
LAUNCH_AT_LOGIN = "Uruchom przy starcie" if _PL else "Launch at login"
NOTIFICATIONS = "Powiadomienia" if _PL else "Notifications"
QUIT = "Zamknij" if _PL else "Quit"

# Notifications
NOTIF_RESTRICTED_TITLE = "Zwiększone zużycie" if _PL else "Higher usage"
NOTIF_RESTRICTED_BODY = (
    "Twoje limity zużywają się szybciej — oszczędzaj tokeny." if _PL
    else "Your limits are consumed faster — conserve tokens."
)
NOTIF_FULL_POWER_TITLE = "Pełna moc" if _PL else "Full power"
NOTIF_FULL_POWER_BODY = (
    "Normalne zużycie limitów — Claude działa na full." if _PL
    else "Normal limit usage — Claude at full capacity."
)


def notif_full_power_soon(minutes: int) -> tuple[str, str]:
    if _PL:
        return (f"Pełna moc za {minutes} min", "Niedługo normalne zużycie limitów.")
    return (f"Full power in {minutes} min", "Normal usage returning soon.")


def notif_restricted_soon(minutes: int) -> tuple[str, str]:
    if _PL:
        return (f"Zwiększone zużycie za {minutes} min", "Niedługo limity będą się szybciej zużywać.")
    return (f"Higher usage in {minutes} min", "Limits will be consumed faster soon.")
