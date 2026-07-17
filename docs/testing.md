# Testowanie i nagrywanie kaset

## 1. Co testuje benchmark

Python oblicza liczby, klasyfikacje, W, TEST 1–9 i atomowe `decision_facts`. Runner usuwa wszystkie wartości `false` i tworzy listę `active_rules` zawierającą tylko prawdziwe reguły oraz ich kody. Model otrzymuje wyłącznie tę listę i zwraca:

```json
{"status":"FINAL","stops":[],"reviews":["REVIEW_09"]}
```

Runner składa decyzję z raportem deterministycznym i waliduje całość. Benchmark mierzy zgodność instrukcji i integracji providera, nie umiejętność modelu do ponownego liczenia podatku.

Historyczne kasety pełnego raportu ujawniły wymyślone kursy NBP, automatyczne `JetBrains → IP`, niespójny NEXUS i TEST-y deklarowane przez model jako PASS. Obecny kontrakt świadomie odbiera modelowi te obowiązki.

## 2. Bezpłatna bramka

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
for script in scripts/*.sh dump-to-md.sh; do bash -n "$script"; done
```

Stan referencyjny z 17 lipca 2026 r.:

- 158 testów jednostkowych PASS;
- coverage `python_helper` 95,27%;
- pełny suite: 158 PASS i 36 kontrolowanych skipów LLM;
- pusty katalog kaset jest dozwolony, częściowa macierz nie jest.

## 3. Testy semantyczne, które muszą pozostać

Szczególnie chronione regresje:

- NEXUS podwyższa A+B, w tym przypadek B+C = 0,65;
- B+R IP pomniejsza dochód przed NEXUS;
- podatek działalności na skali obejmuje inne dochody skali;
- liniowy nie przyjmuje ulg dostępnych wyłącznie na skali;
- `straty_poprzednie` i `ulga_BR` są odrzucane jako niejednoznaczne;
- ujemne faktury, odliczenia i zaliczki są odrzucane;
- limity zdrowotnej/IKZE dla nieobsługiwanego roku są fail-closed;
- STOP zeruje każde finalne pole;
- multi-IP zachowuje grosze;
- playback nie wywołuje sieci i odrzuca `finish_reason` inny niż `stop`;
- tryb record nie nadpisuje istniejącej kasety;
- miesiące muszą odpowiadać `input.rok`, a termomodernizacja nie przekracza 53 000 zł.

## 4. Dlaczego stare kasety są nieważne

Fingerprint obejmuje protokół decyzji, listę aktywnych reguł, system prompt, request, model, profil, schema i format kasety. Zmiana któregokolwiek elementu unieważnia nagranie. Kasety z pełną mapą `true/false` są nieaktualne i muszą zostać nagrane od nowa.

Kasety starego pełnego raportu nie są zgodne z obecną kopertą decyzji. Nie kopiuj ich odpowiedzi, hashy, manifestu ani parsed payloadu. Po obecnych zmianach należy nagrać **108 kaset: 3 modele × 36 scenariuszy**.

## 5. Modele bramkowe

```text
google/gemini-3.5-flash
openai/gpt-5-mini
anthropic/claude-haiku-4.5
```

Wykonywalna lista znajduje się w `tests/llm/models.py`.

## 6. Nagranie

```bash
git switch fix/decouple-mix-allocation-from-w
git pull --ff-only
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt
export OPENROUTER_API_KEY='WKLEJ_KLUCZ'

./scripts/record_all_models.sh --max-cost-usd 5
```

Pojedynczy model lub scenariusz:

```bash
python scripts/record_model.py --model google/gemini-3.5-flash --max-cost-usd 5
python scripts/record_model.py \
  --model openai/gpt-5-mini \
  --scenario 45_multi_ip_two_stage \
  --max-cost-usd 5
```

Skrypt nie nadpisuje poprawnej kasety. Przy 402, 429 lub 5xx uruchom polecenie ponownie. Odrzucenia trafiają do `/tmp/ipbox_llm_rejected/`, a wyniki do `/tmp/ipbox_llm_responses/`.

Nie ma `--force`. Nieaktualny plik usuń dopiero po zidentyfikowaniu zmienionego elementu requestu.

## 7. Playback offline

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

Playback musi przejść przy nieustawionym sekrecie. Live request w tym trybie jest błędem krytycznym.

## 8. Kryterium zaliczenia

Model zalicza tylko przy 36/36. Każda kaseta musi:

- mieć `finish_reason=stop`;
- zawierać czysty JSON bez pól dodatkowych;
- przejść strict schema decyzji;
- zwrócić dokładny zestaw STOP/REVIEW bez duplikatów;
- po złożeniu przejść pełny schema i evaluator;
- mieć zgodny request hash, fingerprint i ponowne parsowanie;
- przejść playback bez klucza API.

35/36 jest diagnostyką, nie bramką wydania.

## 9. Analiza porażki

Przypisz przyczynę:

1. scenariusz lub asercja;
2. kalkulator/oracle;
3. `decision_facts`;
4. schema/integracja providera;
5. model mimo jednoznacznej instrukcji.

Najpierw dodaj test deterministyczny. Nie poszerzaj zakresu i nie usuwaj kodu tylko dlatego, że model go pomija.

Minimalny ręczny przegląd:

- 13 — pełny podatek wspólnej skali;
- 14 — tylko `STOP_01`;
- 18 — właściwy STOP przy zerowych godzinach;
- 22 — NEXUS 0,65 dla B=5000 i C=5000;
- 23 — strata wyłącznie NIE;
- 24/25 — osobiste ulgi na skali;
- 26 — B+R IP przed NEXUS;
- 31 — `ZUS_DOUBLE_DIP` i TEST_3 FAIL;
- 34 — zakup >10 000 zł wyłączony;
- 38/42 — tylko `STOP_08`;
- 44 — KIS MIX bez użycia W;
- 45 — REVIEW 04/16/17 i alokacja 3000 + 5000.

## 10. Commit kaset

```bash
./scripts/verify_all_models.sh
python scripts/benchmark_report.py
python scripts/vcr_precommit.py --all-models
python scripts/check_cassette_policy.py
git status --short
git diff --stat
```

Repo dopuszcza brak kaset albo kompletną aktualną macierz 3 × 36. Nie commituj `/tmp`, raportów lokalnych ani częściowej macierzy.

## 11. Workflow GitHub

`Paid multi-model LLM benchmark` wymaga jawnego potwierdzenia kosztu. Artefakty nie są commitowane automatycznie. Po pobraniu skopiuj trzy katalogi do `tests/llm/vcr/cassettes/` i wykonaj sekcję 10.
