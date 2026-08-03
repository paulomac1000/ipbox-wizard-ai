<!-- agents-md: layout=single profile=safety-critical language=pl -->
# AGENTS.md

Instrukcja operacyjna dla agentów pracujących z `ipbox-wizard-ai`.

## Zakres i pierwszeństwo

Plik obowiązuje w całym repozytorium. Polecenie użytkownika i zasady platformy mają wyższy priorytet. Konflikt między instrukcjami, kodem, testami i dokumentacją zatrzymuje pracę: wskaż źródła konfliktu i ustal kanonicznego właściciela zamiast wybierać wygodniejszą wersję.

Repozytorium ma profil `safety-critical`: wspiera analizę podatkową, ale nie składa deklaracji i nie zastępuje doradcy podatkowego. Nie rozszerzaj zadania read-only do zapisu, publikacji, płatnych wywołań ani operacji destrukcyjnych bez wyraźnego polecenia.

## Wybierz tryb pracy

| Tryb | Kiedy | Przeczytaj przed działaniem |
|---|---|---|
| Analiza rozliczenia | Użytkownik przekazuje dokumenty lub dane podatkowe | [`docs/agent-tax-analysis.md`](docs/agent-tax-analysis.md), następnie [`ipbox_algorytm.md`](ipbox_algorytm.md) |
| Rozwój repozytorium | Użytkownik zleca zmianę kodu, testów, dokumentacji lub CI | [`docs/agent-development.md`](docs/agent-development.md), następnie pliki i testy związane z zadaniem |
| Audyt read-only | Użytkownik prosi wyłącznie o ocenę | Odpowiedni dokument powyżej; nie twórz brancha, commitów, Issue ani PR |

Nie mieszaj analizy danych podatnika z rozwojem kodu bez osobnej, jawnej decyzji użytkownika.

## Kanoniczni właściciele

| Obszar | Właściciel |
|---|---|
| Produkt, sposoby użycia i ograniczenia | [`README.md`](README.md) |
| Znaczenie biznesowe i kolejność decyzji | [`ipbox_algorytm.md`](ipbox_algorytm.md) |
| Publiczna fasada deterministycznych reguł | [`python_helper/ipbox_calculator.py`](python_helper/ipbox_calculator.py) |
| Konfiguracja testów i progów jakości | [`pyproject.toml`](pyproject.toml) |
| Kanoniczny raport i decyzja | [`tests/llm/oracle.py`](tests/llm/oracle.py), [`tests/llm/output_schema.py`](tests/llm/output_schema.py) |
| Profile modeli i transport | [`tests/llm/models.py`](tests/llm/models.py) |
| Walidacja odpowiedzi | [`tests/llm/evaluator.py`](tests/llm/evaluator.py) |
| Konfiguracja i zapis VCR | [`tests/llm/vcr/config.py`](tests/llm/vcr/config.py), [`tests/llm/vcr/recorder.py`](tests/llm/vcr/recorder.py) |
| Procedura testów, scenariuszy i nagrywania | [`docs/testing.md`](docs/testing.md) |
| Lokalne komendy jakości | [`Makefile`](Makefile) |
| Polityka GitHub Actions | [`scripts/check_workflow_policy.py`](scripts/check_workflow_policy.py) |

`AGENTS.md` opisuje konsekwencje operacyjne i kieruje do właścicieli. Nie duplikuj tutaj pełnych kontraktów, list modeli, liczników testów ani definicji workflow.

## Granice architektury

- Kwalifikacja przychodu, podział IP/NIE, współczynnik `W`, alokacja MIX i NEXUS są niezależnymi decyzjami.
- Python ustala liczby, klasyfikacje, `decision_facts`, STOP-y i REVIEW-y. Model nie wykonuje krytycznej arytmetyki ani klasyfikacji podatkowej.
- Brak danych nie jest zerem, `false`, korzystnym założeniem ani dowodem.
- STOP zeruje finalne liczby i klasyfikacje zgodnie z kontraktem, ale może pozostawić diagnostykę i bezpieczny podgląd korekty.
- Opis kosztu może wywołać REVIEW, lecz nie ustala samodzielnie KUP, koszyka ani NEXUS.
- NEXUS wynosi `min(1, ((A+B) × 1,3) / (A+B+C+D))`; przy `A=B=C=D=0` wynosi `0`.
- Część dochodu IP poza NEXUS podlega zwykłemu opodatkowaniu.
- Alokacje muszą zachować każdy grosz i jawną politykę zaokrąglania.
- Parser nie naprawia brakujących pól ani Markdown fences. Odpowiedź musi przejść wspólną schema i evaluator.
- Playback nie może wykonywać live requestu. Recorder nie nadpisuje istniejącej kasety.

Zmiana kontraktu wymaga spójnej aktualizacji jego właściciela, implementacji, testów i dokumentacji. Nie utrzymuj równoległych „aktualnych” wersji ani numerowanych wariantów.

## Granice danych i bezpieczeństwo

- Nie commituj dokumentów podatnika, KPiR, PIT, faktur, umów, interpretacji, danych osobowych, sekretów, kluczy API ani surowych raportów użytkownika.
- Testy, kasety, logi, Issue i komentarze używają wyłącznie danych syntetycznych lub skutecznie zanonimizowanych.
- Nie kopiuj prywatnych danych do zewnętrznego narzędzia bez zgody i ustalonego zakresu.
- Płatne wywołania LLM wymagają jawnego polecenia, potwierdzenia przewidzianego przez skrypt oraz dodatnich limitów kosztu.
- Nie publikuj Issue, PR, komentarza ani artefaktu bez polecenia użytkownika. Przy nowym przypadku podatkowym dodatkowo uzyskaj zgodę na publikację zanonimizowanego Issue.

## Zasady zmian

1. Ustal branch, dokładny SHA i zakres zadania.
2. Odczytaj kanonicznego właściciela oraz testy istniejącego zachowania.
3. Uruchom najmniejszy test odtwarzający problem.
4. Dodaj minimalną regresję przed poprawką, gdy zmieniasz zachowanie.
5. Wprowadź najmniejszą spójną zmianę bez osłabiania testów i walidacji.
6. Zaktualizuj wszystkich konsumentów zmienionego kontraktu.
7. Wykonaj review własnego diffu, w tym danych, sekretów, kosztów i zachowania fail-closed.
8. Uruchom test celowany i pełną bramkę.
9. Sprawdź CI oraz komentarze reviewerów przed deklaracją gotowości.

Nie zmieniaj wygenerowanych kaset, manifestów, hashy ani fingerprintów ręcznie. Używaj skryptów opisanych w [`docs/testing.md`](docs/testing.md).

## Komendy weryfikacyjne

Konfiguracja środowiska:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-test.txt
```

Przykładowy test celowany dla NEXUS i zwykłego opodatkowania:

```bash
pytest tests/unit/test_nexus_ordinary_tax_and_w_policy.py -q
```

Bramki repozytorium:

```bash
make quality   # format, lint, compile, statyczne bezpieczeństwo i polityka workflow
make test      # quality + unit/coverage + pełny bezpłatny suite + polityka kaset
make verify    # pełna macierz VCR w trybie offline
make full      # test + verify
```

Płatne nagrywanie, zależności sieciowe i integracje zewnętrzne mają osobne preconditions w [`docs/testing.md`](docs/testing.md). Brak sekretu lub zgody oznacza bezpieczne pominięcie, nie obejście zabezpieczenia.

## Kryterium zakończenia

Raport końcowy podaje branch i dokładny SHA, zmienione kontrakty i konsumentów, wykonane komendy z wynikami, niewykonane bramki z powodem oraz ryzyka resztkowe, stan CI i wymagany dalszy review.

Lokalny PASS nie jest dowodem zielonego GitHub Actions, działania płatnej integracji ani niezależnej akceptacji. Nie oznaczaj zmiany jako gotowej, jeżeli wymagana macierz VCR jest częściowa, playback nie przechodzi offline albo istotny konflikt pozostaje nierozstrzygnięty.
