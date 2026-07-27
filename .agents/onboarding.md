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
- nie zmieniaj kodu i nie twórz commitów;
- nie zapisuj danych podatnika w repozytorium.

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