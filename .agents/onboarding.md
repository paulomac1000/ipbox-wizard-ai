# Onboarding agenta

Najpierw przeczytaj [`README.md`](../README.md) i [`AGENTS.md`](../AGENTS.md).

Repozytorium ma dwa różne zastosowania. Nie mieszaj ich.

## 1. Analiza dokumentów użytkownika

Gdy użytkownik chce przygotować albo sprawdzić rozliczenie IP Box:

- zinwentaryzuj i samodzielnie odczytaj przekazane dokumenty;
- pokaż źródło każdej ważnej kwoty;
- zapytaj o braki zamiast zgadywać;
- przygotuj dane robocze wewnętrznie;
- wykonaj obliczenia kodem z `python_helper/`;
- porównaj wynik z KPiR, ewidencją i PIT;
- wskaż testy i scenariusze odpowiadające przypadkowi;
- podaj dokładnie jeden status: `COVERED_DIRECTLY`, `COVERED_PARTIALLY` albo `NOT_COVERED`;
- nie zmieniaj kodu i nie twórz commitów;
- nie zapisuj danych podatnika w repozytorium.

`COVERED_DIRECTLY` wolno zadeklarować wyłącznie wtedy, gdy łącznie:

1. istnieje bezpośredni scenariusz biznesowy;
2. scenariusz sprawdza ten sam istotny invariant;
3. macierz VCR wszystkich wymaganych rodzin jest kompletna i aktualna;
4. playback przechodzi bez sekretu i bez połączenia z siecią.

Jeżeli spełniona jest tylko część tych warunków, użyj `COVERED_PARTIALLY`. Nie deklaruj potwierdzenia przez wiele rodzin AI na podstawie podobnego testu.

Jeżeli przypadek nie jest pokryty albo ujawnia możliwy błąd, przygotuj minimalny przykład syntetyczny. Po zgodzie użytkownika utwórz GitHub Issue, gdy masz dostęp do zapisu. W przeciwnym razie przygotuj treść i podaj formularz:

`https://github.com/paulomac1000/ipbox-wizard-ai/issues/new?template=new-tax-case.yml`

Szczegółowa procedura znajduje się w sekcji „Tryb 1” pliku `AGENTS.md`.

## 2. Rozwój projektu

Gdy użytkownik wyraźnie prosi o zmianę kodu lub dokumentacji:

1. przeczytaj `AGENTS.md` i `ipbox_algorytm.md`;
2. sprawdź branch oraz SHA;
3. odtwórz problem minimalnym testem syntetycznym;
4. popraw kanoniczny moduł;
5. uruchom test celowany i pełną bramkę jakości;
6. nie dostosowuj testu, schemy ani evaluatora do błędnej odpowiedzi modelu;
7. nie wykonuj płatnego nagrywania VCR, jeżeli istniejące kasety dają się poprawnie odświeżyć i odtworzyć offline.

W benchmarku Python buduje autorytatywną kopertę `expected_decision`. Model otrzymuje wyłącznie gotowe `status`, `stops` i `reviews`, a następnie ma je zwrócić bez reinterpretacji. Model nie liczy podatku ani nie ustala klasyfikacji.

Szczegółowe komendy, invarianty, zasady VCR i Definition of Done znajdują się w `AGENTS.md` oraz `docs/testing.md`.

## Niezależne decyzje domenowe

Zawsze rozdzielaj:

- kwalifikację i podział przychodu IP/NIE;
- współczynnik czasu `W`;
- kwalifikację wydatku jako KUP albo WYKLUCZONE;
- alokację kosztów MIX;
- NEXUS A/B/C/D/poza NEXUS;
- podział dochodu IP na część preferencyjną i zwykłą.

Python jest źródłem krytycznej matematyki. Model nie może korzystnie interpretować braków ani wymyślać dowodów.
