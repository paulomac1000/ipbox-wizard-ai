# AGENTS.md

Instrukcja dla agentów pracujących z repozytorium `ipbox-wizard-ai`.

Najpierw ustal, **w jakim trybie pracujesz**. Ten sam projekt może służyć do analizy dokumentów podatnika albo do rozwijania kodu. Nie mieszaj tych zadań.

## Tryb 1: analiza rozliczenia użytkownika

Wybierz ten tryb, gdy użytkownik przekazał dokumenty, archiwum ZIP lub link do repozytorium i chce przygotować albo sprawdzić rozliczenie IP Box.

W tym trybie:

1. Przeczytaj `README.md` i `ipbox_algorytm.md`.
2. Zinwentaryzuj wszystkie dokumenty użytkownika.
3. Samodzielnie odczytaj PDF, XLSX, CSV i inne załączniki.
4. Przy każdej ważnej wartości wskaż dokument, stronę, arkusz albo wiersz źródłowy.
5. Pokaż użytkownikowi wyekstrahowane dane przed finalnym obliczeniem.
6. Zapytaj o braki. Brak danych nie jest zerem ani korzystnym założeniem.
7. Przygotuj znormalizowane dane robocze wewnętrznie — użytkownik nie musi pisać YAML-a.
8. Wykonaj krytyczne obliczenia kodem z `python_helper/`, nie w pamięci modelu.
9. Porównaj wynik z KPiR, ewidencją IP Box i formularzami PIT.
10. Oddziel:
    - błąd dokumentu lub rozliczenia;
    - brak danych;
    - obszar wymagający decyzji podatkowej;
    - możliwy błąd algorytmu.
11. Nie zmieniaj kodu, nie twórz commitów i nie modyfikuj testów, chyba że użytkownik wyraźnie zleci rozwój projektu.
12. Nie zapisuj prywatnych dokumentów ani danych podatnika w repozytorium.

Jeżeli odkryjesz możliwy błąd algorytmu, opisz minimalny syntetyczny przypadek odtwarzający. Nie kopiuj rzeczywistych danych podatnika do testów.

## Tryb 2: rozwój kodu w Codex, Claude Code lub podobnym narzędziu

Wybierz ten tryb wyłącznie wtedy, gdy użytkownik wyraźnie prosi o zmianę kodu, testów, dokumentacji albo infrastruktury projektu.

### Pierwsze 5 minut

Przeczytaj w tej kolejności:

1. `README.md` — produkt, sposoby użycia i granice wejścia.
2. `AGENTS.md` — zasady pracy z kodem.
3. `ipbox_algorytm.md` — domenowy kontrakt i kolejność decyzji.
4. Pliki związane z zadaniem.
5. Odpowiadające im testy jednostkowe i scenariusze.

Następnie:

1. sprawdź bieżący branch i SHA;
2. uruchom test celowany;
3. odtwórz problem testem regresyjnym;
4. dopiero potem zmień implementację;
5. przed zakończeniem uruchom pełną bramkę jakości.

## Misja projektu

Utrzymuj audytowalne, fail-closed narzędzie wspierające przygotowanie i kontrolę danych do rozliczenia IP Box programisty B2B.

Projekt nie jest poradą podatkową ani generatorem gotowego zeznania. Wynik musi zostać zweryfikowany przez księgową albo doradcę podatkowego.

## Granica wejścia

Kod przyjmuje znormalizowany YAML/dict. Repozytorium nie zawiera kompletnego, uniwersalnego importera surowych PDF, XLSX, KPiR ani PIT.

W trybie rozmowy ekstrakcję wykonuje agent. W trybie programistycznym nie zakładaj, że kalkulator naprawi błędnie odczytane dane. Warstwa ekstrakcji musi zachować jawne fakty źródłowe, między innymi:

- rok i formę opodatkowania;
- kwalifikację prawa i faktury;
- przychód IP/NIE;
- czas pracy i semantykę `W`;
- `KUP`, koszyk kosztu i informację, czy pozycja pozostała w KPiR;
- metodę i źródło alokacji MIX;
- dowody NEXUS;
- ZUS, zdrowotną, ulgi, straty i zaliczki.

## Topologia projektu

| Obszar | Odpowiedzialność |
|---|---|
| `README.md` | główny punkt wejścia dla użytkownika |
| `ipbox_algorytm.md` | domenowy kontrakt i kolejność decyzji |
| `python_helper/ipbox_calculator.py` | podstawowe obliczenia W, kosztów, NEXUS i rozliczenia |
| `python_helper/tax_year_rules.py` | reguły i limity roczne 2019–2026 |
| `python_helper/tax_cascade.py` | kanoniczna kaskada podatku i ulg |
| `python_helper/allocation_audit.py` | audyt przychodu i współczynnika W |
| `python_helper/cost_audit.py` | KUP, alokacja, dowody NEXUS i audyt KPiR |
| `python_helper/report_metadata.py` | hash wejścia, źródła reguł i tożsamość silnika |
| `tests/llm/oracle.py` | kanoniczny przebieg pełnego raportu |
| `tests/llm/oracle_legacy.py` | aktywna baza zgodności; nie dodawaj tu nowych reguł |
| `tests/llm/output_schema.py` | kontrakt raportu |
| `tests/llm/scenarios/` | syntetyczne przypadki biznesowe |
| `tests/unit/` | wykonywalna specyfikacja i regresje |
| `tests/llm/evaluator.py` | semantyczna walidacja odpowiedzi modelu |
| `tests/llm/vcr/` | fingerprinty, kasety, manifesty i playback |
| `docs/testing.md` | pełna procedura testów i wydania |

Nie używaj numerowanych nazw modułów ani funkcji. Aktualna implementacja ma nazwę kanoniczną, a zachowana baza zgodności jawny sufiks `_legacy`.

## Źródła prawdy

1. `ipbox_algorytm.md` — znaczenie biznesowe i granice procesu.
2. `python_helper/**/*.py` — deterministyczna implementacja.
3. `tests/unit/` — wykonywalne invarianty i przypadki brzegowe.
4. `tests/llm/oracle.py` oraz schema — pełny kontrakt raportu.
5. `tests/llm/scenarios/` — przykłady biznesowe i regresje.
6. Dokumentacja pomocnicza.

Sprzeczność między źródłami jest błędem. Nie wybieraj wygodniejszej wersji. Ustal prawidłowy kontrakt, a następnie popraw implementację, testy i dokumentację razem.

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
- rok i flagi kwalifikacji mają ścisłe typy;
- pola liczbowe odrzucają booleany, tekst i wartości nieskończone;
- `STOP_03` wymaga jawnie potwierdzonej kompletności źródeł;
- dodatnie odliczenie wymaga reguły właściwego roku i dowodu;
- dodatni lot termomodernizacji wymaga `origin_year` i `evidence_ref`;
- STOP zeruje finalne liczby i klasyfikacje, ale może pozostawić diagnostykę i bezpieczny podgląd korekty;
- TEST 1–9 ustala wyłącznie Python.

### LLM i VCR

- Python ustala wynik, `decision_facts`, STOP-y i REVIEW-y;
- model nie wykonuje krytycznej arytmetyki ani klasyfikacji podatkowej;
- parser nie naprawia Markdown fences ani brakujących pól;
- odpowiedź musi przejść pełną lokalną schema i evaluator;
- playback nigdy nie wykonuje live requestu;
- recorder nie nadpisuje istniejącej kasety;
- kaseta powstaje dopiero po schema PASS, semantic PASS i ponownym parsowaniu;
- `engine_source_hash`, request, scenariusz i harness należą do fingerprintu.

## Jak wprowadzać zmiany

### Reguła podatkowa lub limit roczny

1. Zmień `tax_year_rules.py` albo `tax_cascade.py`.
2. Dodaj test roku granicznego i roku sąsiedniego.
3. Sprawdź wpływ na oracle i scenariusze.
4. Odśwież metadane VCR offline.
5. Nagrywaj tylko odpowiedzi rzeczywiście unieważnione zmianą.

### Błąd kalkulatora lub alokacji

1. Najpierw dodaj minimalny test odtwarzający błąd.
2. Popraw kanoniczny moduł w `python_helper/`.
3. Sprawdź wartości zerowe, graniczne, ujemne i błędne typy.
4. Zweryfikuj zachowanie do grosza.
5. Sprawdź, że nie pomieszano przychodu, W, MIX i NEXUS.
6. Uruchom regresje oracle i evaluator.

### Nowy realny przypadek

1. Nie kopiuj danych podatnika do repozytorium.
2. Zredukuj problem do minimalnego syntetycznego scenariusza.
3. Dodaj test jednostkowy dla nowego invariantu.
4. Dodaj scenariusz biznesowy tylko wtedy, gdy wnosi nową ścieżkę procesu.
5. Zachowaj źródła i uzasadnienia, ale użyj fikcyjnych identyfikatorów i kwot.

### Dokumentacja

- `README.md` ma być zrozumiały dla użytkownika wrzucającego pliki do rozmowy;
- `AGENTS.md` opisuje tryb analizy i tryb pracy z kodem;
- `ipbox_algorytm.md` jest kontraktem domenowym, nie instrukcją marketingową;
- szczegóły VCR i wydania należą głównie do `docs/testing.md`;
- nie wpisuj ulotnych liczb testów poza opisem konkretnego wydania.

## Prywatność

- nie commituj dokumentów podatnika, KPiR, PIT-ów, faktur, umów ani interpretacji;
- nie umieszczaj realnych danych w testach, kasetach, fixture, logach ani komentarzach;
- katalog `input/` traktuj jako lokalny i prywatny;
- raporty robocze z danymi użytkownika nie mogą trafiać do Git;
- przy opisywaniu błędu używaj danych syntetycznych.

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
for script in scripts/*.sh dump-to-md.sh; do bash -n "$script"; done
```

Raport końcowy podaje sprawdzony SHA, wykonane polecenia, wyniki testów, coverage i stan VCR.

## Nagrywanie kaset

Najpierw spróbuj bez API:

```bash
python scripts/refresh_vcr_metadata.py --all-models --write
python scripts/vcr_precommit.py --all-models
unset OPENROUTER_API_KEY
./scripts/verify_all_models.sh
python scripts/benchmark_report.py
```

Jeżeli `benchmark_report.py` zwraca `all_complete_and_valid=true`, nie wykonuj płatnych requestów.

Nie nagrywaj całej macierzy profilaktycznie. Gdy zmiana rzeczywiście unieważniła konkretną kasetę, usuń wyłącznie ją i nagraj dokładny model oraz scenariusz zgodnie z `docs/testing.md`.

## Nie wolno

- liczyć krytycznej arytmetyki w modelu zamiast w Pythonie;
- wymyślać kursów NBP, limitów, dowodów lub kwalifikacji;
- osłabiać asercji, schemy lub evaluatora pod odpowiedź modelu;
- ręcznie edytować odpowiedzi, hashy, fingerprintów lub kosztów kaset;
- dodawać korzystnych wartości domyślnych;
- włączać live fallbacku w playbacku;
- deklarować gotowości przy czerwonym CI albo niepełnej macierzy;
- usuwać aktywnych modułów `_legacy` bez osobnego refaktoru i migracji;
- zmieniać kod podczas zwykłej analizy dokumentów bez wyraźnego polecenia użytkownika.

## Definition of Done

Zmiana jest gotowa, gdy:

1. zachowanie jest opisane testem regresyjnym;
2. źródła prawdy są spójne;
3. bramka jakości przechodzi;
4. coverage pozostaje co najmniej 90%;
5. VCR jest kompletny, aktualny i odtwarza się bez sekretu;
6. nie wykonano nieuzasadnionych płatnych requestów;
7. dokumentacja odzwierciedla aktualny sposób użycia;
8. repozytorium nie zawiera danych podatnika ani sekretów;
9. raport końcowy jasno rozróżnia to, co sprawdzono, od tego, czego nie zweryfikowano.