# Changelog

Najważniejsze zmiany w kolejnych wydaniach projektu. Changelog opisuje możliwości produktu i istotne zmiany kontraktu, a nie historię wszystkich commitów.

## 0.2 — deterministyczny silnik i audytowalny benchmark

Wersja rozwijana w PR #2 przebudowuje projekt z instrukcji wspomaganej kodem w deterministyczny, testowalny silnik przygotowania danych do IP Box.

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

## 0.1 — wydanie początkowe

Pierwsza wersja była operacyjnym wizardem Markdown przeznaczonym do pracy z agentem AI podczas przygotowania rozliczenia IP Box programisty B2B.

### Zakres wydania

- Wielofazowa instrukcja `ipbox_algorytm.md` prowadząca od kwalifikacji prawa i zebrania danych do obliczeń, kontroli i przygotowania danych do formularza.
- Pomocniczy kalkulator Python dla współczynnika `W`, NEXUS, podstaw podatku, ulg i kontroli matematycznych.
- Obsługa podstawowych przypadków JDG na podatku liniowym i skali, kosztów IP/MIX/NIE, składek ZUS, ulg, faktur walutowych i różnic kursowych.
- Przykładowe prompty, struktura danych wejściowych oraz instrukcja użycia projektu z popularnymi modelami językowymi.
- Początkowy zestaw testów jednostkowych i scenariuszy LLM/VCR chroniących najważniejsze obliczenia.

### Ograniczenia wydania

- Agent mógł uczestniczyć w interpretacji i arytmetyce, dlatego poprawność zależała w większym stopniu od modelu i ręcznej kontroli.
- Warstwy przychodu, `W`, `MIX` i NEXUS nie były jeszcze wystarczająco rozdzielone.
- Walidacja danych, odtwarzalność i procedura wydania były znacznie słabsze niż w wersji 0.2.
