# Claude Peak Hours — Windows

Wiedz, kiedy korzystać z Claude'a na full, a kiedy oszczędzać tokeny.

W godzinach peak (dni robocze 5:00–11:00 PT / 14:00–20:00 CET) Anthropic stosuje ostrzejsze limity sesji. Ta appka daje Ci wyraźny wskaźnik w system tray, żebyś nigdy nie został zaskoczony throttlingiem.

## Aplikacja System Tray

Zawsze widoczny wskaźnik obok zegarka — zielona/czerwona/żółta kropka.

### Funkcje

- **Ikona w tray** — 🟢 Pełna moc / 🔴 Ograniczenia / 🟡 Ostrzeżenie (15 min przed zmianą)
- **Popup ze szczegółami** — kliknij ikonę, żeby zobaczyć odliczanie, godziny w Twojej strefie czasowej
- **Powiadomienia Windows** — toast notification na start/koniec peak
- **Animacja** — pulsowanie ikony przy zmianie statusu
- **Autostart** — opcjonalne uruchamianie przy starcie Windows
- **Lokalizacja** — polski i angielski, automatycznie z języka systemu
- **Lekka** — zero API calls, czysta logika zegarowa, odświeżanie co 30s
- **Styl Windows 11** — popup z motywem Sun Valley (Fluent Design)

### Instalacja

**Pobierz gotowy `.exe`:**

1. Wejdź w [Releases](https://github.com/Vallhalen/claude-peak-hours-windows/releases)
2. Pobierz `Claude.Peak.Hours.exe`
3. Uruchom — ikona pojawi się w system tray

**Zbuduj ze źródeł:**

```bash
git clone https://github.com/Vallhalen/claude-peak-hours-windows.git
cd claude-peak-hours-windows
pip install -r requirements.txt
python src/main.pyw
```

**Zbuduj `.exe`:**

```bash
pip install -r requirements.txt
python -m PyInstaller --onefile --windowed --name "Claude Peak Hours" --icon assets/icon.ico --paths src src/main.pyw
# Wynik: dist/Claude Peak Hours.exe
```

### Wymagania (ze źródeł)

- Python 3.11+
- `pip install -r requirements.txt`

## Harmonogram Peak Hours

Na podstawie [ogłoszenia Anthropic](https://support.anthropic.com/en/articles/9646069-usage-limits-for-claude-ai):

| | Peak | Off-Peak |
|---|---|---|
| **Kiedy** | Dni robocze 5:00–11:00 PT | Wieczory, noce, weekendy |
| **CET** | 14:00–20:00 | Reszta czasu |
| **Efekt** | Szybsze zużywanie limitów | Normalne limity |

## Jak to działa

Zero zapytań do API, zero ruchu sieciowego. Appka sprawdza aktualny czas względem znanego harmonogramu peak hours (dni robocze 5–11 rano czasu pacyficznego) i przelicza na Twoją strefę czasową.

## Widget Windows 11

> **Status: nie działa** — Microsoft przebudował Widget Board w Windows 11 25H2 (build 26100+) na architekturę opartą o Copilot. Sideloadowane widgety MSIX nie są już wykrywane przez nowy panel. Natywny widget provider (C# + Windows App SDK) jest w katalogu `widget-native/`, ale wymaga publikacji w Microsoft Store żeby pojawić się w panelu widgetów.

Jako alternatywa, aplikacja jest dostępna również jako PWA — otwórz [stronę](https://vallhalen.github.io/claude-peak-hours-windows/) w Edge i zainstaluj jako aplikację.

## Struktura projektu

```
├── src/                    # Aplikacja tray (Python)
│   ├── main.pyw            # Entry point
│   ├── tray_app.py         # System tray + popup (Win32 + tkinter + sv-ttk)
│   ├── peak_hours_manager.py  # Logika peak/off-peak
│   └── strings.py          # Lokalizacja PL/EN
├── widget-native/          # Natywny widget Win11 (C# — nie działa na 25H2+)
├── index.html              # PWA strona
├── sw.js                   # Service Worker
├── peak-hours.js           # Logika JS (shared)
└── manifest.json           # PWA manifest
```

## Licencja

MIT
