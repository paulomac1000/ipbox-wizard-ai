# IP Box Wizard AI

**Deterministyczny silnik wspierający przygotowanie rozliczenia IP Box programisty B2B.**

Projekt przyjmuje znormalizowane dane o przychodach, czasie pracy, kosztach, dowodach i ulgach, a następnie tworzy audytowalny raport z alokacją IP/NIE, współczynnikiem `W`, kosztami `MIX`, NEXUS, podatkiem, testami kontrolnymi oraz śladem decyzji.

Najważniejsza zasada projektu jest prosta:

> **Python liczy i ustala wynik. Model językowy nie wykonuje krytycznej arytmetyki ani klasyfikacji podatkowej.**

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11–3.13-blue.svg)](pyproject.toml)

> [!IMPORTANT]
> To narzędzie pomocnicze, nie porada podatkowa ani generator gotowego zeznania. Dane wejściowe i wynik powinny zostać sprawdzone przez księgową lub doradcę podatkowego przed użyciem w rozliczeniu.

## Co dostajesz

Dla kompletnego, znormalizowanego wejścia silnik potrafi przygotować:

- podział przychodów na IP i NIE;
- miesięczny współczynnik czasu `W` z jawną metodą;
- klasyfikację kosztów jako IP, NIE, MIX albo WYKLUCZONE;
- alokację kosztów pośrednich z zachowaniem każdego grosza;
- koszyki NEXUS A/B/C/D i współczynnik NEXUS;
- dochód kwalifikowany oraz część IP opodatkowaną zwykłą stawką;
- kaskadę podatku i ulg właściwą dla roku 2019–2026;
- TEST 1–9, statusy STOP i REVIEW oraz ostrzeżenia;
- audyt źródłowej KPiR, ewidencji i zeznania;
- `correction_preview` pokazujący skutki korekty bez udawania finalnego wyniku;
- `calculation_meta` z hashem wejścia, źródłami reguł i tożsamością silnika.

Projekt jest szczególnie przydatny, gdy trzeba jasno odpowiedzieć na pytania:

- czy przychód rzeczywiście kwalifikuje się do IP Box;
- czy współczynnik `W` został policzony właściwą metodą;
- czy koszt `MIX` nie został błędnie rozdzielony według `W`;
- czy koszt ma dowód pozwalający przypisać go bezpośrednio do IP;
- czy NEXUS uwzględnia poprawne koszyki i wzór;
- czy rozliczenie źródłowe wymaga korekty;
- która część dochodu podlega 5%, a która zwykłej stawce.

## Zakres i granice

Silnik przyjmuje **znormalizowany YAML/dict**. Repozytorium nie zawiera kompletnego importera surowych PDF, XLSX, KPiR ani formularzy PIT.

Warstwa ekstrakcji dokumentów musi zachować jawne fakty źródłowe, takie jak:

- kwalifikacja prawa i faktury;
- `KUP` i informacja, czy koszt pozostał w KPiR;
- metoda podziału przychodu i kosztów;
- czas pracy i część NIE-IP;
- dowody alokacji oraz dowody NEXUS;
- limity i dokumenty dotyczące ulg.

Brak danych nie jest interpretowany jako zero ani korzystne `true`. Niepewność prowadzi do błędu, STOP albo REVIEW.

## Szybki start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt

ruff format --check .
ruff check .
python -m compileall -q python_helper tests scripts
pytest tests/unit --cov=python_helper --cov-report=term-missing --cov-fail-under=90
pytest -q
```

Pierwsze wywołanie pytest egzekwuje wymagane coverage `python_helper`, a drugie uruchamia pełny bezpłatny suite. Standardowa bramka nie wykonuje płatnych requestów do modeli.

## Uruchom pełny przykład

Repozytorium zawiera syntetyczny scenariusz podstawowego rozliczenia liniowego. Poniższe polecenie uruchamia kanoniczny pipeline referencyjny i zapisuje raport YAML:

```bash
python - <<'PY'
from pathlib import Path

import yaml

from tests.llm.oracle import compute_reference

scenario_path = Path("tests/llm/scenarios/01_basic_linear.yaml")
scenario = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
report = compute_reference(scenario)

Path("report.yaml").write_text(
    yaml.safe_dump(report, allow_unicode=True, sort_keys=False),
    encoding="utf-8",
)
print("Zapisano report.yaml")
PY
```

`yaml.safe_dump` jest funkcją biblioteki PyYAML używanej przez projekt. Pełny przykładowy wynik znajduje się w [`examples/przykladowy_output_yaml.yaml`](examples/przykladowy_output_yaml.yaml).

### Minimalny fragment wejścia

```yaml
input:
  coverage:
    expected_months: 1
    imported_months: 1
    invoices_complete: true
    kpir_complete: true
    work_records_complete: true
    period_closed: true
    confirmed_by: example
  rok: 2025
  forma_opodatkowania: liniowy_19%
  kwalifikowane_IP: true
  polityka_alokacji:
    przychody:
      metoda: czasowa_W
    koszty_MIX:
      metoda: przychodowa_roczna
      źródło: jawna_polityka
      uzasadnienie: Przychód, W, MIX i NEXUS są rozdzielone.
  miesiace:
    - miesiac: 2025-01
      faktury:
        - kwota_PLN: 25000
          kontrahent: ClientA
          kwalifikuje_IP: true
      ewidencja:
        godziny_pracy: 168
        godziny_nie_IP: 16
        procent_faktury_IP: 100
```

To celowo minimalny fragment pokazujący kształt kontraktu. Pełny przykład z kontrahentem, kosztami, dowodami alokacji i NEXUS oraz asercjami znajduje się w [`tests/llm/scenarios/01_basic_linear.yaml`](tests/llm/scenarios/01_basic_linear.yaml). Bardziej złożone przypadki — ulgi, waluty, korekty i wiele IP — znajdują się w [`tests/llm/scenarios/`](tests/llm/scenarios/).

## Używanie deterministycznych helperów

Poszczególne elementy silnika można wykorzystywać bez pipeline'u LLM:

```python
from python_helper import calculate_w_percent

w = calculate_w_percent(
    work_hours=168,
    non_ip_hours=16,
    invoice_percentage=100,
    method="time_only",
)

assert w == 90.48
```

Publiczne helpery obejmują między innymi obliczanie `W`, audyt alokacji, reguły podatkowe per rok, podatek skali, termomodernizację i uzgodnienie ewidencji.

## Jak działa architektura

```text
YAML/dict
   ↓
ścisła walidacja typów, kompletności i dowodów
   ↓
python_helper
W → przychód IP/NIE → koszty i MIX → NEXUS → ulgi → podatek
   ↓
kanoniczny oracle tworzy raport i decision_facts
   ↓
expected_decision: status / stops / reviews
   ↓
LLM kopiuje wyłącznie ograniczoną decyzję protokołu
   ↓
strict JSON Schema + evaluator
   ↓
VCR playback / zweryfikowana kaseta
```

Model nie widzi nazw predykatów podatkowych i nie ustala kodów na podstawie własnej interpretacji. Benchmark mierzy jednoznaczność protokołu i zgodność integracji, a nie zdolność modelu do liczenia podatku.

## Kluczowe invarianty

- przychód IP/NIE, `W`, alokacja `MIX` i NEXUS są niezależnymi decyzjami;
- `W` nie jest domyślnym ani uniwersalnym kluczem `MIX`;
- NEXUS wynosi `min(1, ((A+B)×1,3)/(A+B+C+D))`;
- brak A/B/C/D daje NEXUS `0`, nie `1`;
- część dochodu IP poza preferencją trafia do zwykłej podstawy;
- koszt bez dowodu wyłączności nie staje się kosztem IP;
- opis lub kwota kosztu nie mogą samodzielnie ustalić KUP ani koszyka;
- alokacje zachowują każdy grosz;
- STOP zeruje finalne liczby i klasyfikacje;
- dodatnie odliczenie wymaga zweryfikowanego limitu i dowodu;
- rok, liczby i flagi kwalifikacji mają ścisłe typy;
- odpowiedź modelu musi być czystym JSON-em i zakończyć się `finish_reason=stop`.

Szczegółowy kontrakt znajduje się w [`ipbox_algorytm.md`](ipbox_algorytm.md).

## Mapa repozytorium

| Ścieżka | Rola |
|---|---|
| [`ipbox_algorytm.md`](ipbox_algorytm.md) | kontrakt domenowy i kolejność decyzji |
| [`python_helper/`](python_helper/) | deterministyczna matematyka, walidacja i reguły roczne |
| [`tests/unit/`](tests/unit/) | wykonywalna specyfikacja i regresje |
| [`tests/llm/oracle.py`](tests/llm/oracle.py) | pełny wynik referencyjny |
| [`tests/llm/scenarios/`](tests/llm/scenarios/) | syntetyczne przypadki biznesowe |
| [`tests/llm/vcr/`](tests/llm/vcr/) | fingerprinty, kasety, manifesty i playback |
| [`scripts/`](scripts/) | bramki jakości, raport benchmarku i nagrywanie |
| [`docs/testing.md`](docs/testing.md) | procedura testów, VCR i wydania |
| [`AGENTS.md`](AGENTS.md) | onboarding oraz reguły pracy agenta |
| [`CHANGELOG.md`](CHANGELOG.md) | najważniejsze różnice między wydaniami 0.1 i 0.2 |

## Testy i reprodukowalność

Projekt utrzymuje trzy warstwy kontroli:

1. **Testy jednostkowe** — matematyka, walidacja, reguły roczne i przypadki brzegowe.
2. **Scenariusze referencyjne** — kompletne syntetyczne przypadki biznesowe.
3. **VCR** — zweryfikowane odpowiedzi siedmiu rodzin modeli, odtwarzane offline.

Aktualna macierz wydania 0.2 obejmuje 46 scenariuszy × 7 rodzin modeli, czyli 322 kasety i 7 manifestów. Fingerprint wiąże każdą kasetę z kodem silnika, scenariuszem, requestem i harness VCR.

Pełna bezpłatna bramka:

```bash
ruff format --check .
ruff check .
python -m compileall -q python_helper tests scripts
pytest tests/unit --cov=python_helper --cov-report=term-missing --cov-fail-under=90
pytest -q
python scripts/check_cassette_policy.py
python scripts/vcr_precommit.py --all-models
python scripts/benchmark_report.py
unset OPENROUTER_API_KEY
./scripts/verify_all_models.sh
for script in scripts/*.sh dump-to-md.sh; do bash -n "$script"; done
```

CI uruchamia bezpłatne kontrole na Pythonie 3.11, 3.12 i 3.13. Playback nie ma live fallbacku i nie potrzebuje sekretu.

## Płatne nagrywanie modeli

Nagrywanie jest opcjonalne, jawne i płatne. Nie wykonuj go po każdej zmianie.

Najpierw odśwież metadane i sprawdź istniejące odpowiedzi bez API:

```bash
python scripts/refresh_vcr_metadata.py --all-models --write
python scripts/vcr_precommit.py --all-models
unset OPENROUTER_API_KEY
./scripts/verify_all_models.sh
python scripts/benchmark_report.py
```

Jeżeli raport zwraca `all_complete_and_valid=true`, płatne nagrywanie nie jest potrzebne. Płatnie nagrywaj wyłącznie kasetę rzeczywiście unieważnioną przez zmianę requestu lub semantyki. Każdy przebieg wymaga jawnego potwierdzenia oraz dwóch dodatnich limitów kosztu. Szczegóły: [`docs/testing.md`](docs/testing.md).

## Rozwój projektu

Przed zmianą kodu przeczytaj [`AGENTS.md`](AGENTS.md). Dokument zawiera:

- topologię modułów;
- przepływ danych;
- hierarchię źródeł prawdy;
- procedury dodawania reguły, scenariusza i poprawki;
- typowe ścieżki debugowania;
- zasady bezpiecznego nagrywania;
- Definition of Done.

Dobry wkład do projektu zaczyna się od minimalnego testu odtwarzającego problem i kończy pełną bramką jakości. Nie osłabiaj testów ani schemy pod zachowanie konkretnego modelu.

## Status wersji 0.2

Wersja 0.2 skupia się na deterministycznym obliczaniu, audytowalności, bezpiecznych domyślnych zachowaniach i odtwarzalnym benchmarku. Nie próbuje jeszcze rozwiązać pełnego importu dokumentów ani automatycznego przygotowania gotowego zeznania.

Planowane kierunki dalszego rozwoju mogą obejmować:

- deterministyczny importer KPiR/PIT/XLSX z pełnym lineage danych;
- stabilne identyfikatory dokumentów i decyzji;
- osobny publiczny CLI/API dla pełnego raportu;
- model zdarzeń korekt i certyfikat decyzji;
- dalsze upraszczanie aktywnych warstw zgodności `_legacy`.

## Licencja

Projekt jest udostępniany na licencji [MIT](LICENSE).
