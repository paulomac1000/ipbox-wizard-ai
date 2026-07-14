# ipbox-wizard-ai

Eksperymentalny, deterministyczny-first wizard wspierający przygotowanie rozliczenia IP Box dla programisty B2B.

> To nie jest porada podatkowa. Wynik wymaga sprawdzenia z księgową lub doradcą oraz potwierdzenia reguł zależnych od roku.

## Dlaczego ta architektura

Model językowy nie powinien wykonywać krytycznej arytmetyki podatkowej „w głowie”. System dzieli odpowiedzialność:

1. `python_helper/ipbox_calculator.py` — walidacja, alokacje, NEXUS, zaokrąglenia i podatek;
2. `tests/llm/oracle.py` — deterministyczny scenariuszowy oracle używany wyłącznie przez harness testowy;
3. LLM — zastosowanie instrukcji, kodów STOP/REVIEW i wygenerowanie strict JSON na podstawie wyniku narzędzia;
4. `tests/llm/evaluator.py` — fail-closed porównanie z oracle;
5. VCR — zapisuje tylko odpowiedź, która przeszła schemat i semantykę.

Najważniejszy invariant z issue #1: **alokacja przychodu, kosztów MIX i NEXUS to trzy oddzielne decyzje**. Miesięczne W nie jest domyślnym kluczem MIX.

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
```

`pytest -q` pomija 36 płatnych testów LLM. Standardowy CI jest całkowicie offline.

## Benchmark multi-model

Macierz jest celowo ograniczona do jednego ekonomicznego modelu od każdego dostawcy:

| Dostawca | Model OpenRouter | Rola |
|---|---|---|
| Google | `google/gemini-3.5-flash` | referencyjny Flash, minimal reasoning |
| OpenAI | `openai/gpt-5-mini` | tani, ale wyraźnie mocniejszy od Nano w złożonym instruction following |
| Anthropic | `anthropic/claude-haiku-4.5` | najtańszy aktualny Claude w tej klasie |

Nie używamy `gpt-5-nano` jako bramki produkcyjnej: oszczędność pojedynczego pełnego runu jest mała wobec kosztu diagnozowania niestabilnych odpowiedzi. Nie używamy Gemini 3.1 Flash Lite jako modelu referencyjnego, bo benchmark obejmuje złożone reguły i strict JSON.

Nagrywanie jest jawne i płatne:

```bash
export OPENROUTER_API_KEY='...'
# Soft budget guard per model; the script still records all models sequentially.
./scripts/record_all_models.sh --max-cost-usd 5
```

Szczegóły: [`docs/testing.md`](docs/testing.md).

## Struktura

- `ipbox_algorytm.md` — instrukcja operacyjna dla modelu;
- `python_helper/` — deterministyczny kalkulator;
- `tests/llm/scenarios/` — 36 znormalizowanych przypadków;
- `tests/llm/output_schema.py` — wspólny strict JSON Schema;
- `tests/llm/vcr/` — model-specific, fail-closed cassettes;
- `scripts/record_model.py` — wznawialne nagrywanie z walidacją istniejących kaset i miękkim limitem kosztu;
- `scripts/check_cassette_policy.py` — blokuje commit częściowej lub nieaktualnej macierzy kaset;
- `.github/workflows/full-suite.yml` — bezpłatny CI;
- `.github/workflows/llm-benchmark.yml` — ręczny, płatny benchmark.

## Stan wydań

Projekt pozostaje pre-release. Gotowość do wydania wymaga:

- zielonych testów deterministycznych;
- 36/36 zweryfikowanych kaset dla każdego modelu bramkowego;
- playbacku bez klucza API;
- ręcznego przeglądu odpowiedzi i kaset;
- weryfikacji reguł podatkowych dla obsługiwanego roku.
