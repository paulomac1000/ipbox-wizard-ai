# Onboarding dla agenta — ipbox-wizard-ai

## Co to jest ten projekt?

Narzędzie dla **programistów B2B w Polsce** rozliczających ulgę **IP Box** (art. 30ca PIT). Ulga pozwala opodatkować dochód z kwalifikowanych praw własności intelektualnej (np. autorskie oprogramowanie) stawką 5% zamiast standardowych 19%/12-32%.

Projekt składa się z:
- **Algorytmu w Markdown** (`ipbox_algorytm.md`) — system prompt dla AI, prowadzi użytkownika przez 10 faz rozliczenia
- **Kalkulatora Python** (`python_helper/ipbox_calculator.py`) — czyste funkcje matematyczne bez zależności AI
- **Testów** — weryfikujących zarówno kalkulator (unit) jak i zachowanie AI (LLM scenariusze)

## Pierwsze kroki

```bash
# 1. Zainstaluj zależności
pip install -r requirements.txt
pip install -r requirements-test.txt

# 2. Skonfiguruj klucz Gemini
cp .env.example .env
# Edytuj .env i wpisz OPENROUTER_API_KEY

# 3. Uruchom testy jednostkowe
pytest tests/unit/ -v

# 4. Uruchom testy LLM w trybie playback (offline, zero kosztów)
make test-llm-playback

# 5. Sprawdź świeżość kaset
make vcr-check
```

## Struktura katalogów

```
ipbox-wizard-ai/
├── ipbox_algorytm.md          # Algorytm — GŁÓWNY PLIK
├── python_helper/
│   └── ipbox_calculator.py    # Kalkulator Python
├── tests/
│   ├── conftest.py            # Globalne fixtures + opcja --run-llm
│   ├── unit/                  # Testy deterministyczne kalkulatora
│   └── llm/
│       ├── client.py          # Klient Gemini API
│       ├── runner.py          # Wykonuje scenariusze
│       ├── evaluator.py       # Waliduje wyniki LLM
│       ├── test_scenarios.py  # pytest wrapper
│       └── scenarios/         # Pliki YAML z danymi testowymi
├── docs/
│   └── testing.md             # Dokumentacja testów (VCR, Unit)
├── scripts/
│   ├── vcr_precommit.py       # Check świeżości kaset
│   └── vcr_smoke.sh           # Szybki test offline
├── .github/workflows/         # CI/CD GitHub Actions
├── AGENTS.md                  # Wytyczne dla agentów AI
└── .env.example               # Wymagane zmienne środowiskowe
```

## Kluczowe koncepty algorytmu IP Box

### Współczynnik W
Procent czasu pracy na kwalifikowanym IP w danym miesiącu. Dzielnik = **faktyczny czas pracy** (bez urlopów), nie 160h.

```
W = ((godziny_pracy - godziny_nie_IP) × procent_faktury_IP) / godziny_pracy × 100
```

### Koszyki kosztów
- **IP** — bezpośrednie (nie mnożone przez W)
- **MIX** — pośrednie (mnożone przez W dla IP, przez 1-W dla NIE)
- **NIE** — nie związane z IP Box
- **WYKLUCZONE** — kary, grzywny

### NEXUS
Wskaźnik proporcji własnej działalności B+R. Cap = 1.0.
```
NEXUS = min(1.0, (A×1.3 + B) / (A + B + C + D))
```
gdzie A=własne koszty B+R, B=niezależni podwykonawcy, C=powiązane podmioty, D=nabyte IP.

### Kaskada ulg (kolejność ma znaczenie!)
1. Strata z lat ubiegłych
2. ZUS społeczne (jeśli nie w KPiR)
3. IKZE (use-it-or-lose-it!)
4. Darowizny / rehabilitacja
5. Termomodernizacja (carry-over do następnych lat)

### Różnice kursowe
**ZAWSZE trafiają do koszyka NIE**, nigdy do IP Box.

### Testy weryfikacyjne (Faza 8)
Algorytm uruchamia 6 testów przed wygenerowaniem YAML:
- TEST_1: Bilans KPiR
- TEST_2: Brak kosztów prywatnych w IP
- TEST_3: Anty-dubel ZUS
- TEST_4: Baza ≥ 0 i carry-over ≥ 0
- TEST_5: Zgodność podatku IP
- TEST_6: Zgodność nadpłaty/dopłaty

## Co można modyfikować

### Dodawanie funkcji do kalkulatora
1. Dodaj funkcję do `python_helper/ipbox_calculator.py`
2. Dodaj testy do `tests/unit/test_<nazwa>.py`
3. Każdy test: `@pytest.mark.unit` + `@pytest.mark.P0/P1/P2`

### Dodawanie scenariuszy LLM
1. Stwórz plik `tests/llm/scenarios/NN_angielska_nazwa.yaml`
2. Dane wejściowe po **polsku** (LLM jest dostrojony do polskiego prawa podatkowego)
3. Zawsze dodaj `input.rok` i `input.forma_opodatkowania`

### Modyfikacja algorytmu
Edytuj `ipbox_algorytm.md`. Po zmianach **obowiązkowo** uruchom testy dymne lub pełne nagrywanie:

```bash
make vcr-smoke          # Szybki check offline (P0)
make test-llm-record    # Nagraj nowe kasety (wymaga API KEY)
make vcr-check          # Walidacja fingerprintów
```

## Częste problemy

| Problem | Przyczyna | Rozwiązanie |
|---|---|---|
| `OPENROUTER_API_KEY not set` | Brak pliku `.env` | Skopiuj `.env.example` → `.env` i wpisz klucz |
| Testy LLM pominięte | Brak flagi | Dodaj `--run-llm` do wywołania pytest |
| Coverage < 90% | Nowe funkcje bez testów | Dodaj testy do `tests/unit/` |
| `PytestUnknownMarkWarning` | Nowy marker bez rejestracji | Dodaj do `[tool.pytest.ini_options].markers` w `pyproject.toml` |
