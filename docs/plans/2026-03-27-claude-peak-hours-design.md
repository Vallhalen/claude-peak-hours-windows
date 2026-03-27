# Claude Peak Hours — Design Doc

## Problem
Anthropic dynamicznie ogranicza limity sesji Claude w godzinach peak (dni robocze 5:00-11:00 PT / 14:00-20:00 CET). Brak widocznego wskaźnika sprawia, że użytkownik nie wie kiedy oszczędzać tokeny.

## Rozwiązanie
Dwa narzędzia do wyboru:
1. **Aplikacja macOS menu bar** — natywna Swift + SwiftUI, zawsze widoczna obok zegarka
2. **Status line dla Claude Code** — modułowy plugin bash/PowerShell, cross-platform

---

## 1. Aplikacja macOS Menu Bar

### Technologia
- **Swift + SwiftUI** (popover)
- **NSStatusItem** (ikona w menu barze)
- **macOS 13+ (Ventura)** — wymagane dla SwiftUI popover
- **LSUIElement = true** — brak ikony w Dock, tylko menu bar
- **Code signing** — wymagany dla powiadomień (UNUserNotificationCenter)
- **Zero zależności zewnętrznych**

### Struktura plików
```
ClaudePeakHours/
├── main.swift                      # Entry point, NSApplication
├── AppDelegate.swift               # NSStatusItem, popover, event monitor
├── PeakHoursManager.swift          # Logika peak/off-peak + timer + powiadomienia
├── PopoverView.swift               # SwiftUI widok popoveru
├── Strings.swift                   # Lokalizacja PL/EN (auto-detekcja)
├── ClaudePeakHours.entitlements    # Entitlements dla code signing
└── Info.plist                      # LSUIElement = true
```

### Menu Bar
- `🟢 Pełna moc` / `🟢 Full power` — off-peak
- `🔴 Ograniczenia` / `🔴 Restricted` — peak hours
- `🟡 ⏱ Xmin` — ostrzeżenie 15 min przed zmianą

### Popover (po kliknięciu)
- Status — duży, wyraźny (ciemny szmaragdowy / czerwony / pomarańczowy)
- Opis — krótki tekst kontekstowy
- Odliczanie — ile czasu do zmiany statusu
- Godziny ograniczeń — przeliczone na lokalną strefę
- Toggle: Uruchom przy starcie (SMAppService)
- Toggle: Powiadomienia (UNUserNotificationCenter)
- Przycisk Zamknij

### Lokalizacja
- Automatyczna detekcja języka systemu (`Locale.preferredLanguages`)
- Wszystkie stringi w `Strings.swift` (enum `L`)
- Obsługiwane: polski, angielski

### Budowanie
- `build.sh` — kompilacja `swiftc` + budowa .app bundle + code signing
- Bez Xcode project — czysty swiftc z flagami
- Output: `build/Claude Peak Hours.app` (~43 KB zip)

### Dystrybucja
- GitHub Releases z gotowym .app w zipie
- One-liner installer: `curl ... install.sh | bash`
- Odinstalowanie: `rm -rf "/Applications/Claude Peak Hours.app"`

---

## 2. Status Line dla Claude Code

### Architektura
Modułowy plugin — nie nadpisuje istniejącego statusline, tylko dopisuje segment między markerami.

### Pliki
```
peak-hours-status.sh    # Standalone helper — outputuje TYLKO segment peak hours
peak-hours-status.ps1   # Wersja PowerShell dla Windows
statusline-install.sh   # Instalator bash (macOS/Linux)
statusline-install.ps1  # Instalator PowerShell (Windows)
statusline-uninstall.sh # Uninstalator bash
statusline-uninstall.ps1 # Uninstalator PowerShell
```

### Jak działa instalacja
1. Pobiera `peak-hours-status.sh` do `~/.claude/`
2. Dopisuje na koniec istniejącego `~/.claude/statusline.sh`:
   ```bash
   # >>> claude-peak-hours
   printf " │ "; ~/.claude/peak-hours-status.sh
   # <<< claude-peak-hours
   ```
3. Konfiguruje `settings.json` jeśli brak statusLine

### Jak działa odinstalowanie
1. Usuwa `~/.claude/peak-hours-status.sh`
2. Usuwa TYLKO linie między markerami z statusline.sh
3. Reszta statusline nietknięta

### Wymagania
- **macOS / Linux**: `jq`, bash
- **Windows**: PowerShell 5.1+ (wbudowany)

---

## Logika Peak Hours (wspólna)

```
Peak = poniedziałek–piątek, 5:00–11:00 America/Los_Angeles
Off-peak = weekendy + wszystko poza 5:00–11:00 PT
```
- Obliczenia zawsze w strefie America/Los_Angeles
- Wyświetlanie w lokalnej strefie systemowej (auto-detekcja)
- Odliczanie uwzględnia weekendy (piątek po peak → poniedziałek rano)
- Zero zapytań API, zero ruchu sieciowego

## Weryfikacja
1. `./build.sh` — projekt się buduje
2. Uruchomić — ikona widoczna w menu bar z poprawnym statusem
3. Kliknąć — popover otwiera się z odliczaniem i szczegółami
4. Sprawdzić toggle autostart (System Settings > Login Items)
5. Sprawdzić powiadomienia (Notification Center)
6. Status line: `echo '{}' | bash ~/.claude/statusline.sh` — wyświetla segment peak hours
7. Instalator/uninstalator: cykl install → uninstall nie niszczy istniejącego statusline
