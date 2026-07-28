# AGENTS.md

Instrukcja dla agentów pracujących z repozytorium `ipbox-wizard-ai`.

Najpierw ustal, **w jakim trybie pracujesz**. Ten sam projekt służy do analizy dokumentów podatnika oraz do rozwoju kodu. Nie mieszaj tych zadań bez wyraźnego polecenia użytkownika.

## Tryb 1: analiza rozliczenia użytkownika

Wybierz ten tryb, gdy użytkownik przekazał dokumenty, archiwum ZIP albo link do repozytorium i chce przygotować lub sprawdzić rozliczenie IP Box.

### Kolejność pracy

1. Przeczytaj `README.md` i `ipbox_algorytm.md`.
2. Zinwentaryzuj wszystkie dokumenty użytkownika.
3. Samodzielnie odczytaj PDF, XLSX, CSV i inne załączniki.
4. Przy każdej istotnej wartości wskaż dokument, stronę, arkusz albo wiersz źródłowy.
5. Pokaż użytkownikowi wyekstrahowane dane przed finalnym obliczeniem.
6. Zapytaj o braki. Brak danych nie jest zerem ani korzystnym założeniem.
7. Przygotuj znormalizowane dane robocze wewnętrznie — użytkownik nie musi pisać YAML-a.
8. Wykonaj krytyczne obliczenia kodem z `python_helper/`, nie w pamięci modelu.
9. Porównaj wynik z KPiR, ewidencją IP Box i formularzami PIT.
10. Oddziel błąd dokumentu, brak danych, decyzję podatkową i możliwy błąd algorytmu.
11. Nie zmieniaj kodu, testów ani historii Git, chyba że użytkownik wyraźnie zleci rozwój projektu.
12. Nie zapisuj prywatnych dokumentów ani danych podatnika w repozytorium.

### Raport pokrycia konkretnego przypadku

Na końcu analizy podaj dokładnie jeden status:

```text
COVERED_DIRECTLY | COVERED_PARTIALLY | NOT_COVERED
```

Następnie wskaż:

- testy jednostkowe chroniące istotne reguły;
- scenariusze z `tests/llm/scenarios/` odtwarzające tę samą ścieżkę biznesową;
- elementy przypadku bez bezpośredniego odpowiednika;
- stan kompletności kaset dla wszystkich modeli z `BENCHMARK_MODELS`;
- wynik playbacku offline.

`COVERED_DIRECTLY` wolno zadeklarować wyłącznie wtedy, gdy łącznie:

1. przypadek ma bezpośredni scenariusz biznesowy;
2. scenariusz sprawdza ten sam istotny invariant;
3. kasety wszystkich modeli wymaganych przez bieżącą macierz są kompletne i aktualne;
4. playback przechodzi bez sekretu i bez sieci.

Nie twierdź, że „dokładnie ten przypadek został potwierdzony przez wszystkie rodziny AI”, jeżeli znalazłeś tylko podobny test albo częściowe pokrycie. W takim przypadku użyj `COVERED_PARTIALLY` i nazwij niepotwierdzone elementy.

### Nowy lub nieobsłużony przypadek

Jeżeli przypadek nie jest pokryty albo ujawnia możliwy błąd:

1. nie kopiuj danych podatnika do repozytorium;
2. zredukuj problem do minimalnego przykładu syntetycznego;
3. zachowaj relacje matematyczne, ale zmień kwoty i identyfikatory;
4. opisz wynik rzeczywisty, oczekiwany i źródło oczekiwania;
5. ustal, czy problem dotyczy ekstrakcji, danych wejściowych, reguły podatkowej czy implementacji;
6. poinformuj użytkownika, że przypadek może stać się trwałym testem regresyjnym.

Jeżeli agent ma dostęp do GitHuba, może utworzyć Issue **dopiero po zgodzie użytkownika**. Użyj formularza:

`https://github.com/paulomac1000/ipbox-wizard-ai/issues/new?template=new-tax-case.yml`

Bez dostępu do zapisu przygotuj gotowy tytuł, treść zgłoszenia i powyższy link. Zgłoszenie musi być zanonimizowane i zawierać minimalny przypadek, a nie pełne dokumenty.

Nowy poprawny przypadek jest twardą granicą jakości: po dodaniu regresji algorytm nie może zostać zaakceptowany, jeżeli ten przypadek nie przechodzi.

## Tryb 2: rozwój kodu

Wybierz ten tryb wyłącznie wtedy, gdy użytkownik wyraźnie prosi o zmianę kodu, testów, dokumentacji albo infrastruktury.

### Pierwsze kroki

Przeczytaj kolejno:

1. `README.md` — produkt, sposoby użycia i granice wejścia;
2. `AGENTS.md` — zasady pracy z kodem;
3. `ipbox_algorytm.md` — domenowy kontrakt i kolejność decyzji;
4. pliki związane z zadaniem;
5. odpowiadające im testy i scenariusze.

Następnie:

1. sprawdź branch, SHA i stan working tree;
2. uruchom test celowany;
3. odtwórz problem minimalnym testem regresyjnym;
4. dopiero potem zmień implementację;
5. wykonaj code review własnego diffu;
6. przed zakończeniem uruchom pełną bramkę jakości.

## Misja i granica wejścia

Projekt ma pozostać audytowalnym, fail-closed narzędziem wspierającym przygotowanie i kontrolę danych do rozliczenia IP Box programisty B2B.

Kod przyjmuje znormalizowany YAML/dict. Repozytorium nie zawiera uniwersalnego importera surowych PDF, XLSX, KPiR ani PIT. W trybie rozmowy ekstrakcję wykonuje agent. Kalkulator nie naprawia błędnie odczytanych danych.

Warstwa ekstrakcji musi zachować jawne fakty źródłowe, w tym rok, formę opodatkowania, kwalifikację prawa i faktur, przychód IP/NIE, czas i semantykę `W`, KUP, alokację MIX, dowody NEXUS, składki, ulgi, straty i zaliczki.

## Topologia i źródła prawdy

| Obszar | Odpowiedzialność |
|---|---|
| `README.md` | główny punkt wejścia dla użytkownika |
| `ipbox_algorytm.md` | domenowy kontrakt i kolejność decyzji |
| `python_helper/` | deterministyczna implementacja podatkowa |
| `tests/unit/` | wykonywalne invarianty i przypadki brzegowe |
| `tests/llm/oracle.py` | kanoniczny przebieg pełnego raportu |
| `tests/llm/output_schema.py` | kontrakt raportu i decyzji |
| `tests/llm/models.py` | kanoniczna macierz modeli i profile transportowe |
| `tests/llm/scenarios/` | syntetyczne przypadki biznesowe |
| `tests/llm/evaluator.py` | semantyczna walidacja odpowiedzi modelu |
| `tests/llm/vcr/` | fingerprinty, kasety, manifesty i playback |
| `docs/testing.md` | procedura testów, nagrywania i wydania |

Hierarchia źródeł prawdy:

1. `ipbox_algorytm.md` — znaczenie biznesowe;
2. `python_helper/**/*.py` — deterministyczna implementacja;
3. `tests/unit/` — wykonywalne invarianty;
4. oracle, schema i evaluator;
5. scenariusze biznesowe;
6. dokumentacja pomocnicza.

Sprzeczność między źródłami jest błędem. Ustal prawidłowy kontrakt, a następnie popraw implementację, testy i dokumentację razem.

## Najważniejsze invarianty domenowe

### Przychód, W, MIX i NEXUS

- kwalifikacja przychodu, podział IP/NIE, `W`, alokacja MIX i NEXUS są niezależnymi decyzjami;
- `W` nie jest automatycznym ani uniwersalnym kluczem kosztów MIX;
- koszt `KUP: false` trafia do `WYKLUCZONE`, z kwotami IP, NIE i NEXUS równymi zero;
- opis kosztu może wywołać review, ale nie ustala samodzielnie KUP ani koszyka;
- koszt obniżający dochód IP nie staje się automatycznie NEXUS A/B/C/D;
- `allocation_source` i `nexus_evidence` są odrębnymi dowodami;
- NEXUS = `min(1, ((A+B)×1,3)/(A+B+C+D))`;
- `A=B=C=D=0` oznacza NEXUS `0`;
- część dochodu IP poza preferencją trafia do zwykłej podstawy;
- alokacje zachowują każdy grosz i jawną politykę zaokrąglania.

### Fail-closed i kompletność

- brak danych nie jest zerem ani korzystnym `true`;
- rok, flagi i liczby mają ścisłe typy;
- `STOP_03` wymaga jawnie potwierdzonej kompletności źródeł;
- dodatnie odliczenie wymaga reguły właściwego roku i dowodu;
- STOP zeruje finalne liczby i klasyfikacje, ale może pozostawić diagnostykę i bezpieczny podgląd korekty;
- TEST 1–9 ustala wyłącznie Python.

### LLM i VCR

- Python ustala wynik, `decision_facts`, STOP-y i REVIEW-y;
- model nie wykonuje krytycznej arytmetyki ani klasyfikacji podatkowej;
- model otrzymuje gotową kopertę `expected_decision`;
- parser nie naprawia Markdown fences ani brakujących pól;
- odpowiedź musi przejść wspólną lokalną schema i evaluator;
- playback nigdy nie wykonuje live requestu;
- recorder nie nadpisuje istniejącej kasety;
- kaseta powstaje dopiero po schema PASS, semantic PASS i ponownym parsowaniu;
- substytucja requested/returned model jest błędem;
- każdy model z `BENCHMARK_MODELS` przechodzi ten sam recorder, pre-commit, raport i playback;
- `engine_source_hash`, request, scenariusz i harness należą do fingerprintu;
- profil modelu jest chroniony przez `request_hash`, a nie przez hash silnika podatkowego;
- kompletna macierz wielu rodzin dowodzi przenośności kontraktu, nie poprawności prawnej każdego odczytu dokumentu.

## Jak wprowadzać zmiany

### Reguła podatkowa lub błąd kalkulatora

1. Najpierw dodaj minimalny test odtwarzający problem.
2. Popraw kanoniczny moduł w `python_helper/`.
3. Sprawdź wartości zerowe, graniczne, ujemne i błędne typy.
4. Zweryfikuj zachowanie do grosza i brak pomieszania przychodu, W, MIX i NEXUS.
5. Uruchom oracle, evaluator i pełną bramkę.
6. Odśwież VCR offline przed wykonywaniem płatnych requestów.

### Nowy realny przypadek

1. Zredukuj go do minimalnego syntetycznego scenariusza.
2. Dodaj test jednostkowy dla nowego invariantu.
3. Dodaj scenariusz biznesowy, jeżeli wnosi nową ścieżkę procesu.
4. Zachowaj źródła i uzasadnienia, ale użyj fikcyjnych identyfikatorów i kwot.
5. Zweryfikuj scenariusz na pełnej macierzy modeli, jeżeli zmienia kontrakt LLM.
6. W raporcie wskaż dokładne testy i poziom pokrycia.

### Nowy model

1. Dodaj profil bezpośrednio do `MODEL_PROFILES` w `tests/llm/models.py`.
2. Nie twórz osobnego rejestru kandydatów ani alternatywnych wrapperów.
3. Użyj standardowego `scripts/record_model.py`.
4. Dodaj test profilu i requestu.
5. Nagraj lokalnie komplet 46 kaset.
6. Uruchom standardowy pre-commit, raport i playback pojedynczego modelu.
7. Uruchom pełną politykę i playback całej macierzy.
8. Nie deklaruj pełnego pokrycia przed kompletem kaset.

## Dokumentacja i prywatność

- `README.md` ma być zrozumiały także dla księgowej bez doświadczenia programistycznego;
- szczegóły VCR i wydania należą głównie do `docs/testing.md`;
- przykłady poleceń muszą działać na aktualnym drzewie;
- nie wpisuj ulotnych liczników testów jako trwałego kontraktu;
- nie commituj dokumentów podatnika, KPiR, PIT-ów, faktur, umów ani interpretacji;
- nie umieszczaj realnych danych w testach, kasetach, logach, Issue ani komentarzach;
- raporty robocze z danymi użytkownika nie mogą trafiać do Git.

## Bramka jakości

Najpierw uruchom test celowany. Przed zakończeniem zmiany kodu uruchom:

```bash
ruff format --check .
ruff check .
python -m compileall -q python_helper tests scripts
pytest tests/unit --cov=python_helper --cov-report=term-missing --cov-fail-under=90
pytest -q
python scripts/check_cassette_policy.py
python scripts/vcr_precommit.py --all-models
python scripts/benchmark_report.py
unset OPENROUTER_API_KEY
./scripts/verify_all_models.sh
```

Po zmianach wykonaj code review diffu, sprawdź komentarze botów, stan CI oraz to, czy instrukcje lokalne odpowiadają rzeczywistym komendom. Nie oznaczaj PR jako gotowy, jeśli macierz VCR jest częściowa lub playback nie przechodzi offline.
