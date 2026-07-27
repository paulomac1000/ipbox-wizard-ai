# Benchmark różnorodności modeli

## Cel

Macierz sprawdza, czy mała koperta `status/stops/reviews` jest jednoznaczna dla modeli pochodzących od różnych dostawców i rodzin. Nie prosi modeli o liczenie podatku. Python wyznacza pełną autorytatywną kopertę `expected_decision`, a model ma ją skopiować do czystego JSON.

Przejście wielu tanich i relatywnie małych modeli jest silniejszym dowodem przenośności niż przejście kilku modeli z jednej lub dwóch rodzin. **Nie jest to jednak gwarancja**, że każdy większy model, przyszła wersja providera lub inny endpoint zawsze zachowa się identycznie. Zmiana modelu, schematu, promptu lub routingu wymaga własnej kasety i playbacku.

## Kryteria doboru

Model trafia do macierzy, gdy:

1. reprezentuje odrębną rodzinę lub dostawcę;
2. jest rozsądny kosztowo względem modeli frontier;
3. ma stabilny, jawny slug OpenRouter;
4. pozwala wymusić co najmniej obiekt JSON i przechodzi pełną lokalną walidację;
5. nie jest aliasem routera ani endpointem `:free` o zmiennej dostępności;
6. wykonuje ten sam kontrakt bez wyjątków scenariuszowych;
7. provider-specific adapter jest jawny, minimalny i objęty testem regresyjnym.

## Macierz 8 × 46

| Rodzina | Model OpenRouter | Transport |
|---|---|---|
| Google Gemini | `google/gemini-3-flash-preview` | strict `json_schema` |
| Anthropic Claude | `anthropic/claude-haiku-4.5` | `json_schema`; z kopii transportowej usuwane jest nieobsługiwane przez endpoint `uniqueItems` |
| DeepSeek | `deepseek/deepseek-chat-v3.1` | strict `json_schema` |
| MiniMax | `minimax/minimax-m2.5` | `json_object`; pełna schema jest nadal egzekwowana lokalnie |
| Moonshot Kimi | `moonshotai/kimi-k2.5` | strict `json_schema` |
| Qwen | `qwen/qwen3.5-flash-02-23` | strict `json_schema` |
| Mistral | `mistralai/mistral-small-24b-instruct-2501` | strict `json_schema` |
| OpenAI GPT | `openai/gpt-5-mini` | strict `json_schema`, `reasoning.effort=minimal`, bez temperatury |

Pełna bramka wymaga **368 kaset** i ośmiu manifestów. Każdy model musi osiągnąć 46/46. Wynik częściowy jest wyłącznie diagnostyką.

## Granica adaptera transportowego

Provider nie jest źródłem kontraktu. Źródłem prawdy pozostają `DECISION_JSON_SCHEMA`, parser i evaluator działające lokalnie.

- Claude Haiku przez routing Anthropic/Azure/Bedrock odrzucał `uniqueItems` w przekazanym JSON Schema błędem HTTP 400. Adapter usuwa ten jeden keyword rekursywnie wyłącznie z głębokiej kopii wysyłanej do providera. Lokalna schema nadal wymaga unikalnych kodów.
- MiniMax przez routing DigitalOcean zwracał `content: null` dla `json_schema`. Profil używa więc `json_object`, a pełna schema jest dołączona do instrukcji i bezwarunkowo wykonywana po odpowiedzi.
- GPT-5 Mini używa wspólnego strict `json_schema`; parametr temperatury nie jest wysyłany, a poziom rozumowania jest jawnie ustawiony na `minimal`.
- Parser nie usuwa Markdown fences, nie przenosi kodów między kanałami i nie deduplikuje odpowiedzi.
- Każda odpowiedź nadal musi mieć właściwy model, `finish_reason=stop`, zgodny fingerprint i pełny semantic PASS.

To są ograniczenia adapterów/providerów, a nie zmiany algorytmu podatkowego. Nie wolno rozszerzać ich na inne modele bez odtworzonego błędu transportowego i testu.

## Tożsamość i odtwarzalność

Lista modeli i ich profile znajdują się w `tests/llm/models.py`. Rejestr modeli nie jest częścią `engine_source_hash` silnika podatkowego: pełny model, schema transportowa, reasoning, temperatura i pozostałe parametry należą do `request_hash` konkretnej kasety.

Dzięki temu dodanie nowej rodziny nie unieważnia automatycznie odpowiedzi innych rodzin, ale każda zmiana profilu danego modelu nadal unieważnia jego kasety.

## Wnioski z kolejnych macierzy

1. Pierwsza macierz pełnego raportu wykazała wymyślone kursy, klasyfikacje i TEST-y. Krytyczne obliczenia przeniesiono do Pythona.
2. Macierz 3 × 36 pozornie miała 108/108, ale wszystkie odpowiedzi Claude zawierały Markdown fences naprawiane przez parser. Naprawę usunięto i kasety unieważniono.
3. Protokół listy aktywnych reguł usunął nieaktywne fakty, lecz nadal wymagał klasyfikacji kodów do kanałów. MiniMax w scenariuszu 51 umieścił `REVIEW_09` w `stops`; podobny błąd wcześniej wykonał GPT-5 Nano. Zastąpiono go pełną kopertą `expected_decision` i oddzielnymi enumami STOP/REVIEW.
4. Odrzucenia Claude i MiniMax nie dotyczyły rozumowania ani podatku. Były ograniczeniami transportu opisanymi powyżej.

Sama liczba „46/46” nie wystarcza bez audytu surowych odpowiedzi, request hashy, manifestów, fingerprintów, provider adapterów i zasad parsera.

## Przed nagraniem

Przed kolejnym nagraniem sprawdź aktualność slugów i obsługiwanych parametrów. Kod celowo nie wybiera modelu automatycznie na podstawie ceny, aby zmiana katalogu nie modyfikowała bramki bez review. Procedurę lokalnego nagrania opisują `docs/testing.md` i `docs/openai-model-family.md`.
