# GPT-5 Mini w benchmarku wielomodelowym

`openai/gpt-5-mini` jest ósmym modelem w kanonicznej macierzy benchmarkowej. Nie ma osobnego trybu „candidate”: korzysta z tych samych scenariuszy, recorderów, manifestów, kontroli kosztu, walidacji i playbacku co pozostałe rodziny.

## Stan potwierdzony

Aktualny zestaw został nagrany i zweryfikowany:

- 46/46 zaakceptowanych kaset GPT-5 Mini;
- koszt nagrania: `$0.009166`;
- zero odrzuconych prób;
- `requested_model == returned_model == openai/gpt-5-mini` we wszystkich kasetach;
- `finish_reason=stop` we wszystkich kasetach;
- pełny playback OpenAI przechodzi offline;
- kompletna macierz osiąga 8 × 46, czyli 368/368 kaset i osiem manifestów;
- polityka kaset, pre-commit, raport benchmarku i CI Python 3.11–3.13 przechodzą.

Kasety potwierdzają wykonanie ograniczonego kontraktu `status/stops/reviews` w 46 scenariuszach. Nie dowodzą samodzielnie poprawności ekstrakcji dowolnego dokumentu ani interpretacji prawnej — krytyczne obliczenia i klasyfikacje nadal ustala Python.

## Profil transportowy

- model OpenRouter: `openai/gpt-5-mini`;
- rodzina: `OpenAI GPT`;
- odpowiedź: strict `json_schema`;
- reasoning: `minimal`;
- `uniqueItems` jest usuwane przed transportem;
- temperatura nie jest wysyłana;
- slug kaset: `openai_gpt_5_mini`;
- wymagany komplet: 46 kaset oraz `_manifest.yaml`.

OpenAI, podobnie jak bieżący routing Claude, odrzuca `uniqueItems` w transportowym JSON Schema. Adapter usuwa ten keyword rekursywnie wyłącznie z głębokiej kopii wysyłanej do providera. Kanoniczna lokalna `DECISION_JSON_SCHEMA`, parser i evaluator nadal wymagają unikalnych kodów. Test profilu sprawdza obie strony tej granicy.

Profil znajduje się w `tests/llm/models.py` razem z pozostałymi modelami. `BENCHMARK_MODELS` jest kanonicznym źródłem wykonawczym dla recordera, polityki kaset, raportu i playbacku. Formularz `workflow_dispatch` w `.github/workflows/llm-benchmark.yml` ma osobną statyczną allowlistę wymaganą przez GitHub Actions; test `test_paid_workflow_model_allowlist_matches_canonical_registry` wymusza jej identyczność i kolejność względem `BENCHMARK_MODELS`.

Rejestr modeli nie należy do `engine_source_hash` silnika podatkowego. Każdy request nadal jest chroniony pełnym `request_hash`, który obejmuje model i wszystkie parametry transportowe. Test regresyjny potwierdza, że zmiana profilu GPT-5 Mini zmienia `request_hash`, nawet gdy hash silnika podatkowego pozostaje bez zmian. Dodanie nowego providera nie powinno samo w sobie unieważniać poprawnych kaset innych modeli.

## Jednorazowa migracja wykonana przy dodaniu modelu

Przy dodawaniu GPT-5 Mini zmiana zakresu `engine_source_hash` jednorazowo zmieniła tożsamość bieżącego silnika. Wykonano następującą kolejność:

1. nagrano 46 brakujących kaset GPT-5 Mini standardowym recorderem;
2. usunięto klucz API z procesu;
3. uruchomiono `refresh_vcr_metadata.py --all-models --write`;
4. ponownie zwalidowano surowe odpowiedzi i odświeżono metadane 322 istniejących kaset;
5. wykonano pełny pre-commit, raport i playback 368/368.

W starych kasetach zmieniły się wyłącznie kontrolowane metadane, fingerprinty i ponownie złożony wynik. Surowe odpowiedzi modeli nie zostały przepisane ani ponownie nagrane.

## Lokalne nagranie lub odtworzenie

Standardowy recorder pojedynczego modelu:

```bash
LLM_PAID_RUN_CONFIRMATION=RUN_PAID_BENCHMARK \
python scripts/record_model.py \
  --model openai/gpt-5-mini \
  --max-cost-per-model-usd 5 \
  --max-total-cost-usd 5
```

Nie używaj osobnego wrappera. `scripts/record_model.py` obsługuje GPT-5 Mini dokładnie tak samo jak każdy inny wpis z `BENCHMARK_MODELS`.

Recorder:

1. nie nadpisuje istniejącej kasety;
2. zapisuje kasetę dopiero po strict schema PASS i semantic PASS;
3. odrzuca substytucję modelu;
4. zapisuje każdą naliczoną, odrzuconą próbę w `VCR_REJECTED_ROOT`;
5. respektuje oba limity kosztów;
6. buduje manifest dla `openai/gpt-5-mini`;
7. respektuje `VCR_CASSETTES_ROOT` i `VCR_REJECTED_ROOT` z procesu albo bezpiecznie wczytanego `.env`;
8. normalizuje obie ścieżki do wartości absolutnych przed uruchomieniem pytest, dzięki czemu subprocess i skanowanie kosztów zawsze używają tych samych katalogów.

## Weryfikacja przed commitem

```bash
unset OPENROUTER_API_KEY

PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
LLM_PROVIDER=openrouter \
LLM_MODEL=openai/gpt-5-mini \
VCR_MODE=playback \
python -m pytest tests/llm/test_scenarios.py \
  --run-llm \
  --vcr-mode=playback \
  --llm-model openai/gpt-5-mini \
  -q

python scripts/vcr_precommit.py --model openai/gpt-5-mini
python scripts/benchmark_report.py --model openai/gpt-5-mini
```

Na końcu sprawdź całą macierz:

```bash
python scripts/check_cassette_policy.py
python scripts/vcr_precommit.py --all-models
python scripts/benchmark_report.py
unset OPENROUTER_API_KEY
./scripts/verify_all_models.sh
```

## Twarda bramka

Model i PR zaliczają dopiero, gdy jednocześnie:

1. istnieje dokładnie 46 kaset OpenAI i kompletny manifest;
2. każda kaseta ma `requested_model` oraz `returned_model` równe `openai/gpt-5-mini`;
3. każda odpowiedź ma `finish_reason=stop`;
4. wszystkie odpowiedzi przechodzą wspólną lokalną strict schema, parser, oracle i evaluator;
5. katalog nie zawiera sekretów, danych prywatnych ani odrzuconych prób;
6. playback przechodzi bez klucza API i bez sieci;
7. kompletna macierz osiąga 8 × 46, czyli 368/368 kaset.

45/46 jest wynikiem diagnostycznym, nie akceptacją. Nie ponawiaj błędu semantycznego do skutku i nie osłabiaj promptu, schemy ani evaluatora pod odpowiedź modelu.
