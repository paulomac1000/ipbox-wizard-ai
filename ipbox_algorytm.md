# Algorytm IP Box — kontrakt deterministyczny-first

> Narzędzie wspiera przygotowanie i kontrolę danych. Nie zastępuje interpretacji indywidualnej ani porady podatkowej. Reguły roczne są wersjonowane dla każdego roku istnienia IP Box: 2019–2026. Rok spoza tego zakresu jest blokowany, a nie liczony według „najbliższych” zasad.

## 1. Zasady nadrzędne

1. Każda liczba pochodzi z deterministycznego kodu Python.
2. Brak danych, kursu, limitu, semantyki pola lub dowodu jest błędem albo REVIEW, nigdy automatycznym zerem.
3. Oznaczaj źródło decyzji: `[PRZEPIS]`, `[DOWÓD]`, `[POLITYKA]`, `[HEURYSTYKA]`.
4. Rozdziel pięć decyzji: kwalifikację przychodu, metodę podziału przychodu IP/NIE, kwalifikację wydatku jako KUP, alokację kosztu `MIX` oraz NEXUS.
5. `W` nie jest automatycznie kluczem `MIX`, NEXUS ani dowodem kwalifikacji IP.
6. Interpretacja KIS lub inna udokumentowana polityka ma pierwszeństwo przed domyślną heurystyką, ale wymaga identyfikatora źródła i zgodnego wdrożenia.
7. Wydatek `KUP: false` jest zawsze `WYKLUCZONE`, nawet jeżeli wcześniej oznaczono go jako `IP`, `NON` albo `MIX`.
8. Źródłowa KPiR, kalkulacja i złożone zeznanie są trzema osobnymi artefaktami. Wyłączenie kosztu w kalkulatorze nie naprawia automatycznie błędnej KPiR ani PIT.
9. Po aktywacji STOP status to `STOPPED`, a finalne liczby i klasyfikacje są zerowane. Informacyjny `source_ledger_audit` i bezpieczny `correction_preview` pozostają widoczne.
10. Zeznanie musi uzgadniać się z ewidencją osobno dla przychodów i kosztów IP/NIE oraz dla użytych ulg, podatku i nadpłaty.
11. Testy i przykłady używają wyłącznie danych syntetycznych. Nie kopiuj danych podatnika, identyfikatorów, kontrahentów, sygnatur ani dokładnych rozliczeń do repozytorium.
12. Provider LLM nie jest źródłem reguł. Adapter transportowy nie może osłabić lokalnej strict schema, parsera ani evaluatora.

## 2. Dane i kwalifikacja

Zbierz rok, formę opodatkowania, kwalifikowane IP, sposób komercjalizacji, umowy, raporty pracy, ewidencję B+R, faktury, KPiR, waluty i daty płatności, ZUS, zdrowotną, ulgi, straty, zaliczki, PIT/IP, zeznanie oraz dokumenty stanowiące źródło polityki.

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
| `source_kpir_requires_correction` | `SOURCE_KPIR_REQUIRES_CORRECTION` |
| `social_contributions_double_counted` | `ZUS_DOUBLE_DIP` |
| `health_contribution_double_counted` | `HEALTH_DOUBLE_DIP` |

Kod istnieje wtedy i tylko wtedy, gdy odpowiadający fakt jest `true`. Brak KIS sam w sobie nie jest STOP-em. Podanie `źródło: interpretacja_KIS` bez `źródło_ref` jest błędem kontraktu wejściowego, ponieważ algorytm nie może zgadywać właściwej interpretacji.

## 3. Współczynnik W — najpierw semantyka

Nie wolno zgadywać, czy procent faktury i godziny NIE-IP opisują te same, rozłączne czy warunkowe części wynagrodzenia. Polityka `W.metoda` jest obowiązkowa, gdy oba pola są używane lub ich znaczenie nie jest oczywiste.

### `conditional_product`

```text
W = ((godziny_pracy - godziny_nie_IP) / godziny_pracy)
    × procent_faktury_IP
```

### `disjoint_components`

```text
W = procent_faktury_IP
    - godziny_nie_IP / godziny_pracy
```

### `time_only`

```text
W = (godziny_pracy - godziny_nie_IP) / godziny_pracy
```

Każda metoda musi dawać wynik `0 ≤ W ≤ 1`. Mianownik to faktyczne godziny pracy. `W<50%` daje `REVIEW_02`, `W>95%` — `REVIEW_01`, skok >30 p.p. — `REVIEW_08`. Wiele projektów wymaga W per projekt, średniej ważonej przychodem i `REVIEW_04`.

### Precyzja arkusza

Audyt odróżnia błąd od prawidłowego wyniku powstałego po zaokrągleniu pośrednim. Jeżeli arkusz zapisuje `W` z dokładnością `q` punktu procentowego, ukryta wartość może różnić się o najwyżej `q/2`. Dla kontrolowanego przychodu `R` minimalna koperta kwotowa wynosi:

```text
tolerancja_W = R × q / 200 + tolerancja_zaokrągleń_kwotowych
```

Domyślne `q` to `0,01 pp`. Jeżeli arkusz przechowuje widoczne `W`, kontrola najpierw sprawdza samo W, a następnie odtwarza kwotę z zapisanej wartości. Stała tolerancja 0,02 zł nie zastępuje koperty wynikającej z precyzji procentu i wielkości przychodu.

Rozpoznawanie sygnatur — procent zastosowany raz, procent zastosowany dwukrotnie, warianty W, sam czas i pełny przychód — używa analogicznych przedziałów. Zaokrąglenie procentu nie może ukrywać `STOP_10` ani późniejszego `STOP_11`.

## 4. Przychód IP/NIE i poziom kontroli

Dozwolone metody: `dokumentowa`, `czasowa_W`, `produktowa`, `z_interpretacji`, `custom`. Metoda niedokumentowa wymaga jawnego klucza 0–1, źródła i uzasadnienia. Brak dowodu kwalifikacji oznacza NIE. Ujemna faktura jest błędem. Różnice kursowe pozostają poza przychodem kwalifikowanym.

Kontrola alokacji działa na najniższym dostępnym niezależnym strumieniu:

1. konkretnej fakturze, gdy ma własną kontrolę i dowód;
2. konkretnym projekcie/IP, gdy raport pracy rozdziela projekty;
3. agregacie kwalifikujących się faktur miesiąca dopiero wtedy, gdy nie ma dokładniejszego podziału.

Faktury jawnie NIE-IP są odseparowane przed zastosowaniem W i muszą pozostać w koszyku NIE. Suma kontrolowanych strumieni musi odpowiadać sumie faktur kwalifikujących się; brakujący lub nadmiarowy strumień aktywuje `STOP_09`.

Dla każdego strumienia zachowaj identyfikator, kwotę całkowitą i podział IP/NIE, metodę i wersję polityki, dane wejściowe do W, zapisane W i jego precyzję, liczbę etapów zaokrąglania oraz dowód podziału.

## 5. KUP i źródłowa KPiR

Koszyk dochodowy jest ustalany dopiero po kwalifikacji KUP:

- `IP` — KUP bezpośrednio i udokumentowanie przypisany do kwalifikowanego dochodu;
- `MIX` — KUP wspólny lub pośredni;
- `NON` — KUP działalności, lecz nie-IP;
- `WYKLUCZONE` — prywatny, niededukowalny albo nieuwzględniany jednorazowo.

Jawne `KUP: false`, `kup: false` albo `deductible: false` ma pierwszeństwo przed opisem i wcześniejszym koszykiem. Taki wydatek otrzymuje `ip_amount=0`, `non_ip_amount=0`, `nexus_amount=0` i `WYKLUCZONE`.

Jeżeli wydatek wykluczony został ujęty w źródłowej KPiR, raport ustawia:

```text
source_ledger_audit.status = REQUIRES_CORRECTION
stop = SOURCE_KPIR_REQUIRES_CORRECTION
```

`source_ledger_audit` pokazuje kwotę zgłoszoną w KPiR, sumę surowych pozycji, sumę prawidłowych KUP, kwotę wykluczoną pozostającą w źródle i deltę korekty. Samo pominięcie kosztu w kalkulacji nie może zostać przedstawione jako wykonana korekta dokumentu źródłowego.

## 6. Alokacja MIX

### Identyfikacja polityki

Każda polityka przechowuje `metoda`, `źródło`, `źródło_ref`, uzasadnienie i `rounding_granularity`. Gdy źródłem jest interpretacja KIS, `źródło_ref` musi zostać dostarczone przez użytkownika lub dokument. Kod nie zawiera prywatnych sygnatur i nie dobiera ich heurystycznie.

### `przychodowa_roczna`

```text
klucz_MIX = przychód_IP_roczny / przychód_całkowity_roczny
MIX_IP    = MIX × klucz_MIX
MIX_NIE   = MIX - MIX_IP
```

Koszt miesięczny jest `DEFERRED` do true-up. Klucz `0.0` jest wartością, nie brakiem danych.

### `przychodowa_w_dacie_kosztu`

```text
klucz_miesiąca = przychód_IP_miesiąca / przychód_całkowity_miesiąca
koszt_IP        = koszt_MIX × klucz_miesiąca
koszt_NIE       = koszt_MIX - koszt_IP
```

Mianownik miesiąca musi być dodatni. Każda pozycja przechowuje miesiąc, klucz, źródło, wynik IP/NIE i ślad dowodowy. Metoda ta nie jest synonimem W i nie może zostać po cichu nazwana `czasowa_W` tylko dlatego, że wartości procentowe przypadkiem są równe.

### Poziom zaokrąglania

Polityka musi jawnie wskazać jeden wariant:

- `per_cost_item` — każda pozycja jest mnożona przez klucz i zaokrąglana do grosza osobno;
- `monthly_pool` — najpierw liczona i zaokrąglana jest miesięczna pula `sum(kosztów) × klucz`, a następnie jej grosze są rozdzielane pomiędzy pozycje metodą największych reszt.

Przy `monthly_pool` suma `ip_amount` pozycji musi być dokładnie równa zaokrąglonej puli miesięcznej. `rounding_adjustment` pokazuje groszową różnicę względem niezależnego zaokrąglenia pozycji. Uzgodnienie porównuje źródło zgodnie z zadeklarowaną granularity; nie maskuje różnicy arbitralną tolerancją.

### Wiele IP

```text
stage1 = MIX × przychód_software_IP / przychód_całkowity
IP_i   = stage1 × przychód_IP_i / przychód_software_IP
```

Oba mianowniki muszą być dodatnie. Podział zachowuje każdy grosz. Pełne rozliczenie wielu IP wymaga osobnej ewidencji przychodów, kosztów, NEXUS, dochodów i strat per prawo.

## 7. NEXUS — osobna warstwa dowodowa

```text
NEXUS = min(1, ((A + B) × 1,3) / (A + B + C + D))
```

A — własne B+R; B — wyniki B+R od niepowiązanego; C — od powiązanego; D — nabycie IP.

- KUP i NEXUS nie są tym samym testem. Koszt może obniżać dochód, lecz pozostać `poza_nexus`.
- `A=B=C=D=0` daje NEXUS `0`.
- mnożnik 1,3 obejmuje A i B;
- koszt kwalifikowany do A/B/C/D wymaga `nexus_evidence`;
- `MIX` w A/B/C/D wymaga również jawnego `nexus_basis`: `explicit_amount` albo `allocated_ip_cost`;
- `allocated_ip_cost` wiąże NEXUS z końcowym, po korekcie groszowej `ip_amount`;
- brak dowodu nie tworzy A heurystycznie: pozycja trafia do `poza_nexus` i otrzymuje `NEXUS_EVIDENCE_MISSING`;
- suma A/B/C/D/poza NEXUS musi zgadzać się co do grosza z kosztami wejściowymi.

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

## 10. Kaskada podatkowa i ulgi

### B+R i IP Box

Nie używaj niejednoznacznego pola `ulga_BR`. Podaj `ulga_BR_IP`, `ulga_BR_NIE` oraz `ulga_BR_limit_odliczenia`. `ulga_BR_IP` pomniejsza dochód kwalifikowanego IP przed NEXUS. Kwoty nie mogą przekroczyć udokumentowanych kosztów B+R ani limitu właściwego dla podatnika.

### Straty

`strata_NIE_z_lat_poprzednich` pomniejsza wyłącznie dochód pozostałej działalności. Strata kwalifikowanego IP wymaga identyfikacji konkretnego prawa i osobnej ewidencji.

### Podatek liniowy i skala

Obsługiwane są właściwe dla roku kwoty: strata NIE, ZUS społeczne, zdrowotna bez dubla, IKZE, B+R oraz termomodernizacja. Dodatkowe dochody skali wymagają osobnego obliczenia odpowiedniego zeznania.

### Termomodernizacja

Preferowane wejście to lista pul z rokiem pierwszego wydatku, kwotą pozostałą i odwołaniem do dowodu. Najstarsze ważne pule są zużywane jako pierwsze. Kwota niewykorzystana może być przenoszona nie dłużej niż sześć lat liczonych od końca roku pierwszego wydatku; kwota wygasła jest jawnie raportowana. Łączna pula podatnika nie może przekroczyć 53 000 zł.

Algorytm raportuje osobno `thermomodernization_used`, `termomodernization_carry_over` i `termomodernization_expired`. Nie wolno twierdzić, że podatek po korekcie pozostaje bez zmian wyłącznie dlatego, że istnieje niewykorzystana pula. Warunek jest spełniony dopiero wtedy, gdy poprawiona kwota odliczenia mieści się w puli i została uwzględniona w korekcie zeznania.

## 11. Uzgodnienie KPiR, PIT/IP, PIT/B i ulg

Porównaj osobno:

```text
przychód_IP_ewidencja  == przychód_IP_zeznanie
przychód_NIE_ewidencja == przychód_NIE_zeznanie
koszt_IP_ewidencja     == koszt_IP_zeznanie
koszt_NIE_ewidencja    == koszt_NIE_zeznanie
```

Jeżeli dane są dostępne, porównaj również:

```text
termomodernizacja_użyta == termomodernizacja_w_zeznaniu
podatek_łączny          == podatek_w_zeznaniu
nadpłata_lub_dopłata    == rozliczenie_w_zeznaniu
```

Równość samych sum `IP+NIE` nie wystarcza. Przesunięcie między koszykami albo pozostawienie wydatku NON-KUP w kosztach aktywuje STOP. Różnica ulgi, podatku lub nadpłaty aktywuje `STOP_12` i odpowiedni kod diagnostyczny.

`correction_preview` może zostać policzony mimo korekcyjnego STOP-u, jeżeli nie ma innego błędu blokującego matematykę. Zawiera:

- czy KPiR wymaga korekty;
- czy złożone zeznanie wymaga korekty;
- czy trzeba zmienić wykorzystaną ulgę;
- czy niezmieniony podatek jest prawdziwy tylko pod warunkiem aktualizacji ulg;
- poprawiony podatek, nadpłatę, wykorzystanie i pozostałą pulę termomodernizacyjną.

Preview nie jest finalnym wynikiem: finalne pola finansowe pozostają wyzerowane przy STOP.

## 12. TEST 1–9

Python ustala:

- `TEST_1` — bilans danych źródłowych;
- `TEST_2` — brak kosztów prywatnych zadeklarowanych jako firmowe;
- `TEST_3` — brak podwójnego ZUS/zdrowotnej;
- `TEST_4` — nieujemne podstawy i carry-over;
- `TEST_5` — zgodny podatek IP;
- `TEST_6` — zgodny podatek łączny z historycznym odliczeniem zdrowotnym;
- `TEST_7` — zgodna metoda MIX;
- `TEST_8` — jawny dowód i kwota NEXUS kwalifikowanego MIX;
- `TEST_9` — opis projektu przy przychodzie.

Dodatkowe strażniki KPiR, alokacji, zaokrągleń, limitów rocznych i uzgodnienia zeznania aktywują STOP przed raportem. Model nie zmienia FAIL na PASS.

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

Python i oracle wyznaczają liczby, klasyfikacje, TEST-y, pełne `decision_facts` oraz finalną autorytatywną kopertę:

```json
{
  "expected_decision": {
    "status": "FINAL",
    "stops": [],
    "reviews": ["REVIEW_09"]
  }
}
```

Model widzi wyłącznie tę kopertę. Nie widzi surowych danych podatkowych, nazw predykatów ani faktów `true/false`. Jego jedynym zadaniem jest zwrócenie czystego JSON z dokładną kopią trzech pól:

```json
{"status":"FINAL","stops":[],"reviews":["REVIEW_09"]}
```

Model:

- nie oblicza podatku, W, KUP, NEXUS, ulg ani TEST 1–9;
- nie ustala, czy kod jest STOP-em czy REVIEW;
- nie przenosi, nie pomija, nie deduplikuje i nie dodaje kodów;
- nie zmienia `status`;
- nie używa Markdown fences ani pól dodatkowych.

Lokalna `DECISION_JSON_SCHEMA`, parser i evaluator są źródłem prawdy dla każdego modelu. Adapter providera może wyłącznie zmienić reprezentację transportową. Nie może zmienić lokalnego zestawu dozwolonych kodów, reguł unikalności, rozdziału STOP/REVIEW ani oceny semantycznej.

Aplikacja składa zweryfikowaną kopertę z deterministycznym raportem. Kaseta może powstać dopiero po pełnym schema i semantic PASS, z dokładnym modelem zwróconym i `finish_reason=stop`.
