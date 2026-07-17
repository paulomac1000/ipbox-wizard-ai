# Testowanie i nagrywanie kaset

## 1. Co testuje benchmark

Python oblicza liczby, klasyfikacje, W, TEST 1–9 i atomowe `decision_facts`. Runner usuwa wszystkie wartości `false` i tworzy listę `active_rules` zawierającą tylko rodzaj i kod prawdziwych reguł. Model otrzymuje wyłącznie tę listę i zwraca:

```json
{"status":"FINAL","stops":[],"reviews":["REVIEW_09"]}
```

Runner składa decyzję z raportem deterministycznym i waliduje całość. Benchmark mierzy zgodność instrukcji i integracji providera, nie umiejętność modelu do ponownego liczenia podatku.

Historyczne kasety pełnego raportu ujawniły wymyślone kursy NBP, automatyczne `JetBrains → IP`, niespójny NEXUS i TEST-y deklarowane przez model jako PASS. Pierwsza macierz małej koperty ujawniła inną wadę protokołu: część modeli reinterpretowała nazwy fałszywych faktów i dopisywała nieaktywne kody. `active_rules` usuwa tę dwuznaczność bez wyjątków scenariuszowych.

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

Stan referencyjny po audycie protokołu z 17 lipca 2026 r.:

- 181 testów jednostkowych PASS;
- coverage `python_helper` 94,32%;
- pełny suite: 181 PASS i 36 kontrolowanych skipów LLM;
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
- prompt zawiera wyłącznie prawdziwe `active_rules`; nieaktywny fakt i kod nie mogą być widoczne;
- playback nie wywołuje sieci i odrzuca `finish_reason` inny niż `stop`;
- pre-commit porównuje zapisane `parsed_response` z ponownym parsowaniem;
- tryb record nie nadpisuje istniejącej kasety;
- miesiące muszą odpowiadać `input.rok`, a termomodernizacja nie przekracza 53 000 zł.

## 4. Dlaczego stare kasety są nieważne

Fingerprint obejmuje protokół decyzji, listę aktywnych reguł, system prompt, request, model, profil, schema i format kasety. Zmiana któregokolwiek elementu unieważnia nagranie. Kasety z pełną mapą `true/false` oraz pierwsza macierz `active_rules` z parserem usuwającym Markdown fences są nieaktualne i muszą zostać nagrane od nowa.

Kasety starego pełnego raportu także nie są zgodne z obecną kopertą decyzji. Nie kopiuj ich odpowiedzi, hashy, manifestu ani parsed payloadu. Po obecnych zmianach należy nagrać **324 kasety: 9 modeli × 36 scenariuszy**.

## 5. Modele bramkowe

| Rodzina | Model OpenRouter | Rola w macierzy |
|---|---|---|
| Google Gemini | `google/gemini-3-flash-preview` | tańszy i starszy próg zamiast Gemini 3.5 |
| OpenAI GPT | `openai/gpt-5-nano` | najmniejszy model GPT-5 jako niski próg zgodności |
| Anthropic Claude | `anthropic/claude-haiku-4.5` | mały model Claude |
| DeepSeek | `deepseek/deepseek-chat-v3.1` | otwarta rodzina DeepSeek V3 |
| MiniMax | `minimax/minimax-m2.5` | niezależna rodzina MoE |
| Moonshot Kimi | `moonshotai/kimi-k2.5` | niezależna rodzina Kimi |
| Z.ai GLM | `z-ai/glm-4.7-flash` | tani model Flash GLM |
| Qwen | `qwen/qwen3.5-flash-02-23` | tani model Flash Qwen |
| Mistral | `mistralai/ministral-3b-2512` | bardzo mały model 3B jako dolna granica |


Wykonywalna lista znajduje się wyłącznie w `tests/llm/models.py`; skrypty shell
odczytują ją dynamicznie. Uzasadnienie i migawka cen znajdują się w
[`model-diversity-benchmark.md`](model-diversity-benchmark.md).

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
python scripts/record_model.py --model google/gemini-3-flash-preview --max-cost-usd 5
python scripts/record_model.py \
  --model openai/gpt-5-nano \
  --scenario 45_multi_ip_two_stage \
  --max-cost-usd 5
```

Skrypt nie nadpisuje istniejącej kasety. Przy błędzie transportowym uruchom ponownie tylko po sprawdzeniu, że plik nie powstał. Odrzucenia trafiają do `/tmp/ipbox_llm_rejected/`, a wyniki do `/tmp/ipbox_llm_responses/`.

Nie ma `--force`. Nieaktualny plik usuń dopiero po zidentyfikowaniu zmienionego elementu requestu. Nie ponawiaj błędu semantycznego aż do uzyskania „szczęśliwej” odpowiedzi — zachowaj odrzucenie w raporcie i zdiagnozuj przyczynę.

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
export LLM_MODEL=google/gemini-3-flash-preview
export VCR_MODE=playback
pytest tests/llm/test_scenarios.py --run-llm --vcr-mode=playback -v
python scripts/vcr_precommit.py --model google/gemini-3-flash-preview
```

Playback musi przejść przy nieustawionym sekrecie. Live request w tym trybie jest błędem krytycznym.

## 8. Kryterium zaliczenia

Model zalicza tylko przy 36/36, a cała macierz przy 324/324. Każda kaseta musi:

- mieć `finish_reason=stop`;
- zawierać czysty JSON bez pól dodatkowych, Markdown fences ani naprawiania parserem;
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
3. `decision_facts` albo budowa `active_rules`;
4. schema/integracja providera;
5. model mimo jednoznacznej instrukcji.

Najpierw dodaj test deterministyczny. Nie poszerzaj zakresu i nie usuwaj kodu tylko dlatego, że model go pomija.

Minimalny ręczny przegląd:

- 13 — pełny podatek wspólnej skali;
- 14 — tylko `STOP_01`;
- 17 — tylko `REVIEW_02`, bez nieaktywnego `STOP_02`;
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

Repo dopuszcza brak kaset albo kompletną aktualną macierz 9 × 36. Nie commituj `/tmp`, raportów lokalnych ani częściowej macierzy.

## 11. Workflow GitHub

`Paid multi-model LLM benchmark` wymaga jawnego potwierdzenia kosztu. Artefakty nie są commitowane automatycznie. Po pobraniu skopiuj dziewięć katalogów do `tests/llm/vcr/cassettes/` i wykonaj sekcję 10.
