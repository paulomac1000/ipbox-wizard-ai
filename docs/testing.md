# Testowanie i nagrywanie kaset

## 1. Architektura benchmarku

Benchmark nie wymaga od modelu przepisywania pełnego raportu finansowego.

1. Python oblicza wynik finansowy, klasyfikacje, W i TEST 1–9.
2. Python tworzy atomowe `decision_facts` sprzed ewentualnego wyzerowania po STOP.
3. Model zwraca wyłącznie małą kopertę `status`, `stops`, `reviews`.
4. Runner dołącza kopertę do raportu deterministycznego i waliduje pełny wynik.

Ta granica jest celowa. Model nie powinien ponownie wykonywać arytmetyki ani kopiować kilkuset pól, skoro ich prawidłową wartość zna kod. Benchmark sprawdza interpretację jawnych faktów, zgodność z protokołem oraz kompatybilność providera.

## 2. Bezpłatna bramka przed API

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
python scripts/check_cassette_policy.py
```

Oczekiwany stan przed pierwszym nagraniem:

- wszystkie testy jednostkowe przechodzą;
- coverage wynosi co najmniej 90%;
- 36 testów LLM jest pominiętych bez `--run-llm`;
- polityka kaset akceptuje pusty katalog.

## 3. Dlaczego wszystkie poprzednie kasety są nieaktualne

Tożsamość requestu obejmuje między innymi:

- protokół decyzji wygenerowany z map kodu;
- `decision_facts` scenariusza;
- system prompt;
- model i jego profil;
- mały JSON Schema decyzji;
- wersję formatu kasety.

Po zmianie z pełnego raportu na kopertę decyzji poprzednie 84 kasety nie reprezentują już tego samego requestu. Nie wolno kopiować ich odpowiedzi, hashy ani manifestów. Należy nagrać pełne **108 nowych kaset: 3 modele × 36 scenariuszy**.

## 4. Modele bramkowe

```text
google/gemini-3.5-flash
openai/gpt-5-mini
anthropic/claude-haiku-4.5
```

Każdy model ma zwrócić ten sam semantyczny wynik. Benchmark nie uznaje częściowego wyniku za sukces.

## 5. Nagranie całej macierzy

### Przygotowanie

```bash
git switch fix/decouple-mix-allocation-from-w
git pull --ff-only
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt
export OPENROUTER_API_KEY='WKLEJ_KLUCZ'
```

Najpierw wykonaj bezpłatną bramkę z sekcji 2. Następnie:

```bash
./scripts/record_all_models.sh --max-cost-usd 5
```

Skrypt:

1. nagrywa modele sekwencyjnie;
2. nagrywa każdy scenariusz osobno;
3. wznawia pracę bez ponownego opłacania poprawnych kaset;
4. zapisuje odrzucone odpowiedzi do `/tmp/ipbox_llm_rejected/`;
5. zapisuje pełne złożone wyniki do `/tmp/ipbox_llm_responses/`;
6. stosuje miękki limit kosztu przed kolejnym requestem;
7. wykonuje późniejszy playback bez klucza API;
8. generuje raport benchmarku.

### Jeden model

```bash
python scripts/record_model.py \
  --model google/gemini-3.5-flash \
  --max-cost-usd 5
```

```bash
python scripts/record_model.py --model openai/gpt-5-mini --max-cost-usd 5
python scripts/record_model.py --model anthropic/claude-haiku-4.5 --max-cost-usd 5
```

### Jeden scenariusz

```bash
python scripts/record_model.py \
  --model openai/gpt-5-mini \
  --scenario 45_multi_ip_two_stage \
  --max-cost-usd 5
```

### Wznowienie po 402, 429 lub 5xx

Nie usuwaj poprawnych kaset. Po doładowaniu konta albo odczekaniu uruchom to samo polecenie. Skrypt sprawdzi istniejące kasety offline i nagra tylko brakujące. Nieaktualna kaseta zatrzymuje dany scenariusz do czasu jej jawnego usunięcia.

Nie ma opcji `--force`. Poprawna kaseta jest tylko odtwarzana i pomijana, a nieaktualna kaseta blokuje nagranie. Po świadomej zmianie requestu usuń konkretny stary plik lub cały katalog modelu, przejrzyj diff i dopiero wtedy nagraj od nowa.

## 6. Weryfikacja offline

Po nagraniu usuń klucz z procesu:

```bash
unset OPENROUTER_API_KEY
./scripts/verify_all_models.sh
python scripts/benchmark_report.py
python scripts/vcr_precommit.py --all-models
python scripts/check_cassette_policy.py
```

Dla pojedynczego modelu:

```bash
export LLM_PROVIDER=openrouter
export LLM_MODEL=google/gemini-3.5-flash
export VCR_MODE=playback

pytest tests/llm/test_scenarios.py --run-llm --vcr-mode=playback -v
python scripts/vcr_precommit.py --model google/gemini-3.5-flash
```

## 7. Kryterium zaliczenia

Model zalicza benchmark tylko przy **36/36**. Każda kaseta musi:

- zakończyć się kompletną odpowiedzią;
- zawierać czysty JSON decyzji;
- przejść mały strict JSON Schema;
- wskazać dokładnie oczekiwane STOP i REVIEW, bez duplikatów i nadmiarowych kodów;
- po złożeniu z raportem deterministycznym przejść pełny schema i evaluator;
- mieć zgodny request hash i fingerprint;
- przejść playback bez klucza API.

Wynik 35/36 jest informacją diagnostyczną, a nie akceptowalną bramką produkcyjną.

## 8. Analiza odrzuconej odpowiedzi

```bash
find /tmp/ipbox_llm_rejected -maxdepth 3 -type f -print
```

Dla każdej porażki ustal jedną kategorię:

1. błędny scenariusz lub asercja;
2. błąd oracle albo kalkulatora;
3. sprzeczne lub niewidoczne fakty decyzyjne;
4. błąd schema/integracji providera;
5. model dodał lub pominął kod mimo jednoznacznej tabeli.

Nie zmieniaj prawdy testowej pod odpowiedź modelu. Najpierw dodaj deterministyczny test regresyjny pokazujący, jaki powinien być fakt i kod.

Szczególnie sprawdź:

- 14 — wyłącznie `STOP_01`, bez kaskady;
- 18 — `STOP_04`, a zero W nie tworzy dodatkowego STOP;
- 31 — `ZUS_DOUBLE_DIP` i TEST_3 FAIL;
- 38/42 — wyłącznie `STOP_08`;
- 45 — `REVIEW_04`, `REVIEW_16`, `REVIEW_17` oraz alokacja 3000 + 5000.

## 9. Commit kaset

Przed commitem:

```bash
./scripts/verify_all_models.sh
python scripts/benchmark_report.py
python scripts/vcr_precommit.py --all-models
python scripts/check_cassette_policy.py
git status --short
git diff --stat
```

Repozytorium dopuszcza tylko dwa stany:

- brak kaset;
- kompletna i aktualna macierz 3 × 36.

Nie commituj częściowej macierzy, katalogów `/tmp/ipbox_llm_rejected`, `/tmp/ipbox_llm_responses` ani lokalnych raportów diagnostycznych.

## 10. Manualny workflow GitHub

Workflow `Paid multi-model LLM benchmark` wymaga jawnego potwierdzenia kosztu. Każdy model działa osobno, a artefakty nie są automatycznie commitowane. Po pobraniu artefaktów skopiuj trzy katalogi modeli do `tests/llm/vcr/cassettes/` i ponownie wykonaj pełną weryfikację z sekcji 9.
