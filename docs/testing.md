# System testów IP Box Wizard AI

## Architektura

Dwie niezależne warstwy testów:

| Warstwa | Katalog | Cel | Uruchamia się |
|---|---|---|---|
| **Unit (Python)** | `tests/unit/` | Deterministyczna weryfikacja matematyki (`ipbox_calculator.py`) | Zawsze — bez klucza API |
| **LLM (scenariuszowe)** | `tests/llm/` | Weryfikacja end-to-end `ipbox_algorytm.md` przez Gemini | Tylko z `--run-llm` + `GEMINI_API_KEY` |

## Szybki start

### 1. Instalacja

```bash
pip install -r requirements.txt
pip install -r requirements-test.txt
```

### 2. Konfiguracja `.env`

```env
GEMINI_API_KEY=twoj_klucz_api
GEMINI_MODEL=gemini-2.0-flash
```

### 3. Uruchamianie

```bash
# Testy jednostkowe (szybkie, bez API)
make test-unit
# lub: pytest tests/unit/ -v

# Testy LLM z VCR (domyślnie auto - użyj kaset jeśli aktualne)
make test-llm
# lub: pytest tests/llm/ --run-llm -v

# Testy LLM w trybie playback (użyj wyłącznie kaset, brak API calls)
make test-llm-playback

# Testy LLM w trybie record (nagraj na nowo wszystkie kasety)
make test-llm-record

# Tylko smoke testy LLM (priorytet P0)
make test-llm-smoke

# VCR smoke check (bez API calls)
make vcr-smoke

# Sprawdź świeżość kaset VCR
make vcr-check

# Coverage report
make coverage
```

## VCR (Virtual Cassette Recorder)

System VCR nagrywa i odtwarza odpowiedzi LLM, redukując koszty API o >95%.

### Struktura

```
tests/llm/vcr/
├── __init__.py
├── config.py        # Konfiguracja trybów
├── fingerprint.py  # Obliczanie hash kaset
├── cassette.py     # Model kasety + manifest
├── recorder.py     # Logika nagrywania/odtwarzania
└── cassettes/     # Nagrane kasety (commitowane do repo)
    ├── 01_basic_linear_google_gemini-2.0-flash.yaml
    └── _manifest.yaml
```

### Tryby pracy

| Tryb | Env | Opis |
|------|-----|------|
| `playback` | `VCR_MODE=playback` | Użyj wyłącznie kaset. Fail jeśli brak. Zero API calls. |
| `auto` | `VCR_MODE=auto` (domyślny) | Użyj kasety jeśli aktualna, inaczej nagraj |
| `record` | `VCR_MODE=record` | Zawsze nagraj (nadpisz istniejące) |
| `none` | `VCR_MODE=none` | Wyłącz VCR — zawsze wywołuj API |

### Fingerprint

Kaseta jest unieważniona gdy zmieni się:

- Zawartość `ipbox_algorytm.md`
- Plik scenariusza YAML
- Provider LLM
- Model LLM

Fingerprint = `hash(algorithm + scenario + provider + model)`

### Użycie lokalne

```bash
# Nagraj pierwsze kasety (wymaga GEMINI_API_KEY)
VCR_MODE=record pytest tests/llm/ --run-llm -v

# Kolejne uruchomienia (użyj kaset, brak kosztów)
pytest tests/llm/ --run-llm -v

# Sprawdź czy kasety są świeże
make vcr-check
# lub: python scripts/vcr_precommit.py

# Smoke test (zero API calls)
make vcr-smoke
# lub: ./scripts/vcr_smoke.sh
```

### CI/CD

W GitHub Actions domyślnie używany jest tryb `playback` (zero kosztów API). Gdy kasety są nieaktualne, workflow tworzy PR z nowymi kasetami.

### Rozwiązywanie problemów

| Problem | Rozwiązanie |
|---------|------------|
| `CassetteNotFoundError` w trybie playback | Uruchom z `VCR_MODE=record` aby nagrać nowe kasety |
| Kasety nieaktualne | `make vcr-check` sprawdzi świeżość, `VCR_MODE=record` odświeży |
| Chcesz live API | Uruchom z `VCR_MODE=none` |

## VSCode

Po otwarciu projektu w VSCode panel **Testing** (ikona probówki) pokaże zarówno testy `unit/` jak i `llm/`. Testy LLM mają status "skip" dopóki nie ustawisz `GEMINI_API_KEY` w `.env` i nie uruchomisz ich ręcznie przez terminal z flagą `--run-llm`.

## Markery pytest

| Marker | Opis |
|---|---|
| `unit` | Testy Python (deterministyczne) |
| `llm` | Testy LLM (wymagają API) |
| `smoke` | Minimalne testy do szybkiej walidacji |
| `P0` | Krytyczne — muszą przejść |
| `P1` | Ważne |
| `P2` | Dodatkowe edge cases |

## GitHub CI/CD

### Wymagana konfiguracja repozytorium

| Typ | Nazwa | Wartość |
|---|---|---|
| **Secret** | `GEMINI_API_KEY` | Klucz API Gemini |
| **Variable** | `GEMINI_MODEL` | np. `gemini-2.0-flash` |

### Przepływ

- `unit-tests.yml` — uruchamiany przy zmianach w `python_helper/` lub `tests/unit/`
- `llm-scenario-tests.yml` — uruchamiany przy zmianach w `ipbox_algorytm.md` lub `tests/llm/`
- `full-suite.yml` — orchestrator (unit → llm → summary), uruchamiany na `main` i co poniedziałek

Domyślny limit LLM: `LLM_MAX_CALLS_PER_RUN=0` (wszystkie scenariusze).

## Dodawanie scenariuszy LLM

Nowy plik `NN_nazwa.yaml` w `tests/llm/scenarios/`:

```yaml
meta:
  id: "NN_krotka_nazwa"
  name: "Opis po polsku"
  description: "Szczegółowy opis co testuje scenariusz"
  tags: ["core", "edge", ...]
  priority: "P0"  # P0 / P1 / P2
  expected_stops: []   # opcjonalne
  expected_reviews: [] # opcjonalne
  # skip: true         # opcjonalne — pomija test (WIP)

input:
  rok: 2025
  forma_opodatkowania: "liniowy_19%"
  zus:
    sposob: "w_KPiR"
  miesiace: [...]
  ulgi: {}

assertions:
  nexus: 1.0
  W_miesieczne:
    "2025-01": 90.0
  podatek_IP_range: [1000, 5000]
  testy_pass: ["TEST_1", "TEST_3"]
  zus_dubel: false
  roznice_kursowe_w_IP: false
  koszty_koszyk:
    kawa: "NON"
    jetbrains: "IP"
```

### Typy asercji

| Klucz | Typ | Opis |
|---|---|---|
| `nexus` | HARD | Dokładność ±0.001 |
| `testy_pass` | HARD | Lista TEST_1..TEST_6 które muszą być PASS |
| `zus_dubel` | HARD | `false` = brak podwójnego odliczenia ZUS |
| `roznice_kursowe_w_IP` | HARD | `false` = różnice kursowe nie w IP |
| `expected_stops` | HARD | Lista kodów STOP które muszą wystąpić |
| `expected_reviews` | HARD | Lista kodów REVIEW które muszą wystąpić |
| `koszty_koszyk` | HARD | Mapa koszt→koszyk |
| `podatek_IP_range` | RANGE | `[min, max]` — tolerancja |
| `podatek_NIE_range` | RANGE | `[min, max]` — tolerancja |
| `W_miesieczne` | RANGE | Miesięczne W, tolerancja ±2pp |
| `warnings` | SOFT | Kody ostrzeżeń do sprawdzenia |
