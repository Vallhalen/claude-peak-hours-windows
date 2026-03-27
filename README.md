# Claude Peak Hours

Wiedz, kiedy korzystać z Claude'a na full, a kiedy oszczędzać tokeny.

W godzinach peak (dni robocze 5:00–11:00 PT / 14:00–20:00 CET) Anthropic stosuje ostrzejsze limity sesji. Te narzędzia dają Ci wyraźny wskaźnik, żebyś nigdy nie został zaskoczony throttlingiem.

Dwa narzędzia — wybierz to, które pasuje do Twojego flow:

---

## 1. Aplikacja macOS Menu Bar

Zawsze widoczny wskaźnik obok zegarka.

### Funkcje
- **Wskaźnik w menu barze** — 🟢 Pełna moc / 🔴 Ograniczenia / 🟡 Ostrzeżenie
- **Popover ze szczegółami** — kliknij, żeby zobaczyć odliczanie, godziny ograniczeń w Twojej strefie czasowej
- **Powiadomienia** — opcjonalne alerty macOS na start/koniec peak i 15 min przed zmianą
- **Autostart** — opcjonalne uruchamianie przy starcie systemu
- **Lokalizacja** — polski i angielski, automatycznie wykrywany z języka systemu
- **Lekka** — natywny Swift + SwiftUI, zero zależności

### Wymagania
- macOS 13 (Ventura) lub nowszy
- Xcode Command Line Tools (`xcode-select --install`)

### Instalacja

```bash
curl -sL https://raw.githubusercontent.com/studiogo/claude-peak-hours/main/install.sh | bash
```

### Odinstalowanie

```bash
rm -rf "/Applications/Claude Peak Hours.app"
```

### Alternatywne metody instalacji

**Pobierz ręcznie:**
1. Wejdź w [Releases](https://github.com/studiogo/claude-peak-hours/releases)
2. Pobierz `Claude-Peak-Hours-v*.zip`
3. Rozpakuj i przenieś `Claude Peak Hours.app` do `/Applications`

**Zbuduj ze źródeł:**
```bash
git clone https://github.com/studiogo/claude-peak-hours.git
cd claude-peak-hours
./build.sh
cp -r "build/Claude Peak Hours.app" /Applications/
```

---

## 2. Status Line dla Claude Code

Status peak/off-peak z odliczaniem w terminalu Claude Code. Działa na **macOS, Linux i Windows**.

```
... │ 🟢 OK 6h 34m
... │ 🔴 PEAK 2h 15m
```

### Funkcje
- **🟢 OK 6h 34m** — off-peak, odliczanie do następnego peak
- **🔴 PEAK 2h 15m** — godziny ograniczeń, odliczanie do końca

### Wymagania
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- **macOS / Linux**: `jq` (`brew install jq` / `sudo apt install jq`)
- **Windows**: PowerShell 5.1+ (wbudowany)

### Instalacja — macOS / Linux

```bash
curl -sL https://raw.githubusercontent.com/studiogo/claude-peak-hours/main/statusline-install.sh | bash
```

### Instalacja — Windows (PowerShell)

```powershell
irm https://raw.githubusercontent.com/studiogo/claude-peak-hours/main/statusline-install.ps1 | iex
```

Instalator:
1. Pobiera helper peak-hours do `~/.claude/`
2. Dodaje segment peak hours do Twojego istniejącego statusline (nie nadpisuje go)
3. Konfiguruje `settings.json` jeśli trzeba

### Odinstalowanie — macOS / Linux

```bash
curl -sL https://raw.githubusercontent.com/studiogo/claude-peak-hours/main/statusline-uninstall.sh | bash
```

### Odinstalowanie — Windows (PowerShell)

```powershell
irm https://raw.githubusercontent.com/studiogo/claude-peak-hours/main/statusline-uninstall.ps1 | iex
```

Uninstalator usuwa **tylko** segment peak hours — reszta Twojego statusline zostaje nienaruszona.

---

## Harmonogram Peak Hours

Na podstawie [ogłoszenia Anthropic](https://support.anthropic.com/en/articles/9646069-usage-limits-for-claude-ai):

| | Peak | Off-Peak |
|---|---|---|
| **Kiedy** | Dni robocze 5:00–11:00 PT | Wieczory, noce, weekendy |
| **PT** | 5:00–11:00 | Reszta czasu |
| **CET** | 14:00–20:00 | Reszta czasu |
| **Efekt** | Szybsze zużywanie limitów sesji | Normalne limity sesji |

Oba narzędzia automatycznie przeliczają na Twoją strefę czasową.

## Jak to działa

Zero zapytań do API, zero ruchu sieciowego. Oba narzędzia sprawdzają aktualny czas względem znanego harmonogramu peak hours (dni robocze 5–11 rano czasu pacyficznego).

- **Aplikacja menu bar** — odświeża co 30 sekund
- **Status line** — odświeża po każdej odpowiedzi Claude Code

## Licencja

MIT
