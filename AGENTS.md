# AGENTS.md

## Misja

Utrzymuj wiarygodne, fail-closed narzędzie wspierające przygotowanie danych do IP Box. Nie przedstawiaj wyniku jako porady podatkowej ani kompletnego zeznania bez kontroli księgowej lub doradcy.

## Źródła prawdy

1. `ipbox_algorytm.md` — reguły i granice zakresu.
2. `python_helper/ipbox_calculator.py` — deterministyczna matematyka.
3. `tests/llm/oracle.py` — wynik referencyjny harnessu.
4. `tests/llm/output_schema.py` — kontrakt raportu.
5. `tests/llm/scenarios/` — przypadki biznesowe.
6. `tests/unit/` — wykonywalna specyfikacja.
7. `docs/testing.md` — procedura wydania i VCR.

Sprzeczność między źródłami jest błędem. Nie wybieraj wygodniejszej wersji.

## Invarianty

- przychód, `MIX` i NEXUS są niezależne;
- `W` nie jest uniwersalnym kluczem `MIX`;
- NEXUS = `min(1, ((A+B)×1,3)/(A+B+C+D))`;
- `A=B=C=D=0` oznacza NEXUS `0`;
- koszt bez dowodu wyłączności nie staje się `IP`;
- kwalifikowany `MIX` wymaga `nexus_source` i `nexus_amount`;
- alokacje zachowują każdy grosz;
- B+R jest rozdzielane na część IP i NIE; część IP pomniejsza dochód przed NEXUS;
- strata pozostałej działalności nie jest stratą konkretnego IP;
- działalność na skali obejmuje wspólną podstawę z innymi dochodami skali;
- działalność liniowa nie miesza w jednej kaskadzie osobnego zeznania skali;
- dodatnie odliczenie roczne bez zweryfikowanego limitu jest błędem;
- STOP zeruje finalne liczby i klasyfikacje;
- TEST 1–9 ustala Python;
- model dostaje tylko aktywne reguły (`true`) i zwraca wyłącznie `status`, `stops`, `reviews`;
- parser nie naprawia Markdown ani innych odchyleń od czystego JSON;
- fakt lub kod nieaktywny nie może pojawić się w promptcie modelu;
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
- nadpisywać poprawnych kaset;
- deklarować gotowości bez 252/252 i playbacku offline.

## Bramka jakości

```bash
ruff format --check .
ruff check .
python -m compileall -q python_helper tests scripts
pytest tests/unit --cov=python_helper --cov-report=term-missing --cov-fail-under=90
pytest -q
python scripts/check_cassette_policy.py
for script in scripts/*.sh dump-to-md.sh; do bash -n "$script"; done
```

Stan bazowy po audycie protokołu: 184 testy, 94,32% coverage, 36 kontrolowanych skipów LLM.

## Nagrywanie

Nagrywaj przez `scripts/record_model.py`. Po zmianie requestu, algorytmu, scenariusza lub schematu usuń wyłącznie unieważnione kasety. Wydanie wymaga 36/36 dla każdego z siedmiu modeli (252/252), czystego JSON bez Markdown fences, zgodnego modelu zwróconego, playbacku bez sekretu, kontroli manifestu i raportu niezależnego agenta.
