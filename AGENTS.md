# AGENTS.md — Przewodnik dla agentów AI

## Cel projektu

`ipbox-wizard-ai` to system wspomagający rozliczenie ulgi **IP Box** (art. 30ca PIT) dla programistów B2B w Polsce. Składa się z:

1. **`ipbox_algorytm.md`** — główna instrukcja dla agentów AI (system prompt), prowadzi przez 10 faz rozliczenia
2. **`python_helper/ipbox_calculator.py`** — moduł Pythona z funkcjami matematycznymi (W, NEXUS, kaskada podatkowa, FX)
3. **`tests/`** — testy jednostkowe Pythona i testy LLM weryfikujące działanie algorytmu

## Kluczowe pliki

| Plik | Rola |
|---|---|
| `ipbox_algorytm.md` | Algorytm — system prompt dla AI |
| `python_helper/ipbox_calculator.py` | Kalkulator — funkcje matematyczne |
| `tests/unit/` | Testy deterministyczne kalkulatora |
| `tests/llm/scenarios/` | Scenariusze end-to-end dla LLM |
| `tests/llm/evaluator.py` | Walidator wyników LLM |
| `docs/testing.md` | Dokumentacja systemu testów |
| `.env.example` | Wymagane zmienne środowiskowe |

## Jak uruchamiać testy

```bash
# Testy jednostkowe (nie wymagają klucza API)
pytest tests/unit/ -v

# Testy LLM z VCR (domyślnie auto - użyj kaset jeśli aktualne)
pytest tests/llm/ --run-llm -v

# Testy LLM w trybie playback (użyj wyłącznie kaset, brak API calls)
pytest tests/llm/ --run-llm -v --vcr-mode=playback

# Testy LLM w trybie record (nagraj na nowo wszystkie kasety)
pytest tests/llm/ --run-llm -v --vcr-mode=record

# Makefile shortcuts (alternatywnie)
make test-llm-playback  # Playback (brak kosztów API)
make test-llm-record # Nagraj wszystkie kasety
make vcr-smoke    # Smoke test z VCR
make vcr-check   # Sprawdź świeżość kaset
```

### VCR (Virtual Cassette Recorder)

System VCR pozwala na redukcję kosztów API o >95% poprzez nagrywanie i odtwarzanie odpowiedzi LLM.

| Tryb | Env `VCR_MODE` | Zachowanie |
| ------ | -------------- | ---------- |
| `playback` | `playback` | Użyj wyłącznie kaset. Fail jeśli brak. Zero API calls. |
| `auto` | `auto` (domyślny) | Użyj kasety jeśli aktualna, inaczej nagraj |
| `record` | `record` | Zawsze nagraj (nadpisz istniejące) |
| `none` | `none` | Wyłącz VCR — zawsze wywołuj API |

Kasety są przechowywane w `tests/llm/vcr/cassettes/` i commitowane do repo. Fingerprint kasety = hash(ipbox_algorytm.md + scenariusz.yaml + provider + model). Zmiana któregokolwiek komponentu inwaliduje kasetę.

Pełna dokumentacja: [docs/testing.md](docs/testing.md)

## Wytyczne dla agentów modyfikujących kod

### Język

- Kod źródłowy, nazwy plików, nazwy funkcji: **angielski**
- Treść przekazywana do LLM w testach (prompty, dane YAML): **polski**
- Komentarze w kodzie: angielski lub brak

### Modele AI

- Jedyny obsługiwany provider: **Google Gemini**
- Klucz: `GEMINI_API_KEY` (secret)
- Model: `GEMINI_MODEL` (zmienna środowiskowa, domyślnie `gemini-2.0-flash`)
- Nie dodawać zależności do Anthropic, OpenAI, ani innych providerów

### Testy jednostkowe

- Każda funkcja publiczna `ipbox_calculator.py` musi mieć testy
- Każdy test musi mieć markery: `@pytest.mark.unit` + `@pytest.mark.P0/P1/P2`
- Coverage minimum: 90% (`python_helper/`)

### Scenariusze LLM

- Format pliku: `NN_krotka_angielska_nazwa.yaml`
- Zawartość (input, nazwa po polsku): **po polsku**
- Plik bez `input.rok` i `input.forma_opodatkowania` → dodaj `skip: true` do `meta`
- Nie usuwać scenariuszy — zamiast tego dodaj `skip: true` jeśli są niegotowe

### CI/CD

- `GEMINI_MODEL`: zmienna GitHub Actions (`vars.GEMINI_MODEL`), **nie secret**
- `GEMINI_API_KEY`: secret GitHub Actions (`secrets.GEMINI_API_KEY`)
- Limit scenariuszy LLM w CI: `LLM_MAX_CALLS_PER_RUN` (domyślnie 0 — wszystkie)

## Czego NIE robić

- Nie dodawać zależności do `anthropic`, `openai` ani innych LLM providerów
- Nie commitować kluczy API do plików (`.env` jest w `.gitignore`)
- Nie tworzyć pliku `pytest.ini` — konfiguracja jest w `pyproject.toml`
- Nie dodawać `README_TESTING.md` do katalogu głównego — dokumentacja jest w `docs/`
