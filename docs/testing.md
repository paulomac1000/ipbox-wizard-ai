# Testowanie i nagrywanie kaset

## 1. Co testuje benchmark

Python oblicza liczby, klasyfikacje, W, TEST 1–9 i atomowe `decision_facts`, a następnie składa kompletną autorytatywną kopertę `expected_decision`. Model otrzymuje gotowe, rozdzielone `status`, `stops` i `reviews` i ma je skopiować bez zmian:

```json
{"status":"FINAL","stops":[],"reviews":["REVIEW_09"]}
```

Runner składa decyzję z raportem deterministycznym i waliduje całość. Benchmark mierzy zgodność instrukcji oraz integracji providera, nie umiejętność modelu do ponownego liczenia podatku.

Kolejne historyczne protokoły ujawniły trzy klasy problemów:

1. pełny raport LLM powodował wymyślone kursy, klasyfikacje, NEXUS i TEST-y;
2. widoczność nieaktywnych faktów powodowała dopisywanie nieaktywnych kodów;
3. lista kodów z etykietami wymagała ponownej klasyfikacji do STOP/REVIEW i pozwoliła MiniMax przenieść `REVIEW_09` do `stops`.

`expected_decision` usuwa wszystkie trzy zbędne odpowiedzialności modelu.

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

Stan referencyjny przed końcowym nagraniem:

- wszystkie testy jednostkowe PASS; dokładną liczbę raportuje CI;
- coverage `python_helper` powyżej wymaganego progu 90%;
- pełny suite: wszystkie bezpłatne testy PASS i 46 kontrolowanych skipów LLM;
- pusty katalog kaset jest dozwolony lokalnie, ale nie spełnia merge gate.

Standardowy workflow na Pythonie 3.13 dodatkowo uruchamia:

```bash
python scripts/benchmark_report.py
unset OPENROUTER_API_KEY
./scripts/verify_all_models.sh
```

Dlatego PR z pustą, częściową albo nieaktualną macierzą nie może mieć zielonej bramki wydania.

## 3. Testy semantyczne, które muszą pozostać

Szczególnie chronione regresje:

- NEXUS podwyższa A+B, w tym przypadek B+C = 0,65;
- B+R IP pomniejsza dochód przed NEXUS;
- podatek działalności na skali obejmuje inne dochody skali;
- liniowy nie przyjmuje ulg dostępnych wyłącznie na skali;
- `straty_poprzednie` i `ulga_BR` są odrzucane jako niejednoznaczne;
- ujemne faktury, odliczenia i zaliczki są odrzucane;
- limity zdrowotnej/IKZE dla nieobsługiwanego roku są fail-closed;
- STOP zeruje każde finalne pole i klasyfikacje;
- multi-IP zachowuje grosze;
- prompt zawiera wyłącznie `expected_decision`, bez faktów podatkowych i nazw predykatów;
- schema odrzuca kod REVIEW w `stops`, kod STOP w `reviews` i duplikaty;
- dokumentacja kontraktu nie może opisywać starszego protokołu;
- provider adapter nie mutuje ani nie osłabia lokalnej strict schema;
- playback nie wywołuje sieci i odrzuca `finish_reason` inny niż `stop`;
- live run, playback i pre-commit odrzucają substytucję modelu;
- pre-commit porównuje zapisane `parsed_response` z ponownym parsowaniem;
- tryb record nie nadpisuje istniejącej kasety;
- miesiące muszą odpowiadać `input.rok`, a termomodernizacja nie przekracza 53 000 zł;
- jawna semantyka W odróżnia iloczyn warunkowy, rozłączne składniki i sam czas;
- podwójny procent faktury oraz nieudokumentowana zmiana metody w roku aktywują STOP;
- ewidencja i zeznanie uzgadniają się osobno w IP/NIE nawet przy równych sumach globalnych;
- reguły roczne 2019–2026 obejmują IKZE, zdrowotną, skalę i granicę jednoczesnego B+R/IP Box;
- `rounding_steps` przyjmuje wyłącznie rzeczywisty dodatni `int`, bez booleanów, stringów i obcinania floatów;
- naliczona odpowiedź HTTP 200 z pustą albo odrzuconą treścią trafia do niezmiennego rejestru odrzuceń wraz z kosztem.

## 4. Fingerprint i unieważnienie

Fingerprint obejmuje treściowy hash silnika, treściowy hash harnessu VCR, scenariusz oraz pełny request hash. Zmiana któregokolwiek elementu unieważnia nagranie. Nie kopiuj ręcznie odpowiedzi, hashy, fingerprintów, manifestu ani `parsed_response`. Jeżeli zmienia się wyłącznie deterministyczny kod lub metadane, `scripts/refresh_vcr_metadata.py --all-models --write` może ponownie zwalidować istniejące surowe odpowiedzi bez requestów API; każda niezgodna odpowiedź zatrzymuje proces.

## 5. Modele i adaptery transportowe

Wykonywalna lista znajduje się wyłącznie w `tests/llm/models.py`.

| Model | Transport | Powód wyjątku |
|---|---|---|
| `google/gemini-3-flash-preview` | `json_schema` | — |
| `anthropic/claude-haiku-4.5` | `json_schema` bez `uniqueItems` w kopii transportowej | endpoint odrzuca keyword HTTP 400; lokalna schema nadal wymaga unikalności |
| `deepseek/deepseek-chat-v3.1` | `json_schema` | — |
| `minimax/minimax-m2.5` | `json_object` | routing DigitalOcean zwracał `content: null` dla `json_schema`; lokalna schema nadal jest pełna |
| `moonshotai/kimi-k2.5` | `json_schema` | — |
| `qwen/qwen3.5-flash-02-23` | `json_schema` | — |
| `mistralai/mistral-small-24b-instruct-2501` | `json_schema` | — |

Adapter zmienia wyłącznie transport. Parser, `DECISION_JSON_SCHEMA`, output schema i evaluator są wspólne dla wszystkich modeli.

## 6. Odświeżenie lub nagranie

Po zmianie deterministycznego kodu albo metadanych zacznij bez requestów API:

```bash
python scripts/refresh_vcr_metadata.py --all-models --write
python scripts/vcr_precommit.py --all-models
unset OPENROUTER_API_KEY
./scripts/verify_all_models.sh
```

Skrypt zachowuje surowe odpowiedzi, przelicza tożsamość i ponownie wykonuje pełną walidację. Jeżeli choć jedna odpowiedź nie odpowiada aktualnej semantyce, proces zatrzymuje się — wtedy usuń tylko wskazane, unieważnione kasety i nagraj je ponownie. Nie kasuj całej macierzy rutynowo.

Płatne nagranie pełnej lub brakującej części macierzy:

```bash
git switch fix/decouple-mix-allocation-from-w
git pull --ff-only
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt

cp .env.example .env
chmod 600 .env
# wpisz OPENROUTER_API_KEY oraz dwa dodatnie limity w .env albo przekaż je przez CLI
# potwierdzenia nie zapisuj w .env — ustaw je tylko dla świadomie uruchamianego polecenia
LLM_PAID_RUN_CONFIRMATION=RUN_PAID_BENCHMARK \
./scripts/record_all_models.sh \
  --max-cost-per-model-usd 5 \
  --max-total-cost-usd 5
```

Pojedynczy model lub scenariusz:

```bash
LLM_PAID_RUN_CONFIRMATION=RUN_PAID_BENCHMARK \
python scripts/record_model.py --model google/gemini-3-flash-preview \
  --max-cost-per-model-usd 5 --max-total-cost-usd 5
LLM_PAID_RUN_CONFIRMATION=RUN_PAID_BENCHMARK \
python scripts/record_model.py \
  --model google/gemini-3-flash-preview \
  --scenario 45_multi_ip_two_stage \
  --max-cost-per-model-usd 5 --max-total-cost-usd 5
```

Skrypty lokalne automatycznie czytają tylko dozwolone ustawienia z `.env`. Plik nie jest wykonywany przez powłokę, nieznane klucze są ignorowane, a jawnie ustawione zmienne procesu mają pierwszeństwo. `.env` pozostaje w `.gitignore`; ustaw prawa `chmod 600`. Potwierdzenie płatnego przebiegu celowo nie jest czytane z `.env`: ma być nową, świadomą decyzją dla bieżącego polecenia lub sesji powłoki. Skrypt nie nadpisuje istniejącej kasety. Przy błędzie transportowym uruchom ponownie dopiero po sprawdzeniu, że plik nie powstał i przyczyna została sklasyfikowana. Odrzucenia trafiają do skonfigurowanego `VCR_REJECTED_ROOT` (domyślnie `/tmp/ipbox_llm_rejected/`) jako osobne, niezmienne pliki dla każdej płatnej próby, a wyniki do `/tmp/ipbox_llm_responses/`. Odpowiedź z naliczonym `usage.cost`, lecz pustą albo odrzuconą treścią, również musi pozostać w tym rejestrze.

Nie ma `--force`. Nie ponawiaj błędu semantycznego aż do uzyskania „szczęśliwej” odpowiedzi.

## 7. Playback offline

```bash
python scripts/check_cassette_policy.py
python scripts/vcr_precommit.py --all-models
python scripts/benchmark_report.py
unset OPENROUTER_API_KEY
./scripts/verify_all_models.sh
```

Playback musi przejść przy nieustawionym sekrecie. Live request w tym trybie jest błędem krytycznym.

## 8. Kryterium zaliczenia

Model zalicza tylko przy 46/46, a cała macierz przy 322/322. Każda kaseta musi:

- mieć `finish_reason=stop`;
- mieć `returned_model` identyczny z modelem żądanym;
- zawierać czysty JSON bez pól dodatkowych, Markdown fences ani naprawiania parserem;
- przejść lokalną strict schema decyzji;
- zwrócić dokładny zestaw STOP/REVIEW bez duplikatów;
- po złożeniu przejść pełny schema i evaluator;
- mieć zgodny request hash, fingerprint i ponowne parsowanie;
- przejść playback bez klucza API.

45/46 jest diagnostyką, nie bramką wydania.

## 9. Analiza porażki

Przypisz przyczynę:

1. scenariusz lub asercja;
2. kalkulator/oracle;
3. budowa `expected_decision` lub schema;
4. adapter/routing providera;
5. format odpowiedzi modelu;
6. model mimo jednoznacznej instrukcji.

Najpierw dodaj test deterministyczny. Nie poszerzaj zakresu i nie usuwaj kodu tylko dlatego, że model go pomija.

Minimalny ręczny przegląd obejmuje scenariusze 13, 17, 22, 23, 26, 31, 34, 38, 42, 44, 45 i 46–55. W scenariuszu 51 każdy model ma zwrócić dokładnie `status=STOPPED`, `stops=[STOP_12]`, `reviews=[REVIEW_09]`.

## 10. Commit i merge gate

```bash
./scripts/verify_all_models.sh
python scripts/benchmark_report.py
python scripts/vcr_precommit.py --all-models
python scripts/check_cassette_policy.py
git status --short
git diff --stat
```

Nie commituj `/tmp`, raportów lokalnych ani częściowej macierzy. Po wypchnięciu kaset poczekaj na CI Python 3.11–3.13. Job 3.13 musi wykonać raport i pełny playback offline. Dopiero potem można oznaczyć PR jako ready.
