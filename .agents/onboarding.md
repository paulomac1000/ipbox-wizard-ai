# Onboarding agenta

Repozytorium jest narzędziem **decision-support**, a nie automatycznym doradcą podatkowym. Kontrakt zweryfikowano 17 lipca 2026 r. dla scenariuszy 2025; reguły zależne od roku muszą mieć urzędowe źródło i test.

## Kolejność pracy

1. Przeczytaj `AGENTS.md`, `README.md`, `ipbox_algorytm.md` i `docs/testing.md`.
2. Uruchom wszystkie bezpłatne bramki.
3. Błąd semantyczny najpierw odtwórz testem deterministycznym.
4. Popraw kalkulator/oracle, potem scenariusz, schema i dokumentację.
5. Nie dopasowuj prawdy testowej do odpowiedzi modelu.
6. Nagrywanie LLM rozpocznij dopiero po zielonym CI i czystym drzewie.
7. Używaj dokładnych modeli z `tests/llm/models.py`.
8. Odrzucenia analizuj w `/tmp/ipbox_llm_rejected/<model>/`; wznawiaj tylko brakujące nagrania po sklasyfikowaniu przyczyny.
9. Zakończenie wymaga playbacku bez sekretu i raportu według `docs/independent-audit-brief.md`.

## Model odpowiedzialności

- Python wykonuje wszystkie obliczenia i wyznacza pełne `decision_facts`.
- Runner usuwa fakty `false` i buduje wyłącznie prawdziwe `active_rules` z gotowymi kodami.
- Model kopiuje kody aktywnych reguł do `status/stops/reviews`; nie widzi nieaktywnych nazw ani kodów.
- Evaluator i schema odrzucają pominięcie, dodatkowy kod, duplikat lub niewłaściwy status.
- VCR zapisuje tylko odpowiedź z `finish_reason=stop`, nie nadpisuje istniejącej kasety i nigdy nie wykonuje sieci podczas playbacku.

Nie przywracaj pełnej mapy `true/false`. Pierwsza realna macierz wykazała, że słabsze modele reinterpretowały nazwy nieaktywnych faktów i dopisywały `STOP_02`.

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
- Repo dopuszcza pusty katalog kaset albo kompletną macierz 108/108; częściowej macierzy nie commituj.

## Stan bazowy

Przed nowym nagraniem oczekuj 167 testów PASS, coverage 95,30%, 36 kontrolowanych skipów LLM i katalogu kaset zawierającego tylko `.gitkeep`.
