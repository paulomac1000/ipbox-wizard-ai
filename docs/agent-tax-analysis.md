---
description: Procedura bezpiecznej analizy dokumentów i danych do rozliczenia IP Box przez agenta.
doc_id: workflow.agent-tax-analysis
type: workflow
status: active
rigor: operational
owners: [repository-maintainers]
verification: Porównaj procedurę z README.md, ipbox_algorytm.md oraz testami pokrycia; dla konkretnego przypadku uruchom wskazane testy i playback offline.
upstream: [README.md, ipbox_algorytm.md, docs/testing.md, tests/llm/models.py]
downstream: [AGENTS.md, examples/przykladowy_prompt_startowy.md]
review_triggers: [zmiana kontraktu algorytmu, zmiana statusów pokrycia, zmiana polityki prywatności, zmiana macierzy modeli]
---

# Analiza rozliczenia podatnika przez agenta

## Wynik wymagany

Agent przygotowuje audytowalną analizę opartą na dokumentach, deterministycznym kodzie i jawnych brakach. Nie zgaduje danych, nie składa deklaracji i nie zapisuje materiałów podatnika w repozytorium.

Na końcu nadaje dokładnie jeden status pokrycia:

```text
COVERED_DIRECTLY | COVERED_PARTIALLY | NOT_COVERED
```

Status opisuje pokrycie przypadku przez testy repozytorium, a nie pewność prawną rozliczenia.

## Warunki wstępne

1. Przeczytaj `README.md`, `AGENTS.md` i `ipbox_algorytm.md`.
2. Ustal rok, formę opodatkowania, zakres analizy i oczekiwany rezultat.
3. Potwierdź, że przekazane pliki są potrzebne do zadania. Nie kopiuj ich do repozytorium ani nie commituj ich do Git. Do zewnętrznego narzędzia nie wysyłaj ich bez jawnej zgody i ustalonego zakresu.
4. Oddziel dane źródłowe od założeń, pytań, obliczeń i wniosków.

## Procedura

1. Zinwentaryzuj wszystkie dokumenty, arkusze i okresy.
2. Odczytaj PDF, XLSX, CSV i inne załączniki samodzielnie, gdy narzędzia są dostępne.
3. Przy każdej istotnej wartości zachowaj wskazanie dokumentu, strony, arkusza albo wiersza.
4. Zbuduj rejestr faktów źródłowych i pokaż użytkownikowi wyekstrahowane dane przed finalnym obliczeniem.
5. Wypisz braki blokujące. Brak danych nie jest zerem ani korzystnym założeniem.
6. Przygotuj znormalizowane dane robocze wewnętrznie; użytkownik nie musi pisać YAML-a.
7. Wykonaj krytyczne obliczenia kodem z `python_helper/`, nie w pamięci modelu.
8. Porównaj wynik z KPiR, ewidencją IP Box, PIT i wcześniejszymi wyliczeniami, jeśli je przekazano.
9. Oddziel błąd dokumentu, brak danych, wybór metody podatkowej i możliwy błąd algorytmu.
10. Pokaż źródło, podstawienie, funkcję i wynik dla każdej ważnej liczby.
11. Wskaż STOP-y, REVIEW-y, wariant pierwotny, wariant poprawiony i ryzyka resztkowe.
12. Nie zmieniaj kodu ani historii Git, chyba że użytkownik osobno zleci rozwój repozytorium.

## Ocena pokrycia

Dla statusu pokrycia wskaż:

- testy jednostkowe chroniące istotne reguły;
- scenariusze z `tests/llm/scenarios/` odtwarzające tę samą ścieżkę;
- elementy bez bezpośredniego odpowiednika;
- kompletność kaset dla bieżącego `BENCHMARK_MODELS` z `tests/llm/models.py`;
- wynik playbacku offline.

`COVERED_DIRECTLY` jest dozwolone wyłącznie wtedy, gdy ten sam istotny invariant ma bezpośredni scenariusz, komplet aktualnych kaset dla całej bieżącej macierzy i przechodzący playback bez sekretu i sieci.

Podobny test albo częściowe pokrycie oznacza `COVERED_PARTIALLY`. Brak reprezentatywnego scenariusza lub możliwy błąd oznacza `NOT_COVERED`.

## Nowy lub nieobsłużony przypadek

1. Nie kopiuj danych podatnika do repozytorium, logów, kaset, Issue ani komentarzy.
2. Zredukuj problem do minimalnego przykładu syntetycznego.
3. Zachowaj relacje matematyczne, ale zmień kwoty i identyfikatory.
4. Opisz wynik rzeczywisty, oczekiwany i źródło oczekiwania.
5. Ustal, czy problem dotyczy ekstrakcji, danych wejściowych, reguły podatkowej czy implementacji.
6. Zaproponuj brakujący test jednostkowy i scenariusz biznesowy.
7. Utwórz zanonimizowane GitHub Issue wyłącznie po jawnym poleceniu użytkownika oraz dodatkowej zgodzie na publikację zanonimizowanego Issue.

Formularz:

```text
https://github.com/paulomac1000/ipbox-wizard-ai/issues/new?template=new-tax-case.yml
```

## Bezpieczne zatrzymanie

Zatrzymaj finalne wyliczenie i przedstaw pytania, gdy brakuje danych wymaganych przez algorytm, źródła są sprzeczne, dokument nie daje się wiarygodnie odczytać albo deterministyczny kod i kontrakt biznesowy nie zgadzają się.

Nie zastępuj brakującego dowodu domysłem. Możesz przygotować wariant diagnostyczny tylko wtedy, gdy jest wyraźnie oznaczony jako założenie i nie jest przedstawiany jako finalne rozliczenie.

## Weryfikacja

Dla konkretnego przypadku uruchom testy celowane, a przed deklaracją `COVERED_DIRECTLY` także pełną bezpłatną bramkę i playback offline opisany w `docs/testing.md`. W raporcie rozróżnij komendy wykonane, odnalezione lecz niewykonane oraz niemożliwe do uruchomienia.
