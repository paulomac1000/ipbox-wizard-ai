# AGENTS.md

Ten plik jest punktem wejścia dla agenta pracującego w repozytorium. Po jego przeczytaniu agent powinien rozumieć, co projekt robi, gdzie znajduje się logika, jak wprowadzać zmiany i jak uniknąć naruszenia kontraktu podatkowego lub VCR.

## Misja

Utrzymuj audytowalne, fail-closed narzędzie wspierające przygotowanie danych do rozliczenia IP Box programisty B2B.

Projekt nie jest poradą podatkową ani generatorem gotowego zeznania. Wynik musi zostać zweryfikowany przez księgową lub doradcę podatkowego.

## Pierwsze 5 minut

Przeczytaj w tej kolejności:

1. `README.md` — cel, zakres i uruchomienie projektu.
2. `AGENTS.md` — zasady pracy i architektura.
3. `ipbox_algorytm.md` — domenowy kontrakt oraz kolejność decyzji.
4. Pliki związane z aktualnym zadaniem.
5. Odpowiadające im testy jednostkowe i scenariusze LLM.

Następnie uruchom przynajmniej test celowany. Przed zakończeniem pracy uruchom pełną bramkę jakości z tego dokumentu.

## Co robi projekt

Wejściem jest znormalizowany YAML/dict opisujący rok, formę opodatkowania, kompletność źródeł, faktury, czas pracy, koszty, dowody i ulgi.

Wyjściem jest deterministyczny raport zawierający między innymi:

- przychody IP i NIE;
- miesięczny współczynnik `W`;
- koszty IP, NIE, MIX i WYKLUCZONE;
- alokację MIX z zachowaniem groszy;
- koszyki A/B/C/D i NEXUS;
- dochód kwalifikowany i część opodatkowaną zwykłą stawką;
- podatek oraz wykorzystanie ulg;
- TEST 1–9, STOP, REVIEW i ostrzeżenia;
- audyt źródłowej KPiR i podgląd korekty;
- metadane odtwarzalności.

Repozytorium nie zawiera kompletnego importera surowych PDF, XLSX, KPiR ani PIT. Błędna ekstrakcja danych wejściowych nie może być „naprawiana” domysłami kalkulatora.

## Topologia projektu

| Obszar | Odpowiedzialność |
|---|---|
| `ipbox_algorytm.md` | domenowy kontrakt, kolejność faz, STOP/REVIEW i granice zakresu |
| `python_helper/ipbox_calculator.py` | podstawowe obliczenia W, MIX, NEXUS, dochodu i rozliczenia |
| `python_helper/tax_year_rules.py` | reguły i limity przypisane do lat 2019–2026 |
| `python_helper/tax_cascade.py` | kanoniczna kaskada podatku i ulg |
| `python_helper/allocation_audit.py` | audyt przychodu i współczynnika W |
| `python_helper/cost_audit.py` | klasyfikacja kosztów, dowody i audyt KPiR |
| `python_helper/report_metadata.py` | hash wejścia, źródła reguł i `engine_source_hash` |
| `tests/llm/oracle.py` | kanoniczny referencyjny przebieg pełnego raportu |
| `tests/llm/oracle_legacy.py` | aktywna baza zgodności pod wrapperem; nie dodawaj tu nowych reguł |
| `tests/llm/output_schema.py` | kanoniczny kontrakt raportu |
| `tests/llm/output_schema_legacy.py` | aktywna baza zgodności do osobnej migracji |
| `tests/llm/scenarios/` | syntetyczne przypadki biznesowe |
| `tests/unit/` | wykonywalna specyfikacja zachowania |
| `tests/llm/evaluator.py` | semantyczne porównanie raportu i odpowiedzi modelu |
| `tests/llm/vcr/` | fingerprint, nagrywanie, playback, kasety i manifesty |
| `scripts/` | bramki jakości, raport benchmarku i bezpieczne nagrywanie |
| `docs/testing.md` | pełna procedura testów i wydania |

Nie używaj numerowanych nazw modułów ani funkcji. Aktualna implementacja ma nazwę kanoniczną, a zachowana baza zgodności jawny sufiks `_legacy`.

## Przepływ danych

```text
znormalizowany YAML/dict
        ↓
walidacja typów, kompletności i dowodów
        ↓
python_helper: W, przychód, MIX, NEXUS, reguły roku, ulgi, podatek
        ↓
tests/llm/oracle.py: autorytatywny raport + decision_facts
        ↓
expected_decision: status / stops / reviews
        ↓
LLM kopiuje wyłącznie ograniczoną decyzję protokołu
        ↓
evaluator + strict JSON Schema
        ↓
VCR zapisuje albo odtwarza zweryfikowaną odpowiedź
```

**Python jest źródłem prawdy. LLM nie liczy podatku, nie ustala klasyfikacji i nie widzi nazw predykatów podatkowych.**

## Hierarchia źródeł prawdy

1. `ipbox_algorytm.md` — znaczenie biznesowe i granice procesu.
2. `python_helper/**/*.py` — deterministyczna implementacja.
3. `tests/unit/` — wykonywalne invarianty i przypadki brzegowe.
4. `tests/llm/oracle.py` oraz schema — pełny kontrakt raportu.
5. `tests/llm/scenarios/` — przykłady biznesowe i regresje.
6. Dokumentacja pomocnicza.

Sprzeczność między źródłami jest błędem. Nie wybieraj wygodniejszej wersji. Ustal prawidłowy kontrakt, popraw implementację i testy razem.

## Jak wprowadzać zmiany

### Reguła podatkowa lub limit roczny

1. Zmień `tax_year_rules.py` albo `tax_cascade.py`.
2. Dodaj test roku granicznego i roku sąsiedniego w `tests/unit/`.
3. Sprawdź wpływ na oracle i scenariusze.
4. Odśwież metadane VCR offline.
5. Nagrywaj kasety tylko wtedy, gdy surowa odpowiedź naprawdę stała się niezgodna.

### Błąd kalkulatora lub alokacji

1. Najpierw dodaj minimalny test odtwarzający błąd.
2. Popraw kanoniczny moduł w `python_helper/`.
3. Sprawdź zachowanie na wartościach zerowych, granicznych, ujemnych i błędnych typach.
4. Zweryfikuj zachowanie do grosza i brak mieszania przychodu, W, MIX oraz NEXUS.
5. Uruchom regresje oracle i evaluator.

### Nowy scenariusz biznesowy

1. Dodaj syntetyczny YAML w `tests/llm/scenarios/`.
2. Użyj stabilnego, opisowego `meta.id` zgodnego z nazwą pliku.
3. Dodaj kompletne dowody i jawne polityki. Nie wymyślaj faktów tylko po to, aby scenariusz przeszedł.
4. Dodaj odpowiednie asercje oraz test jednostkowy, jeśli odkryto nowy invariant.
5. Najpierw sprawdź oracle lokalnie, potem playback.

### Zmiana schemy lub protokołu LLM

1. Zmień kanoniczną schemę i evaluator razem.
2. Nie osłabiaj lokalnej walidacji z powodu ograniczeń providera.
3. Provider może dostać transportową kopię schemy, ale wynik musi przejść pełną lokalną schemę i semantykę.
4. Załóż, że zmiana unieważnia wszystkie zależne fingerprinty; potwierdź to narzędziami zamiast edytować kasety ręcznie.

### Dokumentacja

- `README.md` opisuje produkt i pierwszy kontakt.
- `AGENTS.md` opisuje sposób pracy z kodem.
- `ipbox_algorytm.md` jest kontraktem domenowym, nie marketingowym opisem.
- `CHANGELOG.md` zawiera tylko najważniejsze różnice między wydaniami.
- Nie wpisuj do dokumentacji ulotnych liczb testów, chyba że opisujesz konkretną, zamkniętą wersję.

## Invarianty domenowe

### Przychód, W, MIX i NEXUS

- kwalifikacja przychodu, `W`, alokacja `MIX` i NEXUS są niezależnymi decyzjami;
- `W` nie jest uniwersalnym kluczem `MIX`;
- NEXUS = `min(1, ((A+B)×1,3)/(A+B+C+D))`;
- `A=B=C=D=0` oznacza NEXUS `0`;
- część dochodu IP nieobjęta preferencją trafia do zwykłej podstawy;
- koszt bez dowodu wyłączności nie staje się `IP`;
- `allocation_source` i `nexus_evidence` są odrębnymi dowodami;
- alokacje zachowują każdy grosz;
- `rounding_steps` jest prawdziwym dodatnim `int`, nie booleanem, stringiem ani floatem.

### Fail-closed i kompletność

- brak danych nie jest zerem ani korzystnym domyślnym `true`;
- pola liczbowe odrzucają booleany, stringi i wartości nieskończone;
- rok i flagi kwalifikacji mają ścisłe typy;
- `STOP_03` wymaga kompletnego `input.coverage`; brak kompletności daje `PROVISIONAL` i REVIEW;
- dodatnie odliczenie wymaga zweryfikowanego limitu i dowodu;
- dodatni lot termomodernizacji wymaga `origin_year` i `evidence_ref`;
- opis kosztu może utworzyć review, lecz nie ustala samodzielnie KUP, koszyka ani środka trwałego;
- STOP zeruje finalne liczby i klasyfikacje;
- TEST 1–9 ustala wyłącznie Python.

### LLM, schema i VCR

- model zwraca wyłącznie `status`, `stops`, `reviews`;
- parser nie naprawia Markdown fences ani nie dopowiada brakujących pól;
- kanały STOP i REVIEW są rozdzielone w schemie;
- `returned_model` musi odpowiadać modelowi żądanemu;
- odpowiedź wymaga `finish_reason=stop`;
- playback nigdy nie wykonuje live requestu;
- recorder nie nadpisuje istniejącej kasety;
- kaseta powstaje dopiero po schema PASS, semantic PASS i ponownym parsowaniu;
- `engine_source_hash`, request, scenariusz i harness należą do fingerprintu;
- nie używaj chwilowego `GITHUB_SHA` jako semantycznej tożsamości raportu.

### Prywatność i koszty

- testy, przykłady i kasety używają danych syntetycznych;
- nie commituj danych podatnika, dokumentów źródłowych, sekretów ani realnych identyfikatorów;
- standardowy CI nie może wykonywać płatnych requestów;
- płatny przebieg wymaga jawnego potwierdzenia i dwóch dodatnich, skończonych limitów;
- potwierdzenia płatnego przebiegu nie zapisuj w `.env`;
- każda naliczona odrzucona próba musi pozostać w niezmiennym rejestrze kosztów.

## Debugowanie

| Objaw | Najpierw sprawdź |
|---|---|
| test jednostkowy nie przechodzi | czy zmienił się kontrakt roku, typ wejścia, kolejność kaskady lub zaokrąglenie |
| oracle zwraca inny wynik | walidację wejścia, adapter, klasyfikację kosztów i reguły roku |
| playback nie przechodzi | fingerprint, request hash, model, `finish_reason`, schema i semantykę |
| cassette policy nie przechodzi | brakujące lub nadmiarowe pliki, manifest, nazwy scenariuszy i katalogów modeli |
| benchmark ma brakujące rekordy | `meta.id`, nazwa pliku, kompletność manifestu i dokładny wybór scenariusza |
| koszt nagrywania jest niepełny | katalog odrzuceń, timestamp sesji i metadane `usage.cost` |
| wynik jest podejrzanie korzystny | domyślne wartości, brak dowodów, koszty prywatne i błędne mieszanie W z MIX |

Nie „naprawiaj” problemu przez rozszerzenie tolerancji, osłabienie asercji, ręczną edycję kasety albo dodanie `skip`.

## Bramka jakości

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

Najpierw uruchamiaj test celowany, ale nie kończ zadania wyłącznie na nim. Finalny raport musi podać sprawdzony SHA, wykonane polecenia, wyniki testów, coverage i stan VCR.

## Nagrywanie kaset

Najpierw spróbuj bez API:

```bash
python scripts/refresh_vcr_metadata.py --all-models --write
python scripts/vcr_precommit.py --all-models
unset OPENROUTER_API_KEY
./scripts/verify_all_models.sh
python scripts/benchmark_report.py
```

Nie nagrywaj kaset profilaktycznie. Gdy zmiana requestu albo semantyki rzeczywiście unieważniła konkretną kasetę, usuń wyłącznie tę kasetę i nagraj ją przez `scripts/record_model.py`.

Płatny przebieg wymaga:

```bash
LLM_PAID_RUN_CONFIRMATION=RUN_PAID_BENCHMARK \
python scripts/record_model.py \
  --model <MODEL> \
  --scenario <EXACT_SCENARIO_ID> \
  --max-cost-per-model-usd <LIMIT> \
  --max-total-cost-usd <TOTAL_LIMIT>
```

Nie używaj `--force`. Nie uruchamiaj całej macierzy, gdy zmieniła się jedna kaseta.

## Nie wolno

- liczyć krytycznej arytmetyki w modelu zamiast w Pythonie;
- wymyślać kursów NBP, limitów, dowodów lub kwalifikacji;
- osłabiać asercji, schemy lub evaluatora pod odpowiedź modelu;
- ręcznie edytować odpowiedzi, hashy, fingerprintów, kosztów lub timestampów kaset;
- dodawać korzystnych wartości domyślnych dla kwalifikacji IP;
- łączyć niejednoznacznych pól, np. `ulga_BR` albo `straty_poprzednie`;
- włączać live fallbacku w playbacku;
- deklarować gotowości przy niepełnej macierzy lub czerwonym CI;
- usuwać aktywnych modułów `_legacy` bez osobnego refaktoru, testów i migracji.

## Definition of Done

Zmiana jest gotowa, gdy:

1. zachowanie jest opisane przez test regresyjny;
2. źródła prawdy są spójne;
3. bramka jakości przechodzi;
4. coverage pozostaje co najmniej 90%;
5. VCR jest kompletny, aktualny i odtwarza się bez sekretu;
6. nie wykonano nieuzasadnionych płatnych requestów;
7. dokumentacja i changelog są zaktualizowane, jeżeli zmienił się kontrakt użytkownika;
8. repozytorium nie zawiera danych podatnika ani sekretów;
9. raport końcowy jasno rozróżnia to, co sprawdzono, od tego, czego nie można było zweryfikować.
