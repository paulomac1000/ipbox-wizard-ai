# Changelog

## 0.2.0 — Unreleased

### Added

- Atomowy kontrakt `decision_facts`; model zwraca wyłącznie `status/stops/reviews`.
- Kontrakt `active_rules`, który nie pokazuje modelowi fałszywych przesłanek ani nieaktywnych kodów.
- Fail-closed oracle, evaluator, strict JSON Schema i VCR format 4.
- Siedmiorodzinny benchmark tanich modeli; rozmiar macierzy jest wyliczany dynamicznie z liczby scenariuszy.
- Regresje dla wzoru NEXUS podwyższającego A+B.
- Jawny podział ulgi B+R na część IP i NIE wraz z odliczeniem IP przed NEXUS.
- Pełne połączenie działalności na skali z `dochody_dodatkowe_skala`.
- Wersjonowane reguły każdego roku istnienia IP Box: 2019–2026.
- Historyczne limity IKZE przedsiębiorcy dla 2019–2026.
- Historyczne zasady zdrowotnej: odliczenie od podatku do 2021 r. oraz limity liniowe 2022–2026.
- Historyczne skale podatkowe 2019, 2020–2021 oraz 2022–2026.
- Granicę jednoczesnego B+R i IP Box: niedozwolone do 2021 r., obsługiwane od 2022 r.
- Jawne semantyki W: `conditional_product`, `disjoint_components` i `time_only`.
- Audyt miesięcznej alokacji wykrywający podwójny procent, przypisanie 100% mimo części NIE-IP i nieudokumentowaną zmianę metody w roku.
- Metodę MIX `przychodowa_w_dacie_kosztu` z kluczem właściwym dla miesiąca kosztu.
- Uzgodnienie ewidencji i zeznania osobno dla przychodów i kosztów IP/NIE, także gdy sumy globalne są identyczne.
- Rocznikowe pule termomodernizacji z kontrolą limitu 53 000 zł, kolejnością wykorzystania i wygaśnięciem po sześciu latach.
- Rozliczenie korekty odróżniające poprawioną nadpłatę od zwrotu już wypłaconego.
- Syntetyczne scenariusze LLM/VCR `46`–`55` odtwarzające klasy błędów znalezionych w rozliczeniach rzeczywistych bez kopiowania danych podatnika.
- Test blokujący oczywiste identyfikatory osobowe w nowych scenariuszach regresyjnych.
- Dokumentację historycznych źródeł, regresji rzeczywistych oraz brief pełnej odbudowy kaset.

### Fixed

- Rozdzielono przychód, koszty `MIX` i NEXUS zgodnie z issue #1.
- Poprawiono NEXUS z `(A×1,3+B)` na `((A+B)×1,3)`.
- Nieudokumentowane IDE, chmura, sprzęt i repozytoria nie są automatycznie kosztami IP.
- Niesklasyfikowany zakup powyżej 10 000 zł jest wyłączany do udokumentowania odpisu.
- Osobiste ulgi niedostępne przy podatku liniowym są odrzucane.
- Ulga internetowa ma limit 760 zł, a zwykłe darowizny wspólny limit 6%.
- Ulga B+R nie jest już błędnie ograniczona do dochodu NIE-IP.
- Podatek skali obejmuje pełną wspólną podstawę z innymi dochodami skali.
- Niejednoznaczne `ulga_BR` i `straty_poprzednie` są odrzucane; używane są pola rozdzielone semantycznie.
- Ujemne faktury, ujemne odliczenia, błędne mapy ZUS/zaliczek i nieznane limity roczne są odrzucane przed raportem.
- Faktury walutowe zawierają walutę, daty i źródłowe kursy; różnice kursowe są wyliczane, nie wpisywane ręcznie.
- Dodatnie ulgi osobiste i B+R wymagają jawnego, zweryfikowanego śladu dowodowego.
- Bezpośredni koszt IP wymaga `allocation_source`, zamiast syntetycznego źródła „dokument”.
- STOP zeruje cały wynik, brak danych FX nie staje się zerem, W=0/ERROR i carry-over są fail-closed.
- Multi-IP zachowuje każdy grosz metodą największych reszt.
- Kwoty historycznych odliczeń nie są już blokowane tylko dlatego, że rok jest wcześniejszy niż 2025.
- Kwoty ponad limit roczny nie są cicho obcinane do limitu.
- Procent faktury nie może zostać zastosowany dwukrotnie bez aktywacji `STOP_10`.
- Niejawne przejście pomiędzy metodami alokacji w jednym roku aktywuje `STOP_11`.
- Równe sumy przychodów/kosztów nie maskują przesunięcia pomiędzy IP i NIE; aktywowany jest `STOP_12`.
- Rok sprzed IP Box lub po ostatnim zweryfikowanym roku nie używa zasad sąsiedniego roku.
- Retry respektuje `Retry-After`, odpowiedź wymaga `finish_reason=stop`, a playback nie ma live fallbacku.
- Playback i pre-commit odrzucają niekompletne kasety, a recorder nie nadpisuje istniejącego nagrania.
- Parser odrzuca Markdown fences zamiast naprawiać odpowiedź modelu.
- Manifest jest porównywany z kasetą także dla `returned_model`, `recorded_at` i kosztu.
- Recorder odrzuca podmianę zwróconego modelu i wlicza odrzucone płatne wywołania do limitu kosztu.
- Walidacja wiąże każdy miesiąc z rokiem rozliczenia i egzekwuje limit termomodernizacji 53 000 zł.
- Workflowy używają minimalnych uprawnień i `persist-credentials: false`.

### Changed

- Standardowy CI jest bezpłatny i działa na Pythonie 3.11–3.13.
- Roczna metoda przychodowa odracza `MIX` do finalnego true-up.
- Polityka W musi opisywać znaczenie procentu faktury względem godzin NIE-IP, zamiast zakładać jeden wzór dla wszystkich umów.
- Polityka z interpretacji KIS jest oznaczana do przeglądu, a jej faktyczne wdrożenie jest porównywane z ewidencją.
- `strata_NIE_z_lat_poprzednich` dotyczy wyłącznie pozostałej działalności; straty IP wymagają ewidencji per prawo.
- Działalność liniowa z dodatkowymi dochodami skali wymaga osobnej kaskady dla osobnego zeznania.
- Kalkulator multi-IP wspiera podział wspólnych kosztów, ale nie udaje pełnej ewidencji PIT/IP per IP.
- Kasety VCR po tej zmianie muszą zostać zbudowane od zera dla całej macierzy; stara macierz jest niezgodna z nowym oracle i schema.

### Removed

- Wpływ `meta.expected_reviews` na prawdę oracle.
- Pełny raport finansowy w odpowiedzi LLM.
- Pełna mapa aktywnych i nieaktywnych faktów w promptcie modelu.
- Historyczne, częściowe i semantycznie niepoprawne kasety poprzednich kontraktów.
- VCR auto, nadpisywanie `--force`, aliasy Gemini i live fallback z playbacku.
- Założenie, że jedyny poprawny wzór W to iloczyn czasu i procentu faktury.
