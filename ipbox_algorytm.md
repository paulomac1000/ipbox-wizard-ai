# Algorytm IP Box — kontrakt deterministyczny-first

> Narzędzie wspiera przygotowanie danych; nie zastępuje porady podatkowej. Reguły zweryfikowano 17 lipca 2026 r. dla scenariuszy 2025, z jawnymi limitami 2026. Inny rok wymaga aktualizacji źródeł i testów.

## 1. Zasady nadrzędne

1. Każda liczba pochodzi z kalkulatora Python.
2. Brak danych, kursu, limitu lub dowodu jest błędem albo REVIEW, nigdy automatycznym zerem.
3. Oznaczaj źródło decyzji: `[PRZEPIS]`, `[DOWÓD]`, `[POLITYKA]`, `[HEURYSTYKA]`.
4. Rozdziel: przychód IP/NIE, alokację `MIX` i NEXUS.
5. `W` nie jest automatycznie kluczem `MIX` ani NEXUS.
6. KIS lub udokumentowana polityka ma pierwszeństwo przed heurystyką.
7. Po STOP status to `STOPPED`, a finalne liczby i klasyfikacje są zerowane.

## 2. Dane i kwalifikacja

Zbierz rok, formę opodatkowania, kwalifikowane IP, sposób komercjalizacji, umowy, ewidencję B+R, faktury, KPiR, waluty i daty płatności, ZUS, zdrowotną, ulgi, straty, zaliczki i KIS.

| Fakt | Kod |
|---|---|
| `unsupported_tax_form` | `STOP_01` |
| `claimed_ip_without_qualified_right` | `STOP_02` |
| `no_qualifying_ip_income_after_complete_evidence` | `STOP_03` |
| `rd_work_absent` | `STOP_04` |
| `ip_claim_without_required_records` | `STOP_08` |
| `social_contributions_double_counted` | `ZUS_DOUBLE_DIP` |
| `health_contribution_double_counted` | `HEALTH_DOUBLE_DIP` |

Kod istnieje wtedy i tylko wtedy, gdy odpowiadający fakt jest `true`. Brak KIS nie jest STOP-em.

## 3. Współczynnik W

```text
W = ((godziny_pracy - godziny_nie_IP) × procent_faktury_IP / 100)
    / godziny_pracy × 100
```

Mianownik to faktyczne godziny pracy. `W<50%` daje `REVIEW_02`, `W>95%` — `REVIEW_01`, skok >30 p.p. — `REVIEW_08`. Wiele projektów wymaga W per projekt, średniej ważonej przychodem i `REVIEW_04`.

## 4. Przychód IP/NIE

Dozwolone metody: `dokumentowa`, `czasowa_W`, `produktowa`, `z_interpretacji`, `custom`. Metoda niedokumentowa wymaga jawnego klucza 0–1 i źródła. Brak dowodu kwalifikacji oznacza NIE. Ujemna faktura jest błędem. Różnice kursowe pozostają poza przychodem kwalifikowanym.

## 5. Koszty dochodowe

- `IP` — bezpośrednio i udokumentowanie przypisany;
- `MIX` — wspólny lub pośredni;
- `NON` — firmowy, ale nie-IP;
- `WYKLUCZONE` — prywatny, niededukowalny albo nieuwzględniany jednorazowo.

IDE, chmura, serwer, repozytorium i sprzęt są domyślnie `MIX`, chyba że istnieje dowód wyłącznego użycia. Kara, mandat i koszt prywatny są `WYKLUCZONE`. Niesklasyfikowany zakup powyżej 10 000 zł jest wyłączony; wprowadź osobno prawidłowy odpis lub amortyzację.

## 6. Alokacja MIX

Dla `przychodowa_roczna`:

```text
klucz_MIX = przychód_IP_roczny / przychód_całkowity_roczny
MIX_IP    = MIX × klucz_MIX
MIX_NIE   = MIX - MIX_IP
```

Koszt miesięczny jest `DEFERRED` do true-up. Klucz `0.0` jest wartością, nie brakiem danych.

Dla wspólnych kosztów wielu IP:

```text
stage1 = MIX × przychód_software_IP / przychód_całkowity
IP_i   = stage1 × przychód_IP_i / przychód_software_IP
```

Oba mianowniki muszą być dodatnie. Podział zachowuje grosze. To tylko alokacja kosztu wspólnego; pełne rozliczenie wielu IP wymaga osobnej ewidencji przychodów, kosztów, NEXUS, dochodów i strat per IP.

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

Użyj kursu NBP z właściwego poprzedniego dnia roboczego i zapisz kurs oraz datę. Przy metodzie memoriałowej data płatności jest konieczna do różnicy kursowej. Brak kursu lub daty jest błędem. Dodatnia różnica zwiększa NIE, ujemna staje się kosztem `NON`.

## 9. Kaskada podatkowa

### 9.1 Ulga B+R i IP Box

Nie używaj pola `ulga_BR`. Podaj:

- `ulga_BR_IP` — kwalifikowane odliczenie przypisane do dochodu z kwalifikowanego IP;
- `ulga_BR_NIE` — część przypisana do pozostałej działalności;
- `ulga_BR_limit_odliczenia` — udokumentowany limit po zastosowaniu właściwego procentu.

`ulga_BR_IP` pomniejsza dochód kwalifikowanego IP przed zastosowaniem NEXUS. Suma części IP i NIE nie może przekroczyć limitu.

### 9.2 Straty

`strata_NIE_z_lat_poprzednich` pomniejsza wyłącznie dochód pozostałej działalności. Nie używaj `straty_poprzednie`. Strata kwalifikowanego IP wymaga identyfikacji konkretnego prawa i osobnej ewidencji; oracle agregujący jej nie zgaduje.

### 9.3 Podatek liniowy

Obsługiwane są wcześniej zweryfikowane kwoty: strata NIE, ZUS społeczne, zdrowotna do limitu i bez dubla, IKZE, B+R oraz termomodernizacja. Zwykłe darowizny, internet, rehabilitacja i dziecko są odrzucane. Dodatkowe dochody opodatkowane skalą wymagają osobnego obliczenia zeznania skali i nie są mieszane z PIT-36L.

### 9.4 Skala

Dochód działalności na skali łączy się z `dochody_dodatkowe_skala`. Kalkulator liczy podatek od pełnej wspólnej podstawy. Strata działalności i `ulga_BR_NIE` nie mogą konsumować dochodu z pracy; ZUS, IKZE, darowizny, internet, rehabilitacja i termomodernizacja pomniejszają odpowiednią wspólną podstawę zgodnie z kontraktem.

Zwykłe darowizny mają wspólny limit 6%, internet limit 760 zł. Warunki osobiste i historyczne muszą być zweryfikowane przed przekazaniem kwoty.

### 9.5 Limity roczne

Oracle zawiera zweryfikowane limity przedsiębiorcy:

| Rok | zdrowotna liniowa | IKZE przedsiębiorcy |
|---|---:|---:|
| 2025 | 12 900 zł | 15 611,40 zł |
| 2026 | 14 100 zł | 16 956 zł |

Dodatnie odliczenie dla innego roku jest blokowane do aktualizacji źródeł i testów.

## 10. TEST 1–9

Python ustala:

- `TEST_1` — bilans KPiR;
- `TEST_2` — brak kosztów prywatnych;
- `TEST_3` — brak podwójnego ZUS/zdrowotnej;
- `TEST_4` — nieujemne podstawy i carry-over;
- `TEST_5` — zgodny podatek IP;
- `TEST_6` — zgodny podatek łączny;
- `TEST_7` — zgodna metoda MIX;
- `TEST_8` — jawny NEXUS kwalifikowanego MIX;
- `TEST_9` — opis projektu przy przychodzie.

Model nie zmienia FAIL na PASS.

## 11. REVIEW

| Fakt | Kod |
|---|---|
| `w_above_95` | `REVIEW_01` |
| `w_below_50` | `REVIEW_02` |
| `multiple_projects_or_ips` | `REVIEW_04` |
| `w_jump_above_30pp` | `REVIEW_08` |
| `single_positive_revenue_client` | `REVIEW_09` |
| `uses_kis_interpretation` | `REVIEW_16` |
| `kis_implementation_requires_confirmation` | `REVIEW_17` |

## 12. Kontrakt modelu

Python wyznacza liczby, klasyfikacje, TEST-y i `decision_facts`. Model zwraca wyłącznie:

```json
{"status":"FINAL","stops":[],"reviews":["REVIEW_09"]}
```

Aplikacja składa i waliduje raport. Model nie analizuje surowych danych ponownie i nie dodaje pól. `status=STOPPED`, gdy `stops` nie jest puste; inaczej `FINAL`.
