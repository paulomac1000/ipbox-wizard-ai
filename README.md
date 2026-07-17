# ipbox-wizard-ai

Deterministyczny-first wizard wspierający przygotowanie danych do rozliczenia IP Box programisty B2B.

> To nie jest porada podatkowa ani generator gotowego zeznania. Wynik wymaga sprawdzenia z księgową lub doradcą. Audyt techniczny i prawny wykonano 17 lipca 2026 r.; scenariusze referencyjne dotyczą 2025 r., a zakodowane limity 2026 są jawnie wersjonowane.

## Architektura

Model językowy nie wykonuje krytycznej arytmetyki:

1. `python_helper/ipbox_calculator.py` waliduje dane i liczy W, alokacje, NEXUS, ulgi, podatek oraz zaokrąglenia.
2. `tests/llm/oracle.py` tworzy niezależny wynik referencyjny i atomowe `decision_facts`.
3. Runner usuwa wszystkie fakty `false` i przekazuje modelowi wyłącznie aktywne reguły z gotowym kodem STOP/REVIEW.
4. LLM kopiuje kody aktywnych reguł do małej koperty `status/stops/reviews`; nie widzi reguł nieaktywnych.
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

Stan po audycie protokołu: **167 testów PASS**, coverage `python_helper` **95,30%**; pełny bezpłatny suite: **167 PASS i 36 kontrolowanych skipów LLM**.

## Benchmark multi-model

| Dostawca | Model OpenRouter |
|---|---|
| Google | `google/gemini-3.5-flash` |
| OpenAI | `openai/gpt-5-mini` |
| Anthropic | `anthropic/claude-haiku-4.5` |

Nagrywanie jest jawne i płatne:

```bash
export OPENROUTER_API_KEY='...'
./scripts/record_all_models.sh --max-cost-usd 5
```

Pełna procedura: [`docs/testing.md`](docs/testing.md). Niezależny audyt: [`docs/independent-audit-brief.md`](docs/independent-audit-brief.md).

## Zakres multi-IP

`allocate_multi_ip()` wykonuje dwustopniowy podział wspólnych kosztów z zachowaniem groszy. Nie zastępuje pełnej ewidencji PIT/IP dla każdego kwalifikowanego prawa. Finalne rozliczenie wielu IP wymaga osobnych przychodów, kosztów bezpośrednich, kosztów NEXUS, dochodu i straty dla każdego IP.

## Stan wydania

Rdzeń deterministyczny i protokół `active_rules` są po audycie. PR pozostaje **draftem**, ponieważ aktualny kontrakt nie ma jeszcze kompletnej macierzy kaset.

Warunki zakończenia:

- 36/36 kaset dla każdego z trzech modeli, czyli 108 aktualnych nagrań;
- playback bez `OPENROUTER_API_KEY`;
- ręczny przegląd odpowiedzi, odrzuceń i raportu kosztu;
- niezależny raport `READY` bez nierozwiązanych uwag;
- ponowna weryfikacja źródeł przy zmianie roku lub zakresu podatkowego.
