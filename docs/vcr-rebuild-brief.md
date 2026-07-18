# Brief: odbudowa kaset po zmianie reguł historycznych i alokacyjnych

## Cel

Pobrać najnowszy branch `fix/decouple-mix-allocation-from-w`, uruchomić wszystkie bezpłatne bramki, potwierdzić pusty katalog VCR i nagrać kompletną macierz od zera dla dokładnych modeli z `tests/llm/models.py`.

Punkt docelowy: **46 scenariuszy × 7 modeli = 322 świeże kasety oraz 7 manifestów**.

## Kroki

```bash
git switch fix/decouple-mix-allocation-from-w
git pull --ff-only
python -m pip install -r requirements.txt -r requirements-test.txt

ruff format --check .
ruff check .
python -m compileall -q python_helper tests scripts
pytest tests/unit --cov=python_helper --cov-report=term-missing --cov-fail-under=90
pytest -q

find tests/llm/vcr/cassettes -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} +
find tests/llm/vcr/cassettes -maxdepth 1 -type f ! -name '.gitkeep' -delete

export VCR_MODE=record
export OPENROUTER_API_KEY='...'
bash scripts/record_all_models.sh

python scripts/check_cassette_policy.py
python scripts/vcr_precommit.py --all-models
export VCR_MODE=playback
unset OPENROUTER_API_KEY
pytest tests/llm -q --run-llm
bash scripts/vcr_smoke.sh
```

## Kryteria odbioru

- liczba scenariuszy jest pobierana dynamicznie z `tests/llm/scenarios`, ale aktualnie musi wynosić 46;
- każdy z siedmiu modeli ma dokładnie 46 świeżych kaset i kompletny manifest;
- łącznie istnieją dokładnie 322 kasety;
- zero starych modeli, dodatkowych katalogów i częściowych manifestów;
- zero odpowiedzi z Markdown fences, złym modelem, złym `finish_reason`, skrzyżowanymi STOP/REVIEW albo niezgodnym fingerprintem;
- wszystkie testy deterministyczne i playback przechodzą bez klucza API;
- nie zmieniać oracle ani expected values pod odpowiedź modelu;
- w razie odrzucenia zachować pliki z `/tmp/ipbox_llm_rejected/<model>/` i opisać przyczynę przed ponowieniem;
- ręcznie przejrzeć scenariusze 46–55 i potwierdzić poprawne kanały STOP 09–16;
- wypchnąć kasety na ten sam branch;
- po wypchnięciu wywołać świeże `@coderabbitai review`, przeanalizować nowe uwagi na aktualnym HEAD i poprawić tylko zasadne;
- nie mergować PR i nie oznaczać go ready przed kompletnym playbackiem, świeżym review i niezależnym werdyktem.

## Raport końcowy agenta

Podaj HEAD, wynik unit/coverage, pełnego suite, liczbę scenariuszy, oczekiwaną i rzeczywistą liczbę kaset, wynik 46/46 per model, liczbę retry/odrzuceń, koszt, wynik playbacku bez sekretu oraz wynik świeżego CodeRabbit review.
