# Algorytm IP Box — kontrakt deterministyczny-first

> Narzędzie wspiera przygotowanie i kontrolę danych. Nie zastępuje interpretacji indywidualnej ani porady podatkowej. Reguły roczne są wersjonowane dla lat 2019–2026; rok spoza zweryfikowanego zakresu jest blokowany.

## 1. Zasady nadrzędne

1. Wszystkie liczby, klasyfikacje, STOP-y i REVIEW-y wyznacza kod Python.
2. Brak danych, źródła, semantyki lub dowodu nie może być automatycznie zamieniony na zero ani na korzystne założenie.
3. Rozdzielaj niezależne decyzje:
   - kwalifikację przychodu;
   - podział przychodu IP/NIE;
   - kwalifikację wydatku jako KUP;
   - alokację KUP `IP` / `MIX` / `NON`;
   - przypisanie kosztu do NEXUS A/B/C/D albo poza NEXUS;
   - podział dochodu IP przez NEXUS na część preferencyjną i zwykłą.
4. `W`, klucz `MIX` i NEXUS są trzema różnymi mechanizmami.
5. Interpretacja KIS lub inna polityka może zmienić metodę tylko wtedy, gdy ma identyfikator źródła i ślad zgodnego wdrożenia.
6. Źródłowa KPiR, ewidencja IP Box, kalkulacja oraz złożone zeznanie są osobnymi artefaktami i muszą być uzgodnione.
7. Testy i przykłady używają wyłącznie niezależnych danych syntetycznych. Nie zapisuj danych podatnika, kontrahentów, identyfikatorów, prywatnych sygnatur ani dokładnych historycznych rozliczeń.
8. Provider LLM nie jest źródłem reguł podatkowych. Model kopiuje wyłącznie gotową kopertę decyzji.
9. Pola roku przyjmują wyłącznie rzeczywisty typ całkowity; tekst, liczba zmiennoprzecinkowa i boolean są błędami wejścia.
10. Flagi kwalifikacji przyjmują wyłącznie rzeczywiste wartości boolean. Tekst `"false"`, `"nie"` lub `"0"` nie jest konwertowany.

## 2. STOP-y

| Fakt | Kod |
|---|---|
| nieobsługiwana forma opodatkowania | `STOP_01` |
| brak kwalifikowanego prawa przy zadeklarowanym IP Box | `STOP_02` |
| brak kwalifikowanego dochodu po kompletnej analizie | `STOP_03` |
| brak działalności B+R | `STOP_04` |
| brak wymaganej ewidencji | `STOP_08` |
| niespójna alokacja przychodu | `STOP_09` |
| procent faktury zastosowany dwukrotnie | `STOP_10` |
| zmiana metody bez dowodu | `STOP_11` |
| brak uzgodnienia ewidencji i zeznania | `STOP_12` |
| niedostępne historycznie łączenie B+R i IP Box | `STOP_13` |
| przekroczony limit roczny | `STOP_14` |
| błędny tryb odliczenia zdrowotnego | `STOP_15` |
| nieobsługiwany rok | `STOP_16` |
| wykluczony koszt nadal ujęty w źródłowej KPiR | `SOURCE_KPIR_REQUIRES_CORRECTION` |
| podwójne ujęcie składek społecznych | `ZUS_DOUBLE_DIP` |
| podwójne ujęcie składki zdrowotnej | `HEALTH_DOUBLE_DIP` |

Po STOP-ie status wynosi `STOPPED`, a finalne wartości finansowe i klasyfikacje są zerowane. Diagnostyka źródła oraz bezpieczny `correction_preview` mogą pozostać widoczne.

## 3. Współczynnik W

Dozwolone semantyki:

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

Gdy w tym samym miesiącu `godziny_nie_IP != 0` oraz `procent_faktury_IP != 100`, pole `polityka_alokacji.W.metoda` jest obowiązkowe. Brak metody jest błędem wejścia; kod nie wybiera po cichu `conditional_product`.

Jeżeli aktywny jest najwyżej jeden z tych modyfikatorów, wszystkie obsługiwane wzory dają ten sam wynik. Adapter może wtedy użyć kanonicznej reprezentacji bez zmiany rezultatu.

Każda metoda musi spełniać `0 ≤ W ≤ 1`. `W > 95%` daje `REVIEW_01`, `W < 50%` daje `REVIEW_02`, skok powyżej 30 p.p. daje `REVIEW_08`, a wiele projektów lub IP daje `REVIEW_04`.

### Precyzja W

Jeżeli arkusz zapisuje W z dokładnością `q` punktu procentowego, minimalna koperta kontrolna dla przychodu `R` wynosi:

```text
tolerancja_W = R × q / 200 + tolerancja_zaokrągleń_kwotowych
```

Audyt najpierw sprawdza zapisane W, a potem kwotę odtworzoną z tej wartości. Stała tolerancja kilku groszy nie może zastępować koperty wynikającej z precyzji procentu i wartości przychodu.

## 4. Alokacja przychodu IP/NIE

Dozwolone metody: `dokumentowa`, `czasowa_W`, `produktowa`, `z_interpretacji`, `custom`.

Kontrola działa na najniższym dostępnym niezależnym poziomie:

1. faktury;
2. projektu lub konkretnego IP;
3. miesięcznego agregatu kwalifikujących się faktur dopiero jako fallback.

Jawne faktury NIE-IP są oddzielane przed użyciem W. Suma strumieni musi zachować przychód źródłowy. Podwójne zastosowanie procentu aktywuje `STOP_10`, a nieudokumentowana zmiana metody `STOP_11`.

Dodatni przychód IP wymaga jawnego `kwalifikowane_IP: true`; brak pola nie oznacza potwierdzenia prawa. Przy metodzie `dokumentowa` każda kwalifikująca faktura wymaga jawnej `kwota_IP` albo `całość_IP: true`. Brak podziału nie oznacza 100% IP.

## 5. KUP i źródłowa KPiR

Najpierw ustal, czy wydatek jest KUP. Dopiero potem wybierz koszyk dochodowy:

- `IP` — KUP bezpośrednio i udokumentowanie przypisany do dochodu IP;
- `MIX` — wspólny lub pośredni KUP;
- `NON` — KUP działalności, lecz nie-IP;
- `WYKLUCZONE` — wydatek prywatny, niededukowalny albo nieujmowany jednorazowo.

Jawne `KUP: false`, `kup: false` lub `deductible: false` ma pierwszeństwo przed opisem oraz wcześniejszym koszykiem:

```text
basket       = WYKLUCZONE
ip_amount    = 0
non_ip_amount = 0
nexus_amount = 0
```

Jeżeli taki wydatek pozostaje w źródłowej KPiR:

```text
source_ledger_audit.status = REQUIRES_CORRECTION
stop = SOURCE_KPIR_REQUIRES_CORRECTION
```

Samo pominięcie pozycji w kalkulatorze nie oznacza korekty KPiR.

Opis kosztu może utworzyć wyłącznie sygnał `NON_DEDUCTIBLE_CANDIDATE`. Samo słowo lub fragment nazwy kontrahenta nie ustala `KUP: false`, nie zeruje kosztu i nie uruchamia korekty KPiR.

## 6. Alokacja kosztów MIX

Każda polityka przechowuje:

```yaml
metoda: ...
źródło: ...
źródło_ref: ...
uzasadnienie: ...
rounding_granularity: per_cost_item | monthly_pool
```

Przy `źródło: interpretacja_KIS` identyfikator `źródło_ref` musi pochodzić z danych lub dokumentu. Kod nie hardcoduje prywatnej sygnatury.

### `przychodowa_roczna`

```text
klucz_MIX = przychód_IP_roczny / przychód_całkowity_roczny
MIX_IP    = MIX × klucz_MIX
MIX_NIE   = MIX - MIX_IP
```

Koszty miesięczne są `DEFERRED` do rocznego true-up. Pozycyjny `allocation_key` lub `allocation_method` jest w tej metodzie sprzecznym wejściem i musi zostać odrzucony.

### `przychodowa_w_dacie_kosztu`

```text
klucz_miesiąca = przychód_IP_miesiąca / przychód_całkowity_miesiąca
koszt_IP        = koszt_MIX × klucz_miesiąca
koszt_NIE       = koszt_MIX - koszt_IP
```

Ta metoda nie jest W i nie wolno zmieniać jej nazwy tylko dlatego, że wartości procentowe przypadkiem są równe. Mianownik miesięczny używa tej samej definicji przychodu całkowitego co rozliczenie roczne, w tym dodatnich różnic kursowych zaliczanych do przychodu `NIE`.

### Zaokrąglenia

- `per_cost_item` — każda pozycja jest mnożona i zaokrąglana osobno;
- `monthly_pool` — najpierw zaokrąglana jest miesięczna pula, a grosze są rozdzielane metodą największych reszt.

Przy `monthly_pool` suma pozycyjnych `ip_amount` musi dokładnie odpowiadać zaokrąglonej puli. `rounding_adjustment` zachowuje ślad rozdzielenia groszy.

## 7. NEXUS

```text
NEXUS = min(1, ((A + B) × 1,3) / (A + B + C + D))
```

- A — własna działalność B+R;
- B — wyniki B+R od podmiotu niepowiązanego;
- C — wyniki B+R od podmiotu powiązanego;
- D — nabycie kwalifikowanego IP.

KUP i NEXUS są odrębnymi testami. Koszt może obniżać dochód, ale pozostać poza NEXUS.

A/B/C/D wymaga jawnego `nexus_evidence`. `allocation_source` dowodzi alokacji dochodowej i nie jest automatycznie kopiowane jako dowód NEXUS. Koszt MIX wymaga dodatkowo `nexus_basis`:

- `explicit_amount`;
- `allocated_ip_cost`.

Brak dowodu nie tworzy A/B/C/D heurystycznie. Pozycja trafia do `poza_nexus`, otrzymuje `NEXUS_EVIDENCE_MISSING` oraz `REVIEW_18`. Wynik może pozostać `FINAL`, ponieważ nieudowodniona część dochodu jest opodatkowana zwykłą stawką, a nie zerowana.

## 8. Podział dochodu przez NEXUS

Po ewentualnym odliczeniu dopuszczalnej ulgi B+R od dochodu IP:

```text
dochód_IP_po_BR = dochód_IP - ulga_BR_IP_wykorzystana

dochód_IP_kwalifikowany = dochód_IP_po_BR × NEXUS
dochód_IP_poza_preferencją = dochód_IP_po_BR - dochód_IP_kwalifikowany
```

Część preferencyjna jest opodatkowana stawką 5%:

```text
podstawa_IP = zaokrąglij(dochód_IP_kwalifikowany)
podatek_IP  = zaokrąglij(podstawa_IP × 5%)
```

Część poza preferencją jest zwykłym dochodem działalności:

```text
dochód_zwykły_przed_odliczeniami = dochód_NIE + dochód_IP_poza_preferencją
```

Następnie stosuje się właściwe dla formy opodatkowania straty, składki, ulgi i zwykłą stawkę. Nigdy nie wolno obliczać całego podatku jako wyłącznie `dochód_IP × NEXUS × 5%`.

Przykład syntetyczny dla podatku liniowego:

```text
dochód_IP = 10 000
NEXUS = 0,65

kwalifikowany = 6 500 → 325 podatku 5%
poza preferencją = 3 500 → 665 podatku 19%
razem = 990
```

Dla `NEXUS = 0` cały dochód IP trafia do zwykłej podstawy; podatek nie może wynosić zero tylko z powodu braku preferencji.

Raport pokazuje jawnie:

- `dochód_IP_po_uldze_BR`;
- `dochód_IP_kwalifikowany`;
- `dochód_IP_poza_preferencją`;
- `podstawa_IP`;
- `podstawa_zwykła`;
- podatek preferencyjny, zwykły i łączny.

Pole zgodnościowe `podstawa_NIE` reprezentuje całą zwykłą podstawę i może zawierać część IP poza preferencją.

## 9. Waluty

Dla faktur walutowych zapisz walutę, daty wystawienia i płatności, kursy NBP z właściwych poprzednich dni roboczych oraz źródła kursów. Lookup zapisuje rzeczywistą datę tabeli znalezioną po cofnięciu przez dni wolne, a nie wyłącznie datę pierwotnie żądaną. Różnice kursowe są wyliczane, nie wpisywane ręcznie. Dodatnia różnica zwiększa przychód NIE, a ujemna staje się kosztem `NON`.

## 10. Reguły roczne i ulgi

Obsługiwane są lata 2019–2026. Limity IKZE, sposób rozliczenia zdrowotnej, skala podatkowa oraz dopuszczalność jednoczesnego B+R/IP Box pochodzą z wersjonowanego katalogu reguł.

Kwoty ponad limit nie są cicho obcinane. Nieobsługiwany rok nie używa zasad roku sąsiedniego. Dodatnia darowizna wymaga jawnego, zweryfikowanego limitu kwotowego właściwego dla jej kategorii; kalkulator odrzuca brak limitu i jego przekroczenie.

Termomodernizacja używa rocznikowych pul, najstarszych najpierw. Raportuje osobno wykorzystanie, carry-over i wygaśnięcie. Niezmieniony podatek po korekcie może zostać stwierdzony tylko wtedy, gdy poprawiona kwota odliczenia mieści się w dostępnej puli i została uwzględniona w korekcie.

## 11. Uzgodnienie dokumentów

Porównaj osobno:

```text
przychód_IP_ewidencja   == przychód_IP_zeznanie
przychód_NIE_ewidencja  == przychód_NIE_zeznanie
koszt_IP_ewidencja      == koszt_IP_zeznanie
koszt_NIE_ewidencja     == koszt_NIE_zeznanie
termomodernizacja_użyta  == termomodernizacja_w_zeznaniu
podatek_łączny           == podatek_w_zeznaniu
nadpłata_lub_dopłata     == rozliczenie_w_zeznaniu
```

Równość samych sum globalnych nie wystarcza. Przesunięcie między IP i NIE albo pozostawienie NON-KUP w kosztach aktywuje właściwy STOP.

`correction_preview` może pokazać poprawioną matematykę przy korekcyjnym STOP-ie, ale nie jest wynikiem finalnym.

## 12. TEST 1–9

Python ustala:

- `TEST_1` — bilans danych źródłowych;
- `TEST_2` — brak prywatnych wydatków zadeklarowanych jako firmowe;
- `TEST_3` — brak podwójnego ZUS lub zdrowotnej;
- `TEST_4` — nieujemne podstawy i carry-over;
- `TEST_5` — poprawny podatek 5% od kwalifikowanej podstawy IP;
- `TEST_6` — poprawny podatek zwykły, preferencyjny i łączny;
- `TEST_7` — zgodna metoda MIX;
- `TEST_8` — jawny dowód i kwota NEXUS;
- `TEST_9` — opis projektu przy przychodzie.

## 13. REVIEW

| Fakt | Kod |
|---|---|
| W powyżej 95% | `REVIEW_01` |
| W poniżej 50% | `REVIEW_02` |
| wiele projektów lub IP | `REVIEW_04` |
| skok W powyżej 30 p.p. | `REVIEW_08` |
| jeden klient z dodatnim przychodem | `REVIEW_09` |
| użycie interpretacji KIS | `REVIEW_16` |
| konieczność potwierdzenia wdrożenia KIS | `REVIEW_17` |
| brak dowodu dla deklarowanego kosztu NEXUS | `REVIEW_18` |

## 14. Kontrakt modelu

Python tworzy kompletną kopertę:

```json
{
  "expected_decision": {
    "status": "FINAL",
    "stops": [],
    "reviews": ["REVIEW_09"]
  }
}
```

Model widzi tylko tę kopertę i zwraca dokładną kopię trzech pól:

```json
{"status":"FINAL","stops":[],"reviews":["REVIEW_09"]}
```

Model nie liczy podatku, W, KUP, MIX, NEXUS ani ulg. Nie dodaje, nie usuwa, nie przenosi i nie deduplikuje kodów. Lokalna schema, parser, oracle i evaluator pozostają źródłem prawdy.
