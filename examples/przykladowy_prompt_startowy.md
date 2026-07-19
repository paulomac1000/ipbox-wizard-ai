# Przykładowy prompt startowy

```text
Przeanalizuj moje dane IP Box zgodnie z `ipbox_algorytm.md` i używaj
`python_helper/ipbox_calculator.py` do wszystkich obliczeń.

Rok: 2025. Forma: liniowy 19% albo skala — ustal na podstawie dokumentów.

Najpierw sprawdź kompletność: kwalifikowane IP, umowy, ewidencję B+R,
faktury, KPiR, daty płatności i kursy, ZUS, zdrowotną, ulgi, straty,
zaliczki, interpretację KIS i politykę alokacji. Brak danych nie jest zerem.

Rozdziel:
1. przychód IP/NIE,
2. koszty pośrednie MIX,
3. NEXUS A/B/C/D/poza NEXUS.

Nie używaj W jako domyślnego klucza MIX. IDE, chmura, laptop i repozytorium
nie są kosztami IP bez dowodu wyłącznego wykorzystania. NEXUS licz jako
`min(1, ((A+B) × 1,3)/(A+B+C+D))`.

Dla ulgi B+R rozdziel udokumentowaną kwotę na `ulga_BR_IP` i `ulga_BR_NIE`
oraz podaj `ulga_BR_limit_odliczenia`. Część IP odejmij przed NEXUS.
Nie używaj ogólnego pola `ulga_BR`.

Stratę pozostałej działalności podaj jako `strata_NIE_z_lat_poprzednich`.
Nie przypisuj zagregowanej straty do IP bez ewidencji konkretnego prawa.

Przy działalności na skali połącz inne dochody skali w pełnej podstawie.
Przy działalności liniowej policz osobne zeznanie skali oddzielnie. Nie stosuj
przy liniowym zwykłych darowizn, internetu, rehabilitacji ani ulgi na dziecko.

Sprawdź roczne limity zdrowotnej i IKZE. Dla roku bez zweryfikowanego limitu
zatrzymaj obliczenie. Miesiące muszą mieć format YYYY-MM i rok zgodny z rokiem
rozliczenia. Pula termomodernizacji nie może przekraczać 53 000 zł. Po STOP
wyzeruj finalne liczby.

Na końcu pokaż ślad dowodów, alokacji, TEST 1–9, ograniczenia zakresu i pytania
do księgowej lub doradcy.
Nie przedstawiaj wyniku jako porady podatkowej ani kompletnego zeznania.
To materiał roboczy wymagający weryfikacji przez księgową lub doradcę podatkowego.
```

W harnessie model nie dostaje pełnego zadania rachunkowego ani faktów podatkowych. Python ustala `decision_facts`, buduje pełną kopertę `expected_decision`, a model kopiuje bez zmian wyłącznie `status`, `stops` i `reviews`.
