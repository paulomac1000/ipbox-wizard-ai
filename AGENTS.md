# AGENTS.md

- Nie używaj numerowanych nazw modułów ani funkcji. Aktualna implementacja ma nazwę kanoniczną, a stara — jawny sufiks `_legacy`.
- `STOP_03` wymaga jawnej, kompletnej deklaracji `input.coverage`; brak kompletności daje `PROVISIONAL` i REVIEW.
- Opis, nazwa kontrahenta i sama kwota nie mogą nadpisać jawnego koszyka ani samodzielnie ustalić KUP, składki czy środka trwałego.
- Pola liczbowe odrzucają booleany i teksty wyglądające jak liczby.
- Finalny raport musi zawierać `calculation_meta` z hashem wejścia, źródłami reguł i rewizją kodu.
- Semantyczną tożsamością treści jest `engine_source_hash`; nie używaj chwilowego `GITHUB_SHA` jako fingerprintu wyniku ani kasety.
- Dodatnia przeniesiona kwota termomodernizacji wymaga osobnego lotu z `origin_year` i `evidence_ref`; zbiorcza pula jest wyłącznie trybem zgodnościowym `PROVISIONAL`.

## Misja

Utrzymuj wiarygodne, fail-closed narzędzie wspierające przygotowanie danych do IP Box. Nie przedstawiaj wyniku jako porady podatkowej ani kompletnego zeznania bez kontroli księgowej lub doradcy.

## Źródła prawdy

1. `ipbox_algorytm.md` — reguły i granice zakresu.
2. `python_helper/ipbox_calculator.py`, `tax_year_rules.py` i `allocation_audit.py` — deterministyczna matematyka, reguły roczne i strażniki alokacji.
3. `tests/llm/oracle.py` — kanoniczny wynik referencyjny harnessu; `oracle_legacy.py` jest wyłącznie jawnym adapterem zgodności.
4. `tests/llm/output_schema.py` — kanoniczny kontrakt raportu; `output_schema_legacy.py` jest bazą zgodności.
5. `tests/llm/scenarios/` — przypadki biznesowe.
6. `tests/unit/` — wykonywalna specyfikacja.
7. `docs/testing.md` — procedura wydania i VCR.

Sprzeczność między źródłami jest błędem. Nie wybieraj wygodniejszego źródła.

## Invarianty

- przychód, `MIX` i NEXUS są niezależne;
- `W` nie jest uniwersalnym kluczem `MIX`;
- NEXUS = `min(1, ((A+B)×1,3)/(A+B+C+D))`;
- `A=B=C=D=0` oznacza NEXUS `0`;
- koszt bez dowodu wyłączności nie staje się `IP`;
- kwalifikowany `MIX` wymaga `nexus_source` i `nexus_amount`;
- alokacje zachowują każdy grosz;
- testy i scenariusze nie zawierają danych osobowych ani rzeczywistych kwot podatnika;
- B+R jest rozdzielane na część IP i NIE; część IP pomniejsza dochód przed NEXUS;
- strata pozostałej działalności nie jest stratą konkretnego IP;
- działalność na skali obejmuje wspólną podstawę z innymi dochodami skali;
- działalność liniowa nie miesza w jednej kaskadzie osobnego zeznania skali;
- dodatnie odliczenie roczne bez zweryfikowanego limitu jest błędem;
- dodatni lot termomodernizacji wymaga roku pochodzenia i referencji dowodu;
- rok i flagi kwalifikacji mają ścisłe typy; nie konwertuj stringów, floatów ani booleanów na rok;
- `kwalifikowane_IP`, `kwalifikuje_IP` i `klauzula_IP` nie mają korzystnych domyślnych wartości;
- `allocation_source` i `nexus_evidence` są odrębnymi dowodami;
- opis kosztu może utworzyć kandydaturę do review, ale nie może sam ustalić `KUP: false`;
- STOP zeruje finalne liczby i klasyfikacje;
- TEST 1–9 ustala Python;
- Python buduje pełną autorytatywną kopertę `expected_decision`; model kopiuje bez zmian wyłącznie `status`, `stops`, `reviews`;
- parser nie naprawia Markdown ani innych odchyleń od czystego JSON;
- fakty podatkowe i nazwy predykatów nie mogą pojawić się w promptcie modelu; kanały STOP i REVIEW są rozdzielone także w JSON Schema;
- provider-specific transport nie może osłabić lokalnej strict schema ani evaluatora;
- `json_object` jest dopuszczalny wyłącznie jako jawny adapter modelu i nadal wymaga pełnej lokalnej walidacji;
- `returned_model` musi być identyczny z modelem żądanym podczas live runu, playbacku i pre-commit;
- playback nigdy nie wykonuje live requestu;
- playback i pre-commit odrzucają `finish_reason` inny niż `stop`;
- tryb record nie nadpisuje istniejącej kasety;
- kaseta powstaje dopiero po schema i semantic PASS.

## Nie wolno

- osłabiać asercji lub poszerzać zakresów pod model;
- dodawać `skip: true` jako obejścia;
- ręcznie edytować response, hash, fingerprint lub timestamp kasety;
- wymyślać kursów, limitów, NEXUS A/B lub dowodów kwalifikacji;
- używać niejednoznacznych pól `ulga_BR` albo `straty_poprzednie`;
- włączać płatnych requestów do standardowego CI;
- uruchamiać płatnej macierzy bez jawnego potwierdzenia oraz limitu per model i limitu całego przebiegu;
- nadpisywać poprawnych kaset;
- deklarować gotowości bez 322/322, raportu kompletności i playbacku offline.

## Bramka jakości

```bash
ruff format --check .
ruff check .
python -m compileall -q python_helper tests scripts
pytest tests/unit --cov=python_helper --cov-report=term-missing --cov-fail-under=90
pytest -q
python scripts/check_cassette_policy.py
python scripts/benchmark_report.py
unset OPENROUTER_API_KEY
./scripts/verify_all_models.sh
for script in scripts/*.sh dump-to-md.sh; do bash -n "$script"; done
```

Stan bazowy: co najmniej 256 testów jednostkowych, coverage powyżej wymaganych 90% i 46 scenariuszy LLM. CI na Pythonie 3.13 wymaga kompletnej aktualnej macierzy i wykonuje playback bez sekretu.

## Nagrywanie

Lokalnie `scripts/record_model.py` i `scripts/record_all_models.sh` bezpiecznie wczytują wyłącznie dozwolone ustawienia z ignorowanego przez Git pliku `.env`; istniejące zmienne procesu mają pierwszeństwo. Nigdy nie loguj wartości sekretu. Nagrywaj przez `scripts/record_model.py` lub ręczny workflow `Paid multi-model LLM benchmark`. Wybór scenariusza jest dokładny, a literówka kończy proces przed requestem sieciowym. Każdy płatny przebieg musi mieć osobny limit per model i limit globalny obejmujący odpowiedzi zaakceptowane oraz odrzucone. Po zmianie requestu, algorytmu, scenariusza lub schematu usuń wyłącznie unieważnione kasety. Wydanie wymaga 46/46 dla każdego z siedmiu modeli (322/322), czystego JSON bez Markdown fences, zgodnego modelu zwróconego, playbacku bez sekretu, kontroli manifestu i raportu niezależnego agenta.
