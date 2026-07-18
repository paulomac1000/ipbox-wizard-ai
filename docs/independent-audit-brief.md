# Brief dla niezależnego agenta kończącego PR #2

## Cel

Pobrać aktualny branch `fix/decouple-mix-allocation-from-w`, niezależnie zweryfikować kod i dokumentację, nagrać kompletną macierz VCR, wykonać playback offline i wydać jednoznaczny werdykt. Nie ufaj wcześniejszym raportom ani historycznym kasetom.

## Zasady

- Nie zmieniaj asercji pod odpowiedź modelu.
- Nie twórz ani nie poprawiaj kaset ręcznie.
- Nie kopiuj starych kaset pełnego raportu ani kaset starej mapy `true/false`.
- Nie wymyślaj kursów, limitów, NEXUS ani dowodów.
- Każdą lukę najpierw pokaż testem deterministycznym.
- Nie ponawiaj semantycznie błędnej odpowiedzi aż do uzyskania szczęśliwego wyniku.
- Nie merguj i nie oznaczaj PR jako ready bez 252/252 i playbacku bez klucza.
- Zachowaj PR jako draft do końca audytu.

## Pobranie i bramki

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
python scripts/check_cassette_policy.py
for script in scripts/*.sh dump-to-md.sh; do bash -n "$script"; done
```

Oczekiwany punkt startowy: 181 testów PASS, coverage co najmniej 94,32%, 36 kontrolowanych skipów LLM i pusty katalog kaset poza `.gitkeep`.

## Niezależny code review

Sprawdź szczególnie:

1. rozdzielenie przychodu, `MIX` i NEXUS;
2. wzór `((A+B)×1,3)/(A+B+C+D)`;
3. B+R IP przed NEXUS i limit części IP+NIE;
4. pełną wspólną podstawę działalności na skali z `dochody_dodatkowe_skala`;
5. odmowę mieszania liniowego z osobnym zeznaniem skali;
6. `strata_NIE_z_lat_poprzednich` i brak zgadywania straty per IP;
7. limity zdrowotnej/IKZE oraz fail-closed dla innego roku;
8. ujemne faktury, zaliczki, ulgi i błędne typy wejścia;
9. ścisłe `YYYY-MM`, zgodność roku miesiąca z `input.rok` i limit termomodernizacji 53 000 zł;
10. zachowanie groszy w multi-IP oraz jawne ograniczenie: to nie jest pełna ewidencja per IP;
11. brak `IDE/chmura/laptop → IP` bez dowodu;
12. zerowanie wszystkich pól po STOP;
13. `active_rules` zawiera tylko fakty prawdziwe, a nieaktywne nazwy i kody nie trafiają do promptu;
14. brak live fallbacku, integralność manifestu, request hashy i fingerprintów;
15. playback i pre-commit odrzucają `finish_reason != stop` i niespójne `parsed_response`;
16. recorder nie nadpisuje istniejącej kasety;
17. zgodność każdego pliku Markdown z kodem.

Nie ograniczaj się do botów. Uruchom także własne testy właściwości dla alokacji i NEXUS.

## Nagranie VCR

```bash
export OPENROUTER_API_KEY='...'
./scripts/record_all_models.sh --max-cost-usd 5
```

Nagraj wszystkie 252 kasety od nowa. Poprzednia macierz 108 plików została usunięta: 36 odpowiedzi Claude zawierało Markdown fences akceptowane przez dawny parser, a lista modeli została rozszerzona do siedmiu rodzin.

Po każdym modelu przejrzyj `/tmp/ipbox_llm_rejected/`, surowe odpowiedzi i raport kosztu. Przy realnym błędzie zatrzymaj nagranie, sklasyfikuj przyczynę i dodaj regresję przed zmianą kodu. Nie używaj `--force` i nie edytuj kaset.

Szczególnie sprawdź wcześniejsze problematyczne kombinacje:

- Claude Haiku: scenariusz 17;
- GPT-5 Mini: scenariusze 17, 21, 22, 29 i 30.

Nieaktywne `STOP_02` nie powinno być widoczne w ich promptach.

## Playback końcowy

```bash
unset OPENROUTER_API_KEY
./scripts/verify_all_models.sh
python scripts/benchmark_report.py
python scripts/vcr_precommit.py --all-models
python scripts/check_cassette_policy.py
git status --short
git diff --stat
```

Potwierdź, że żaden request sieciowy nie został wykonany, wszystkie siedem modeli ma 36/36, a macierz ma dokładnie 324 aktualne kasety.

## Wymagany raport

Raport ma zawierać:

1. SHA audytowanego commita i stan drzewa.
2. Wynik każdej bramki i coverage.
3. Wynik 36/36 dla każdego z siedmiu modeli, koszt, retry i odrzucenia.
4. Potwierdzenie playbacku bez `OPENROUTER_API_KEY`.
5. Klasyfikację błędów: kod/oracle, scenariusz, instrukcja, provider, model.
6. Dla poprawki: test regresyjny, pliki, uzasadnienie i wynik po zmianie.
7. Kontrolę 252 kaset, manifestu, request hashy, fingerprintów, `finish_reason` i reparsowania.
8. Ręczne wnioski dla scenariuszy 13, 17, 22, 23, 26, 31, 34, 44 i 45.
9. Wyjaśnienie pełnego kosztu, łącznie z odrzuconymi próbami.
10. Werdykt dokładnie `READY` albo `NOT READY`.
11. Przy `NOT READY` — minimalną uporządkowaną listę blokad.
12. Potwierdzenie, że PR nie został zmergowany.
