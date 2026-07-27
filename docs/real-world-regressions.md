# Regresje wynikające z rozliczeń rzeczywistych — dane wyłącznie syntetyczne

Repozytorium nie przechowuje danych podatnika. Nowe przypadki odtwarzają klasy błędów i strukturę obliczeń przy użyciu zmienionych nazw, okresów i kwot.

## Odtworzone klasy problemów

1. **Podwójne użycie procentu faktury** — np. kwota faktury jest mnożona przez procent, a później ponownie przez ten sam procent zamiast przez jawny W.
2. **Niejawna zmiana metody w roku** — jedna część roku używa procentu dwukrotnie, a druga przypisuje 100% przychodu mimo wykazanych godzin NIE-IP.
3. **Niejednoznaczna semantyka W** — obsługiwane są oddzielnie warunkowy iloczyn, rozłączne składniki i sam czas.
4. **Równe sumy, inny podział** — zeznanie i ewidencja mogą mieć identyczny przychód i koszt łącznie, ale różne koszyki IP/NIE. Taki przypadek jest STOP-em.
5. **Kaskada podobna do korekty** — ZUS, IKZE, część termomodernizacji, podatek IP i nadpłata są testowane razem, ale na innych kwotach.
6. **Proporcja przychodowa w dacie kosztu** — każdy koszt MIX używa klucza miesiąca poniesienia zamiast rocznego W lub rocznego true-up.
7. **Granice lat** — pierwszy rok IP Box, rok sprzed IP Box, limity historyczne, zdrowotna przed i po 2022 r. oraz B+R/IP Box przed 2022 r.
8. **Korekta i zwrot** — odróżniono poprawioną nadpłatę od przepływu pieniężnego, gdy pierwotny zwrot został już wypłacony.

## Scenariusze LLM/VCR

Scenariusze `46`–`55` są częścią pełnej macierzy ośmiu rodzin modeli. Scenariusz 51 ujawnił wcześniej wadę protokołu LLM: MiniMax, podobnie jak GPT-5 Nano używany w poprzednim eksperymencie, przeniósł `REVIEW_09` do `stops`. Nie był to błąd podatkowy ani oracle. Słabszy model ujawnił zbędną transformację i zbyt szeroką schema; dlatego Python przekazuje teraz gotową kopertę `expected_decision`, a schema ma osobne enumy STOP/REVIEW.

Bieżący `openai/gpt-5-mini` przeszedł scenariusz 51 z dokładnym wynikiem `status=STOPPED`, `stops=[STOP_12]`, `reviews=[REVIEW_09]`. Cała aktualna macierz osiąga 8 × 46 = 368/368 kaset i przechodzi playback offline. Provider-specific problem GPT-5 Mini dotyczył wyłącznie nieobsługiwanego `uniqueItems` w transportowym JSON Schema; keyword jest usuwany z kopii transportowej, podczas gdy lokalna schema nadal wymaga unikalności.

Po zmianie deterministycznego kodu najpierw należy uruchomić `scripts/refresh_vcr_metadata.py --all-models --write`, które ponownie waliduje istniejące surowe odpowiedzi bez API. Płatne ponowne nagranie jest potrzebne tylko dla kaset, których odpowiedź nie przechodzi aktualnego kontraktu albo których request uległ zmianie.
