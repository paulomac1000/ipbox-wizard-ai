# ipbox-wizard-ai

Deterministyczny-first wizard wspierający przygotowanie danych do rozliczenia IP Box programisty B2B.

> To nie jest porada podatkowa ani generator gotowego zeznania. Wynik wymaga sprawdzenia z księgową lub doradcą. Audyt techniczny i semantyczny wykonano 25 lipca 2026 r.; reguły podatkowe są jawnie przypisane do wszystkich lat obowiązywania IP Box 2019–2026.

## Architektura

Model językowy nie wykonuje krytycznej arytmetyki:

1. `python_helper/ipbox_calculator.py`, `tax_year_rules.py` i `allocation_audit.py` walidują dane, liczą W, alokacje, NEXUS, reguły roczne, ulgi i podatek.
2. `tests/llm/oracle.py` tworzy niezależny wynik referencyjny i atomowe `decision_facts`.
3. Python składa kompletną autorytatywną kopertę `expected_decision` z rozdzielonymi kanałami STOP i REVIEW.
4. LLM kopiuje bez zmian `status/stops/reviews`; nie klasyfikuje kodów i nie widzi faktów podatkowych ani nazw predykatów.
5. Runner składa kopertę z raportem deterministycznym.
6. Evaluator i lokalna strict JSON Schema porównują wynik fail-closed.
7. Adapter providera może zmienić wyłącznie reprezentację transportową. Pełna lokalna schema i evaluator pozostają niezmienione.
8. VCR zapisuje tylko odpowiedź, która przeszła schema, semantykę i ponowne parsowanie.

Najważniejszy invariant z issue #1: **przychód IP/NIE, alokacja kosztów pośrednich `MIX` i klasyfikacja NEXUS są trzema niezależnymi decyzjami**. Współczynnik czasu `W` nie jest domyślnym kluczem `MIX`.

## Twarde reguły

- NEXUS: `min(1, ((A+B) × 1,3) / (A+B+C+D))`.
- Brak kosztów A/B/C/D daje NEXUS `0`, nie `1`.
- Koszt bez dowodu wyłącznego związku nie staje się automatycznie `IP`.
- Kwota powyżej 10 000 zł sama nie rozstrzyga klasyfikacji. Bez jawnego statusu aktywa i udokumentowanego sposobu ujęcia koszt pozostaje `MIX`, raport jest `PROVISIONAL` i wymaga `REVIEW_20`.
- Zwykłe darowizny, ulga internetowa, rehabilitacyjna i na dziecko są odrzucane dla podatku liniowego.
- Ulga B+R jest rozdzielana jawnie na `ulga_BR_IP` i `ulga_BR_NIE`; część IP pomniejsza dochód kwalifikowany przed NEXUS.
- `strata_NIE_z_lat_poprzednich` dotyczy wyłącznie pozostałej działalności. Straty kwalifikowanego IP wymagają osobnej ewidencji per IP.
- Działalność na skali łączy `dochody_dodatkowe_skala` z pozostałym dochodem skali i liczy pełny podatek od wspólnej podstawy.
- Działalność liniowa i dodatkowe dochody na skali wymagają dwóch odrębnych kaskad/zeznań; oracle odmawia ich mieszania.
- Limity zdrowotnej i IKZE są przypisane per rok; nieznany rok z dodatnim odliczeniem kończy się błędem.
- Miesiąc musi mieć ścisły format `YYYY-MM` i rok zgodny z `input.rok`.
- Limit termomodernizacji pochodzi z reguł roku. Dodatni lot wymaga `origin_year` i niepustego `evidence_ref`; zbiorcza `termomodernizacja_pula` jest wyłącznie trybem zgodnościowym `PROVISIONAL` z `REVIEW_22`.
- Odpowiedź z modelem innym niż żądany jest odrzucana podczas live runu, playbacku i pre-commit.
- Brak kursu, daty płatności, dowodu kwalifikacji lub ujemna faktura jest błędem danych, nie wartością zero.
- Rok i flagi kwalifikacji mają ścisłe typy; stringi nie są konwertowane na boolean ani rok.
- Metoda `dokumentowa` wymaga jawnego `kwota_IP` albo `całość_IP: true`.
- Opis wydatku może utworzyć sygnał do przeglądu, ale nie ustala samodzielnie `KUP: false`.

## Kompletność i reprodukowalność

`STOP_03` oznacza brak kwalifikowanego przychodu dopiero po jawnym potwierdzeniu kompletności źródeł w `input.coverage`. Brak potwierdzenia nie tworzy fałszywego STOP-u: wynik ma status `PROVISIONAL` i `REVIEW_19`. Podobnie nierozstrzygnięta klasyfikacja składki lub aktywa generuje review zamiast automatycznego wyzerowania kosztu.

Każdy raport zawiera `calculation_meta`: identyfikator silnika, rule pack roku, źródła reguł, SHA-256 wejścia, czas obliczenia i rewizję kodu.

`calculation_meta.engine_source_hash` jest autorytatywną, stabilną tożsamością treści silnika i kontraktu raportu. `code_revision` domyślnie używa tej tożsamości w formie `engine:<hash>`; chwilowy `GITHUB_SHA` nie wpływa na semantyczny playback kaset.

## Granica wejścia

Silnik przyjmuje znormalizowany YAML/dict. Repozytorium nie zawiera kompletnego, deterministycznego importera PDF/XLSX/KPiR/PIT. Odczyt dokumentów musi zachować jawne fakty źródłowe, w szczególności `KUP`, `source_ledger_included`, kwalifikację prawa, podział faktury i referencje dowodów. Poprawny kalkulator nie naprawi błędnie wyekstrahowanych danych.

Szczegółowy kontrakt: [`ipbox_algorytm.md`](ipbox_algorytm.md). Raport audytu: [`docs/audit-2026-07-17.md`](docs/audit-2026-07-17.md).

## Szybki start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt

ruff format --check .
ruff check .
python -m compileall -q python_helper tests scripts
pytest tests/unit --cov=python_helper --cov-report=term-missing --cov-fail-under=90
pytest -q
python scripts/check_cassette_policy.py
for script in scripts/*.sh dump-to-md.sh; do bash -n "$script"; done
```

Bramka deterministyczna obejmuje co najmniej **256 testów jednostkowych**, coverage `python_helper` powyżej wymaganych **90%**, pełny bezpłatny suite i Python 3.11–3.13. Dokładne wartości raportuje CI.

## Benchmark wielorodzinny

Benchmark używa siedmiu modeli z siedmiu niezależnych rodzin:

| Rodzina | Model OpenRouter | Transport |
|---|---|---|
| Google Gemini | `google/gemini-3-flash-preview` | strict `json_schema` |
| Anthropic Claude | `anthropic/claude-haiku-4.5` | `json_schema` bez nieobsługiwanego przez endpoint keywordu `uniqueItems`; lokalna schema pozostaje pełna |
| DeepSeek | `deepseek/deepseek-chat-v3.1` | strict `json_schema` |
| MiniMax | `minimax/minimax-m2.5` | `json_object` z pełną lokalną schema, ponieważ routing DigitalOcean zwracał `content: null` dla `json_schema` |
| Moonshot Kimi | `moonshotai/kimi-k2.5` | strict `json_schema` |
| Qwen | `qwen/qwen3.5-flash-02-23` | strict `json_schema` |
| Mistral | `mistralai/mistral-small-24b-instruct-2501` | strict `json_schema` |

To jest **test przenośności protokołu**, nie dowód poprawności podatkowej i nie matematyczna gwarancja zachowania każdego mocniejszego modelu. Jeżeli małe modele różnych dostawców przechodzą identyczny lokalny kontrakt bez naprawiania odpowiedzi, rośnie wiarygodność, że interfejs jest jednoznaczny i niezależny od jednej rodziny. Prawdą podatkową nadal pozostają Python, oracle i testy deterministyczne.

Nagrywanie jest jawne i płatne. Wybór scenariusza jest dokładny, a koszty zaakceptowanych i odrzuconych odpowiedzi wliczają się do limitu przebiegu:

```bash
export OPENROUTER_API_KEY='...'
./scripts/record_all_models.sh \
  --max-cost-per-model-usd 5 \
  --max-total-cost-usd 5
```

Ręczny workflow `Paid multi-model LLM benchmark` wymaga wpisania tekstu potwierdzenia oraz podania obu limitów. Standardowy CI nigdy nie wykonuje płatnych requestów. Limit globalny jest sprawdzany przed i po każdym requestcie; ponieważ provider raportuje koszt po odpowiedzi, pojedyncza odpowiedź może przekroczyć próg, lecz po jej zaksięgowaniu żaden kolejny request nie zostanie uruchomiony.

Pełna procedura: [`docs/testing.md`](docs/testing.md). Dobór modeli i ograniczenia wnioskowania: [`docs/model-diversity-benchmark.md`](docs/model-diversity-benchmark.md). Niezależny audyt: [`docs/independent-audit-brief.md`](docs/independent-audit-brief.md).

## Zakres multi-IP

`allocate_multi_ip()` wykonuje dwustopniowy podział wspólnych kosztów z zachowaniem groszy. Nie zastępuje pełnej ewidencji PIT/IP dla każdego kwalifikowanego prawa. Finalne rozliczenie wielu IP wymaga osobnych przychodów, kosztów bezpośrednich, kosztów NEXUS, dochodu i straty dla każdego IP.

## Stan wydania

Docelowa macierz VCR obejmuje 46 scenariuszy dla siedmiu rodzin modeli, czyli dokładnie 322 kasety i 7 manifestów. Jej aktualność nie wynika z tekstu dokumentacji: fingerprinty wiążą kasety z algorytmem, scenariuszem, requestem, schemą i profilem modelu, a CI odrzuca stan niepełny lub nieaktualny.

PR jest gotowy do merge wyłącznie wtedy, gdy aktualny HEAD spełnia jednocześnie:

- 46/46 kaset dla każdego z siedmiu modeli, czyli dokładnie 322 aktualne nagrania i 7 manifestów;
- `python scripts/benchmark_report.py` zwraca `all_complete_and_valid=true`;
- `python scripts/vcr_precommit.py --all-models` przechodzi bez błędów;
- playback wszystkich modeli przechodzi bez `OPENROUTER_API_KEY`;
- CI na Pythonie 3.11–3.13 jest zielone, a job Python 3.13 wykonuje pełny playback offline;
- nie ma nierozwiązanych uwag do bieżącego HEAD;
- niezależny audyt wydaje werdykt `READY`.

Zmiana `ipbox_algorytm.md`, scenariusza, requestu, profilu modelu lub schema unieważnia odpowiednie fingerprinty. Takich kaset nie wolno poprawiać ręcznie — trzeba je usunąć i nagrać ponownie.
