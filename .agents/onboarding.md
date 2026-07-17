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
8. Odrzucenia analizuj w `/tmp/ipbox_llm_rejected/<model>/`; wznawiaj tylko brakujące nagrania.
9. Zakończenie wymaga playbacku bez sekretu i raportu według `docs/independent-audit-brief.md`.

## Pułapki

- `W` nie jest domyślnym kluczem `MIX`.
- NEXUS podwyższa łącznie A+B.
- IDE, chmura, laptop i repozytorium bez dowodu są `MIX` albo `WYKLUCZONE`, nie automatycznie `IP`.
- B+R wymaga jawnego rozdziału `IP/NIE`; nie używaj niejednoznacznego `ulga_BR`.
- `strata_NIE_z_lat_poprzednich` nie obejmuje strat kwalifikowanego IP.
- Dodatkowe dochody skali łączy się tylko z działalnością na skali; przy liniowym potrzebna jest osobna kaskada.
- Limity zdrowotnej i IKZE są roczne; nie zgaduj limitu dla nieobsługiwanego roku.
- Kasety historyczne są diagnostyką starego kontraktu, nie dowodem poprawności obecnego kodu.
