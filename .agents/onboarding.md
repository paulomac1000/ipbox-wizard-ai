# Onboarding agenta

Repozytorium jest narzędziem **decision-support**, a nie automatycznym doradcą podatkowym. Kontrakt roczny i procedurę wydania ostatnio zweryfikowano 26 lipca 2026 r. dla wszystkich lat obowiązywania IP Box 2019–2026; każdy kolejny rok musi mieć urzędowe źródło i test.

## Kolejność pracy

1. Przeczytaj `AGENTS.md`, `README.md`, `ipbox_algorytm.md` i `docs/testing.md`.
2. Uruchom wszystkie bezpłatne bramki.
3. Błąd semantyczny najpierw odtwórz testem deterministycznym.
4. Popraw kalkulator/oracle, potem scenariusz, schema i dokumentację.
5. Nie dopasowuj prawdy testowej do odpowiedzi modelu.
6. Najpierw spróbuj bezpłatnego odświeżenia metadanych istniejących kaset. Nagrywanie LLM rozpocznij dopiero wtedy, gdy surowa odpowiedź nie przechodzi aktualnego kontraktu, po zielonych bramkach deterministycznych i przy czystym drzewie.
7. Używaj dokładnych modeli z `tests/llm/models.py`.
8. Odrzucenia analizuj w `${VCR_REJECTED_ROOT:-/tmp/ipbox_llm_rejected}/<model>/`; każda próba ma osobny plik. Wznawiaj tylko brakujące nagrania po sklasyfikowaniu przyczyny.
9. Zakończenie wymaga 322/322 dla siedmiu rodzin, czystego JSON bez Markdown fences, playbacku bez sekretu i raportu `scripts/benchmark_report.py` oraz procedury z `docs/testing.md`.

## Model odpowiedzialności

- Python wykonuje wszystkie obliczenia, wyznacza `decision_facts` i buduje pełną autorytatywną kopertę `expected_decision`.
- Model otrzymuje gotowe `status`, `stops` i `reviews` i kopiuje je bez zmian; nie widzi faktów podatkowych ani nazw predykatów.
- Evaluator i lokalna strict schema odrzucają pominięcie, dodatkowy kod, duplikat, skrzyżowanie kanałów lub niewłaściwy status.
- Adapter transportowy może usunąć keyword nieobsługiwany przez providera albo użyć `json_object`, ale nie może osłabić lokalnej schema ani walidacji semantycznej.
- VCR zapisuje tylko odpowiedź z `finish_reason=stop`, nie nadpisuje istniejącej kasety i nigdy nie wykonuje sieci podczas playbacku.

Nie przywracaj pełnej mapy `true/false` ani listy wymagającej ponownej klasyfikacji kodów. Kolejne realne macierze wykazały, że słabsze modele potrafiły reinterpretować nieaktywne fakty albo przenosić REVIEW do STOP. `expected_decision` usuwa obie zbędne decyzje modelu.

## Pułapki

- `W` nie jest domyślnym kluczem `MIX`.
- NEXUS podwyższa łącznie A+B.
- IDE, chmura, laptop i repozytorium bez dowodu są `MIX` albo `WYKLUCZONE`, nie automatycznie `IP`.
- B+R wymaga jawnego rozdziału `IP/NIE`; nie używaj niejednoznacznego `ulga_BR`.
- `strata_NIE_z_lat_poprzednich` nie obejmuje strat kwalifikowanego IP.
- Dodatkowe dochody skali łączy się tylko z działalnością na skali; przy liniowym potrzebna jest osobna kaskada.
- Limity zdrowotnej i IKZE są roczne; nie zgaduj limitu dla nieobsługiwanego roku.
- Miesiąc musi należeć do `input.rok`, a pula termomodernizacji nie może przekraczać 53 000 zł.
- Kasety historyczne są diagnostyką poprzednich kontraktów, nie dowodem poprawności obecnego kodu.
- Lokalnie dopuszczalny jest pusty katalog VCR, ale merge gate wymaga kompletnej i aktualnej macierzy 322/322.

## Stan bazowy

Bramka deterministyczna obejmuje Python 3.11–3.13, pełny zestaw testów jednostkowych, coverage powyżej 90%, pełny bezpłatny suite, politykę kaset i składnię shell. Dokładną liczbę testów raportuje CI. Na Pythonie 3.13 CI dodatkowo wymaga kompletnego raportu macierzy i wykonuje pełny playback offline bez `OPENROUTER_API_KEY`.
