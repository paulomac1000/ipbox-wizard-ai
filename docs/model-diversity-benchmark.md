# Benchmark różnorodności modeli

## Cel

Macierz sprawdza, czy mała koperta `status/stops/reviews` jest jednoznaczna dla modeli pochodzących od różnych dostawców i rodzin. Nie prosi modeli o liczenie podatku. Python wyznacza pełną autorytatywną kopertę `expected_decision`, a model ma ją skopiować do czystego JSON.

Przejście wielu tanich i relatywnie małych modeli jest silniejszym dowodem przenośności niż przejście kilku modeli z jednej lub dwóch rodzin. **Nie jest to jednak gwarancja**, że każdy większy model, przyszła wersja providera lub inny endpoint zawsze zachowa się identycznie. Zmiana modelu, schematu, promptu lub routingu wymaga własnej kasety i playbacku.

## Kryteria doboru

Model trafia do macierzy, gdy na dzień 19 lipca 2026 r.:

1. reprezentuje odrębną rodzinę lub dostawcę;
2. jest tani w porównaniu z modelami frontier;
3. ma stabilny, jawny slug OpenRouter;
4. pozwala wymusić co najmniej obiekt JSON i przechodzi pełną lokalną walidację;
5. nie jest aliasem routera ani endpointem `:free` o zmiennej dostępności;
6. wykonuje ten sam kontrakt bez wyjątków scenariuszowych;
7. provider-specific adapter jest jawny, minimalny i objęty testem regresyjnym.

## Aktualna macierz 7 × 46

| Rodzina | Model OpenRouter | Transport |
|---|---|---|
| Google Gemini | `google/gemini-3-flash-preview` | strict `json_schema` |
| Anthropic Claude | `anthropic/claude-haiku-4.5` | `json_schema`; z kopii transportowej usuwane jest nieobsługiwane przez endpoint `uniqueItems` |
| DeepSeek | `deepseek/deepseek-chat-v3.1` | strict `json_schema` |
| MiniMax | `minimax/minimax-m2.5` | `json_object`; pełna schema jest nadal egzekwowana lokalnie |
| Moonshot Kimi | `moonshotai/kimi-k2.5` | strict `json_schema` |
| Qwen | `qwen/qwen3.5-flash-02-23` | strict `json_schema` |
| Mistral | `mistralai/mistral-small-24b-instruct-2501` | strict `json_schema` |

Łącznie wydanie wymaga **322 kaset** i siedmiu manifestów. Każdy model musi osiągnąć 46/46. Wynik częściowy jest wyłącznie diagnostyką.

## Granica adaptera transportowego

Provider nie jest źródłem kontraktu. Źródłem prawdy pozostają `DECISION_JSON_SCHEMA`, parser i evaluator działające lokalnie.

- Claude Haiku przez routing Anthropic/Azure/Bedrock odrzucał `uniqueItems` w przekazanym JSON Schema błędem HTTP 400. Adapter usuwa ten jeden keyword rekursywnie wyłącznie z głębokiej kopii wysyłanej do providera. Lokalna schema nadal wymaga unikalnych kodów.
- MiniMax przez routing DigitalOcean zwracał `content: null` dla `json_schema`. Profil używa więc `json_object`, a pełna schema jest dołączona do instrukcji i bezwarunkowo wykonywana po odpowiedzi.
- Parser nie usuwa Markdown fences, nie przenosi kodów między kanałami i nie deduplikuje odpowiedzi.
- Każda odpowiedź nadal musi mieć właściwy model, `finish_reason=stop`, zgodny fingerprint i pełny semantic PASS.

To są ograniczenia adapterów/providerów, a nie zmiany algorytmu podatkowego. Nie wolno rozszerzać ich na inne modele bez odtworzonego błędu transportowego i testu.

## Migawka cen OpenRouter

Ceny są informacyjne, za milion tokenów wejścia/wyjścia, według katalogu OpenRouter z 18 lipca 2026 r.; mogą się zmienić bez zmiany kodu:

| Model | Wejście USD/M | Wyjście USD/M |
|---|---:|---:|
| Gemini 3 Flash Preview | 0,50 | 3,00 |
| GPT-5 Nano | 0,05 | 0,40 |
| Claude Haiku 4.5 | 1,00 | 5,00 |
| DeepSeek V3.1 | 0,21 | 0,79 |
| MiniMax M2.5 | 0,15 | 0,90 |
| Kimi K2.5 | 0,375 | 2,025 |
| GLM 4.7 Flash | 0,06 | 0,40 |
| Qwen 3.5 Flash | 0,065 | 0,26 |
| Mistral Small 24B | 0,20 | 0,30 |

GPT-5 Nano i GLM pozostają w tabeli historycznej ceny, ale nie należą do wykonywalnej macierzy. Jedynym źródłem listy modeli jest `tests/llm/models.py`.

Krótki prompt i odpowiedź utrzymują realny koszt macierzy na niskim poziomie, lecz źródłem prawdy jest koszt zapisany w kasetach i raporcie po nagraniu.

## Wnioski z kolejnych macierzy

1. Pierwsza macierz pełnego raportu wykazała wymyślone kursy, klasyfikacje i TEST-y. Krytyczne obliczenia przeniesiono do Pythona.
2. Macierz 3 × 36 pozornie miała 108/108, ale wszystkie odpowiedzi Claude zawierały Markdown fences naprawiane przez parser. Naprawę usunięto i kasety unieważniono.
3. Protokół listy aktywnych reguł usunął nieaktywne fakty, lecz nadal wymagał klasyfikacji kodów do kanałów. MiniMax w scenariuszu 51 umieścił `REVIEW_09` w `stops`; podobny błąd wcześniej wykonał GPT-5 Nano. Zastąpiono go pełną kopertą `expected_decision` i oddzielnymi enumami STOP/REVIEW.
4. Ostatnie odrzucenia Claude i MiniMax nie dotyczyły rozumowania ani podatku. Były ograniczeniami transportu opisanymi powyżej.

Sama liczba „46/46” nie wystarcza bez audytu surowych odpowiedzi, request hashy, manifestów, fingerprintów, provider adapterów i zasad parsera.

## Źródła migawki modeli

- katalog OpenRouter i strona Gemini 3 Flash Preview;
- strony modelowe GPT-5 Nano i Claude Haiku 4.5;
- strony modelowe DeepSeek V3.1, MiniMax M2.5, Kimi K2.5 i GLM 4.7 Flash;
- strony modelowe Qwen 3.5 Flash i Ministral 3B.

Przed kolejnym nagraniem należy sprawdzić, czy slugi, ceny i obsługiwane parametry nadal są aktualne. Kod celowo nie wybiera modelu automatycznie na podstawie ceny, aby zmiana katalogu nie modyfikowała bramki bez review.
