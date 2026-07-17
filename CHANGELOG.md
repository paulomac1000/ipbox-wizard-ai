# Changelog

## Unreleased

### Added

- Atomowy kontrakt `decision_facts`; model zwraca wyłącznie `status/stops/reviews`.
- Fail-closed oracle, evaluator, strict JSON Schema i VCR format 4.
- 36 znormalizowanych scenariuszy oraz trzymodelowy benchmark.
- Regresje dla wzoru NEXUS podwyższającego A+B.
- Jawny podział ulgi B+R na część IP i NIE wraz z odliczeniem IP przed NEXUS.
- Pełne połączenie działalności na skali z `dochody_dodatkowe_skala`.
- Roczne limity odliczenia zdrowotnej i IKZE dla 2025–2026 oraz odmowa dla niezweryfikowanego roku.
- Niezależny brief audytowy i raport z 17 lipca 2026 r.

### Fixed

- Rozdzielono przychód, koszty `MIX` i NEXUS zgodnie z issue #1.
- Poprawiono NEXUS z `(A×1,3+B)` na `((A+B)×1,3)`.
- Nieudokumentowane IDE, chmura, sprzęt i repozytoria nie są automatycznie kosztami IP.
- Niesklasyfikowany zakup powyżej 10 000 zł jest wyłączany do udokumentowania odpisu.
- Osobiste ulgi niedostępne przy podatku liniowym są odrzucane.
- Ulga internetowa ma limit 760 zł, a zwykłe darowizny wspólny limit 6%.
- Ulga B+R nie jest już błędnie ograniczona do dochodu NIE-IP.
- Podatek skali obejmuje pełną wspólną podstawę z innymi dochodami skali, zamiast zwracać wyłącznie marginalny podatek działalności.
- Niejednoznaczne `ulga_BR` i `straty_poprzednie` są odrzucane; używane są pola rozdzielone semantycznie.
- Ujemne faktury, ujemne odliczenia, błędne mapy ZUS/zaliczek i nieznane limity roczne są odrzucane przed raportem.
- STOP zeruje cały wynik, brak danych FX nie staje się zerem, W=0/ERROR i carry-over są fail-closed.
- Multi-IP zachowuje każdy grosz metodą największych reszt.
- Retry respektuje `Retry-After`, odpowiedź wymaga `finish_reason=stop`, a playback nie ma live fallbacku.
- Workflowy używają minimalnych uprawnień i `persist-credentials: false`.

### Changed

- Standardowy CI jest bezpłatny i działa na Pythonie 3.11–3.13.
- Roczna metoda przychodowa odracza `MIX` do finalnego true-up.
- `strata_NIE_z_lat_poprzednich` dotyczy wyłącznie pozostałej działalności; straty IP wymagają ewidencji per prawo.
- Działalność liniowa z dodatkowymi dochodami skali wymaga osobnej kaskady dla osobnego zeznania.
- Kalkulator multi-IP wspiera podział wspólnych kosztów, ale nie udaje pełnej ewidencji PIT/IP per IP.

### Removed

- Wpływ `meta.expected_reviews` na prawdę oracle.
- Pełny raport finansowy w odpowiedzi LLM.
- Historyczne, częściowe i semantycznie niepoprawne kasety starego kontraktu.
- VCR auto, nadpisywanie `--force`, aliasy Gemini i live fallback z playbacku.
