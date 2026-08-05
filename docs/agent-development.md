---
description: Procedura bezpiecznego rozwijania kodu, testów, dokumentacji i CI w ipbox-wizard-ai.
doc_id: workflow.agent-development
type: workflow
status: active
rigor: operational
owners: [repository-maintainers]
verification: Uruchom make full, a po pushu potwierdź zewnętrzny auditor workflow z finalnego, przypiętego wydania ai-skills oraz porównaj zmianę z kanonicznym kontraktem domenowym. Raport końcowy podaje branch i dokładny SHA, zmienione kontrakty i konsumentów, komendy i wyniki, pominięte bramki z powodami, ryzyka rezydualne, status CI oraz wymagane dalsze review.
upstream: [README.md, AGENTS.md, ipbox_algorytm.md, Makefile, docs/testing.md]
downstream: [AGENTS.md, README.md]
review_triggers: [zmiana komend jakości, zmiana architektury testów, zmiana VCR, zmiana polityki CI]
---

# Rozwój repozytorium przez agenta

## Wynik wymagany

Zmiana ma być minimalna, odtwarzalna, fail-closed i chroniona testem. Agent nie osłabia bramek jakości, nie modyfikuje ręcznie wygenerowanych kaset ani nie deklaruje gotowości bez rozróżnienia lokalnych testów, GitHub Actions i niezależnego review.

## Rozpoznanie zadania

1. Przeczytaj `README.md`, `AGENTS.md`, `ipbox_algorytm.md` oraz pliki związane z zadaniem.
2. Ustal branch, dokładny SHA i stan working tree.
3. Zidentyfikuj kanonicznego właściciela zmienianego kontraktu oraz wszystkich konsumentów.
4. Odczytaj istniejące testy jednostkowe, scenariusze, schema, evaluator i dokumentację właściwe dla zmiany.
5. Określ, czy zadanie dotyczy reguły podatkowej, importu danych, LLM/VCR, dokumentacji czy CI.

## Reguła podatkowa lub błąd kalkulatora

1. Dodaj minimalny test odtwarzający problem.
2. Popraw kanoniczny moduł w `python_helper/`.
3. Sprawdź wartości zerowe, graniczne, ujemne i błędne typy.
4. Zweryfikuj zachowanie do grosza oraz rozdzielenie przychodu, `W`, MIX i NEXUS.
5. Zaktualizuj `ipbox_algorytm.md`, schema, oracle, evaluator i dokumentację tylko wtedy, gdy ich kontrakt rzeczywiście się zmienia.
6. Uruchom test celowany, `make test` i `make verify`.

## Nowy przypadek biznesowy

1. Zredukuj przypadek do syntetycznego, minimalnego wejścia.
2. Dodaj test jednostkowy dla nowego invariantu.
3. Dodaj scenariusz biznesowy, gdy wnosi nową ścieżkę procesu lub kombinację warunków.
4. Nie przenoś realnych identyfikatorów, kwot i dokumentów do repozytorium.
5. Jeżeli zmiana wpływa na kontrakt LLM, doprowadź pełną macierz kaset do zgodności zgodnie z `docs/testing.md`.

## Zmiana LLM, VCR lub modelu

1. `tests/llm/models.py` jest jedynym właścicielem profili i `BENCHMARK_MODELS`.
2. Używaj standardowych skryptów `record_model.py`, `record_all_models.sh`, `refresh_vcr_metadata.py`, `vcr_precommit.py` i `verify_all_models.sh`.
3. Nie twórz alternatywnego rejestru modeli ani osobnego wrappera bez zmiany architektury.
4. Nie edytuj ręcznie odpowiedzi, hashy, fingerprintów, manifestów ani `parsed_response`.
5. Najpierw próbuj odświeżenia deterministycznych metadanych bez płatnych requestów.
6. Płatne nagranie wymaga jawnego polecenia, potwierdzenia i dodatnich limitów kosztu.
7. Nie uznawaj modelu lub macierzy za kompletne na podstawie częściowych kaset.

## Dokumentacja

1. Ustal jeden kanoniczny dokument dla trwałej reguły lub procedury.
2. Umieść odpowiedź lub wymagane zachowanie przed tłem.
3. Oddziel wymagania, zweryfikowane fakty, przykłady, założenia i pytania otwarte.
4. Linkuj do właściciela zamiast kopiować pełny kontrakt.
5. Dokument operacyjny podaje weryfikację oraz bezpieczne zatrzymanie lub rollback, gdy są istotne.
6. Zmiana kontraktu wskazuje konsumentów i dokumenty zależne.
7. Nie wpisuj ulotnych liczników, hashy, dat weryfikacji ani host-specific ścieżek jako trwałej polityki.

## CI/CD

1. Pull request CI jest pełną, nieuprzywilejowaną bramką; płatny benchmark pozostaje osobnym, ręcznie potwierdzanym workflow.
2. Zewnętrzne GitHub Actions muszą być przypięte do pełnego SHA z komentarzem wersji.
3. `actions/checkout` używa `persist-credentials: false`.
4. Workflow ma minimalne permissions, timeout, concurrency i jawne zachowanie artefaktów.
5. Kod z niezaufanego pull requestu nie otrzymuje sekretów ani uprawnień zapisu.
6. Lokalny `python scripts/check_workflow_policy.py` jest diagnostycznym launcherem bajtowo zweryfikowanego snapshotu runtime w `vendor/ai-skills`. CI porównuje upstreamowy wrapper, implementację i `contracts/confined_io.py` z finalnym wydaniem `ai-skills`, a następnie uruchamia zewnętrzny auditor z przypiętego commita na ocenianym drzewie.
7. Zmiana workflow musi przejść testy repozytorium i zewnętrzny auditor polityki; pull request nie może sam dostarczać autorytatywnej reguły, która go zatwierdza.
8. Nie publikuj artefaktu, który nie był testowany w publikowanej postaci. To repo obecnie nie ma automatycznego workflow publikacji.

## Weryfikacja i review

Najpierw uruchom najmniejszy test. Następnie:

```bash
make quality
make test
make verify
```

`make full` łączy pełną bezpłatną bramkę i playback offline. Płatne nagrywanie nie jest częścią zwykłej bramki. Lokalna bramka nie zastępuje zewnętrznego sprawdzenia polityki workflow na przypiętej rewizji po wypchnięciu zmian.

Własny review obejmuje:

- zgodność z kanonicznym kontraktem;
- zachowanie fail-closed i wartości brzegowe;
- prywatność, sekrety i koszty;
- deterministyczność oraz brak ręcznej edycji artefaktów VCR;
- uprawnienia i piny workflow;
- zgodność dokumentacji i komend z aktualnym drzewem.

Raport końcowy zawiera:

- branch i dokładny SHA;
- zmienione kontrakty oraz ich konsumentów;
- wykonane komendy i wyniki;
- pominięte bramki wraz z powodami;
- ryzyka rezydualne;
- status CI;
- wymagane dalsze review lub działania.

## Bezpieczne zatrzymanie i rollback

Zatrzymaj publikację, gdy test regresyjny nie przechodzi, pełna macierz jest częściowa, playback wymaga sieci lub sekretu, workflow żąda zbędnego write permission albo konflikt kontraktów pozostaje nierozstrzygnięty.

Rollback polega na wycofaniu spójnej zmiany kontraktu wraz z jej konsumentami. Nie przywracaj starego zachowania przez drugi „aktualny” plik, numerowany wariant ani wyłączenie testu.
