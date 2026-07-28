# Benchmark różnorodności modeli

## Cel

Benchmark sprawdza, czy ograniczony kontrakt `status/stops/reviews` jest jednoznaczny dla modeli z różnych rodzin i od różnych dostawców.

Model nie liczy podatku i nie klasyfikuje reguł samodzielnie. Python wyznacza kompletną kopertę `expected_decision`, a model ma zwrócić jej dokładną reprezentację JSON. Dzięki temu macierz mierzy przenośność protokołu i przewidywalność integracji providera, a nie zdolność modelu do zastępowania silnika podatkowego.

Przejście wszystkich modeli nie gwarantuje poprawnego odczytu dowolnego PDF ani poprawności prawnej rozliczenia. Te granice nadal wymagają potwierdzenia danych źródłowych, deterministycznych testów i profesjonalnej oceny podatkowej.

## Aktualna macierz

| Rodzina | Model OpenRouter | Transport |
|---|---|---|
| Google Gemini | `google/gemini-3-flash-preview` | strict `json_schema` |
| Anthropic Claude | `anthropic/claude-haiku-4.5` | `json_schema`; `uniqueItems` usuwane wyłącznie z kopii transportowej |
| DeepSeek | `deepseek/deepseek-chat-v3.1` | strict `json_schema` |
| MiniMax | `minimax/minimax-m2.5` | `json_object`; pełna schema egzekwowana lokalnie |
| Moonshot Kimi | `moonshotai/kimi-k2.5` | strict `json_schema` |
| Qwen | `qwen/qwen3.5-flash-02-23` | strict `json_schema` |
| Mistral | `mistralai/mistral-small-24b-instruct-2501` | strict `json_schema` |
| OpenAI GPT | `openai/gpt-5-mini` | `json_schema`; `uniqueItems` usuwane z kopii transportowej, `reasoning.effort=minimal`, bez temperatury |

Bieżąca bramka obejmuje:

- 8 rodzin modeli;
- 46 scenariuszy na model;
- 368/368 kaset VCR;
- 8/8 manifestów;
- zero braków, osieroconych kaset i błędów integralności;
- pełny playback offline bez klucza API i bez połączenia z providerem.

Wynik 45/46 albo brak jednego manifestu oznacza diagnostykę, a nie zaliczenie.

## Kryteria przyjęcia modelu

Model może wejść do macierzy, gdy:

1. reprezentuje odrębną rodzinę lub dostawcę;
2. ma jawny, stabilny identyfikator providera;
3. jest rozsądny kosztowo względem celu benchmarku;
4. wykonuje ten sam kontrakt bez wyjątków scenariuszowych;
5. zwraca co najmniej obiekt JSON, który przechodzi wspólną lokalną walidację;
6. nie jest aliasem routera ani niestabilnym endpointem `:free`;
7. każdy wyjątek transportowy jest minimalny, jawny i chroniony testem regresyjnym;
8. przechodzi komplet 46 kaset, manifest, pre-commit, raport i playback offline.

## Granica adaptera transportowego

Provider nie jest źródłem kontraktu. Źródłem prawdy pozostają lokalne:

- `DECISION_JSON_SCHEMA`;
- parser;
- oracle;
- evaluator.

Dopuszczone wyjątki dotyczą wyłącznie transportu:

- **Claude Haiku** i **GPT-5 Mini** nie akceptują `uniqueItems` w transportowym JSON Schema. Keyword jest usuwany rekursywnie tylko z głębokiej kopii wysyłanej do providera. Lokalna schema nadal wymaga unikalnych kodów.
- **MiniMax** używa `json_object`, ponieważ jego routing zwracał pustą treść dla `json_schema`. Pełna schema nadal jest bezwarunkowo wykonywana po odpowiedzi.

Adapter nie może:

- zmieniać znaczenia STOP lub REVIEW;
- przenosić kodów między kanałami;
- deduplikować wyniku;
- usuwać Markdown fences;
- naprawiać brakujących pól;
- akceptować innego `returned_model`;
- omijać `finish_reason=stop`.

## Tożsamość kasety

`tests/llm/models.py` zawiera profile modeli, ale nie jest częścią `engine_source_hash` silnika podatkowego. Dodanie nowej rodziny nie powinno unieważniać kaset innych modeli.

Tożsamość konkretnego wywołania chroni `request_hash`, który obejmuje między innymi:

- model;
- prompt;
- schema transportową;
- reasoning;
- temperaturę;
- limit tokenów;
- pozostałe parametry requestu.

Zmiana profilu danego modelu zmienia `request_hash` i blokuje ponowne użycie starej kasety. Osobny test regresyjny potwierdza tę granicę dla GPT-5 Mini.

Formularz `workflow_dispatch` w `.github/workflows/llm-benchmark.yml` wymaga statycznej listy wyboru. Test `test_paid_workflow_model_allowlist_matches_canonical_registry` pilnuje, aby ta lista była identyczna i w tej samej kolejności co `BENCHMARK_MODELS`.

## Jedno drzewo kaset

`VCR_CASSETTES_ROOT` może wskazywać katalog domyślny w repozytorium albo jawnie wybrane drzewo robocze. Ścieżka jest wczytywana z procesu lub dozwolonego `.env`, sprawdzana jako niepusta i normalizowana do postaci absolutnej przed przekroczeniem granicy `cwd` lub subprocessu.

Recorder, odświeżanie metadanych, pre-commit, raport, polityka kaset oraz pełny playback muszą używać dokładnie tego samego drzewa. Żadne narzędzie następcze nie może po nagraniu do katalogu niestandardowego bez ostrzeżenia wrócić do kaset commitowanych w repozytorium. Narzędzia Python przyjmują także jawne `--cassette-root`, a skrypty macierzy eksportują jedną rozwiązaną wartość dla całego przebiegu.

`VCR_REJECTED_ROOT` podlega tej samej walidacji i normalizacji, aby skaner kosztów obejmował wszystkie naliczone, także odrzucone próby. Domyślny katalog tymczasowy jest rozdzielony per użytkownik, aby nie używać wspólnej przewidywalnej lokalizacji.

## Najważniejsze wnioski z regresji

Historia macierzy ujawniła problemy architektoniczne, których nie powinno się ponownie wprowadzać:

1. Model nie może obliczać kursów, NEXUS, klasyfikacji ani TEST 1–9 — krytyczne decyzje należą do Pythona.
2. Parser nie może naprawiać odpowiedzi, ponieważ pozorne 46/46 może ukrywać niespełniony kontrakt.
3. Model nie powinien ponownie przypisywać kodów do STOP i REVIEW. Scenariusz 51 ujawnił tę zbędną transformację; obecny protokół przekazuje gotową `expected_decision`.
4. Błąd transportowy providera nie jest powodem do osłabienia lokalnej schemy ani evaluatora.
5. Sama liczba kaset nie wystarcza bez zgodnych manifestów, fingerprintów, request hashy i playbacku bez sieci.

Syntetyczne scenariusze regresyjne są źródłem prawdy dla tych przypadków. Repozytorium nie przechowuje dokumentów ani danych rzeczywistych podatników.

## Zmiana lub dodanie modelu

1. Dodaj profil bezpośrednio do `MODEL_PROFILES`.
2. Zaktualizuj statyczną allowlistę workflow; test spójności musi przejść.
3. Dodaj test profilu, payloadu i granicy `request_hash`.
4. Użyj standardowego `scripts/record_model.py`; nie twórz osobnego wrappera.
5. Nagraj 46 kaset i sprawdź odrzucone próby oraz koszt.
6. Uruchom pre-commit i raport pojedynczego modelu.
7. Uruchom formatowanie, lint, kompilację oraz testy z pokryciem.
8. Uruchom politykę kaset i playback całej macierzy bez sekretu.
9. Dopiero po pełnym wyniku zaktualizuj dokumentację i deklarację pokrycia.

Procedurę operacyjną opisują [`docs/testing.md`](testing.md) oraz [`docs/openai-model-family.md`](openai-model-family.md).
