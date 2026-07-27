# Dodanie rodziny OpenAI do benchmarku

Ten dokument opisuje kontrolowane dołączenie `openai/gpt-5-mini` jako ósmej rodziny modeli. Profil może być nagrywany już teraz, ale nie jest jeszcze częścią bramki wydania. Dzięki temu standardowe CI pozostaje zielone i README nie deklaruje pokrycia, którego repozytorium jeszcze nie posiada.

## Stan przygotowawczy

- model: `openai/gpt-5-mini`;
- rodzina: `OpenAI GPT`;
- transport: OpenRouter Chat Completions;
- odpowiedź: strict `json_schema`;
- reasoning: `minimal`;
- temperatura nie jest wysyłana;
- slug kaset: `openai_gpt_5_mini`;
- oczekiwany komplet: 46 kaset plus `_manifest.yaml`.

`MODEL_PROFILES` zawiera profil modelu, natomiast `BENCHMARK_MODELS` nadal obejmuje siedem rodzin z kompletnymi kasetami. Kandydat pozostaje w `CANDIDATE_MODELS`, dopóki nie przejdzie całej procedury poniżej.

## Nagranie przez GitHub Actions

Uruchom ręcznie workflow **Paid multi-model LLM benchmark** na branchu `feat/openai-model-family` z parametrami:

```text
confirmation: RUN_PAID_BENCHMARK
model: openai/gpt-5-mini
max-cost-per-model-usd: 5
max-total-cost-usd: 5
```

Workflow przed pierwszym płatnym wywołaniem uruchamia deterministyczne bramki jakości. Po nagraniu usuwa klucz API z procesu, odtwarza cały model offline i publikuje artefakt zawierający kasety, manifest, odpowiedzi diagnostyczne oraz odrzucone próby.

Nie uruchamiaj trybu `all` na tym etapie. `all` oznacza aktualną macierz wydania i celowo nie obejmuje kandydata.

## Weryfikacja artefaktu

Do repozytorium należy skopiować wyłącznie zaakceptowany katalog:

```text
tests/llm/vcr/cassettes/openai_gpt_5_mini/
```

Przed commitowaniem sprawdź:

1. istnieje dokładnie 46 kaset scenariuszy oraz `_manifest.yaml`;
2. manifest ma 46 wpisów i wskazuje `openai/gpt-5-mini` jako requested i returned model;
3. każda odpowiedź ma `finish_reason=stop` i przechodzi strict schema;
4. nie ma kluczy API, nagłówków autoryzacji, danych użytkownika ani plików z katalogu rejected;
5. koszt manifestu zgadza się z raportem workflow;
6. playback przechodzi bez `OPENROUTER_API_KEY` i bez dostępu do sieci.

## Komendy po zaimportowaniu kaset

```bash
unset OPENROUTER_API_KEY
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
LLM_PROVIDER=openrouter \
LLM_MODEL=openai/gpt-5-mini \
VCR_MODE=playback \
python -m pytest tests/llm/test_scenarios.py --run-llm --vcr-mode=playback -q

python scripts/vcr_precommit.py --model openai/gpt-5-mini
python scripts/benchmark_report.py --model openai/gpt-5-mini
```

## Promocja do bramki wydania

Dopiero po poprawnym imporcie i playbacku:

1. przenieś `openai/gpt-5-mini` z `CANDIDATE_MODELS` do `BENCHMARK_MODELS`;
2. zmień testy bramki z siedmiu na osiem niezależnych rodzin;
3. uruchom `./scripts/verify_all_models.sh` bez sekretu;
4. uruchom `python scripts/check_cassette_policy.py` i `python scripts/benchmark_report.py`;
5. zaktualizuj README i dokumentację z 322 do 368 kaset oraz z siedmiu do ośmiu rodzin;
6. dopiero wtedy uznaj `COVERED_DIRECTLY` za potwierdzone także przez rodzinę OpenAI.

Brak choć jednej poprawnej kasety, niezgodny model zwrócony przez dostawcę albo nieudany playback jest twardą granicą i blokuje promocję modelu do macierzy wydania.
