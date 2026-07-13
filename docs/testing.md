# System testów IP Box Wizard AI

## Architektura

Dwie niezależne warstwy testów:

| Warstwa | Katalog | Cel | Uruchamia się |
|---|---|---|---|
| **Unit (Python)** | `tests/unit/` | Deterministyczna weryfikacja matematyki (`ipbox_calculator.py`) | Zawsze — bez klucza API |
| **LLM (scenariuszowe)** | `tests/llm/` | Weryfikacja end-to-end `ipbox_algorytm.md` przez OpenRouter / Gemini | Tylko z `--run-llm` + `LLM_API_KEY` |

## Szybki start

### 1. Instalacja

```bash
pip install -r requirements.txt
pip install -r requirements-test.txt
```

### 2. Konfiguracja `.env`

```env
# Preferred: OpenRouter
LLM_PROVIDER=openrouter
LLM_MODEL=google/gemini-3.5-flash
OPENROUTER_API_KEY=twoj_klucz_api

# Legacy alias (optional)
# GEMINI_MODEL=google/gemini-3.5-flash
# GEMINI_API_KEY=
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
├── config.py        # Konfiguracja trybów (VCR_CASSETTES_ROOT)
├── fingerprint.py  # Obliczanie hash kaset
├── cassette.py     # Model kasety + manifest (format v3)
├── recorder.py     # Logika nagrywania/odtwarzania
├── request_spec.py # LLMRequestSpec — kompletna specyfikacja żądania
└── cassettes/      # Nagrane kasety, per-model (commitowane do repo)
    ├── _manifest.yaml
    ├── openrouter/
    │   └── google_gemini_3_5_flash/
    │       ├── 01_basic_linear.yaml
    │       └── ...
    └── google/
        ├── google_gemini_3_5_flash/
        │   └── ...
        └── google_gemma_4_31b_it/
            └── ...
```

Kasety są teraz przechowywane per-model w `cassettes/{provider}/{model_slug}/`, gdzie `model_slug` to nazwa modelu z `/` → `_` i bezpieczna dla systemu plików. Domyślny katalog kaset to `tests/llm/vcr/cassettes/`, ale można go zmienić przez zmienną środowiskową `VCR_CASSETTES_ROOT`.

### Cassette format version 3

Kasety używają formatu w wersji **3** (zamiast 2). Kluczowe zmiany:

- `cassette_format_version: 3` w meta
- Każdy turn zawiera `request_hash` — SHA-256 całej specyfikacji żądania (provider, model, prompt, system_prompt, temperature, max_tokens itd.)
- `request_hash = SHA-256(JSON(LLMRequestSpec))` — pozwala wykryć zmiany w dowolnym parametrze wywołania LLM
- Dodatkowe pola: `system_prompt_hash` w turn, `algorithm_hash` w meta

### Tryby pracy

| Tryb | Env | Opis |
|------|-----|------|
| `playback` | `VCR_MODE=playback` | Użyj wyłącznie kaset. Fail jeśli brak. Zero API calls. |
| `auto` | `VCR_MODE=auto` (domyślny) | Użyj kasety jeśli aktualna, inaczej nagraj |
| `record` | `VCR_MODE=record` | Zawsze nagraj (nadpisz istniejące) |
| `none` | `VCR_MODE=none` | Wyłącz VCR — zawsze wywołuj API |

### Fingerprint

Kaseta jest unieważniona gdy zmieni się:

- Zawartość `ipbox_algorytm.md` (hash SHA-256)
- Plik scenariusza YAML (hash SHA-256)
- Provider LLM
- Model LLM
- System prompt (hash SHA-256)

Fingerprint = `hash(algorithm + scenario + provider + model + system_prompt)` z prefiksem wersji.

Format: `v{PROMPT_TEMPLATE_VERSION}_{algo_hash}_{scenario_hash}_{provider}_{model_hash}_sp{sp_hash}`

`PROMPT_TEMPLATE_VERSION` (obecnie `"2"`) jest inkrementowany gdy zmienia się format prompta wysyłanego do LLM, co unieważnia wszystkie istniejące kasety.

### request_hash — pełna specyfikacja żądania

Od formatu v3 każdy `CassetteTurn` zawiera `request_hash` obliczany jako SHA-256 z kanonicznego JSON-a całej struktury `LLMRequestSpec`:

```
LLMRequestSpec {
    provider: str           # np. "openrouter"
    model: str              # np. "google/gemini-3.5-flash"
    system_prompt: str      # pełny prompt systemowy
    user_prompt: str        # prompt użytkownika
    temperature: float      # 0.0
    max_tokens: int         # 16000
    response_format: dict   # opcjonalny
    schema: dict            # opcjonalny
    schema_version: str     # opcjonalny
    provider_preferences: dict  # opcjonalny
    seed: int               # opcjonalny
    reasoning_settings: dict    # opcjonalny
}
```

Dzięki temu zmiana dowolnego parametru (np. temperatury, schematu, providera) unieważnia kasetę — nie tylko zmiana prompta.

### Dodatkowa walidacja w playbacku

- **Prompt hash**: Podczas odtwarzania kasety VCR weryfikuje SHA-256 prompta. Jeśli hash nie zgadza się z zapisanym w kasecie, rzuca `ValueError` — to sygnalizuje zmianę w generacji prompta (np. zmiana algorytmu lub scenariusza).
- **request_hash**: Od formatu v3 `request_hash` obejmuje pełną specyfikację LLM (provider, model, prompt, temperature, max_tokens, schema itd.). Zmiana dowolnego parametru → mismatch → re-record.
- **system_prompt_hash**: Dodatkowa walidacja SHA-256 prompta systemowego (oddzielnie od prompt_hash użytkownika).
- **Fail-closed**: W trybie `playback` VCR nie ma fallbacku do live API. Jeśli kasety brakuje lub jest nieaktualna, test kończy się błędem z komunikatem o konieczności przejścia w tryb `record`.

### Użycie lokalne

```bash
# Nagraj pierwsze kasety (wymaga LLM_API_KEY / OPENROUTER_API_KEY)
VCR_MODE=record pytest tests/llm/ --run-llm -v

# Kolejne uruchomienia (użyj kaset, brak kosztów)
pytest tests/llm/ --run-llm -v

# Użyj alternatywnego katalogu kaset
VCR_CASSETTES_ROOT=/path/to/cassettes pytest tests/llm/ --run-llm -v

# Sprawdź czy kasety są świeże
make vcr-check
# lub: python scripts/vcr_precommit.py

# Smoke test (zero API calls)
make vcr-smoke
# lub: ./scripts/vcr_smoke.sh
```

### CI/CD

W GitHub Actions domyślnie używany jest tryb `playback` (zero kosztów API). Gdy kasety są nieaktualne, workflow tworzy PR z nowymi kasetami.

### Playback bez klucza API

W trybie `playback` klucz API nie jest wymagany. `LLMClient` akceptuje `require_api_key=False`, a fixture `llm_client` w `test_scenarios.py` automatycznie przekazuje tę flagę gdy `VCR_MODE=playback`. Nie potrzebujesz ani `OPENROUTER_API_KEY` ani `GEMINI_API_KEY` — kasety są odtwarzane lokalnie.

### Rozwiązywanie problemów

| Problem | Rozwiązanie |
|---------|------------|
| `CassetteNotFoundError` w trybie playback | Uruchom z `VCR_MODE=record` aby nagrać nowe kasety |
| Kasety nieaktualne | `make vcr-check` sprawdzi świeżość, `VCR_MODE=record` odświeży |
| `ValueError: Prompt hash mismatch` | Zmienił się prompt (algorytm/scenariusz). Przejdź w tryb `record` aby nagrać nowe kasety |
| `ValueError: Request hash mismatch` | Zmieniła się specyfikacja żądania LLM (provider, model, temperatura itd.). Przejdź w tryb `record` |
| `request_hash not found` (format < v3) | Kaseta w starym formacie. Przejdź w tryb `record` aby nagrać z `cassette_format_version=3` |
| Chcesz live API | Uruchom z `VCR_MODE=none` |

## VSCode

Po otwarciu projektu w VSCode panel **Testing** (ikona probówki) pokaże zarówno testy `unit/` jak i `llm/`. Testy LLM mają status "skip" dopóki nie ustawisz `OPENROUTER_API_KEY` (lub `GEMINI_API_KEY`) w `.env` i nie uruchomisz ich ręcznie przez terminal z flagą `--run-llm`.

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
| **Secret** | `OPENROUTER_API_KEY` | Klucz API OpenRouter (lub `GEMINI_API_KEY` jako alias) |
| **Variable** | `LLM_MODEL` | np. `google/gemini-3.5-flash` |
| **Variable** | `GEMINI_MODEL` | (alias) np. `google/gemini-3.5-flash` |

### Przepływ

- `full-suite.yml` — orchestrator (lint → unit → llm → summary), uruchamiany na `main` i co poniedziałek
  - `lint` — Ruff (`ruff check .`) — walidacja składni i stylu Pythona
  - `unit` — testy jednostkowe (wywołuje `unit-tests.yml`)
  - `llm` — testy scenariuszowe (wywołuje `llm-scenario-tests.yml`)
- `unit-tests.yml` — uruchamiany przy zmianach w `python_helper/` lub `tests/unit/`
- `llm-scenario-tests.yml` — uruchamiany przy zmianach w `ipbox_algorytm.md` lub `tests/llm/`
  - PR: tryb `playback` (zero kosztów API)
  - push/dispatch: tryb `auto` (używa kaset lub nagrywa)

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

#### HARD — blokujące (fail-closed)

Wszystkie HARD assertions są fail-closed: wartość musi być jawnie obecna i poprawna. Brak sekcji w odpowiedzi LLM lub brak wartości to błąd.

| Klucz | Opis |
|---|---|
| `nexus` | Dokładność ±0.001. `None` → failure. |
| `nexus_range` | Zakres `[min, max]` z tolerancją ±0.001. |
| `testy_pass` | Lista `TEST_1..TEST_9` które muszą być jawnie PASS. Brak testu w bloku `<tests>` → failure. |
| `testy_fail` | Lista testów które muszą być jawnie FAIL. PASS → failure, brak → failure. |
| `zus_dubel` | `false` = TEST_3 musi być PASS (brak podwójnego odliczenia ZUS). |
| `roznice_kursowe_w_IP` | `false` = różnice kursowe nie mogą trafić do koszyka IP. |
| `expected_stops` | Lista kodów STOP (z `meta`) które muszą wystąpić w `<stops_reviews>`. |
| `assertions.stops` | Lista kodów STOP (z `assertions.stops`) które muszą wystąpić. |
| `expected_reviews` | Lista kodów REVIEW (z `meta`) które muszą wystąpić. |
| `review_obecne` | Lista kodów REVIEW które muszą być obecne (alternatywna nazwa). |
| `klucz_MIX_metoda` | Oczekiwana metoda klucza MIX (np. `przychodowa_roczna`, `czasowa_W`). |
| `klucz_MIX_źródło` | Źródło klucza MIX (np. `interpretacja_KIS`, `polityka_wizard`). |
| `nie_używaj_W_do_MIX` | `true` = W nie może być użyty do alokacji MIX. |
| `alokacja_multi_ip` | Mapa wartości alokacji dwustopniowej (dla wielu projektów IP), tolerancja ±0.5. |
| `koszty_koszyk` | Mapa koszt→koszyk (IP / MIX / NIE / WYKLUCZONE). |
| `warnings` | Kody ostrzeżeń które muszą być wygenerowane. **HARD** (blokujące). |

#### RANGE — zakresy

| Klucz | Opis |
|---|---|
| `podatek_IP_range` | `[min, max]` — podatek IP. `None` → failure. |
| `podatek_NIE_range` | `[min, max]` — podatek NIE. `None` → failure. |
| `przychod_IP_roczny_range` | `[min, max]` — roczny przychód IP. `None` → failure. |
| `przychod_NIE_roczny_range` | `[min, max]` — roczny przychód NIE. `None` → failure. |
| `W_miesieczne` | Mapa miesiąc→W%, tolerancja ±2pp. Brak miesiąca → failure. |

#### SOFT — nieblokujące

| Klucz | Opis |
|---|---|
| `soft_warnings` | Kody ostrzeżeń do sprawdzenia (nieblokujące, tylko print). |

### Per-section validation

Evaluator automatycznie sprawdza, czy odpowiedź LLM zawiera wymagane sekcje (tagi XML) na podstawie użytych asercji:

| Gdy asercja zawiera... | Wymagana sekcja |
|---|---|
| `nexus`, `nexus_range`, `podatek_IP_range`, `podatek_NIE_range`, `przychod_IP_roczny_range`, `przychod_NIE_roczny_range`, `alokacja_multi_ip`, `klucz_MIX_metoda`, `klucz_MIX_źródło` | `<result>` |
| `W_miesieczne` | `<monthly_W>` |
| `testy_pass`, `testy_fail` | `<tests>` |
| `stops`, `review_obecne`, `warnings`, `soft_warnings` lub `meta.expected_stops`/`meta.expected_reviews` | `<stops_reviews>` |
| `koszty_koszyk`, `nie_używaj_W_do_MIX`, `roznice_kursowe_w_IP` | `<classifications>` |

Brak wymaganej sekcji → failure.

### Normalizacja ID testów

Evaluator normalizuje ID testów przez regex: `TEST[\s_-]*(\d+)` → `TEST_N`.

- `TEST 1` → `TEST_1`
- `test_1_bilans` → `TEST_1`
- `TEST-3` → `TEST_3`

Dzięki temu asercje `testy_pass: ["TEST_1"]` dopasują się niezależnie od formatu użytego przez LLM.

### Koncepty alokacji MIX

Przy kluczu `przychodowa_roczna` koszty MIX są **deferred** — odkładane do rozliczenia rocznego (Faza 7.2.A):

- Koszty z `klucz: null` (lub brak klucza per-item) trafiają do puli `MIX_deferred` w danym miesiącu
- Miesięczne dochody przed alokacją MIX mają status **PROVISIONAL**
- Po Fazie 7.2.A (roczne rozliczenie MIX) dochody stają się **FINAL**
- W wynikach YAML: `mix_deferred: 0.00` (kwota odroczona) i `result_status: "PROVISIONAL"` / `"FINAL"`
