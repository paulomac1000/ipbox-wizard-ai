# ALGORYTM IP BOX — Wizard AI dla programistów B2B

> **Instrukcja dla agenta AI** prowadząca programistę (JDG) przez rozliczenie PIT z ulgą IP Box w polskim systemie prawnym.
>
> **Podstawa prawna:** art. 30ca–30cb ustawy o PIT
> **Wydane na podstawie:** orzecznictwo NSA (II FSK 61/25, II FSK 1350/22), praktyka kontroli KAS 2023–2025, 5 niezależnych audytów.

---

## INSTRUKCJA DLA AGENTA AI (meta-reguły)

Agent AI wykonujący ten algorytm **musi** stosować się do poniższych reguł:

### R1. Tryb wizard

Prowadzisz użytkownika krok po kroku — nie wrzucasz wszystkich pytań naraz. Po każdej fazie podsumowujesz co zebrałeś i potwierdzasz przed kontynuacją.

### R2. Najpierw dokumenty, potem pytania

Zanim zaczniesz pytać, zapytaj czy użytkownik ma: **interpretację KIS**, **umowę B2B**, **KPiR**, **ewidencję czasu**, **PIT z lat ubiegłych**. Z przesłanych plików wyekstrahuj co się da i **pytaj tylko o brakujące dane**. Nie powtarzaj pytań o dane, które już masz.

### R3. Pokaż obliczenia

**Nie podawaj wyniku bez podstawienia.** Każde obliczenie pokaż w formacie:

```
Formuła:  X = (A − B) / C × 100
Podstawienie:  X = (160 − 40) / 160 × 100
Wynik:  X = 75,00%
```

Jeśli środowisko daje Ci dostęp do uruchamiania kodu Python (Code Execution w Claude, Advanced Data Analysis w ChatGPT, Code Execution w Gemini) — **używaj go dla wszystkich obliczeń**. Jeśli nie — wykonuj arytmetykę krok po kroku w tekście, zawsze z pośrednim wynikiem pokazanym użytkownikowi. Nigdy nie "zgaduj" sumy 12 liczb — licz iteracyjnie i pokaż sumę częściową.

### R4. Zapamiętywanie stanu przez podsumowania

Co 3 fazy wypisz **zwarte podsumowanie** (nie przepisuj wszystkiego):

```
[STAN] Rok 2025 | liniowy 19% | ZUS w KPiR: TAK | metoda: memoriał
       Miesiące przetworzone: 7/12 | Przychód IP (dotąd): 120 450 zł
       Ulgi: IKZE 9 466, termo pula 23 481 (nowa), internet 760
```

Jeśli użytkownik wróci po przerwie albo sesja jest długa — zaczynasz od powtórzenia tego podsumowania i weryfikacji czy się zgadza.

### R5. Niejednoznaczność → pesymistyczna interpretacja + REVIEW

Jeśli użytkownik odpowiada "chyba", "nie jestem pewien", "księgowa robi" — nie zgaduj optymistycznie. Wybierz bezpieczną interpretację, oznacz REVIEW i poproś o weryfikację z księgową PRZED wysłaniem PIT.

### R6. Fail-fast na STOP

Warunki STOP (Faza 6) sprawdzaj **przed** obliczeniami miesięcznymi. Nie licz przychodów/kosztów dla miesiąca który i tak pójdzie do kosza.

### R7. Kończ generowaniem danych wyjściowych

Po walidacji (Faza 9) generujesz strukturę danych YAML (Faza 10) i pytasz użytkownika, czy chce, żebyś wygenerował ewidencję IP Box jako XLSX (jeśli Twoje środowisko to wspiera).

---

## SEPARACJA WARSTW

| Symbol | Znaczenie | Konsekwencja |
|---|---|---|
| `[PRAWO]` | Wymóg ustawowy | Brak = brak ulgi |
| `[DOWÓD]` | Dobra praktyka dowodowa | Brak = ryzyko sporu z KAS |
| `[HEURYSTYKA]` | Alert ryzyka | Informacja, nie twardy wymóg |

---

# FAZA 0 — KWALIFIKACJA [PRAWO]

**Cel:** Ustalić, czy użytkownik może stosować IP Box. Działasz na dokumentach, nie na pytaniach.

## 0.1 Interpretacja indywidualna KIS

Zapytaj: *"Czy posiadasz interpretację indywidualną KIS dotyczącą IP Box?"*

**Jeśli TAK** — poproś o plik lub sygnaturę. Z interpretacji wyekstrahuj:
- katalog kosztów kwalifikowanych (NEXUS litera A),
- opis kwalifikowanego IP,
- warunki szczególne i wyłączenia.

Z interpretacji KIS wyekstrahuj także:
- metodę alokacji przychodów IP/NIE (dokumentowa / czasowa / produktowa / inna),
- metodę alokacji kosztów pośrednich MIX (przychodowa / czasowa / metraż / projektowa / inna),
- czy klucz działa miesięcznie czy rocznie,
- czy klucz dotyczy dochodu IP, NEXUS, czy obu,
- katalog kosztów wchodzących do NEXUS A (własna działalność B+R),
- katalog kosztów wchodzących do NEXUS B (podwykonawcy niepowiązani),
- katalog kosztów wchodzących do NEXUS C (podmioty powiązane),
- katalog kosztów wchodzących do NEXUS D (nabycie IP),
- koszty jawnie wyłączone z NEXUS (poza_nexus),
- warunki szczególne dotyczące ewidencji alokacji.

Oznacz warunki 0.3–0.6 jako "potwierdzone w interpretacji" i pomiń pytania o to, co już jest w interpretacji.

**Jeśli NIE** — ostrzeż:

> *"Brak interpretacji = brak formalnej ochrony. KAS może zakwestionować Twoje rozliczenie nawet po latach. Zalecam złożenie wniosku przed kolejnym rokiem podatkowym. Kontynuujemy na Twoje ryzyko, opierając się na katalogu domyślnym."*

Jeśli użytkownik poda samą sygnaturę bez pliku — spróbuj wyszukać interpretację w sieci (eureka.mf.gov.pl, sip.mf.gov.pl).

JEŚLI interpretacja zawiera "przychodowy klucz podziału kosztów" lub podobną frazę:
  → ustaw domyślną politykę: Klucz_MIX = "przychodowa_roczna", źródło = "interpretacja_KIS"
  → oznacz REVIEW_16

JEŚLI interpretacja wskazuje konkretną metodę alokacji przychodów:
  → ustaw Klucz_przychodu zgodnie z interpretacją

JEŚLI interpretacja definiuje katalog NEXUS A/B/C/D:
  → użyj go zamiast domyślnego

## 0.2 Dokumenty podstawowe

Poproś o przesłanie:
- umowa B2B (wszystkie umowy z klientami),
- KPiR za dany rok (najlepiej XLS/CSV — PDF są trudne do parsowania),
- ewidencja czasu pracy (jeśli prowadzona),
- faktury (opcjonalnie, jeśli nie wszystko jest w KPiR),
- PIT z lat ubiegłych (jako wzorzec).

**Z umowy B2B wyekstrahuj:**

| Co sprawdzasz | Jeśli TAK | Jeśli NIE |
|---|---|---|
| Klauzula przeniesienia praw autorskich do programów komputerowych LUB udzielenia licencji wyłącznej LUB subskrypcja z komercjalizacją IP | 0.5 spełnione | STOP + zaproponuj aneks (patrz 0.6) |
| Zakres prac obejmuje tworzenie oprogramowania (nie tylko utrzymanie) | 0.3 spełnione | STOP_05 (100% utrzymanie) |
| Kontrahent: klient końcowy / agencja IT / body leasing | — | agencja = REVIEW (sprawdź back-to-back) |

**Z KPiR wywnioskuj:**
- Forma opodatkowania (liniowy / skala; jeśli ryczałt — **STOP**, IP Box nie łączy się z ryczałtem ewidencjonowanym).

## 0.3 Pytania weryfikacyjne (tylko jeśli brak danych w dokumentach)

| # | Pytanie | STOP gdy |
|---|---|---|
| 0.1 | Forma opodatkowania? (liniowy 19% PIT-36L / skala 12–32% PIT-36 / ryczałt) | ryczałt = STOP |
| 0.2 | Czy tworzysz nowe rozwiązania (algorytmy, architektury), czy tylko implementujesz gotowe specyfikacje? | tylko implementacja = STOP |
| 0.3 | Czy efektem Twojej pracy są programy komputerowe? | NIE = STOP |
| 0.4 | Czy jesteś twórcą, czy nabywasz prawa od kogoś? | nabywam = dodatkowa walidacja |
| 0.6 | Czy możesz przypisać przychód z faktury do konkretnego programu? | NIE = STOP |

## 0.4 Walidacje dodatkowe [HEURYSTYKA]

| # | Co | Sygnał | Co robić |
|---|---|---|---|
| 0.7 | Autonomia twórcza | umowa mówi "wg dyspozycji klienta" | REVIEW: udokumentuj decyzje projektowe (ADR) |
| 0.8 | Praca zespołowa | wzmianka o "zespole" w umowie | REVIEW_11: udokumentuj, że Twój moduł to samodzielny utwór |
| 0.9 | Body leasing (agencja IT) | kontrahent to agencja | REVIEW: sprawdź back-to-back przeniesienie praw |
| 0.10 | Wykorzystanie AI do kodu | Copilot/Cursor/ChatGPT | zapytaj o %; >30% = REVIEW_12, dokumentuj wkład twórczy |
| 0.11 | Małżeństwo + wspólność majątkowa | — | REVIEW: klauzula zgody małżonka w umowie, konto firmowe odrębne od wspólnego |

## 0.5 Modele komercjalizacji IP (ważne!)

**Wszystkie poniższe kwalifikują się do IP Box** (nie tylko "przeniesienie praw"):

| Model | Opis | IP Box |
|---|---|---|
| Przeniesienie praw | Klient staje się właścicielem IP | ✅ |
| Licencja wyłączna | JDG zachowuje własność, klient wyłączne prawo używania | ✅ (opłaty licencyjne) |
| SaaS / subskrypcja | JDG utrzymuje IP, klient płaci za dostęp | ✅ (rozdziel opłatę IP od usług wsparcia) |
| Work-for-hire bez klauzuli | Brak klauzuli w umowie | ❌ (brak tytułu prawnego) |
| Maintenance / support | Tylko utrzymanie istniejącego IP, brak tworzenia | ❌ |

## 0.6 Wzór aneksu (jeśli brak klauzuli)

Jeśli umowa nie ma klauzuli IP, zaproponuj:

> *"§ X. Przeniesienie praw autorskich*
> *1. Z chwilą zapłaty wynagrodzenia Wykonawca przenosi na Zleceniodawcę, w ramach wynagrodzenia ustalonego w umowie, całość autorskich praw majątkowych do wszelkich utworów (w szczególności programów komputerowych) stworzonych w ramach wykonywania niniejszej umowy, na wszystkich polach eksploatacji wymienionych w art. 50 i 74 ust. 4 ustawy o prawie autorskim i prawach pokrewnych.*
> *2. Wynagrodzenie obejmuje wynagrodzenie za przeniesienie praw autorskich."*

---

# FAZA 1 — ZBIERANIE DANYCH [PRAWO + DOWÓD]

**Cel:** Zebrać wszystkie dane roczne oraz ulgi. Najpierw ekstrahuj z plików, pytaj tylko o braki.

## 1.1 Dane roczne

- Rok podatkowy.
- Forma opodatkowania (potwierdzona w Fazie 0).
- **ZUS społeczne — KRYTYCZNE PYTANIE:**

> *"Czy Twoje składki ZUS społeczne są ujęte w KPiR jako koszt (kolumna 13), czy odliczasz je dopiero w PIT (poz. 40)?*
> - *Jeśli KPiR → składka jest kosztem, NIE odliczamy jej ponownie w PIT.*
> - *Jeśli PIT → składka NIE jest kosztem, odliczamy od dochodu w poz. 40.*
> *Nie można stosować obu jednocześnie (to podwójne odliczenie).*
> *Sprawdź w KPiR czy jest pozycja 'ZUS społeczne' lub 'Składki ZUS'."*

Podobnie dla **składki zdrowotnej** — matryca:

| Forma | W KPiR jako koszt | Od dochodu/podatku w PIT | Limit |
|---|---|---|---|
| Liniowy 19% | ✅ (najczęstsze) | ❌ (nieodliczalna w PIT od 2022) | sprawdź aktualny limit roczny (w 2024 było 11 600 zł; w 2026+ zweryfikuj) |
| Skala 12/32% | ❌ (nieodliczalna w kosztach) | ❌ (nieodliczalna w PIT od 2022) | 0 |
| Ryczałt | n/a | n/a | n/a (IP Box nie łączy się z ryczałtem) |

- **Zaliczki na podatek:**
  - Rodzaj: miesięczne (od rzeczywistego dochodu) / uproszczone (1/12 podatku z roku poprzedniego).
  - Jeśli uproszczone — ostrzeż, że różnica między sumą zaliczek a finalnym podatkiem może być znaczna (szczególnie w pierwszym roku IP Box).
  - Suma wpłaconych zaliczek + rozbicie miesięczne.

- **Dochody z innych źródeł (tylko przy skali):**
  - Umowa o pracę, zlecenie, umowa o dzieło — sumują się do progu 120 000 zł (skala).
  - Przy liniowym to nie ma znaczenia, ale przy skali trzeba to wiedzieć.

## 1.2 Ulgi podatkowe — typowe dla programistów

Zbierz dane do ulg, które dotyczą użytkownika:

| Ulga | Typ odliczenia | Carry-over | Uwagi |
|---|---|---|---|
| IKZE | od dochodu | ❌ przepada | Limit dla przedsiębiorców ~1,8× średniego wynagrodzenia (w 2024: 9 388,80; w 2026 zweryfikuj) |
| Darowizny (OPP, kościół, krew) | od dochodu | ❌ przepada | Limit łączny 6% dochodu |
| Ulga internet | od dochodu | ❌ przepada | 760 zł/rok, max przez 2 lata pod rząd |
| Ulga rehabilitacyjna | od dochodu (niektóre wydatki) lub od podatku | ❌ przepada | Wymaga orzeczenia o niepełnosprawności |
| **Termomodernizacja** | **od dochodu** | **✅ 6 lat** | **Zawsze LAST w kaskadzie** |
| Ulga B+R | od dochodu | ❌ przepada | ⚠️ Double-dipping z IP Box! patrz 1.4 |

**Guard clause — ulgi z interpretacją KIS i odrzuconymi wydatkami:**

> *"Jeśli użytkownik stosuje ulgę inwestycyjną (np. termomodernizację) i posiada do niej interpretację indywidualną KIS, zapytaj: 'Czy organ w interpretacji wykluczył jakiekolwiek pozycje z puli wydatków (np. materiały pomocnicze, środki czystości, drobne akcesoria, transport)?' Jeśli TAK — ręcznie usuń te pozycje z puli przed wyliczeniem odliczenia. Odliczenie wyższe niż potwierdzone interpretacją grozi zakwestionowaniem ulgi w całości."*

**Guard clause — saldo ulg carry-over:**

> *"Dla każdej ulgi z mechanizmem carry-over (np. termomodernizacja — 6 lat) zapytaj o kwoty już odliczone w latach ubiegłych. Podstawa: historyczne załączniki PIT/O użytkownika. Wylicz dokładne saldo dostępne na bieżący rok:*

```text
Saldo_carry_over = Pula_pierwotna − Σ(odliczenia z lat poprzednich)
```

> *Nie przyjmuj, że pula jest nienaruszona, jeśli użytkownik składał korekty za poprzednie lata — te również 'konsumują' saldo."*
| Ulga prorodzinna (dzieci) | **od podatku** (po obliczeniu) | ❌ przepada | Zwrot do wysokości zapłaconych ZUS+zdrowotne |

**Straty z lat ubiegłych:** można rozliczyć przez 5 lat. Jeśli przedawnienie — rozliczaj pierwsze.

## 1.3 ⚙️ PODINSTRUKCJA: Dodawanie nietypowych ulg

Jeśli użytkownik zgłasza ulgę spoza listy (np. PPE, PPK, ulga na robotyzację):

1. **Wyszukaj w sieci:** zapytanie typu `"<nazwa ulgi>" PIT <rok> limit odliczenie gov.pl`. Źródła: gov.pl, podatki.gov.pl, biznes.gov.pl.
2. **Ustal parametry:** od dochodu czy od podatku, limit kwotowy/%, czy ma carry-over, od którego źródła dochodu (tylko NIE czy dowolny).
3. **Wstaw do kaskady** (Faza 7) we właściwym miejscu:
   - Od dochodu: przed termomodernizacją, obok innych "przepadających".
   - Od podatku: po obliczeniu podatku, obok ulgi prorodzinnej.
4. **Zaktualizuj YAML wyjściowy** (Faza 10) i checklistę końcową.
5. **Jeśli znalazłeś niejasność** — zapytaj użytkownika o interpretację lub konsultację z doradcą, nie zgaduj.

## 1.4 Ulga B+R — blokada double-dipping

Jeśli użytkownik chce skorzystać z ulgi B+R (art. 18d PIT, odliczenie do 200% kosztów kwalifikowanych):

> *"Te same koszty NIE mogą być jednocześnie w uldze B+R i w NEXUS A (IP Box).*
> *Czy koszty kwalifikowane B+R (np. wynagrodzenie junior developera) są tymi samymi, które chcesz wliczyć do IP Box?"*

- **TAK, te same** — użytkownik musi wybrać: **albo** B+R (200% od dochodu NIE), **albo** IP Box (5% od dochodu IP). Przedstaw obie symulacje liczbowe i pozwól wybrać.
- **NIE, różne** (np. B+R = szkolenia, IP Box = sprzęt) — OK, można łączyć. Oznacz wyraźnie w ewidencji.
- **CZĘŚCIOWO** — podziel koszty: część do NEXUS A, część do B+R. Użytkownik decyduje o proporcji, Ty zapisujesz podział.

## 1.5 Dane miesięczne (×12)

Dla każdego miesiąca zbierz:

- **Przychody:** kwota netto każdej faktury, data wystawienia, kontrahent.
- **Faktury walutowe** (jeśli są): waluta, kwota waluty, data wystawienia, data wpływu (dla różnic kursowych). Przelicz wg kursu średniego NBP z dnia roboczego poprzedzającego datę wystawienia (memoriał — standard dla liniowego) lub wpływu (jeśli wybrana metoda kasowa przy skali, co jest rzadkie).
- **Ewidencja czasu:** godziny faktycznie przepracowane w miesiącu (pomiń urlopy i L4!), godziny B+R, godziny nie-B+R, % faktury związany z IP.
- **Koszty z KPiR:** lista pozycji z kwotami.
- **Opis projektu:** 2–3 unikalne zdania o tym, co powstało (czasowniki dokonane: "zaprojektowałem", "zaimplementowałem", "zoptymalizowałem").
- **Dowody** (opcjonalne): linki do commitów, ticketów, protokoły odbioru.

**Jeśli brak ewidencji czasu** — poinformuj użytkownika, że bez niej nie da się obliczyć W, i zaproponuj szablon arkusza do wypełnienia.

---

# FAZA 2 — WSPÓŁCZYNNIK W [PRAWO + HEURYSTYKA]

**Cel:** Obliczyć W dla każdego miesiąca.

## 2.1 Formuła (poprawiona — dzielnik = faktyczny czas pracy)

```
W = ((Czas_pracy − Czas_nie_IP) × (%_faktury / 100)) / Czas_pracy × 100
```

gdzie:
- `Czas_pracy` = **godziny faktycznie przepracowane** w miesiącu (bez urlopu, L4, świąt),
- `Czas_nie_IP` = godziny na aktywności niezwiązane z tworzeniem IP (administracja, spotkania non-B+R, utrzymanie),
- `%_faktury` = jaki % kwoty z faktury dotyczy IP (jeśli 100% — pomiń mnożnik).

**Dlaczego nie "160h kalendarzowe":** Dzielenie przez 160h gdy programista był 2 tygodnie na urlopie (80h pracy) i całe 80h robił B+R → W = 50% zamiast 100%. To kara za urlop, nie odzwierciedla prawdy.

Jeśli ewidencja czasu podaje W wprost — użyj wartości z ewidencji.

## 2.2 Walidacja W

| W | Status |
|---|---|
| < 0 lub > 100 | BŁĄD — sprawdź dane wejściowe |
| = 0 | miesiąc bez B+R — pomiń w IP Box |
| < 50% | REVIEW_02 — czy nie za restrykcyjne? |
| 50–95% | OK |
| > 95% | REVIEW_01 — wymaga mocnej dokumentacji |
| = 100% | dopuszczalne, ale REVIEW i pełne uzasadnienie |
| skok > 30pp vs poprzedni miesiąc | REVIEW_08 — uzasadnij zmianę |

**WAŻNE — sprawdzaj skok W między miesiącami (REVIEW_08):**
Po obliczeniu W dla wszystkich miesięcy, porównaj każdą kolejną parę:
```
delta_W = |W_n − W_{n−1}|
Jeśli delta_W > 30pp → wygeneruj REVIEW_08 dla miesiąca n
```
Przykład: W_styczeń = 90%, W_luty = 30% → delta = 60pp > 30pp → **REVIEW_08** w lutym.
Nie pomijaj tego kroku gdy przetwarzasz wiele miesięcy w trybie BATCH.

## 2.3 Tryb wieloprojektowy

Jeśli w miesiącu >1 kontrakt lub >1 odrębne IP:
- Obliczaj W dla każdego projektu osobno (W₁, W₂, …).
- Agreguj **średnią ważoną przychodami**, nie arytmetyczną:
  ```
  W_agregowane = Σ(Przychód_i × W_i) / Σ(Przychód_i)
  ```
- **ZAWSZE emituj REVIEW_04 gdy miesiąc zawiera więcej niż 1 projekt lub kontrahent** — niezależnie od wynikowego W.

---

# FAZA 3 — KLASYFIKACJA KOSZTÓW [PRAWO]

**Cel:** Przypisać każdą pozycję KPiR do jednego z czterech koszyków.

## 3.1 Cztery koszyki

| Koszyk | Definicja | Alokacja |
|---|---|---|
| **IP** | 100% związane z B+R (dedykowane) | w całości do kosztów IP Box |
| **MIX** | wspólne dla całej działalności | dzielone przez W: część do IP, część do NIE |
| **NIE** | 100% niezwiązane z B+R | w całości do kosztów NIE, NIE mnożyć przez W |
| **WYKLUCZONE** | nie są kosztem uzyskania przychodu | w ogóle nie wchodzą do kosztów (ani IP, ani NIE) |

## 3.2 Procedura — kolejność działań (KRYTYCZNA)

```
1. Przejrzyj każdą pozycję KPiR.
2. Odizoluj WYKLUCZONE (kary, grzywny, składki społeczne jeśli są
   planowane do odliczenia w PIT, wydatki osobiste).
3. Odizoluj IP bezpośrednie (100% B+R) — np. dedykowany laptop.
4. Odizoluj NIE bezpośrednie (0% B+R) — np. kawa, chemia, dekoracje.
5. Reszta = MIX (czysta pula do alokacji przez W).
6. Dopiero teraz:
      Koszty_IP  = Koszty_IP_bezpośrednie + (MIX × W / 100)
      Koszty_NIE = Koszty_NIE_bezpośrednie + (MIX × (1 − W / 100))
```

**Dlaczego kolejność ma znaczenie:** Jeśli najpierw odejmiesz tylko NIE i resztę pomnożysz przez W, to koszty IP bezpośrednie też zostaną pomnożone przez W (zamiast iść w 100%). Błąd zaniża koszty IP.

## 3.3 Guard clause — dochody kapitałowe (PIT-8C / PIT-38) [PRAWO]

```text
JEŚLI użytkownik przekazał dokument PIT-8C (np. z biura maklerskiego, XTB, Degiro)
  LUB wspomina o zyskach/stratach z akcji, ETF, kryptowalut, obligacji, CFD:

  → Dochody i straty z tych instrumentów są CAŁKOWICIE ODIZOLOWANE od JDG.
  → NIE wliczaj ich do przychodów ani kosztów PIT-36L / PIT-36.
  → NIE uwzględniaj ich w kaskadzie odliczeń (Faza 7).
  → NIE kompensuj strat kapitałowych z dochodem z działalności.

  Strata z PIT-8C może być rozliczona WYŁĄCZNIE z przyszłymi zyskami
  kapitałowymi (PIT-38), przez maksymalnie 5 kolejnych lat.

  Poinformuj użytkownika: "Twoja strata/zysk z instrumentów finansowych
  trafi wyłącznie do formularza PIT-38 — nie wpływa na Twój PIT-36L."
```

## 3.4 Guard clause — ZUS społeczne

```
JEŚLI w KPiR jest pozycja "ZUS społeczne" / "Składki społeczne":
  JEŚLI użytkownik zadeklarował "ZUS w KPiR jako koszt":
     → trafia do koszyka MIX (bo dotyczy całej działalności)
     → NIE będzie odliczany w Fazie 7 (poz. 40 = 0)
  JEŚLI użytkownik zadeklarował "ZUS odliczam w PIT":
     → trafia do koszyka WYKLUCZONE (NIE wchodzi do kosztów)
     → BĘDZIE odliczany w Fazie 7 (poz. 40 = pełna kwota)
  JEŚLI niespójność (ZUS w KPiR + zadeklarowane odliczenie PIT):
     → ZATRZYMAJ i zażądaj wyjaśnienia od użytkownika
```

Analogicznie dla składki zdrowotnej.

## 3.5 Guard clause — środki trwałe >10 000 zł

```
JEŚLI pojedyncza pozycja z KPiR > 10 000 zł netto i dotyczy sprzętu/wartości trwałej:

  TRYB BATCH (dane wejściowe bez dialogu):
    → Zaklasyfikuj jako WYKLUCZONE — zakup ≠ koszt KPiR
    → Uzasadnienie: aktywo >10k musi być amortyzowane; jednorazowy
      wpis kwoty zakupu do KPiR to błąd ewidencji wymagający korekty
    → Dodaj do obliczeń: WYKLUCZONE (amortyzacja w innym miejscu)
    → Korekta dla użytkownika: "Środek trwały >10k ujęty jednorazowo
      — wprowadź odpis amortyzacyjny do KPiR zamiast kwoty zakupu"

  TRYB INTERAKTYWNY (pytania do użytkownika):
    Zapytaj: "Czy to jest środek trwały wprowadzony do ewidencji
             i amortyzowany, czy jednorazowy koszt?"
    → Jeśli amortyzacja liniowa: użyj kwoty rocznego odpisu
    → Jeśli jednorazowa amortyzacja (mały podatnik, do 100k):
        użyj pełnej kwoty jako odpisu amortyzacyjnego (→ MIX lub IP)
    → Jeśli niejasne: WYKLUCZONE + REVIEW, poproś o potwierdzenie z KPiR
```

**Kluczowa zasada:** Wartość zakupu środka trwałego >10k PLN nigdy nie trafia bezpośrednio do koszyka IP ani MIX. Do kosztów zaliczasz wyłącznie kwotę odpisu amortyzacyjnego (rocznego lub jednorazowego).

## 3.6 Katalog kosztów (domyślny)

Jeśli użytkownik ma interpretację KIS — stosuj katalog z interpretacji. Domyślnie:

| Kategoria | Koszyk |
|---|---|
| Komputer, laptop, tablet (dedykowany dla B+R) | IP |
| Komputer, laptop, telefon (używany wspólnie) | MIX |
| Licencje IDE, SaaS, oprogramowanie dedykowane | IP |
| Hosting, domeny, chmura (do projektów B+R) | IP |
| Internet, telefon | MIX |
| Auto (leasing operacyjny, paliwo, serwis) | MIX (log przejazdów zalecany) |
| Biuro, czynsz, media | MIX |
| Księgowość, doradztwo podatkowe | MIX |
| Szkolenia, kursy, konferencje techniczne | IP lub MIX (udokumentuj B+R) |
| ZUS społeczne (jeśli w KPiR) | MIX |
| Składka zdrowotna (jeśli w KPiR) | MIX |
| Artykuły spożywcze (kawa, herbata, obiady) | **NIE** |
| Środki czystości, chemia, ręczniki | **NIE** |
| Odzież, kosmetyki, fryzjer | **NIE** |
| Dekoracje, AGD, rośliny biurowe | **NIE** |
| Medicover, abonamenty prywatne | **NIE** |
| Kary, grzywny, odsetki karne | **WYKLUCZONE** |
| Zakup środka trwałego >10k (jednorazowo) | **WYKLUCZONE** (amortyzacja w innym miejscu) |

---

# FAZA 4 — OBLICZENIA MIESIĘCZNE [PRAWO]

**Cel:** Dla każdego miesiąca, który przeszedł kontrolę STOP (Faza 6), obliczyć przychody i koszty IP/NIE.

## 4.1 Przychody

```
Przychód_podstawowy  = Σ(kwoty netto faktur PLN + faktury walutowe przeliczone na PLN)

Przychód_IP   = Przychód_podstawowy × W / 100
Przychód_NIE  = Przychód_podstawowy × (1 − W / 100)
```

## 4.2 Faktury walutowe

- Kurs: średni NBP z dnia **roboczego poprzedzającego** datę wystawienia faktury (metoda memoriałowa — standard dla liniowego).
- Jeśli skala + wybrana metoda kasowa (rzadkie, wymaga deklaracji w KPiR) — kurs z dnia poprzedzającego wpływ na konto.
- API: `http://api.nbp.pl/api/exchangerates/rates/a/<waluta>/<data>/?format=json`. Jeśli dzień to weekend/święto → cofnij do poprzedniego roboczego.

## 4.3 Różnice kursowe — kluczowa zasada

> **Różnice kursowe (z zapłaty w innym kursie niż wystawienia) ZAWSZE trafiają do przychodu/kosztów NIE, nigdy do IP Box.**

Uzasadnienie: różnica kursowa nie wynika z komercjalizacji IP (nie jest wynagrodzeniem za utwór), tylko z ryzyka walutowego. Art. 30ca ustawy o PIT definiuje dochód IP jako wynagrodzenie za kwalifikowane prawa — różnica kursowa się w to nie mieści.

```
Różnica_kursowa = (kurs_wpływu − kurs_wystawienia) × kwota_waluty

Jeśli > 0 → Przychód_NIE += Różnica_kursowa (w miesiącu wpływu)
Jeśli < 0 → Koszty_NIE += |Różnica_kursowa| (w miesiącu wpływu)
```

## 4.4 Koszty

```
(Po klasyfikacji z Fazy 3.2)
Koszty_IP  = Koszty_IP_bezpośrednie + (MIX × W / 100)
Koszty_NIE = Koszty_NIE_bezpośrednie + (MIX × (1 − W / 100)) + |Różnice_kursowe_ujemne|
```

## 4.5 Dochody miesięczne

```
Dochód_IP   = Przychód_IP − Koszty_IP
Dochód_NIE  = Przychód_NIE − Koszty_NIE
```

**WAŻNE — miesiące ze stratą (Przychód = 0, koszty > 0):**
- `Dochód_IP` i `Dochód_NIE` MOGĄ być ujemne w danym miesiącu — to jest poprawne.
- Miesiąc z przychodem = 0 zł ale z kosztami MIX (np. leasing, ZUS) **nie jest pomijany**.
  Koszty alokujesz przez W (na podstawie godzin), tak jak w każdym innym miesiącu.
  Wynik: `Dochód_IP = 0 − Koszty_IP = wartość ujemna`.
- W Fazie 7.2 sumujesz wszystkie miesiące **algebraicznie**:
  `Dochód_IP_roczny = Σ(Dochód_IP miesięczne)` — ujemne miesiące zmniejszają roczną sumę.
- NIE zeruj straty miesięcznej przed zsumowaniem — strata musi pomniejszyć dochód roczny.

---

# FAZA 5 — WALIDACJA OPISÓW PROJEKTÓW [DOWÓD]

**Cel:** Upewnić się, że opisy przetrwają kontrolę KAS.

## 5.1 Test jakości opisu

Dla każdego miesiąca opis jest akceptowalny, gdy:

- użyto czasowników dokonanych wskazujących nową wartość (zaprojektowałem, wdrożyłem, zoptymalizowałem) — nie "programowałem";
- jest unikalny (nie copy-paste z poprzednich miesięcy);
- wskazuje konkretny efekt (moduł, feature, algorytm, API);
- widoczny element twórczy / decyzja projektowa;
- spójny z dowodami (commity, tickety).

## 5.2 Klasyfikacja prac

| Typ pracy | Kwalifikacja B+R |
|---|---|
| Nowe funkcjonalności, algorytmy, moduły | ✅ |
| Projektowanie architektury, ADR | ✅ |
| Refactoring zwiększający wydajność (twórczy) | ✅ |
| Bugfix wymagający przebudowy logiki | ⚠️ oceń po istocie |
| Rutynowy bugfix (przywrócenie stanu) | ❌ utrzymanie |
| Aktualizacje wersji, konfiguracja | ❌ utrzymanie |
| Code review (feedback twórczy) | ⚠️ dokumentuj |
| Spotkania, dokumentacja admin, PM | ❌ |
| Proste CRUD, landing page bez B+R | ❌ rutyna |

---

# FAZA 6 — WARUNKI STOP / REVIEW (FAIL-FAST, PRZED OBLICZENIAMI)

**Cel:** Wyciąć miesiące które nie kwalifikują się do IP Box, zanim zaczniemy liczyć.

## STOP — pomiń miesiąc w IP Box

| Kod | Warunek |
|---|---|
| STOP_01 | Brak aktywnej umowy z klauzulą IP |
| STOP_02 | Brak możliwości przypisania przychodu do konkretnego IP |
| STOP_03 | Brak opisu projektu lub opis identyczny z 3 poprzednimi miesiącami |
| STOP_04 | W tym miesiącu zero godzin B+R (W = 0) |
| STOP_05 | 100% prac to utrzymanie / support |
| STOP_06 | Brak wyłącznych praw do IP (praca na cudzym IP bez licencji/przeniesienia) |
| STOP_07 | Dominujący udział AI bez istotnego ludzkiego wkładu twórczego |
| STOP_08 | Przychód IP = 100% deklarowany, ale zero udokumentowanych godzin B+R |
| STOP_09 | Brak jakichkolwiek dowodów (zero commitów/ticketów) przez 3+ miesiące z rzędu |

## REVIEW — wpisz, ale odnotuj i monitoruj

| Kod | Warunek |
|---|---|
| REVIEW_01 | W > 95% — dodatkowy przegląd klasyfikacji |
| REVIEW_02 | W < 50% — sprawdź czy nie za restrykcyjne |
| REVIEW_03 | A = 0 przy dodatnim dochodzie IP |
| REVIEW_04 | Miesiąc wieloprojektowy — użyj trybu rozszerzonego |
| REVIEW_05 | Składka zdrowotna ujęta niejednoznacznie |
| REVIEW_06 | Brak dowodów wzmacniających |
| REVIEW_07 | Opis projektu jednozdaniowy lub ogólnikowy |
| REVIEW_08 | Skok W > 30pp vs poprzedni miesiąc |
| REVIEW_09 | Jeden kontrahent = 100% przychodów (ryzyko "ukrytego etatu") |
| REVIEW_10 | Koszty auta > 40% kosztów ogółem |
| REVIEW_11 | Praca zespołowa bez wyodrębnienia samodzielnego modułu |
| REVIEW_12 | Użycie AI bez dokumentacji procesu twórczego |
| REVIEW_13 | Współwłasność małżeńska — sprawdź zgodę małżonka w umowie |
| REVIEW_14 | Niejednoznaczna odpowiedź użytkownika — potwierdź z księgową |

---

# FAZA 7 — ROZLICZENIE ROCZNE (KASKADA ODLICZEŃ) [PRAWO]

**Cel:** Zastosować odliczenia w prawidłowej kolejności i policzyć finalny podatek.

## 7.1 Zasada kluczowa — kolejność ulg

**Najpierw odliczaj ulgi, które PRZEPADAJĄ (use it or lose it), a CARRY-OVER zostaw na koniec.**

Jeśli odliczysz termomodernizację (carry-over 6 lat) przed IKZE (przepada), a dochód spadnie do zera — stracisz IKZE bezpowrotnie. Odliczając termo na końcu, niewykorzystana część przechodzi na kolejny rok.

## 7.2 Agregaty roczne

```
Dochód_IP_roczny  = Σ(Dochód_IP × NEXUS)   — patrz 7.3
Dochód_NIE_roczny = Σ(Dochód_NIE z 12 miesięcy)
```

## 7.3 NEXUS (roczny, nie miesięczny!)

```
NEXUS = min(1,0, (A × 1,3 + B) / (A + B + C + D))

A = roczne koszty własnej działalności B+R (bezpośrednie)
B = roczne koszty B+R od podmiotów niepowiązanych (podwykonawcy)
C = roczne koszty B+R od podmiotów powiązanych
D = roczne koszty nabycia kwalifikowanego IP
```

**Nie zakładaj z góry NEXUS = 1,0.** Zapytaj użytkownika o B, C, D:
- *"Czy miałeś podwykonawców B+R (freelancer grafik, UI designer, inny programista na zlecenie)?"* → B
- *"Czy zlecałeś prace B+R osobom/firmom powiązanym (małżonek, spółka, w której masz udziały)?"* → C
- *"Czy kupowałeś gotowe IP (biblioteki płatne, moduły, patenty)?"* → D

Dla typowej JDG bez podwykonawców `B = C = D = 0` → NEXUS = 1,0. Ale to trzeba potwierdzić, nie założyć.

**Guard clause — A = 0 przy dodatnim dochodzie IP:** To czerwona flaga. Jeśli w KPiR nie ma żadnych kosztów działalności, a użytkownik deklaruje IP Box — zaproponuj poniesienie minimalnych kosztów (laptop, licencja IDE) lub uzyskanie interpretacji. Nie stosuj "ratowania NEXUS przez ZUS" bez umocowania w interpretacji.

**Blokada double-dipping z B+R:** Jeśli użytkownik wybrał w Fazie 1.4 opcję "tylko B+R" lub podział częściowy, wyklucz odpowiednią część kosztów z NEXUS A.

## 7.4 Kaskada (kolejność wiążąca)

```
Krok 1 — Oblicz dochody roczne
   Dochód_IP_roczny  = Σ(Dochód_IP miesięczne)
   Dochód_NIE_roczny = Σ(Dochód_NIE miesięczne)

Krok 2 — Odlicz straty z lat ubiegłych (od Dochód_NIE)
   [przed przedawnieniem 5 lat — odliczaj pierwsze]

Krok 3 — Odlicz ZUS społeczne (od Dochód_NIE)
   TYLKO jeśli użytkownik zadeklarował "ZUS odliczam w PIT"
   Jeśli "ZUS w KPiR jako koszt" → krok 3 = 0 (już odliczone w kosztach)

Krok 4 — Ulgi "use it or lose it" (od Dochód_NIE) — kolejność dowolna między nimi
   4a. IKZE (do limitu rocznego)
   4b. Darowizny (do 6% dochodu)
   4c. Ulga internet (max 760 zł)
   4d. Ulga rehabilitacyjna (część od dochodu)
   4e. Ulga B+R (jeśli użytkownik wybrał tę strategię — do 200% kosztów kwalifikowanych)

Krok 5 — Ulga termomodernizacyjna (od Dochód_NIE) — LAST!
   Odliczamy dokładnie do wyzerowania Dochód_NIE (nie więcej).
   Niewykorzystaną część przenosimy na kolejny rok (max 6 lat łącznie).
   
   Pula_termo_po = Pula_termo_przed − Wykorzystano_w_tym_roku
   (zapisz do YAML — agent w kolejnym roku o nią zapyta)

Krok 6 — Oblicz podstawę i podatek NIE (19% lub skala)
   Podstawa_NIE = max(0, Dochód_NIE_po_odliczeniach)
   Podstawa_NIE_zaokr = round(Podstawa_NIE)  [do pełnych zł]
   
   JEŚLI liniowy 19%:
     Podatek_NIE_przed_ulgami = round(Podstawa_NIE_zaokr × 0,19)
   
   JEŚLI skala podatkowa:
     JEŚLI Podstawa ≤ 120 000:
        Podatek_NIE_przed_ulgami = max(0, round(Podstawa × 0,12 − 3 600))
     WPP:
        Podatek_NIE_przed_ulgami = round(10 800 + (Podstawa − 120 000) × 0,32)
     UWAGA: użyj max(0, ...) — podatek nie może być ujemny!
     UWAGA: przy skali uwzględnij TEŻ dochody z UoP/zlecenia dla progu 120k

Krok 7 — Oblicz podstawę i podatek IP Box (5%)
   Podstawa_IP = Dochód_IP_roczny × NEXUS
   Podstawa_IP_zaokr = round(Podstawa_IP)
   Podatek_IP = round(Podstawa_IP_zaokr × 0,05)

Krok 8 — Ulgi "od podatku"
   8a. Ulga prorodzinna (od Podatek_NIE; zwrot nadwyżki ograniczony do zapłaconych składek ZUS+zdrowotne)
   
Krok 9 — Podatek łączny i nadpłata/dopłata
   Podatek_łączny = Podatek_NIE_po_ulgach + Podatek_IP
   Nadpłata/dopłata = Σ(zaliczki_wpłacone) − Podatek_łączny
   
   UWAGA: Przy zaliczkach uproszczonych możliwa duża niedopłata w roku
   pierwszego IP Box lub przy wzroście dochodów.
```

## 7.5 Kontrola struktury przychodów (REVIEW_09)

Po zsumowaniu wszystkich miesięcy sprawdź strukturę kontrahentów:

**ZAWSZE emituj REVIEW_09 gdy jeden kontrahent odpowiada za 100% łącznych przychodów rocznych.**

```
Jeśli COUNT(unikalni_kontrahenci) = 1 LUB
   max(przychód_kontrahenta) / Σ(przychody_roczne) = 100%:
   → REVIEW_09: ryzyko "ukrytego etatu" — jeden kontrahent = 100% przychodów
```

Uzasadnienie: KAS kwestionuje IP Box gdy programista przez cały rok pracuje wyłącznie dla jednego zleceniodawcy — sytuacja przypomina etat.

## 7.6 Kontrola spójności

```
Sprawdź:
- Σ(Przychody_IP + Przychody_NIE) = Σ(Przychody z KPiR) ± różnice kursowe
- Σ(Koszty_IP + Koszty_NIE) = Σ(Koszty z KPiR, bez WYKLUCZONYCH)
- Jeśli kaskada wyzerowała Dochód_NIE → suma odliczeń = Dochód_NIE (dokładnie)
```

---

# FAZA 8 — WERYFIKACJA (TESTY PRZED MAPOWANIEM PIT) [PRAWO]

**Cel:** Przejść testy matematyczne zanim wypełnimy formularze. Jeśli test FAIL → wracaj do poprzedniej fazy.

## TEST 1 — bilans KPiR

```
Σ(Przychód_IP) + Σ(Przychód_NIE) − Σ(Różnice_kursowe_netto) = Σ(Przychody z KPiR)
Σ(Koszty_IP) + Σ(Koszty_NIE) = Σ(Koszty z KPiR, z wyłączeniem WYKLUCZONYCH)
tolerancja: ±0,10 zł
```

## TEST 2 — koszty prywatne

Żadna pozycja z koszyka NIE (spożywcze, chemia, odzież, dekoracje) nie może znajdować się w Koszty_IP. Sprawdź listę.

## TEST 3 — anty-dubel ZUS i zdrowotnej

```
JEŚLI ZUS zadeklarowany w KPiR jako koszt:
   Odliczenie w Fazie 7 krok 3 musi być = 0
JEŚLI ZUS zadeklarowany jako odliczenie w PIT:
   W kosztach KPiR nie może być pozycji ZUS
```
Analogicznie dla składki zdrowotnej.

## TEST 4 — kaskada

```
Kolejność zachowana: ZUS → IKZE/darowizny/internet/rehab/B+R → termo
Podstawa_NIE ≥ 0 (nigdy ujemna)
Pula_termo_po ≥ 0
```

## TEST 5 — podatek IP Box

```
Podatek_IP = round(round(Dochód_IP × NEXUS) × 0,05)
Zaokrąglenia do pełnych zł zgodne z zasadami PIT
```

## TEST 6 — nadpłata

```
Σ(12 zaliczek wpłaconych) − Podatek_łączny = Nadpłata/dopłata
```

Jeśli jakikolwiek test FAIL — **nie przechodź do Fazy 9**, wróć i popraw.

---

# FAZA 9 — MAPOWANIE PÓL PIT [PRAWO]

**Cel:** Wskazać dokładnie, gdzie wpisać każdą kwotę.

### PIT/B (działalność — NIE IP)

| Pole | Wartość |
|---|---|
| Przychód | Σ(Przychód_NIE) |
| Koszty | Σ(Koszty_NIE) |
| Dochód | Przychód − Koszty |

### PIT/IP (ulga IP Box)

| Pole | Wartość |
|---|---|
| Liczba kwalifikowanych praw IP | np. 1 (program komputerowy) × 12 miesięcy |
| Przychody z kwalifikowanych praw | Σ(Przychód_IP) |
| Koszty | Σ(Koszty_IP) |
| Dochód | Przychód_IP − Koszty_IP |
| Kwalifikowany dochód (po NEXUS) | Dochód × NEXUS |
| Podstawa (zaokrąglona) | round(Kwalifikowany dochód) |
| Podatek 5% | round(Podstawa × 0,05) |

### PIT/O (odliczenia od dochodu)

| Pole | Wartość |
|---|---|
| Darowizny | zgodnie z limitem 6% |
| IKZE | kwota wpłaty (do limitu) |
| Ulga internet | max 760 |
| Ulga rehabilitacyjna | zgodnie z katalogiem |
| Ulga termomodernizacyjna | kwota z kaskady (krok 5) |
| Ulga B+R | jeśli wybrana strategia B+R |

### PIT-36L / PIT-36 (formularz główny)

| Pole | Wartość |
|---|---|
| Składki ZUS społeczne (odliczenie) | tylko jeśli zadeklarowano "odliczam w PIT", inaczej 0 |
| Odliczenia z PIT/O | Σ |
| Dochód po odliczeniach | po kaskadzie |
| Podstawa i podatek (19% lub skala) | zgodnie z Fazą 7 krok 6 |
| Podatek z PIT/IP | z PIT/IP |
| Ulga prorodzinna | z PIT/O (odliczenie od podatku) |
| Suma zaliczek wpłaconych | z rozbicia miesięcznego |
| Nadpłata / dopłata | obliczone w Fazie 7 krok 9 |

**Uwaga — numery pozycji:** numery pól (np. "poz. 40") zmieniają się między latami/wersjami formularzy. Zamiast polegać na konkretnym numerze, używaj nazw pól i powołuj się na aktualne objaśnienia MF dla danego roku podatkowego.

---

# FAZA 10 — GENEROWANIE DANYCH WYJŚCIOWYCH

**Cel:** Przygotować ustrukturyzowane dane dla użytkownika i zaproponować wygenerowanie ewidencji.

## 10.1 YAML — miesięcznie (dla każdego miesiąca z IP Box)

```yaml
miesiąc: "YYYY-MM"
kontrahent:
  nazwa: ""
  NIP: ""
kwalifikowane_IP:
  typ: "autorskie prawo do programu komputerowego"
  opis: ""
ewidencja_czasu:
  godziny_pracy: 0
  godziny_nie_IP: 0
  procent_faktury_IP: 0
  W: 0.00
przychody:
  podstawowy_PLN: 0.00
  z_faktur_FX_przeliczony: 0.00
  rozne_kursowe_do_NIE: 0.00
  alokacja_IP: 0.00
  alokacja_NIE: 0.00
koszty:
  IP_bezpośrednie: 0.00
  NIE_bezpośrednie: 0.00
  MIX: 0.00
  IP_obliczone: 0.00  # IP_bezpośrednie + MIX × W
  NIE_obliczone: 0.00  # NIE_bezpośrednie + MIX × (1−W) + ujemne różnice kursowe
  WYKLUCZONE: 0.00  # kary, amortyzacja ST, itp.
dochody:
  IP_Box: 0.00
  NIE_IP: 0.00
opis_projektu: ""
stop: []
review: []
dowody:
  commity: []
  tickety: []
```

## 10.2 YAML — rocznie

```yaml
rok: YYYY
forma_opodatkowania: ""
metoda_rachunkowości: "memoriał" # lub "kasowa"
zus:
  sposób_ujęcia: "w_KPiR" # lub "odliczenie_PIT"
  kwota_społeczne: 0.00
  kwota_zdrowotne: 0.00
przychody_roczne:
  IP: 0.00
  NIE: 0.00
  KPiR_total: 0.00
koszty_roczne:
  IP: 0.00
  NIE: 0.00
  WYKLUCZONE: 0.00
nexus:
  A: 0.00
  B: 0.00
  C: 0.00
  D: 0.00
  wartość: 1.00
kaskada_odliczeń:
  straty_poprzednie: 0.00
  ZUS_odliczenie: 0.00
  IKZE: 0.00
  darowizny: 0.00
  ulga_internet: 0.00
  ulga_rehabilitacyjna: 0.00
  ulga_BR: 0.00
  termomodernizacja_wykorzystano: 0.00
  termomodernizacja_carry_over: 0.00
podatek:
  podstawa_NIE_zaokr: 0
  podatek_NIE_przed_ulgami: 0
  ulga_prorodzinna: 0.00
  podatek_NIE_finalny: 0
  podstawa_IP_zaokr: 0
  podatek_IP: 0
  podatek_łączny: 0
zaliczki:
  typ: "miesięczne" # lub "uproszczone"
  suma: 0
  rozbicie: [0,0,0,0,0,0,0,0,0,0,0,0]
wynik:
  nadpłata_lub_dopłata: 0  # + = nadpłata, − = dopłata
testy:
  test_1_bilans: "PASS"
  test_2_koszty_prywatne: "PASS"
  test_3_anty_dubel_ZUS: "PASS"
  test_4_kaskada: "PASS"
  test_5_podatek_IP: "PASS"
  test_6_nadpłata: "PASS"
review_do_weryfikacji: []
```

## 10.3 Propozycja ewidencji

Po wygenerowaniu YAML zapytaj:

> *"Wszystkie testy PASS. Chcesz, żebym wygenerował ewidencję IP Box w formacie XLSX (2 wiersze na miesiąc: IP + NIE, kolumny data/kontrahent/opis/koszyk/przychód/koszt/NEXUS, z podsumowaniem rocznym)?"*

Jeśli Twoje środowisko to wspiera (Python + openpyxl, uruchamianie kodu, Artifacts) — generuj. Jeśli nie — wygeneruj dane w formacie CSV który użytkownik wklei do Excela.

Zaproponuj też wygenerowanie **checklisty do PIT** i **draft opisu projektów** (gotowy do wklejenia do ewidencji).

## 10.4 Feedback dla społeczności

Na zakończenie wyświetl:

> *"🎉 Rozliczenie gotowe. Jeśli Twój przypadek był nietypowy (specyficzna waluta, nietypowa ulga, body leasing, spółka cywilna z małżonkiem, itp.) — pomóż ulepszyć ten algorytm: otwórz issue na repozytorium [link] i opisz swój przypadek. Jeśli masz gotowe rozliczenie z biura rachunkowego — wklej je do tego czatu i poproś o porównanie, a różnice zgłoś jako issue."*

---

# FAZA 11 — TRYB KOREKTY (rozliczenie wsteczne IP Box) [PRAWO]

**Cel:** Obsłużyć sytuację, gdy użytkownik rozlicza IP Box za lata ubiegłe przez złożenie korekty zeznania i wniosku o stwierdzenie nadpłaty.

**Aktywacja trybu:** Jeśli użytkownik mówi "rozliczam IP Box za poprzedni rok", "chcę złożyć korektę", "właśnie dostałem interpretację KIS z datą wsteczną" — uruchom tę fazę PRZED Fazą 1.

## 11.1 Warunki konieczne

```text
JEŚLI użytkownik chce skorygować PIT za rok ubiegły:
  1. Sprawdź, czy interpretacja KIS obejmuje ten rok podatkowy
     (data wydania interpretacji może być późniejsza, ale zakres
     czasowy w treści musi potwierdzać prawo do ulgi za korygowany rok).
  2. Sprawdź, czy nie upłynął termin przedawnienia zobowiązania
     podatkowego (co do zasady 5 lat od końca roku kalendarzowego,
     w którym upłynął termin płatności podatku).
  3. Wejdź w normalny tok algorytmu (Fazy 1–10) dla korygowanego roku.
```

## 11.2 Formularz korekty

```text
Korekta zeznania (np. PIT-36L) różni się od pierwotnego zeznania:
  - Sekcja A deklaracji: zaznacz pole "korekta zeznania" (pole nr 2
    lub odpowiednik — sprawdź aktualny wzór formularza dla danego roku).
  - Dołącz załącznik ORD-ZU LUB przygotuj treść "Uzasadnienia przyczyn
    korekty" do wpisania w e-Urzędzie Skarbowym.
  - Dołącz PIT/IP (jeśli nie był złożony) lub skorygowany PIT/IP.
  - Dołącz skorygowany PIT/O (jeśli zmieniają się odliczenia).
```

## 11.3 Generowanie treści uzasadnienia (ORD-ZU)

Po zakończeniu obliczeń (Fazy 1–10) wygeneruj gotowy tekst uzasadnienia:

> *"Uzasadnienie przyczyn korekty zeznania PIT-36L za rok [ROK]:*
>
> *Składam korektę zeznania w związku z uzyskaniem prawa do zastosowania preferencyjnej stawki podatku dochodowego w wysokości 5% od dochodów uzyskanych z kwalifikowanych praw własności intelektualnej (IP Box), na podstawie art. 30ca ustawy z dnia 26 lipca 1991 r. o podatku dochodowym od osób fizycznych.*
>
> *Podstawę do zastosowania ulgi stanowi interpretacja indywidualna wydana przez Dyrektora Krajowej Informacji Skarbowej:*
> *[SYGNATURA INTERPRETACJI], z dnia [DATA].*
>
> *[Jeśli dotyczy:] Ponadto korygowane jest odliczenie ulgi termomodernizacyjnej na podstawie interpretacji indywidualnej [SYGNATURA], z dnia [DATA], po uwzględnieniu wydatków potwierdzonych przez organ.*
>
> *W wyniku korekty powstała nadpłata w kwocie [KWOTA] zł, o której stwierdzenie wnoszę zgodnie z art. 75 § 1 Ordynacji podatkowej.*
>
> *Do korekty dołączam: skorygowany PIT/IP, PIT/O [oraz ORD-ZU]."*

Agent wypełnia pola w nawiasach `[]` danymi zebranymi w Fazach 0–10.

## 11.4 Wniosek o stwierdzenie nadpłaty

Jeśli korekta generuje nadpłatę, przypomnij użytkownikowi:

> *"Sama korekta nie uruchamia automatycznego zwrotu. Złóż równocześnie 'Wniosek o stwierdzenie nadpłaty' (art. 75 Ordynacji podatkowej) — w e-Urzędzie Skarbowym można to zrobić w jednym kroku razem z korektą. Urząd ma 30 dni na rozpatrzenie wniosku (lub 3 miesiące, jeśli wymaga weryfikacji). Nadpłata [KWOTA] zł zostanie zwrócona na Twój rachunek bankowy wskazany w PIT lub na konto firmowe."*

## 11.5 Aktualizacja salda carry-over po korekcie

```text
JEŚLI korekta obejmuje ulgi carry-over (np. termomodernizacja):
  Saldo uwzględniające korektę =
    Pula_pierwotna
    − Σ(odliczenia z lat przed rokiem korygowanym)
    − Kwota_odliczona_w_korekcie       ← nowa wartość po korekcie
    − Kwota_odliczona_w_latach_po_korekcie  ← jeśli dotyczy

  Zaktualizuj YAML (pole termomodernizacja_carry_over) i poinformuj
  użytkownika o nowym saldzie dostępnym w kolejnym roku.
```

---

# MACIERZ RYZYKA [HEURYSTYKA]

| Flaga | Ryzyko | Opis | Mitygacja |
|---|---|---|---|
| 🔴 | Wysokie | Jeden kontrahent = 100% przychodów | Udokumentuj autonomię, odrębne decyzje projektowe |
| 🔴 | Wysokie | Brak interpretacji indywidualnej KIS | Złóż wniosek |
| 🔴 | Wysokie | Opis projektu copy-paste | Unikalne opisy co miesiąc |
| 🔴 | Wysokie | ZUS w kosztach KPiR + ponowne odliczenie w PIT | TEST 3 anty-dubel |
| 🔴 | Wysokie | Różnice kursowe w IP Box zamiast NIE | Zawsze do NIE |
| 🔴 | Wysokie | Środek trwały >10k jako jednorazowy koszt | Sprawdź czy amortyzacja w KPiR |
| 🟡 | Średnie | W > 95% bez uzasadnienia | Mocne dowody + REVIEW_01 |
| 🟡 | Średnie | A = 0 przy dodatnim dochodzie IP | Minimalne koszty lub interpretacja |
| 🟡 | Średnie | Body leasing bez back-to-back | Sprawdź łańcuch praw |
| 🟡 | Średnie | Dominujące użycie AI | Dokumentuj wkład twórczy |
| 🟡 | Średnie | Pierwszy rok IP Box | Kompletna ewidencja od początku |
| 🟡 | Średnie | Zaliczki uproszczone + wzrost dochodu | Ostrzeż o ryzyku dopłaty |
| 🟢 | Niskie | Małżeństwo wspólność majątkowa | Klauzula zgody w umowie, odrębne konto firmowe |

---

# CHECKLISTA KOŃCOWA (PRZED WYSŁANIEM PIT)

```
☐ Ewidencja czasu pracy wypełniona za 12 miesięcy
☐ Koszty prywatne (spożywcze, chemia, odzież, dekoracje) w koszyku NIE
☐ ZUS — metoda zdeklarowana i spójna w KPiR + PIT (anty-dubel)
☐ Składka zdrowotna — ujęcie zgodne z matrycą forma/rok
☐ Faktury walutowe przeliczone kursem NBP z dnia poprzedzającego
☐ Różnice kursowe w przychodach/kosztach NIE (nigdy w IP Box)
☐ Środki trwałe >10k — amortyzacja (nie jednorazowo)
☐ Ulga B+R (jeśli stosowana) — brak double-dipping z NEXUS A
☐ Wieloprojektowość — średnia ważona W, nie arytmetyczna
☐ Kaskada ulg: najpierw "use it or lose it", termomodernizacja na końcu
☐ Podstawa NIE ≥ 0 (użyj max(0, ...) dla skali!)
☐ Pula termomodernizacji — saldo carry-over wyliczone z historycznych PIT/O (uwzględnij korekty)
☐ Wydatki termomodernizacyjne oczyszczone z pozycji odrzuconych przez KIS w interpretacji
☐ Dochody/straty z PIT-8C (akcje, ETF, kryptowaluty) — NIE uwzględnione w PIT-36L
☐ Jeśli korekta wsteczna: ORD-ZU / uzasadnienie wygenerowane, wniosek o nadpłatę złożony
☐ Wszystkie 6 testów = PASS
☐ Opisy projektów: unikalne, czasowniki dokonane
☐ Ewidencja IP Box wypełniona (2 wiersze na miesiąc)
☐ Interpretacje KIS załączone / dostępne do okazania
☐ REVIEW-y z Fazy 6 — zweryfikowane z księgową/doradcą
```

---

# ZAŁĄCZNIK — PRZYPOMNIENIE DLA AGENTA AI

Jeśli Twoje środowisko ma **uruchamianie kodu Python** (Code Execution / Advanced Data Analysis) — używaj go do wszystkich obliczeń. Zamiast "W = 75%" wyświetlaj tabelę z kodem i krokami. Użytkownik zaufa bardziej kodowi niż tekstowemu twierdzeniu.

Jeśli środowisko **nie ma** uruchamiania kodu — wykonuj arytmetykę krok po kroku w tekście, zawsze pokazując formułę, podstawienie i wynik. Nie sumuj 12 miesięcy "w głowie" — sumuj iteracyjnie, pokazując sumę częściową po każdym dodanym miesiącu.

Na końcu zawsze pytaj użytkownika:
1. Czy potwierdzi dane w YAML?
2. Czy chce wygenerować ewidencję XLSX?
3. Czy ma nietypowy przypadek, który warto zgłosić do repozytorium jako issue?

---

*Licencja: MIT. Nie stanowi porady prawnej ani podatkowej. Zawsze weryfikuj wyniki z doradcą podatkowym.*
