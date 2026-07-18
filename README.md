# ipbox-wizard-ai

Deterministyczny-first wizard wspierający przygotowanie danych do rozliczenia IP Box programisty B2B.

> To nie jest porada podatkowa ani generator gotowego zeznania. Wynik wymaga sprawdzenia z księgową lub doradcą. Audyt techniczny i semantyczny wykonano 18 lipca 2026 r.; reguły podatkowe są jawnie wersjonowane dla wszystkich lat obowiązywania IP Box 2019–2026.

## Architektura

Model językowy nie wykonuje krytycznej arytmetyki:

1. `python_helper/ipbox_calculator.py`, `tax_year_rules.py` i `allocation_audit.py` walidują dane, liczą W, alokacje, NEXUS, reguły roczne, ulgi i podatek.
2. `tests/llm/oracle_v2.py` tworzy niezależny wynik referencyjny i atomowe `decision_facts`.
3. Python składa kompletną autorytatywną kopertę `expected_decision` z rozdzielonymi kanałami STOP i REVIEW.
4. LLM kopiuje bez zmian `status/stops/reviews`; nie klasyfikuje kodów i nie widzi faktów podatkowych ani nazw predykatów.
5. Runner składa kopertę z raportem deterministycznym.
6. Evaluator i JSON Schema porównują wynik fail-closed.
7. VCR zapisuje tylko odpowiedź, która przeszła schema, semantykę i ponowne parsowanie.

Najważniejszy invariant z issue #1: **przychód IP/NIE, alokacja kosztów pośrednich `MIX` i klasyfikacja NEXUS są trzema niezależnymi decyzjami**. Współczynnik czasu `W` nie jest domyślnym kluczem `MIX`.

## Twarde reguły

- NEXUS: `min(1, ((A+B) × 1,3) / (A+B+C+D))`.
- Brak kosztów A/B/C/D daje NEXUS `0`, nie `1`.
- Koszt bez dowodu wyłącznego związku nie staje się automatycznie `IP`.
- Niesklasyfikowany zakup powyżej 10 000 zł jest `WYKLUCZONE` do czasu wprowadzenia udokumentowanego odpisu lub amortyzacji.
- Zwykłe darowizny, ulga internetowa, rehabilitacyjna i na dziecko są odrzucane dla podatku liniowego.
- Ulga B+R jest rozdzielana jawnie na `ulga_BR_IP` i `ulga_BR_NIE`; część IP pomniejsza dochód kwalifikowany przed NEXUS.
- `strata_NIE_z_lat_poprzednich` dotyczy wyłącznie pozostałej działalności. Straty kwalifikowanego IP wymagają osobnej ewidencji per IP.
- Działalność na skali łączy `dochody_dodatkowe_skala` z pozostałym dochodem skali i liczy pełny podatek od wspólnej podstawy.
- Działalność liniowa i dodatkowe dochody na skali wymagają dwóch odrębnych kaskad/zeznań; oracle odmawia ich mieszania.
- Limity zdrowotnej i IKZE są wersjonowane per rok; nieznany rok z dodatnim odliczeniem kończy się błędem.
- Miesiąc musi mieć ścisły format `YYYY-MM` i rok zgodny z `input.rok`.
- Pula ulgi termomodernizacyjnej nie może przekroczyć 53 000 zł na podatnika.
- Odpowiedź z modelem innym niż żądany jest odrzucana podczas live runu, playbacku i pre-commit.
- Brak kursu, daty płatności, dowodu kwalifikacji lub ujemna faktura jest błędem danych, nie wartością zero.

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

Stan po rozszerzeniu regresji: co najmniej **255 testów jednostkowych PASS**, coverage `python_helper` powyżej wymaganych **90%**; pełny bezpłatny suite i 46 kontrolowanych przypadków LLM przechodzą na Pythonie 3.11–3.13. Dokładne wartości raportuje CI.

## Benchmark wielorodzinny

Benchmark używa siedmiu modeli z siedmiu niezależnych rodzin:

| Rodzina | Model OpenRouter | Rola w macierzy |
|---|---|---|
| Google Gemini | `google/gemini-3-flash-preview` | tańszy i starszy próg zamiast Gemini 3.5 |
| Anthropic Claude | `anthropic/claude-haiku-4.5` | mały model Claude |
| DeepSeek | `deepseek/deepseek-chat-v3.1` | otwarta rodzina DeepSeek V3 |
| MiniMax | `minimax/minimax-m2.5` | niezależna rodzina MoE |
| Moonshot Kimi | `moonshotai/kimi-k2.5` | niezależna rodzina Kimi |
| Qwen | `qwen/qwen3.5-flash-02-23` | tani model Flash Qwen |
| Mistral | `mistralai/ministral-3b-2512` | bardzo mały model 3B jako dolna granica |

To jest **test przenośności protokołu**, nie dowód poprawności podatkowej i nie
matematyczna gwarancja zachowania każdego mocniejszego modelu. Jeżeli małe modele
różnych dostawców przechodzą identyczny ścisły kontrakt bez naprawiania odpowiedzi,
to rośnie wiarygodność, że zadanie jest jednoznaczne i niezależne od jednej rodziny.
Prawdą podatkową nadal pozostają Python, oracle i testy deterministyczne.

Nagrywanie jest jawne i płatne:

```bash
export OPENROUTER_API_KEY='...'
./scripts/record_all_models.sh --max-cost-usd 5
```

Pełna procedura: [`docs/testing.md`](docs/testing.md). Dobór modeli i ograniczenia
wnioskowania: [`docs/model-diversity-benchmark.md`](docs/model-diversity-benchmark.md).
Niezależny audyt: [`docs/independent-audit-brief.md`](docs/independent-audit-brief.md).

## Zakres multi-IP

`allocate_multi_ip()` wykonuje dwustopniowy podział wspólnych kosztów z zachowaniem groszy. Nie zastępuje pełnej ewidencji PIT/IP dla każdego kwalifikowanego prawa. Finalne rozliczenie wielu IP wymaga osobnych przychodów, kosztów bezpośrednich, kosztów NEXUS, dochodu i straty dla każdego IP.

## Stan wydania

Rdzeń deterministyczny jest po audycie. Diagnostyczna macierz 317/322 ujawniła, że MiniMax w scenariuszu 51 przeniósł `REVIEW_09` do `stops`; ten sam błąd wcześniej wykonał GPT-5 Nano. Podatek i oracle były poprawne, lecz protokół wymagał zbędnej transformacji listy `{kind, code}`, a schema nie rozróżniała kanałów. Protokół zastąpiono autorytatywną kopertą `expected_decision`, schema ma osobne enumy STOP/REVIEW, a wszystkie stare kasety usunięto. Przed review trzeba nagrać od zera 322 odpowiedzi. PR pozostaje **draftem**.

Warunki zakończenia:

- 46/46 kaset dla każdego z siedmiu modeli, czyli 322 aktualne nagrania;
- playback bez `OPENROUTER_API_KEY`;
- ręczny przegląd odpowiedzi, odrzuceń i raportu kosztu;
- niezależny raport `READY` bez nierozwiązanych uwag;
- ponowna weryfikacja źródeł przy zmianie roku lub zakresu podatkowego.
