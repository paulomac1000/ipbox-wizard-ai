# Benchmark różnorodności modeli

## Cel

Macierz sprawdza, czy mała koperta `status/stops/reviews` jest jednoznaczna dla
modeli pochodzących od różnych dostawców i rodzin. Nie prosi modeli o liczenie
podatku. Python wcześniej wyznacza `active_rules`, a model ma skopiować ich kody
do ścisłego JSON.

Przejście wielu tanich i relatywnie małych modeli jest silniejszym dowodem
przenośności niż przejście kilku modeli z jednej lub dwóch rodzin. **Nie jest to
jednak gwarancja**, że każdy większy model, przyszła wersja providera lub inny
endpoint zawsze zachowa się identycznie. Zmiana modelu, schematu lub routingu nadal
wymaga własnej kasety i playbacku.

## Kryteria doboru

Model trafia do macierzy, gdy na dzień 18 lipca 2026 r.:

1. reprezentuje odrębną rodzinę lub dostawcę;
2. jest tani w porównaniu z modelami frontier;
3. ma stabilny, jawny slug OpenRouter;
4. deklaruje obsługę `response_format`/structured output;
5. nie jest aliasem routera ani endpointem `:free` o zmiennej dostępności;
6. wykonuje ten sam ścisły request bez specjalnych wyjątków scenariuszowych.

## Aktualna macierz 7 × 46

| Rodzina | Model OpenRouter | Rola w macierzy |
|---|---|---|
| Google Gemini | `google/gemini-3-flash-preview` | tańszy i starszy próg zamiast Gemini 3.5 |
| Anthropic Claude | `anthropic/claude-haiku-4.5` | mały model Claude |
| DeepSeek | `deepseek/deepseek-chat-v3.1` | otwarta rodzina DeepSeek V3 |
| MiniMax | `minimax/minimax-m2.5` | niezależna rodzina MoE |
| Moonshot Kimi | `moonshotai/kimi-k2.5` | niezależna rodzina Kimi |
| Qwen | `qwen/qwen3.5-flash-02-23` | tani model Flash Qwen |
| Mistral | `mistralai/ministral-3b-2512` | bardzo mały model 3B jako dolna granica |


Łącznie wydanie wymaga **322 kaset** i siedmiu manifestów. Każdy model musi
osiągnąć 46/46. Wynik częściowy jest wyłącznie diagnostyką.

## Migawka cen OpenRouter

Ceny są informacyjne, za milion tokenów wejścia/wyjścia, według katalogu
OpenRouter z 18 lipca 2026 r.; mogą się zmienić bez zmiany kodu:

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
| Ministral 3B | 0,10 | 0,10 |

Krótki prompt i odpowiedź sprawiają, że realny koszt pełnej macierzy powinien
pozostać niski, lecz jedynym źródłem prawdy jest koszt zapisany w kasetach i
raporcie po nagraniu.

## Wnioski z pierwszej macierzy

Pierwsze nagranie 3 × 36 kosztowało 0,071419 USD i pozornie miało 108/108.
Audyt surowych odpowiedzi wykazał jednak, że wszystkie 36 odpowiedzi Claude było
opakowanych w bloki Markdown rozpoczynające się od ` ```json `. Parser usuwał fences przed walidacją, więc
benchmark naprawiał odpowiedź modelu zamiast egzekwować kontrakt „pure JSON”.

Naprawa:

- parser nie usuwa już Markdown;
- wszystkie modele używają schema-based structured output;
- stare kasety usunięto, ponieważ nie spełniają nowego requestu;
- macierz rozszerzono do siedmiu rodzin.

To pokazuje, dlaczego sama liczba „36/36” nie wystarcza bez audytu surowych
odpowiedzi, request hashy, manifestów i zasad parsera.


## Źródła migawki modeli

- katalog OpenRouter i strona Gemini 3 Flash Preview;
- strony modelowe GPT-5 Nano i Claude Haiku 4.5;
- strony modelowe DeepSeek V3.1, MiniMax M2.5, Kimi K2.5 i GLM 4.7 Flash;
- strony modelowe Qwen 3.5 Flash i Ministral 3B.

Przed kolejnym nagraniem należy sprawdzić, czy slugi, ceny i obsługiwane
parametry nadal są aktualne. Kod celowo nie wybiera modelu automatycznie na
podstawie ceny, aby zmiana katalogu nie modyfikowała bramki bez review.
