# Brief dla niezależnego agenta kończącego PR #2

## Cel

Pobrać aktualny branch `fix/decouple-mix-allocation-from-w`, niezależnie zweryfikować kod i dokumentację, nagrać kompletną macierz VCR, wykonać playback offline i wydać jednoznaczny werdykt. Nie ufaj wcześniejszym raportom ani historycznym kasetom.

## Zasady

- Nie zmieniaj asercji pod odpowiedź modelu.
- Nie twórz ani nie poprawiaj kaset ręcznie.
- Nie kopiuj starych kaset pełnego raportu.
- Nie wymyślaj kursów, limitów, NEXUS ani dowodów.
- Każdą lukę najpierw pokaż testem deterministycznym.
- Nie merguj i nie oznaczaj PR jako ready bez 108/108 i playbacku bez klucza.
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

Oczekiwany punkt startowy: 158 testów PASS, coverage co najmniej 95,27%, 36 kontrolowanych skipów LLM i pusty katalog kaset.

## Niezależny code review

Sprawdź szczególnie:

1. rozdzielenie przychodu, `MIX` i NEXUS;
2. wzór `((A+B)×1,3)/(A+B+C+D)`;
3. B+R IP przed NEXUS i limit części IP+NIE;
4. pełną wspólną podstawę działalności na skali z `dochody_dodatkowe_skala`;
5. odmowę mieszania działalności liniowej z osobnym zeznaniem skali;
6. `strata_NIE_z_lat_poprzednich` i brak zgadywania straty per IP;
7. limity zdrowotnej/IKZE oraz fail-closed dla innego roku;
8. ujemne faktury, zaliczki, ulgi i błędne typy wejścia;
9. zachowanie groszy w multi-IP oraz jawne ograniczenie: to nie jest pełna ewidencja per IP;
10. brak `IDE/chmura/laptop → IP` bez dowodu;
11. zerowanie wszystkich pól po STOP;
12. brak live fallbacku, integralność manifestu, retry i `finish_reason`;
13. zgodność każdego pliku Markdown z kodem.

Nie ograniczaj się do botów. Uruchom także własne testy właściwości dla alokacji i NEXUS.

## Nagranie VCR

```bash
export OPENROUTER_API_KEY='...'
./scripts/record_all_models.sh --max-cost-usd 5
```

Po każdym modelu przejrzyj `/tmp/ipbox_llm_rejected/`, surowe odpowiedzi i raport kosztu. Przy realnym błędzie dodaj regresję, popraw kod i nagraj wyłącznie unieważnione/brakujące kasety.

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

Potwierdź, że żaden request sieciowy nie został wykonany.

## Wymagany raport

Raport ma zawierać:

1. SHA audytowanego commita i stan drzewa.
2. Wynik każdej bramki i coverage.
3. Wynik 36/36 per model, koszt, retry i odrzucenia.
4. Potwierdzenie playbacku bez `OPENROUTER_API_KEY`.
5. Klasyfikację błędów: kod/oracle, scenariusz, instrukcja, provider, model.
6. Dla poprawki: test regresyjny, pliki, uzasadnienie i wynik po zmianie.
7. Kontrolę 108 kaset, manifestu, request hashy i fingerprintów.
8. Ręczne wnioski dla scenariuszy 13, 22, 23, 26, 31, 34, 44 i 45.
9. Werdykt dokładnie `READY` albo `NOT READY`.
10. Przy `NOT READY` — minimalną uporządkowaną listę blokad.
11. Potwierdzenie, że PR nie został zmergowany.

## Uzupełnienie: aktywne reguły i integralność VCR

Po nagraniu pierwszej macierzy wykryto jeden wspólny wzorzec błędu: słabsze modele reinterpretowały nazwę fałszywego faktu i dodawały `STOP_02` mimo wartości `false`. Protokół został uproszczony bez wyjątków scenariuszowych: model otrzymuje wyłącznie `active_rules` dla faktów prawdziwych. Nieaktywne nazwy i kody nie trafiają do promptu. Zmiana unieważnia wszystkie wcześniejsze kasety. Playback oraz pre-commit wymagają `finish_reason=stop`, recorder nie nadpisuje istniejących plików, miesiące muszą należeć do `input.rok`, a pula termomodernizacji jest ograniczona do 53 000 zł.
