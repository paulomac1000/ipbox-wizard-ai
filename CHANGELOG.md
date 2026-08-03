# Changelog

Najważniejsze zmiany w kolejnych wydaniach projektu. Changelog opisuje możliwości produktu i istotne zmiany kontraktu, a nie historię wszystkich commitów.

## Unreleased

### Instrukcje agentów, dokumentacja i bezpieczeństwo CI

- Przebudowano `AGENTS.md` w kompaktowy router dla profilu safety-critical, rozdzielający analizę rozliczenia, rozwój repozytorium i audyt read-only oraz kierujący do kanonicznych właścicieli kontraktów.
- Dodano osobne, zarządzane zgodnie z AFDS procedury analizy dokumentów podatnika i rozwoju repozytorium, z jawnym ownership, weryfikacją, bezpiecznym zatrzymaniem i wpływem zmian.
- Adaptację `ci-cd-architect`, `afds-doc-writer` i `agents-md-architect` przypięto do niezmiennej rewizji upstream; Deterministic CI potwierdza jej SHA i uruchamia oryginalne upstreamowe validatory AGENTS.md oraz AFDS na ocenianym drzewie.
- GitHub Actions korzystają z pełnych SHA akcji, konkretnych obrazów runnerów, minimalnych uprawnień i checkoutu bez utrwalania poświadczeń; workflow pull requestu nie może odczytywać sekretów.
- Dodano wykonywalną politykę workflow, statyczny skan bezpieczeństwa, audyt podatności zależności runtime oraz regresje chroniące pin upstream, izolację validatorów i wymagany kontrakt zależności.
- Uporządkowano lokalne bramki `make quality`, `make test`, `make verify` i `make full`; płatny benchmark pozostaje oddzielony od bezpłatnej walidacji i wymaga jawnego potwierdzenia oraz limitów kosztu.

### Poprawność podatkowa

- Bieżąca strata z działalności kompensuje dochód IP opodatkowany zwykłą stawką (poza preferencją 5%); niewykorzystana część straty nie pomniejsza niezależnych dochodów ze skali (`extra_income_scale`).
- Wszystkie odliczenia (ZUS, IKZE, darowizny, ulgi, termomodernizacja) działają wyłącznie na nieujemnej podstawie — wprowadzono `max(0, ...)` przed każdym odliczeniem i na końcowej podstawie zwykłej.
- Każde dodatnie odliczenie wymaga pełnego rekordu weryfikacyjnego (`zweryfikowana: true`, niepusta `kategoria`, niepusty `dowod`). Brak dowodu odrzuca scenariusz fail-closed zamiast cichego obniżenia podatku.
- Flaga `source_ledger_included` oraz polskie aliasy (`ujęty_w_kpir`, `ujety_w_kpir`) mają jeden ścisły kontrakt boolean — jawne `null`, `0`, `"false"` i `"nie"` są odrzucane. Koszt oznaczony `false` nie jest doliczany do odtworzonego salda KPiR.

### Bezpieczeństwo płatnych testów LLM

- Bezpośrednie uruchomienie pytest w trybach `record` i `none` wymaga jawnej flagi potwierdzenia (`LLM_PAID_RUN_CONFIRMATION`) oraz dwóch skończonych, dodatnich limitów budżetowych.
- Dodano `PaidCostGuard` — strażnika kosztów śledzącego limity per-model i całkowity, księgującego koszt każdej odpowiedzi i blokującego kolejne żądania przed warstwą transportu po przekroczeniu.
- Koszt odpowiedzi z błędem HTTP (np. 500, 503) jest księgowany przed ponownym rzuceniem oryginalnego `HTTPError`. Nieparsowalne odpowiedzi (np. HTML przy 502) aktywują tryb fail-closed i blokują dalsze żądania.
- Limity budżetowe są propagowane z `record_model.py` do podprocesu pytest, tworząc dwie niezależne warstwy ochrony. Playback pozostaje bezpłatny.

### Kontrakt workflow i jakość

- Utwardzono testy workflow benchmarku: wymuszono hermetyczność środowiska testowego, ścisłą kolejność kroków (record → offline verification → upload → polityka kompletności), propagację kodów wyjścia oraz zakaz maskowania błędów przez `|| true`.
- Scentralizowano rozwiązywanie ścieżek VCR (`VCR_CASSETTES_ROOT`, `VCR_REJECTED_ROOT`) w `scripts/vcr_paths.py` z obsługą `.env` i scopes per użytkownik.
- Odświeżono metadane (fingerprinty, `engine_source_hash`, `code_revision`) kompletnej macierzy 368 kaset bez wykonywania nowych, płatnych zapytań do API.
- Usunięto nieużywany duplikat klienta (`tests/llm/client.py.orig`).

### Macierz benchmarkowa

- Rozszerzono kanoniczną macierz benchmarkową o rodzinę OpenAI przez `openai/gpt-5-mini`.
- Nagrano i zweryfikowano 46/46 kaset GPT-5 Mini; pełna macierz obejmuje obecnie 8 rodzin × 46 scenariuszy, czyli 368 kaset i osiem manifestów z playbackiem offline.
- GPT-5 Mini używa tego samego recordera, manifestu, pre-commit, raportu i playbacku co pozostałe modele — bez osobnego rejestru kandydatów ani alternatywnej bramki.
- Profil OpenAI używa strict `json_schema`, `reasoning.effort=minimal` i nie wysyła temperatury. Nieobsługiwane przez endpoint `uniqueItems` jest usuwane wyłącznie z kopii transportowej; lokalna schema nadal wymaga unikalnych kodów.
- Profile modeli oddzielono od `engine_source_hash` silnika podatkowego. Parametry każdego modelu pozostają chronione przez pełny `request_hash` jego kaset.
- Recorder respektuje `VCR_CASSETTES_ROOT` zarówno z procesu, jak i z bezpiecznie wczytanego lokalnego `.env`.
- Dodano instrukcję lokalnego nagrywania i code review przed dopuszczeniem nowej rodziny do wydania.

## 0.2 — 27 lipca 2026

Wydanie 0.2 przebudowuje projekt z instrukcji wspomaganej kodem w deterministyczny, testowalny silnik przygotowania danych do IP Box.

### Najważniejsze zmiany

- Python stał się źródłem prawdy dla arytmetyki, klasyfikacji, reguł rocznych oraz TEST 1–9. Model językowy obsługuje wyłącznie ograniczony kontrakt `status/stops/reviews`.
- Rozdzielono cztery niezależne decyzje: kwalifikację przychodu, współczynnik czasu `W`, alokację kosztów pośrednich `MIX` oraz NEXUS.
- Poprawiono wzór NEXUS do `min(1, ((A+B)×1,3)/(A+B+C+D))` i zachowano zwykłe opodatkowanie części dochodu IP nieobjętej preferencją.
- Dodano ścisłą walidację typów, kompletności danych i dowodów. Braki nie są zamieniane na korzystne wartości domyślne; wynik zatrzymuje się lub wymaga review.
- Zakodowano reguły podatkowe dla lat 2019–2026, w tym historyczne skale, IKZE, składkę zdrowotną, B+R oraz termomodernizację.
- Dodano audyt źródłowej KPiR, uzgodnienie ewidencji i zeznania oraz `correction_preview` pokazujący skutki korekty bez odblokowania niepewnego wyniku.
- Uporządkowano obsługę walut, kursów NBP, zaokrągleń do grosza, wieloprojektowości i wielu kwalifikowanych praw IP.
- Wprowadzono reprodukowalne `calculation_meta`, `engine_source_hash`, fingerprinty requestów i ściśle walidowane manifesty VCR.
- Rozszerzono benchmark do 46 syntetycznych scenariuszy uruchamianych na siedmiu rodzinach modeli — łącznie 322 kasety — z pełnym playbackiem offline.
- Zabezpieczono płatne nagrywanie przez jawne potwierdzenie, obowiązkowe limity kosztów i niezmienny rejestr każdej naliczonej, odrzuconej próby.
- Standardowy CI waliduje formatowanie, lint, kompilację, testy, coverage, politykę kaset i playback na Pythonie 3.11–3.13 bez wykonywania płatnych requestów.
- Dane regresyjne i przykłady zostały zastąpione danymi syntetycznymi.

### Zmiany kontraktu

- Pełny przebieg przyjmuje znormalizowany YAML/dict. Import surowych PDF, XLSX, KPiR i formularzy PIT pozostaje osobną warstwą poza zakresem wersji 0.2.
- Koszt bez jawnej klasyfikacji i dowodu nie staje się automatycznie kosztem IP.
- `STOP` zeruje finalne liczby i klasyfikacje; `REVIEW` sygnalizuje niepewność bez udawania wyniku finalnego.
- Zmiana kodu, scenariusza, schemy lub requestu może unieważnić kasety. Najpierw należy wykonać bezpłatne odświeżenie metadanych i playback; płatnie nagrywa się wyłącznie faktycznie nieaktualne kasety.

## 0.1 — 19 kwietnia 2026

Pierwsze wydanie było operacyjnym wizardem Markdown przeznaczonym do pracy z agentem AI podczas przygotowania rozliczenia IP Box programisty B2B.

### Zakres wydania

- Wielofazowa instrukcja `ipbox_algorytm.md` prowadząca od kwalifikacji prawa i zebrania danych do obliczeń, kontroli i przygotowania danych do formularza.
- Pomocniczy kalkulator Python dla współczynnika `W`, NEXUS, podstaw podatku, ulg i kontroli matematycznych.
- Obsługa podstawowych przypadków JDG na podatku liniowym i skali, kosztów IP/MIX/NIE, składek ZUS, ulg, faktur walutowych i różnic kursowych.
- Przykładowe prompty, struktura danych wejściowych oraz instrukcja użycia projektu z modelami językowymi.
- Początkowy zestaw testów jednostkowych i scenariuszy LLM/VCR chroniących najważniejsze obliczenia.

### Ograniczenia wydania

- Agent mógł uczestniczyć w interpretacji i arytmetyce, dlatego poprawność zależała w większym stopniu od modelu i ręcznej kontroli.
- Warstwy przychodu, `W`, `MIX` i NEXUS nie były jeszcze wystarczająco rozdzielone.
- Walidacja danych, odtwarzalność i procedura wydania były znacznie słabsze niż w wersji 0.2.
