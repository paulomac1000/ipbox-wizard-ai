# Brief: końcowa odbudowa kaset po poprawce audytu kosztów

## Cel

Pobrać branch `fix/decouple-mix-allocation-from-w`, potwierdzić poprawki audytu KUP, źródłowej KPiR, zaokrągleń kosztów, źródła polityki MIX i dowodów NEXUS, a następnie nagrać kompletną macierz VCR od zera.

Punkt docelowy: **46 scenariuszy × 7 modeli = 322 świeże kasety oraz 7 manifestów**.

Nie dodawaj do repozytorium danych podatnika, prawdziwych nazw, identyfikatorów, sygnatur interpretacji ani dokładnych kwot z historycznego rozliczenia. Regresje 32 i 52 używają wyłącznie niezależnych danych syntetycznych.

## Dlaczego dotychczasowe kasety są nieważne

Zmieniły się:

- autorytatywny `ipbox_algorytm.md`, którego hash wchodzi do fingerprintu;
- deterministyczny oracle i schema raportu;
- zestaw dozwolonych STOP-ów — dodano `SOURCE_KPIR_REQUIRES_CORRECTION`;
- wykonywalna kwalifikacja `KUP: false` oraz audyt źródłowej KPiR;
- polityka groszowa `per_cost_item` / `monthly_pool`;
- raport `source_ledger_audit` i bezpieczny `correction_preview`;
- obowiązkowe źródło referencyjne polityki KIS oraz dowód NEXUS;
- scenariusze 32, 44, 45 i 52;
- request fingerprinty i deterministyczne raporty scenariuszy.

Nie kopiuj odpowiedzi, nie edytuj fingerprintów i nie zachowuj poprzednich kaset przez ręczną podmianę metadanych.

## 1. Pobierz dokładny branch

```bash
git fetch origin
git switch fix/decouple-mix-allocation-from-w
git pull --ff-only
git status --short
git log -1 --oneline
```

Przed rozpoczęciem zapisz HEAD w raporcie. Drzewo robocze musi być czyste.

## 2. Utwórz środowisko i wykonaj bezpłatną bramkę

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt

ruff format --check .
ruff check .
python -m compileall -q python_helper tests scripts
pytest tests/unit \
  --cov=python_helper \
  --cov-report=term-missing \
  --cov-fail-under=90
pytest -q
for script in scripts/*.sh dump-to-md.sh; do bash -n "$script"; done
```

Nie wykonuj płatnych requestów, dopóki wszystkie powyższe polecenia nie przejdą.

## 3. Potwierdź najważniejsze regresje

```bash
pytest -q \
  tests/unit/test_cost_audit.py \
  tests/unit/test_allocation_precision.py \
  tests/unit/test_allocation_guard_streams.py \
  tests/unit/test_real_world_regressions_synthetic.py
```

Oczekiwane zachowanie:

### Scenariusz 32 — NON-KUP pozostawiony w KPiR i zeznaniu

- status `STOPPED`;
- dokładne STOP-y obejmują `SOURCE_KPIR_REQUIRES_CORRECTION` i `STOP_12`;
- wydatek z `KUP: false` jest `WYKLUCZONE`, a nie `NON`;
- `source_ledger_audit.status` to `REQUIRES_CORRECTION`;
- `correction_preview.status` to `AVAILABLE`;
- preview wskazuje konieczność korekty KPiR i zeznania;
- preview rozróżnia korektę ulgi od końcowej kwoty podatku;
- `tax_unchanged_only_if_reliefs_updated=true` występuje wyłącznie wtedy, gdy poprawiona ulga rzeczywiście zachowuje podatek;
- finalne pola finansowe pozostają wyzerowane, ponieważ istnieje STOP.

### Scenariusz 52 — miesięczna pula kosztów

- status `FINAL`;
- `rounding_granularity=monthly_pool`;
- suma pozycyjnych `ip_amount` dokładnie odpowiada zaokrąglonej miesięcznej puli;
- pojedynczy grosz jest rozdzielony deterministycznie metodą największych reszt;
- `rounding_adjustment` zachowuje ślad tej korekty;
- każda pozycja A/B/C/D ma `nexus_evidence`;
- polityka `interpretacja_KIS` zawiera wyłącznie syntetyczny `źródło_ref`.

### Pozostałe krytyczne regresje

- scenariusz 39 audytuje projekty niezależnie;
- scenariusz 49 nadal wykrywa podwójny procent mimo zaokrąglenia;
- scenariusz 50 nadal wykrywa nieudokumentowaną zmianę metody;
- scenariusz 55 pozostaje `FINAL` dla poprawnie zaokrąglonego W i oddzielnego strumienia NIE-IP;
- scenariusze 44, 45 i 52 nie używają prawdziwej sygnatury interpretacji;
- dokładnie 46 scenariuszy przechodzi pełną walidację oracle i schema.

## 4. Kontrola prywatności przed nagraniem

```bash
pytest -q tests/unit/test_real_world_regressions_synthetic.py

grep -RInE \
  'PESEL|NIP|REGON|@|ul\. |0111-[A-Z0-9.-]+' \
  tests/llm/scenarios python_helper tests/unit || true
```

Przejrzyj każde trafienie. Dozwolone są wyłącznie wartości jawnie syntetyczne, nazwy techniczne i testy walidatora. Nie kopiuj danych z dokumentów użytkownika nawet wtedy, gdy wydają się zanonimizowane przez usunięcie nazwiska.

## 5. Usuń całą unieważnioną macierz

```bash
find tests/llm/vcr/cassettes \
  -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} +
find tests/llm/vcr/cassettes \
  -maxdepth 1 -type f ! -name '.gitkeep' -delete
find tests/llm/vcr/cassettes -mindepth 1 -print
```

Ostatnie polecenie nie może zwrócić nic poza ewentualnym `.gitkeep` na właściwym poziomie. Nie pozostawiaj częściowej macierzy.

## 6. Nagraj całość od zera

```bash
export VCR_MODE=record
export OPENROUTER_API_KEY='...'
./scripts/record_all_models.sh --max-cost-usd 5
```

Zasady:

- nie zmieniaj modeli ani profili transportowych bez odtworzonego błędu i osobnej regresji;
- nie osłabiaj schema, parsera, oracle ani evaluatora;
- nie edytuj odpowiedzi modelu ani wygenerowanej kasety;
- nie ponawiaj błędu semantycznego tylko po to, aby uzyskać szczęśliwy wynik;
- odrzucone płatne wywołania muszą pozostać ujęte w limicie kosztu.

## 7. Obsługa odrzucenia

1. Zachowaj `/tmp/ipbox_llm_rejected/<model>/`.
2. Sklasyfikuj problem jako transport/provider, format, schema, semantyka, model albo kod/oracle.
3. W raporcie podaj model, scenariusz, liczbę prób, koszt i dokładną przyczynę.
4. Problem kodu lub oracle napraw testem deterministycznym przed kolejnym nagraniem całej unieważnionej macierzy.
5. Problem modelu nie uprawnia do ręcznej korekty odpowiedzi ani zmiany oczekiwanego wyniku.

## 8. Pełna weryfikacja offline

```bash
python scripts/check_cassette_policy.py
python scripts/benchmark_report.py
python scripts/vcr_precommit.py --all-models

unset OPENROUTER_API_KEY
export VCR_MODE=playback
./scripts/verify_all_models.sh
pytest tests/llm -q --run-llm
pytest -q
```

Playback nie może próbować połączenia z providerem i musi przejść bez sekretu.

## 9. Wypchnij i sprawdź CI

```bash
git status --short
git add tests/llm/vcr/cassettes
git commit -m "test: regenerate cassettes after cost audit corrections"
git push origin fix/decouple-mix-allocation-from-w
```

Po pushu:

- poczekaj na pełny Deterministic CI dla Pythonów 3.11, 3.12 i 3.13;
- potwierdź, że Python 3.13 wykonał kompletną bramkę i playback offline;
- wywołaj świeże `@coderabbitai review` dla aktualnego HEAD;
- rozwiąż wyłącznie zasadne uwagi i po każdej zmianie sprawdź, czy fingerprinty znów nie zostały unieważnione.

## Kryteria odbioru

- dokładnie 46 scenariuszy;
- dokładnie 46/46 dla każdego z siedmiu modeli;
- dokładnie 322 kasety i 7 manifestów;
- `all_complete_and_valid=true`;
- zero substytucji modelu;
- zero błędnych `finish_reason`;
- zero skrzyżowanych STOP/REVIEW;
- zero niespójnych request hashy i fingerprintów;
- brak osieroconych lub brakujących kaset;
- playback przechodzi bez `OPENROUTER_API_KEY`;
- pełny `pytest -q` przechodzi;
- Deterministic CI jest zielony na Pythonie 3.11, 3.12 i 3.13;
- wszystkie świeże uwagi review do bieżącego HEAD są rozwiązane;
- PR pozostaje draftem do czasu niezależnego werdyktu `READY`.

## Raport końcowy

Podaj:

- HEAD przed i po nagraniu;
- wersje Pythona i narzędzi;
- liczbę testów oraz coverage `python_helper`;
- wynik każdej regresji krytycznej z punktu 3;
- 46/46 dla każdego modelu;
- liczbę kaset i manifestów;
- retry i odrzucenia per model/scenariusz;
- całkowity koszt;
- wynik `check_cassette_policy.py`, `benchmark_report.py` i `vcr_precommit.py`;
- wynik playbacku bez sekretu;
- wynik CI;
- wynik świeżego review;
- werdykt `READY` albo `NOT READY` wraz z blockerami.

Nie merguj PR i nie przełączaj go z draftu bez osobnej zgody.