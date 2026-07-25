# Wersjonowane reguły podatkowe 2019–2026

Stan źródeł zweryfikowany: 18 lipca 2026 r.

## Zakres

`python_helper/tax_year_rules.py` obsługuje każdy rok, w którym IP Box obowiązywał do dnia weryfikacji: 2019–2026. Wartości nie są przenoszone pomiędzy latami. Rok spoza zakresu kończy obliczenie błędem/`STOP_16`.

## Źródła urzędowe

- `MF_IPBOX_2019`: Ministerstwo Finansów, „Polski Ład — ulga IP Box” — wprowadzenie IP Box w 2019 r. i jednoczesne B+R/IP Box od 2022 r.
- `KNF_IKZE`: Komisja Nadzoru Finansowego, historyczne limity wpłat na IKZE 2019–2026.
- `MF_HEALTH`: podatki.gov.pl, „Odliczenie składek na ubezpieczenie zdrowotne PIT” — limity liniowe 2022–2026.
- `MF_HEALTH_HISTORY`: ta sama informacja wraz z zasadami obowiązującymi do 31 grudnia 2021 r.; kwota jest odliczeniem od podatku opartym o udokumentowane 7,75% podstawy, a nie stałym rocznym limitem.
- `MF_SCALE_HISTORY`: podatki.gov.pl, historyczne skale 2019–2021, w tym zmienna kwota zmniejszająca podatek.
- `MF_SCALE_CURRENT`: skala 12%/32%, próg 120 000 zł i kwota zmniejszająca 3 600 zł od 2022 r.
- `MF_THERMOMODERNIZATION`: podatki.gov.pl, zasady ulgi termomodernizacyjnej — limit 53 000 zł na podatnika i przenoszenie niewykorzystanej kwoty przez maksymalnie sześć lat.

## Limity

| Rok | IKZE — działalność | Zdrowotna przy liniowym |
|---|---:|---:|
| 2019 | 5 718,00 | historyczne odliczenie od podatku |
| 2020 | 6 272,40 | historyczne odliczenie od podatku |
| 2021 | 9 466,20 | historyczne odliczenie od podatku |
| 2022 | 10 659,60 | 8 700,00 |
| 2023 | 12 483,00 | 10 200,00 |
| 2024 | 14 083,20 | 11 600,00 |
| 2025 | 15 611,40 | 12 900,00 |
| 2026 | 16 956,00 | 14 100,00 |

Algorytm nie obcina kwoty do limitu. Przekroczenie choćby o grosz jest błędem, ponieważ ciche obcięcie ukrywa wadliwe dane zeznania.

## Granice modelu

- Kwota zdrowotna 2019–2021 musi być już zweryfikowaną kwotą odliczenia od podatku. Silnik nie rekonstruuje podstaw miesięcznych ZUS bez dokumentów.
- Ulga B+R pomniejszająca dochód IP jest niedozwolona w modelu dla 2019–2021 i dozwolona od 2022 r.
- Dodatnia przeniesiona kwota termomodernizacji wymaga osobnego lotu z `origin_year` i `evidence_ref`; zbiorcza `termomodernizacja_pula` jest wyłącznie trybem zgodnościowym `PROVISIONAL`.
- Kolejny rok wymaga dodania urzędowych źródeł, stałych i regresji przed odblokowaniem.
