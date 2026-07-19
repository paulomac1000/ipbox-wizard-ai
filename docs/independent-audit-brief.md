# Brief dla niezależnego agenta kończącego PR #2

## Cel

Pobrać aktualny branch `fix/decouple-mix-allocation-from-w`, niezależnie zweryfikować kod, dokumentację i świeżo nagraną macierz VCR, wykonać playback offline oraz wydać jednoznaczny werdykt. Nie ufaj wcześniejszym raportom ani kasetom z innego fingerprintu.

## Zasady

- Nie zmieniaj asercji pod odpowiedź modelu.
- Nie twórz ani nie poprawiaj kaset ręcznie.
- Nie kopiuj odpowiedzi, hashy, fingerprintów, manifestów ani `parsed_response` ze starszej macierzy.
- Nie wymyślaj kursów, limitów, NEXUS ani dowodów.
- Każdą lukę najpierw pokaż testem deterministycznym.
- Nie ponawiaj semantycznie błędnej odpowiedzi aż do uzyskania szczęśliwego wyniku.
- Nie merguj. Oznacz PR jako ready dopiero po spełnieniu wszystkich kryteriów.

## Kontekst ostatniego nagrania

Macierz 322/322 na HEAD `be22ebb` przeszła semantykę i playback, ale nie jest finalną macierzą wydania. Końcowy audyt wykrył, że `ipbox_algorytm.md` nadal opisywał starszy protokół listy kodów, podczas gdy kod używał autorytatywnej koperty `expected_decision`. Ponieważ algorytm jest źródłem prawdy i częścią fingerprintu, synchronizacja dokumentu unieważniła wszystkie wcześniejsze nagrania.

Ostatnie odrzucenia nie były błędami podatkowymi:

- Claude Haiku: endpoint odrzucał `uniqueItems` w transportowym JSON Schema; adapter usuwa keyword tylko z głębokiej kopii transportowej, lokalna strict schema pozostaje pełna.
- MiniMax: routing DigitalOcean zwracał `content: null` dla `json_schema`; jawny profil używa `json_object`, ale parser, pełna lokalna schema i evaluator pozostają obowiązkowe.

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

Oczekiwany punkt startowy: co najmniej 256 testów jednostkowych PASS, coverage co najmniej 90%, 46 kontrolowanych skipów LLM i brak niesklasyfikowanych zmian roboczych.

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
10. zachowanie groszy w multi-IP i jawne ograniczenie zakresu;
11. brak `IDE/chmura/laptop → IP` bez dowodu;
12. zerowanie wszystkich pól i klasyfikacji po STOP;
13. prompt zawiera tylko `expected_decision`, bez faktów i nazw predykatów;
14. STOP/REVIEW są rozdzielone w danych, local schema i evaluatorze;
15. provider adapter nie mutuje i nie osłabia lokalnej strict schema;
16. brak live fallbacku oraz integralność manifestu, request hashy i fingerprintów;
17. playback i pre-commit odrzucają `finish_reason != stop`, substytucję modelu i niespójne `parsed_response`;
18. recorder nie nadpisuje istniejącej kasety;
19. zgodność każdego pliku Markdown z aktualnym kodem;
20. jawne semantyki W, blokadę podwójnego procentu i niejawnej zmiany metody;
21. uzgodnienie kategorii IP/NIE pomiędzy ewidencją i zeznaniem;
22. reguły roczne 2019–2026 i syntetyczne scenariusze 46–55.

Nie ograniczaj się do botów. CodeRabbit może pominąć pełny review z powodu liczby plików; taki status nie zastępuje ręcznego audytu aktualnego HEAD.

## Nagranie VCR

```bash
find tests/llm/vcr/cassettes -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} +
find tests/llm/vcr/cassettes -maxdepth 1 -type f ! -name '.gitkeep' -delete

export OPENROUTER_API_KEY='...'
./scripts/record_all_models.sh --max-cost-usd 5
```

Nagraj wszystkie 322 kasety od zera. Po każdym modelu przejrzyj `/tmp/ipbox_llm_rejected/`, surowe odpowiedzi i raport kosztu. Przy realnym błędzie zatrzymaj nagranie, sklasyfikuj przyczynę i dodaj regresję przed zmianą kodu. Nie używaj `--force` i nie edytuj kaset.

Szczególnie sprawdź:

- scenariusze 46–55;
- każdy STOP 09–16 dokładnie w `stops`;
- scenariusz 51: dokładnie `status=STOPPED`, `stops=[STOP_12]`, `reviews=[REVIEW_09]`;
- brak Markdown fences również dla modeli korzystających z `json_object`;
- dokładny `returned_model` i `finish_reason=stop`.

## Playback końcowy

```bash
python scripts/check_cassette_policy.py
python scripts/benchmark_report.py
python scripts/vcr_precommit.py --all-models
unset OPENROUTER_API_KEY
./scripts/verify_all_models.sh
git status --short
git diff --stat
```

Potwierdź, że żaden request sieciowy nie został wykonany podczas playbacku, wszystkie siedem modeli ma 46/46, a macierz ma dokładnie 322 aktualne kasety i 7 manifestów.

Po wypchnięciu poczekaj na `Deterministic CI`. Wszystkie trzy wersje Pythona muszą być zielone; job Python 3.13 ma wykonać `benchmark_report.py` oraz pełny playback offline.

## Wymagany raport

Raport ma zawierać:

1. SHA audytowanego commita i stan drzewa.
2. Wynik każdej bramki i coverage.
3. Wynik 46/46 dla każdego modelu, koszt, retry i odrzucenia.
4. Potwierdzenie playbacku bez `OPENROUTER_API_KEY`.
5. Klasyfikację błędów: kod/oracle, scenariusz, instrukcja, adapter/provider, format albo model.
6. Dla poprawki: test regresyjny, pliki, uzasadnienie i wynik po zmianie.
7. Kontrolę 322 kaset, 7 manifestów, request hashy, fingerprintów, `finish_reason` i reparsowania.
8. Ręczne wnioski dla scenariuszy 13, 17, 22, 23, 26, 31, 34, 44, 45 oraz 46–55.
9. Wyjaśnienie pełnego kosztu, łącznie z odrzuconymi próbami.
10. Stan CI dla Pythonów 3.11–3.13.
11. Werdykt dokładnie `READY` albo `NOT READY`.
12. Przy `NOT READY` — minimalną uporządkowaną listę blokad.
13. Potwierdzenie, że PR nie został zmergowany.
