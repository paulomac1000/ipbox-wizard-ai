# GPT-5 Mini w benchmarku wielomodelowym

`openai/gpt-5-mini` jest ósmym modelem w kanonicznej macierzy benchmarkowej. Nie ma osobnego trybu „candidate”: korzysta z tych samych scenariuszy, recorderów, manifestów, kontroli kosztu, walidacji i playbacku co pozostałe rodziny.

## Profil transportowy

- model OpenRouter: `openai/gpt-5-mini`;
- rodzina: `OpenAI GPT`;
- odpowiedź: strict `json_schema`;
- reasoning: `minimal`;
- `uniqueItems` jest usuwane przed transportem (identycznie jak Claude);
- temperatura nie jest wysyłana;
- slug kaset: `openai_gpt_5_mini`;
- wymagany komplet: 46 kaset oraz `_manifest.yaml`.

Profil znajduje się w `tests/llm/models.py` razem z pozostałymi modelami. Lista `BENCHMARK_MODELS` jest jedynym źródłem macierzy używanym przez recorder, politykę kaset, raport, playback i workflow.

Rejestr modeli nie należy do `engine_source_hash` silnika podatkowego. Każdy request nadal jest chroniony pełnym `request_hash`, który obejmuje model i wszystkie parametry transportowe. Dodanie nowego providera nie powinno samo w sobie unieważniać poprawnych kaset innych modeli.

## Kolejność dla tego brancha

Zmiana zakresu `engine_source_hash` jednorazowo zmienia tożsamość bieżącego silnika, dlatego istniejące 322 kasety wymagają bezpłatnego odświeżenia metadanych. Jednocześnie `--all-models` obejmuje już GPT-5 Mini, więc przed nagraniem brakujących kaset OpenAI pełne odświeżenie zatrzymałoby się na brakującym katalogu.

Prawidłowa kolejność jest następująca:

1. nagraj 46 brakujących kaset GPT-5 Mini standardowym recorderem;
2. usuń klucz API z procesu;
3. uruchom `refresh_vcr_metadata.py --all-models --write`, który zwaliduje surowe odpowiedzi i odświeży metadane wszystkich ośmiu rodzin;
4. wykonaj pełny pre-commit, raport i playback 368/368.

Nie edytuj ręcznie fingerprintów, hashy, manifestów ani `parsed_response`.

## Lokalne nagranie kaset

Przełącz się na branch i przygotuj środowisko zgodnie z `docs/testing.md`. Następnie uruchom standardowy recorder pojedynczego modelu:

```bash
LLM_PAID_RUN_CONFIRMATION=RUN_PAID_BENCHMARK \
python scripts/record_model.py \
  --model openai/gpt-5-mini \
  --max-cost-per-model-usd 5 \
  --max-total-cost-usd 5
```

Nie używaj osobnego wrappera. `scripts/record_model.py` musi obsługiwać GPT-5 Mini dokładnie tak samo jak każdy inny wpis z `BENCHMARK_MODELS`.

Recorder:

1. nie nadpisuje istniejącej kasety;
2. zapisuje kasetę dopiero po strict schema PASS i semantic PASS;
3. odrzuca substytucję modelu;
4. zapisuje każdą naliczoną, odrzuconą próbę w `VCR_REJECTED_ROOT`;
5. respektuje oba limity kosztów;
6. buduje manifest dla `openai/gpt-5-mini`.

## Odświeżenie i weryfikacja przed commitem

Po nagraniu usuń klucz API i odśwież metadane całej, już kompletnej macierzy:

```bash
unset OPENROUTER_API_KEY
python scripts/refresh_vcr_metadata.py --all-models --write
```

Następnie wykonaj standardową ścieżkę pojedynczego modelu:

```bash
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
4. wszystkie odpowiedzi przechodzą wspólną strict schema, parser, oracle i evaluator;
5. katalog nie zawiera sekretów, danych prywatnych ani odrzuconych prób;
6. playback przechodzi bez klucza API i bez sieci;
7. kompletna macierz osiąga 8 × 46, czyli 368/368 kaset.

45/46 jest wynikiem diagnostycznym, nie akceptacją. Nie ponawiaj błędu semantycznego do skutku i nie osłabiaj promptu, schemy ani evaluatora pod odpowiedź modelu.
