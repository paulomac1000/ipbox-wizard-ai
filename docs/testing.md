# Testowanie i nagrywanie kaset

## 1. Bezpłatna bramka przed API

Uruchom dokładnie:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt

ruff format --check .
ruff check .
python -m compileall -q python_helper tests scripts
pytest tests/unit \
  --cov=python_helper \
  --cov-report=term-missing \
  --cov-fail-under=90
pytest -q
```

Oczekiwany wynik: testy jednostkowe PASS, coverage >=90%, testy LLM oznaczone jako skipped bez `--run-llm`.

## 2. Dlaczego stare kasety muszą być usunięte

Tożsamość requestu obejmuje:

- cały `ipbox_algorytm.md`;
- scenariusz YAML;
- system prompt i user prompt;
- wynik narzędzia deterministycznego dołączony do promptu;
- model, limit tokenów, reasoning/temperature;
- pełny strict JSON Schema.

Zmiana któregokolwiek elementu unieważnia kasetę. Nie przenoś starych response, hashy ani manifestów.

## 3. Modele bramkowe

```text
google/gemini-3.5-flash
openai/gpt-5-mini
anthropic/claude-haiku-4.5
```

GPT-5 Mini jest świadomym wyborem zamiast Nano: zadanie wymaga ścisłego odwzorowania dużego JSON i wielu warunków. Różnica kosztu pełnego runu jest mała wobec czasu potrzebnego na analizę niestabilnych odpowiedzi.

## 4. Konkretna instrukcja dla agenta nagrywającego

### Przygotowanie

```bash
git switch fix/decouple-mix-allocation-from-w
git pull --ff-only
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt
export OPENROUTER_API_KEY='WKLEJ_KLUCZ'
```

Sprawdź saldo OpenRouter przed startem. Nie uruchamiaj trzech modeli równolegle; ogranicza to ryzyko rate-limitów i ułatwia kontrolę kosztu.

### Nagrywanie wszystkich modeli

```bash
./scripts/record_all_models.sh --max-cost-usd 5
```

Skrypt:

1. uruchamia bezpłatne testy;
2. nagrywa każdy scenariusz osobno;
3. pomija kasetę już obecną po rzeczywistym offline playbacku, więc wznowienie nie płaci ponownie;
4. kontynuuje kolejne modele nawet wtedy, gdy jeden model ma chwilowy błąd;
5. zapisuje odrzucone odpowiedzi do `/tmp/ipbox_llm_rejected/`;
6. stosuje miękki limit kosztu przed każdym następnym requestem;
7. wykonuje offline playback i walidację manifestu;
8. generuje `reports/benchmark-summary.json`.

### Nagrywanie jednego modelu

```bash
python scripts/record_model.py \
  --model google/gemini-3.5-flash \
  --max-cost-usd 5
```

Potem:

```bash
python scripts/record_model.py --model openai/gpt-5-mini
python scripts/record_model.py --model anthropic/claude-haiku-4.5
```

### Wznowienie po błędzie 402/429/5xx

Nie usuwaj poprawnych kaset. Po doładowaniu lub odczekaniu uruchom to samo polecenie. Skrypt pominie istniejące pliki i nagra wyłącznie brakujące.

### Nagranie pojedynczego scenariusza

```bash
python scripts/record_model.py \
  --model openai/gpt-5-mini \
  --scenario 44_mix_revenue_key_kis
```

### Pełne nagranie po zmianie requestu

Tylko po zmianie algorytmu, schematu, promptu, profilu modelu lub scenariuszy:

```bash
rm -rf tests/llm/vcr/cassettes/google_gemini_3_5_flash
python scripts/record_model.py --model google/gemini-3.5-flash
```

Analogicznie dla pozostałych modeli. Opcja `--force` również nagrywa wszystko ponownie, ale jest droższa i powinna być używana wyłącznie świadomie.

## 5. Weryfikacja offline

Dla jednego modelu:

```bash
unset OPENROUTER_API_KEY
export LLM_PROVIDER=openrouter
export LLM_MODEL=google/gemini-3.5-flash
export VCR_MODE=playback

pytest tests/llm/test_scenarios.py --run-llm --vcr-mode=playback -v
python scripts/vcr_precommit.py --model google/gemini-3.5-flash
```

Dla całej macierzy:

```bash
./scripts/verify_all_models.sh
```

## 6. Kryterium zaliczenia

Model zalicza benchmark tylko przy **36/36**. Odpowiedź musi jednocześnie:

- zakończyć się `finish_reason=stop`;
- być czystym JSON;
- przejść strict JSON Schema;
- zgadzać się z niezależnym oracle;
- mieć poprawny request hash i fingerprint;
- przejść późniejszy playback bez klucza API.

13/36 albo 30/36 to wynik diagnostyczny, nie gotowa bramka produkcyjna.

## 7. Analiza odrzuconych odpowiedzi

```bash
find /tmp/ipbox_llm_rejected -type f -maxdepth 3 -print
```

Dla każdej porażki ustal jedną kategorię:

1. błąd scenariusza/asercji;
2. błąd kalkulatora/oracle;
3. niejasna instrukcja;
4. błąd schematu lub integracji OpenRouter;
5. ograniczenie modelu.

Nie poprawiaj asercji tylko dlatego, że model zwrócił inną liczbę. Najpierw przelicz prawdę deterministycznie i dodaj test regresyjny.

## 8. Przegląd przed commitem kaset

```bash
python scripts/benchmark_report.py
python scripts/vcr_precommit.py --all-models
git status --short
git diff --stat
```

Sprawdź ręcznie szczególnie:

- 11 — FX;
- 23–27 — W=90% i ulgi;
- 29–30 — NEXUS C i A+C;
- 31–33 — TEST 1–3 FAIL;
- 39 — ważona średnia W;
- 44 — KIS/MIX bez automatycznego NEXUS A;
- 45 — alokacja 8000 = 3000 + 5000.

Repozytorium przyjmuje tylko dwa stany: brak kaset albo kompletna, poprawna macierz 3 × 36. `python scripts/check_cassette_policy.py` blokuje częściowy commit. Nie commituj `/tmp/ipbox_llm_rejected` ani raportów.

## 9. Manualny workflow GitHub

Workflow `Paid multi-model LLM benchmark` wymaga jawnego tekstu potwierdzającego koszt i ma miękki limit kosztu per model. Każdy model działa w osobnym, sekwencyjnym jobie. Pobierz trzy artefakty, skopiuj katalogi modeli do `tests/llm/vcr/cassettes/`, a następnie uruchom:

```bash
./scripts/verify_all_models.sh
python scripts/benchmark_report.py
python scripts/check_cassette_policy.py
```

Workflow nie commituję kaset automatycznie. Dzięki temu odrzucona odpowiedź ani częściowy zestaw nie może trafić na branch bez przeglądu.
