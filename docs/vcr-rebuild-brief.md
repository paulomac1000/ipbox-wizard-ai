# Brief: ponowna odbudowa kaset po finalnej poprawce NEXUS i W

## Cel

Pobrać najnowszy branch `fix/decouple-mix-allocation-from-w`, potwierdzić poprawkę opodatkowania części dochodu IP poza preferencją oraz fail-closed dla niejednoznacznej metody W, a następnie nagrać kompletną macierz VCR od zera.

Punkt docelowy:

```text
46 scenariuszy × 7 modeli = 322 kasety
7 manifestów
```

Nie merguj PR i nie przełączaj go z draftu.

## Dlaczego poprzednie 322 kasety są nieważne

Po poprzednim nagraniu zmieniły się:

- deterministyczna kaskada podatkowa;
- raport podatkowy i jego strict schema;
- lista REVIEW — dodano `REVIEW_18`;
- walidacja semantyki W;
- `ipbox_algorytm.md`, którego hash wchodzi do fingerprintu;
- oczekiwane raporty scenariuszy z `NEXUS < 1`.

Starych kaset nie wolno edytować, kopiować, przepisywać ani zachować przez podmianę hashy.

## 1. Pobranie aktualnego kodu

```bash
git fetch origin
git switch fix/decouple-mix-allocation-from-w
git pull --ff-only
git status --short
git log -1 --oneline
```

Zapisz HEAD w raporcie. Drzewo robocze musi być czyste.

## 2. Bezpłatna bramka przed requestami

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

Nie uruchamiaj płatnych requestów, dopóki cała bramka nie przejdzie.

## 3. Krytyczne regresje

```bash
pytest -q \
  tests/unit/test_nexus_ordinary_tax_and_w_policy.py \
  tests/unit/test_cost_audit.py \
  tests/unit/test_allocation_precision.py \
  tests/unit/test_allocation_guard_streams.py \
  tests/unit/test_real_world_regressions_synthetic.py
```

### Kaskada NEXUS

Syntetyczny przypadek:

```text
dochód IP = 10 000
NEXUS = 0,65
forma = liniowy 19%
```

Musi dać:

```text
dochód kwalifikowany = 6 500
podatek IP 5% = 325

dochód IP poza preferencją = 3 500
podatek zwykły 19% = 665

podatek łączny = 990
```

### Scenariusz 29 — NEXUS zero

Musi pozostać `FINAL` i dać:

```text
dochód_IP_kwalifikowany = 0
dochód_IP_poza_preferencją = 5 000
podatek_IP = 0
podatek_NIE_finalny = 950
podatek_całościowy = 950
```

NEXUS zero nie może wyzerować podatku od całego dochodu IP.

### Scenariusz 30 — NEXUS mieszany

Musi dać:

```text
podstawa_IP = 8 931
podstawa_zwykła = 17 569
podatek_IP = 447
podatek_NIE_finalny = 3 338
podatek_całościowy = 3 785
```

### Metoda W

Brak `polityka_alokacji.W.metoda` musi zostać odrzucony, gdy w tym samym miesiącu jednocześnie:

```text
godziny_nie_IP != 0
procent_faktury_IP != 100
```

Nie dodawaj domyślnego `conditional_product` dla tego przypadku.

Jeżeli aktywny jest tylko jeden modyfikator, kanoniczna reprezentacja może pozostać używana, ponieważ obsługiwane wzory dają wtedy identyczny wynik.

### Brak dowodu NEXUS

Pozycja bez `nexus_evidence`:

- trafia do `poza_nexus`;
- ma `nexus_amount = 0`;
- emituje `NEXUS_EVIDENCE_MISSING`;
- aktywuje `REVIEW_18`;
- nie wyzerowuje podatku, ponieważ część nieobjęta preferencją jest opodatkowana zwykłą stawką.

### Wcześniejsze krytyczne regresje

Potwierdź również:

- scenariusz 32: `SOURCE_KPIR_REQUIRES_CORRECTION` i `STOP_12`;
- scenariusz 52: `monthly_pool`, zachowanie groszy i kompletne dowody NEXUS;
- scenariusz 39: niezależny audyt projektów;
- scenariusz 49: wykrycie podwójnego procentu;
- scenariusz 50: wykrycie nieudokumentowanej zmiany metody;
- scenariusz 55: poprawny `disjoint_components` pozostaje `FINAL`;
- katalog zawiera dokładnie 46 scenariuszy.

## 4. Kontrola prywatności

```bash
pytest -q tests/unit/test_real_world_regressions_synthetic.py

grep -RInE \
  'PESEL|NIP|REGON|@|ul\. |0111-[A-Z0-9.-]+' \
  tests/llm/scenarios python_helper tests/unit || true
```

Przejrzyj każde trafienie. Do repozytorium nie wolno dodawać:

- danych podatnika;
- prawdziwych nazw i identyfikatorów;
- sygnatur prywatnych interpretacji;
- dokładnych kwot historycznego rozliczenia użytkownika;
- fragmentów przesłanych dokumentów.

Regresje mają pozostać niezależne i syntetyczne.

## 5. Usuń unieważnioną macierz

```bash
find tests/llm/vcr/cassettes \
  -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} +
find tests/llm/vcr/cassettes \
  -maxdepth 1 -type f ! -name '.gitkeep' -delete
find tests/llm/vcr/cassettes -mindepth 1 -print
```

Nie pozostawiaj częściowej macierzy.

## 6. Nagraj wszystkie modele od zera

```bash
export VCR_MODE=record
export OPENROUTER_API_KEY='...'
./scripts/record_all_models.sh --max-cost-usd 5
```

Zasady:

- nie zmieniaj modeli ani profili transportowych bez odtworzonego błędu i regresji;
- nie osłabiaj schema, parsera, oracle ani evaluatora;
- nie edytuj odpowiedzi ani kaset;
- nie ponawiaj błędu semantycznego tylko po to, aby uzyskać PASS;
- odrzucone płatne wywołania ujmij w koszcie.

## 7. Obsługa odrzucenia

Dla każdego odrzucenia zachowaj `/tmp/ipbox_llm_rejected/<model>/` i sklasyfikuj problem jako:

- transport/provider;
- format;
- schema;
- semantyka;
- model;
- kod/oracle.

Problem kodu lub oracle napraw najpierw testem deterministycznym. Każda taka zmiana może ponownie unieważnić całą macierz.

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

## 9. Push i CI

```bash
git status --short
git add tests/llm/vcr/cassettes
git commit -m "test: regenerate cassettes after final NEXUS cascade fix"
git push origin fix/decouple-mix-allocation-from-w
```

Po pushu:

1. poczekaj na Deterministic CI dla Pythonów 3.11, 3.12 i 3.13;
2. potwierdź pełny playback offline w jobie 3.13;
3. wywołaj `@coderabbitai review` dla aktualnego HEAD;
4. nie zmieniaj kodu po nagraniu bez ponownej kontroli fingerprintów.

## Kryteria odbioru

- 46 scenariuszy;
- 46/46 dla każdego z siedmiu modeli;
- 322 kasety i 7 manifestów;
- `all_complete_and_valid=true`;
- zero substytucji modelu;
- `finish_reason=stop` dla każdej kasety;
- zero skrzyżowanych STOP/REVIEW;
- zero brakujących i osieroconych plików;
- zero niespójnych request hashy i fingerprintów;
- playback bez `OPENROUTER_API_KEY`;
- pełny `pytest -q` i coverage powyżej 90%;
- zielony CI 3.11–3.13;
- świeże review bez nierozwiązanych blockerów.

## Raport końcowy

Podaj:

- HEAD przed i po nagraniu;
- wersje Pythona i narzędzi;
- liczbę testów oraz coverage;
- wyniki scenariuszy 29, 30, 32, 39, 49, 50, 52 i 55;
- wynik testu niejednoznacznego W i `REVIEW_18`;
- 46/46 per model;
- liczbę kaset i manifestów;
- retry, odrzucenia i koszt;
- wyniki trzech skryptów VCR;
- wynik playbacku bez sekretu;
- wynik CI i CodeRabbit;
- werdykt `READY` albo `NOT READY` z dokładnymi blockerami.

Nie merguj PR i nie przełączaj go z draftu bez osobnej zgody.
