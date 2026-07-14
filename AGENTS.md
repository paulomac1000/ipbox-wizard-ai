# AGENTS.md

## Misja

Utrzymuj wiarygodne narzędzie decision-support dla IP Box. Nie przedstawiaj wyniku jako porady podatkowej.

## Źródła prawdy

1. `ipbox_algorytm.md` — reguły procesu.
2. `python_helper/ipbox_calculator.py` — deterministyczna matematyka.
3. `tests/llm/oracle.py` — atomowe fakty oraz niezależna oczekiwana semantyka.
4. `tests/llm/output_schema.py` — osobny kontrakt małej decyzji i finalnego raportu.
5. `tests/llm/scenarios/` — przypadki biznesowe.
6. `tests/unit/` — wykonywalna specyfikacja.

Sprzeczność między źródłami jest błędem do naprawy, nie wyborem modelu.

## Invarianty

- przychód, MIX i NEXUS są rozdzielone;
- W nie jest uniwersalnym kluczem MIX;
- KIS/jawna polityka ma pierwszeństwo przed heurystyką;
- MIX nie trafia do A bez `nexus_source` i `nexus_amount`;
- A=B=C=D=0 oznacza NEXUS=0;
- alokacje zachowują kwotę co do grosza;
- STOP zeruje finalne liczby;
- TEST 1–9 ustala Python;
- model zwraca tylko status/stops/reviews; pełny raport składa kod;
- kody STOP i REVIEW wynikają wyłącznie z jawnych `decision_facts`;
- playback nigdy nie wykonuje live requestu;
- kaseta powstaje dopiero po schema + semantic PASS.

## Nie wolno

- osłabiać asercji pod odpowiedź modelu;
- dodawać `skip: true`;
- ręcznie edytować response/hash/timestamp kasety;
- tworzyć fikcyjnego NEXUS A;
- włączać płatnych requestów do zwykłego CI;
- wznawiać pełnego nagrywania, gdy brakuje tylko kilku kaset i request się nie zmienił;
- oczekiwać od modelu przepisywania deterministycznego raportu;
- dodawać globalnych ignore Ruff.

## Polecenia jakości

```bash
ruff format --check .
ruff check .
python -m compileall -q python_helper tests scripts
pytest tests/unit --cov=python_helper --cov-report=term-missing --cov-fail-under=90
pytest -q
python scripts/check_cassette_policy.py
```

## Nagrywanie

Nagrywaj przez `scripts/record_model.py`, który pomija już istniejące, poprawne pliki. Po każdej zmianie algorytmu, scenariusza, schematu lub requestu usuń kasety konkretnego modelu i nagraj od nowa.

Nigdy nie commituj częściowego zestawu jako bramki. Najpierw 36/36, offline playback, `vcr_precommit.py`, przegląd diffu.
