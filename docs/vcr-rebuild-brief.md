# Brief: końcowa odbudowa kaset po poprawce audytu precyzji

## Cel

Pobrać branch `fix/decouple-mix-allocation-from-w`, potwierdzić nowe regresje zaokrąglonego W i audytu per strumień, a następnie nagrać kompletną macierz VCR od zera.

Punkt docelowy: **46 scenariuszy × 7 modeli = 322 świeże kasety oraz 7 manifestów**.

## Dlaczego poprzednie 322 kasety są nieważne

Zmieniły się:

- autorytatywny `ipbox_algorytm.md`, którego hash wchodzi do fingerprintu;
- oracle audytu alokacji;
- scenariusze 39, 49, 50 i 55;
- request fingerprinty wynikające z nowych kopert decyzji tych scenariuszy.

Nie kopiuj odpowiedzi, nie edytuj fingerprintów i nie próbuj zachować poprzednich kaset.

## Bramka przed płatnymi requestami

```bash
git fetch origin
git switch fix/decouple-mix-allocation-from-w
git pull --ff-only
git status --short
git log -1 --oneline

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt

ruff format --check .
ruff check .
python -m compileall -q python_helper tests scripts
pytest tests/unit --cov=python_helper --cov-report=term-missing --cov-fail-under=90
pytest -q
for script in scripts/*.sh dump-to-md.sh; do bash -n "$script"; done
```

Przed nagraniem potwierdź szczególnie:

```bash
pytest -q \
  tests/unit/test_allocation_precision.py \
  tests/unit/test_allocation_guard_streams.py \
  tests/unit/test_real_world_regressions_synthetic.py
```

Oczekiwane zachowanie:

- scenariusz 55 ma status `FINAL`, zachowuje zaokrąglone `W=68,72%` i nie emituje `STOP_09`;
- scenariusz 49 emituje co najmniej `STOP_09` i `STOP_10` mimo zaokrąglonego procentu;
- scenariusz 50 emituje co najmniej `STOP_09`, `STOP_10` i `STOP_11`;
- scenariusz 39 audytuje oba projekty niezależnie;
- wszystkie 46 scenariuszy deterministycznych pozostaje zielone.

## Usuń unieważnione kasety

```bash
find tests/llm/vcr/cassettes -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} +
find tests/llm/vcr/cassettes -maxdepth 1 -type f ! -name '.gitkeep' -delete
find tests/llm/vcr/cassettes -mindepth 1 -print
```

Dozwolony jest tylko `.gitkeep`.

## Nagranie

```bash
export VCR_MODE=record
export OPENROUTER_API_KEY='...'
./scripts/record_all_models.sh --max-cost-usd 5
```

Nie zmieniaj profili transportowych bez odtworzonego błędu i osobnej regresji.

## Obsługa odrzucenia

1. Zachowaj `/tmp/ipbox_llm_rejected/<model>/`.
2. Sklasyfikuj problem jako transport/provider, format, schema, semantyka, model albo kod/oracle.
3. Nie edytuj odpowiedzi ani kasety.
4. Nie osłabiaj schema, parsera, oracle ani evaluatora.
5. Nie ponawiaj błędu semantycznego dla uzyskania szczęśliwego wyniku.

## Weryfikacja offline

```bash
python scripts/check_cassette_policy.py
python scripts/benchmark_report.py
python scripts/vcr_precommit.py --all-models
unset OPENROUTER_API_KEY
export VCR_MODE=playback
./scripts/verify_all_models.sh
pytest tests/llm -q --run-llm
```

## Kryteria odbioru

- dokładnie 46 scenariuszy;
- 46/46 dla każdego z siedmiu modeli;
- dokładnie 322 kasety i 7 manifestów;
- `all_complete_and_valid=true`;
- zero substytucji modelu, błędnych `finish_reason`, skrzyżowanych STOP/REVIEW i niespójnych fingerprintów;
- playback przechodzi bez `OPENROUTER_API_KEY`;
- Deterministic CI przechodzi na Pythonie 3.11, 3.12 i 3.13;
- job Python 3.13 wykonuje pełny raport i playback offline;
- wszystkie świeże uwagi review do bieżącego HEAD są rozwiązane;
- PR pozostaje draftem do czasu niezależnego werdyktu `READY`.

## Raport końcowy

Podaj HEAD, testy, coverage, 46/46 per model, liczbę kaset i manifestów, retry/odrzucenia, całkowity koszt, wynik playbacku bez sekretu, wynik CI oraz werdykt `READY` lub `NOT READY`. Nie merguj PR.
