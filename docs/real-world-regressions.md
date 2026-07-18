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

Scenariusze `46`–`55` są częścią pełnej macierzy modeli. Po zmianie scenariusza, oracle, schema lub algorytmu wszystkie kasety muszą zostać usunięte i nagrane od nowa. Nie wolno mieszać starych kaset z nowym kontraktem.
