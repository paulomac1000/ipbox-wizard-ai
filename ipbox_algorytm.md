# Algorytm IP Box — kontrakt deterministyczny-first

> Narzędzie wspiera przygotowanie i kontrolę danych. Nie zastępuje interpretacji indywidualnej ani porady podatkowej. Reguły roczne są wersjonowane dla każdego roku istnienia IP Box: 2019–2026. Rok spoza tego zakresu jest blokowany, a nie liczony według „najbliższych” zasad.

## 1. Zasady nadrzędne

1. Każda liczba pochodzi z deterministycznego kodu Python.
2. Brak danych, kursu, limitu, semantyki pola lub dowodu jest błędem albo REVIEW, nigdy automatycznym zerem.
3. Oznaczaj źródło decyzji: `[PRZEPIS]`, `[DOWÓD]`, `[POLITYKA]`, `[HEURYSTYKA]`.
4. Rozdziel cztery decyzje: kwalifikację przychodu, metodę podziału przychodu IP/NIE, alokację kosztów `MIX` oraz NEXUS.
5. `W` nie jest automatycznie kluczem `MIX`, NEXUS ani dowodem kwalifikacji IP.
6. Interpretacja KIS lub inna udokumentowana polityka ma pierwszeństwo przed domyślną heurystyką, ale jej treść i faktyczne wdrożenie wymagają zgodności.
7. Po aktywacji STOP status to `STOPPED`, a finalne liczby, klasyfikacje i rozliczenie są zerowane.
8. Zeznanie musi uzgadniać się z ewidencją nie tylko sumą globalną, lecz także osobno w przychodach i kosztach IP/NIE.
9. Testy i przykłady używają wyłącznie danych syntetycznych. Nie kopiuj danych podatnika, identyfikatorów, kontrahentów ani dokładnych rozliczeń do repozytorium.

## 2. Dane i kwalifikacja

Zbierz rok, formę opodatkowania, kwalifikowane IP, sposób komercjalizacji, umowy, raporty pracy, ewidencję B+R, faktury, KPiR, waluty i daty płatności, ZUS, zdrowotną, ulgi, straty, zaliczki, PIT/IP, zeznanie oraz KIS.

| Fakt | Kod |
|---|---|
| `unsupported_tax_form` | `STOP_01` |
| `claimed_ip_without_qualified_right` | `STOP_02` |
| `no_qualifying_ip_income_after_complete_evidence` | `STOP_03` |
| `rd_work_absent` | `STOP_04` |
| `ip_claim_without_required_records` | `STOP_08` |
| `revenue_allocation_inconsistent` | `STOP_09` |
| `invoice_percentage_double_applied` | `STOP_10` |
| `allocation_method_changed_without_evidence` | `STOP_11` |
| `return_ledger_reconciliation_failed` | `STOP_12` |
| `rd_ip_relief_not_available_for_year` | `STOP_13` |
| `year_limit_exceeded` | `STOP_14` |
| `health_deduction_mode_invalid_for_year` | `STOP_15` |
| `unsupported_tax_year` | `STOP_16` |
| `social_contributions_double_counted` | `ZUS_DOUBLE_DIP` |
| `health_contribution_double_counted` | `HEALTH_DOUBLE_DIP` |

Kod istnieje wtedy i tylko wtedy, gdy odpowiadający fakt jest `true`. Brak KIS sam w sobie nie jest STOP-em.

## 3. Współczynnik W — najpierw semantyka

Nie wolno zgadywać, czy procent faktury i godziny NIE-IP opisują te same, rozłączne czy warunkowe części wynagrodzenia. Polityka `W.metoda` jest obowiązkowa, gdy oba pola są używane w rozliczeniu historycznym lub ich znaczenie nie jest oczywiste.

### `conditional_product`

Procent faktury jest drugim filtrem stosowanym do czasu potencjalnie kwalifikowanego:

```text
W = ((godziny_pracy - godziny_nie_IP) / godziny_pracy)
    × procent_faktury_IP
```

### `disjoint_components`

Procent faktury i godziny NIE-IP opisują rozłączne części tej samej faktury:

```text
W = procent_faktury_IP
    - godziny_nie_IP / godziny_pracy
```

### `time_only`

Udokumentowana polityka używa wyłącznie czasu:

```text
W = (godziny_pracy - godziny_nie_IP) / godziny_pracy
```

Każda metoda musi dawać wynik `0 ≤ W ≤ 1`. Mianownik to faktyczne godziny pracy. `W<50%` daje `REVIEW_02`, `W>95%` — `REVIEW_01`, skok >30 p.p. — `REVIEW_08`. Wiele projektów wymaga W per projekt, średniej ważonej przychodem i `REVIEW_04`.

Kontrola miesięczna rozpoznaje między innymi: zastosowanie procentu raz, zastosowanie go dwukrotnie, oba warianty W, sam czas i przypisanie 100% faktury. Niezgodność z zadeklarowaną metodą, podwójny procent lub niejawna zmiana metody w trakcie roku aktywują STOP.

## 4. Przychód IP/NIE

Dozwolone metody: `dokumentowa`, `czasowa_W`, `produktowa`, `z_interpretacji`, `custom`. Metoda niedokumentowa wymaga jawnego klucza 0–1, źródła i uzasadnienia. Brak dowodu kwalifikacji oznacza NIE. Ujemna faktura jest błędem. Różnice kursowe pozostają poza przychodem kwalifikowanym.

Dla każdego miesiąca zachowaj:

- kwotę całkowitą,
- kwotę IP i NIE,
- metodę i wersję polityki,
- dane wejściowe do W,
- wynik W,
- dowód podziału.

`IP + NIE` musi równać się fakturze co do grosza. Algorytm odrzuca arkusz, w którym część miesięcy używa procentu dwukrotnie, a inne przypisują 100% przychodu bez jawnej zmiany polityki.

## 5. Koszty dochodowe

- `IP` — bezpośrednio i udokumentowanie przypisany;
- `MIX` — wspólny lub pośredni;
- `NON` — firmowy, ale nie-IP;
- `WYKLUCZONE` — prywatny, niededukowalny albo nieuwzględniany jednorazowo.

IDE, chmura, serwer, repozytorium i sprzęt są domyślnie `MIX`, chyba że istnieje dowód wyłącznego użycia. Kara, mandat i koszt prywatny są `WYKLUCZONE`. Niesklasyfikowany zakup powyżej 10 000 zł jest wyłączony; wprowadź osobno prawidłowy odpis lub amortyzację.

## 6. Alokacja MIX

### `przychodowa_roczna`

```text
klucz_MIX = przychód_IP_roczny / przychód_całkowity_roczny
MIX_IP    = MIX × klucz_MIX
MIX_NIE   = MIX - MIX_IP
```

Koszt miesięczny jest `DEFERRED` do true-up. Klucz `0.0` jest wartością, nie brakiem danych.

### `przychodowa_w_dacie_kosztu`

Każdy koszt wspólny otrzymuje klucz z miesiąca jego poniesienia:

```text
klucz_miesiąca = przychód_IP_miesiąca / przychód_całkowity_miesiąca
koszt_IP        = koszt_MIX × klucz_miesiąca
koszt_NIE       = koszt_MIX - koszt_IP
```

Mianownik miesiąca musi być dodatni. Każda pozycja przechowuje miesiąc, klucz, źródło, wynik IP/NIE i ślad dowodowy. Metoda ta nie jest synonimem rocznego true-up i nie może zostać po cichu zastąpiona `W`.

### Wiele IP

```text
stage1 = MIX × przychód_software_IP / przychód_całkowity
IP_i   = stage1 × przychód_IP_i / przychód_software_IP
```

Oba mianowniki muszą być dodatnie. Podział zachowuje grosze. Pełne rozliczenie wielu IP wymaga osobnej ewidencji przychodów, kosztów, NEXUS, dochodów i strat per prawo.

## 7. NEXUS

```text
NEXUS = min(1, ((A + B) × 1,3) / (A + B + C + D))
```

A — własne B+R; B — wyniki B+R od niepowiązanego; C — od powiązanego; D — nabycie IP.

- `A=B=C=D=0` → NEXUS `0`;
- mnożnik 1,3 obejmuje A i B;
- `MIX` w A/B/C/D wymaga `nexus_source` i `nexus_amount`;
- nie twórz A/B tylko dlatego, że istnieje przychód IP;
- suma A/B/C/D/poza NEXUS musi zgadzać się co do grosza.

## 8. Waluty

Użyj kursu NBP z właściwego poprzedniego dnia roboczego i zapisz kurs oraz datę. Przy metodzie memoriałowej data płatności jest konieczna do różnicy kursowej. Faktura walutowa zapisuje kwotę i walutę źródłową, datę wystawienia i zapłaty, daty kursów, wartości kursów oraz źródło. Różnica jest wyliczana z tych danych; ręczne pole `różnica_kursowa` jest odrzucane. Brak kursu lub daty jest błędem. Dodatnia różnica zwiększa NIE, ujemna staje się kosztem `NON`.

## 9. Reguły roczne 2019–2026

IP Box istnieje od 2019 r. Rok wcześniejszy lub późniejszy niż ostatni zweryfikowany jest `STOP_16`.

| Rok | IKZE przedsiębiorcy | Zdrowotna — sposób obsługi | Limit liniowy |
|---|---:|---|---:|
| 2019 | 5 718,00 | udokumentowane odliczenie od podatku według zasad do 2021 r. | brak stałej kwoty rocznej |
| 2020 | 6 272,40 | jak wyżej | brak stałej kwoty rocznej |
| 2021 | 9 466,20 | jak wyżej | brak stałej kwoty rocznej |
| 2022 | 10 659,60 | dochód albo KUP przy liniowym | 8 700,00 |
| 2023 | 12 483,00 | dochód albo KUP przy liniowym | 10 200,00 |
| 2024 | 14 083,20 | dochód albo KUP przy liniowym | 11 600,00 |
| 2025 | 15 611,40 | dochód albo KUP przy liniowym | 12 900,00 |
| 2026 | 16 956,00 | dochód albo KUP przy liniowym | 14 100,00 |

Dla 2019–2021 zdrowotna używa osobnego pola `odliczenie_zdrowotne_od_podatku`; dla 2022+ używa `odliczenie_zdrowotne_od_dochodu` albo udokumentowanego kosztu. Mieszanie trybów aktywuje `STOP_15`. Kwoty ponad limit nie są obcinane, lecz aktywują `STOP_14`.

Skala:

- 2019: 17,75% / 32%, próg 85 528 zł i historyczna zmienna kwota zmniejszająca;
- 2020–2021: 17% / 32%, próg 85 528 zł i historyczna zmienna kwota zmniejszająca;
- 2022–2026: 12% / 32%, próg 120 000 zł i kwota zmniejszająca 3 600 zł.

Jednoczesne pomniejszenie dochodu IP o ulgę B+R jest obsługiwane dopiero od 2022 r. Dodatnia `ulga_BR_IP` dla 2019–2021 aktywuje `STOP_13`.

## 10. Kaskada podatkowa

### B+R i IP Box

Nie używaj niejednoznacznego pola `ulga_BR`. Podaj `ulga_BR_IP`, `ulga_BR_NIE` oraz `ulga_BR_limit_odliczenia`. `ulga_BR_IP` pomniejsza dochód kwalifikowanego IP przed NEXUS. Kwoty nie mogą przekroczyć udokumentowanych kosztów B+R ani limitu właściwego dla podatnika.

### Straty

`strata_NIE_z_lat_poprzednich` pomniejsza wyłącznie dochód pozostałej działalności. Strata kwalifikowanego IP wymaga identyfikacji konkretnego prawa i osobnej ewidencji.

### Podatek liniowy

Obsługiwane są właściwe dla roku kwoty: strata NIE, ZUS społeczne, zdrowotna bez dubla, IKZE, B+R oraz termomodernizacja. Zwykłe darowizny, internet, rehabilitacja i dziecko są odrzucane. Dodatkowe dochody skali wymagają osobnego obliczenia zeznania skali.

### Skala

Dochód działalności łączy się z `dochody_dodatkowe_skala`. Strata działalności i `ulga_BR_NIE` nie mogą konsumować dochodu z pracy; wspólne odliczenia pomniejszają odpowiednią łączną podstawę. Darowizny mają limit 6%, internet 760 zł i wymagają zweryfikowanego dowodu.

### Termomodernizacja

Preferowane wejście to lista pul z rokiem pierwszego wydatku, kwotą pozostałą i odwołaniem do dowodu. Najstarsze ważne pule są zużywane jako pierwsze. Kwota niewykorzystana może być przenoszona nie dłużej niż sześć lat liczonych od końca roku pierwszego wydatku; kwota wygasła jest jawnie raportowana. Łączna pula podatnika nie może przekroczyć 53 000 zł. Nie podawaj jednocześnie listy pul i jednej zbiorczej puli.

## 11. Uzgodnienie ewidencji, PIT/IP i zeznania

Przed finalizacją porównaj osobno:

```text
przychód_IP_ewidencja  == przychód_IP_zeznanie
przychód_NIE_ewidencja == przychód_NIE_zeznanie
koszt_IP_ewidencja     == koszt_IP_zeznanie
koszt_NIE_ewidencja    == koszt_NIE_zeznanie
```

Równość samych sum `IP+NIE` nie wystarcza. Przesunięcie między koszykami przy zachowaniu sumy aktywuje `STOP_12`. Korekta zeznania rozdziela:

- pierwotny podatek i pierwotną nadpłatę,
- poprawiony podatek i poprawioną nadpłatę,
- kwotę zwrotu już wypłaconą,
- dodatkowy zwrot albo kwotę do zwrotu/zaliczenia.

## 12. TEST 1–9

Python ustala:

- `TEST_1` — bilans KPiR;
- `TEST_2` — brak kosztów prywatnych;
- `TEST_3` — brak podwójnego ZUS/zdrowotnej;
- `TEST_4` — nieujemne podstawy i carry-over;
- `TEST_5` — zgodny podatek IP;
- `TEST_6` — zgodny podatek łączny z historycznym odliczeniem zdrowotnym;
- `TEST_7` — zgodna metoda MIX;
- `TEST_8` — jawny NEXUS kwalifikowanego MIX;
- `TEST_9` — opis projektu przy przychodzie.

Dodatkowe strażniki alokacji, limitów rocznych i uzgodnienia zeznania aktywują STOP przed raportem. Model nie zmienia FAIL na PASS.

## 13. REVIEW

| Fakt | Kod |
|---|---|
| `w_above_95` | `REVIEW_01` |
| `w_below_50` | `REVIEW_02` |
| `multiple_projects_or_ips` | `REVIEW_04` |
| `w_jump_above_30pp` | `REVIEW_08` |
| `single_positive_revenue_client` | `REVIEW_09` |
| `uses_kis_interpretation` | `REVIEW_16` |
| `kis_implementation_requires_confirmation` | `REVIEW_17` |

## 14. Kontrakt modelu

Python wyznacza liczby, klasyfikacje, TEST-y i pełne `decision_facts`. Runner usuwa fakty `false` i tworzy wyłącznie prawdziwe `active_rules`. Model nie widzi surowych danych podatkowych ani nieaktywnych reguł. Zwraca czysty JSON:

```json
{"status":"FINAL","stops":[],"reviews":["REVIEW_09"]}
```

Aplikacja składa i waliduje raport. Model kopiuje każdy aktywny kod do właściwej listy, nie dodaje kodów nieobecnych w `active_rules` i nie wykonuje obliczeń podatkowych.
