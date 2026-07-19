# Brief: końcowa odbudowa kaset przed merge PR #2

## Cel

Pobrać najnowszy branch `fix/decouple-mix-allocation-from-w`, uruchomić wszystkie bramki deterministyczne i nagrać ostatnią kompletną macierz VCR od zera dla modeli z `tests/llm/models.py`.

Punkt docelowy: **46 scenariuszy × 7 modeli = 322 świeże kasety oraz 7 manifestów**.

## Dlaczego poprzednie 322/322 nie są finalne

Macierz nagrana na HEAD `be22ebb` poprawnie przeszła semantykę i playback. Końcowy audyt wykrył jednak, że `ipbox_algorytm.md` nadal opisywał starszy protokół zamiast wykonywalnej koperty `expected_decision`. Plik algorytmu jest źródłem prawdy i częścią fingerprintu, więc jego synchronizacja celowo unieważnia wszystkie stare kasety.

Nie kopiuj poprzednich odpowiedzi i nie aktualizuj ręcznie hashy ani fingerprintów.

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

Oczekuj co najmniej 256 testów jednostkowych PASS, coverage ponad 90% i 46 kontrolowanych skipów LLM. `check_cassette_policy.py` może przejść dla pustego katalogu, ale pełny merge gate pozostanie czerwony do czasu nagrania 322/322.

## Usuń unieważnione kasety

```bash
find tests/llm/vcr/cassettes -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} +
find tests/llm/vcr/cassettes -maxdepth 1 -type f ! -name '.gitkeep' -delete
```

Sprawdź:

```bash
find tests/llm/vcr/cassettes -mindepth 1 -print
```

Dozwolony jest tylko `.gitkeep`.

## Nagranie

```bash
export VCR_MODE=record
export OPENROUTER_API_KEY='...'
./scripts/record_all_models.sh --max-cost-usd 5
```

Profile transportowe są już ustalone:

- Claude Haiku używa `json_schema` z usuniętym `uniqueItems` wyłącznie w głębokiej kopii transportowej;
- MiniMax używa `json_object` z pełną lokalną walidacją;
- pozostałe modele używają pełnego `json_schema`.

Nie zmieniaj tych profili bez nowego odtworzonego błędu i regresji.

## Obsługa odrzucenia

Przy odrzuceniu:

1. zatrzymaj się i zachowaj `/tmp/ipbox_llm_rejected/<model>/`;
2. sklasyfikuj problem jako transport/provider, format, schema, semantyka, model albo kod/oracle;
3. nie edytuj odpowiedzi lub kasety;
4. nie osłabiaj lokalnej schema i asercji;
5. nie ponawiaj błędu semantycznego dla „szczęśliwego” wyniku;
6. przy błędzie transportowym sprawdź, czy żadna kaseta nie powstała, zanim wznowisz brakujący model.

## Końcowa weryfikacja offline

```bash
python scripts/check_cassette_policy.py
python scripts/benchmark_report.py
python scripts/vcr_precommit.py --all-models
unset OPENROUTER_API_KEY
export VCR_MODE=playback
./scripts/verify_all_models.sh
```

## Kryteria odbioru

- liczba scenariuszy wynosi 46;
- każdy z siedmiu modeli ma dokładnie 46 świeżych kaset i kompletny manifest;
- łącznie istnieją dokładnie 322 kasety i 7 manifestów;
- `benchmark_report.py` zwraca `all_complete_and_valid=true`;
- zero starych modeli, dodatkowych katalogów i częściowych manifestów;
- zero Markdown fences, substytucji modelu, błędnych `finish_reason`, skrzyżowanych STOP/REVIEW i niespójnych fingerprintów;
- playback przechodzi po usunięciu `OPENROUTER_API_KEY`;
- scenariusz 51 dla każdego modelu ma dokładnie `status=STOPPED`, `stops=[STOP_12]`, `reviews=[REVIEW_09]`;
- git status jest czysty po commit/push;
- `Deterministic CI` przechodzi na Pythonie 3.11, 3.12 i 3.13;
- job Python 3.13 wykonuje pełny raport i playback offline;
- PR pozostaje niezmieniony po zatwierdzonym nagraniu poza aktualizacją opisu/statusu.

## Wypchnięcie i raport

Wypchnij kasety na ten sam branch. Nie twórz nowego PR i nie merguj.

Raport końcowy ma zawierać:

- HEAD;
- wynik unit/coverage, pełnego suite i shell check;
- liczbę scenariuszy, kaset i manifestów;
- wynik 46/46 per model;
- retry i odrzucenia wraz z klasyfikacją;
- pełny koszt, łącznie z odrzuconymi requestami;
- wynik `benchmark_report.py`, `vcr_precommit.py` i playbacku bez sekretu;
- wynik CI dla Pythonów 3.11–3.13;
- potwierdzenie, że PR nadal nie został zmergowany;
- werdykt `READY` lub `NOT READY`.
