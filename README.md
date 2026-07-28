# IP Box Wizard AI

> Deterministyczny silnik i instrukcja dla AI do analizy polskiego rozliczenia IP Box na podstawie dokumentów użytkownika.

Projekt pomaga uporządkować dokumenty, wykryć braki i niespójności, policzyć wariant rozliczenia oraz przygotować ścieżkę korekty. Nie opiera wyniku na swobodnej odpowiedzi modelu: obliczenia i reguły przechodzą przez kod, walidację oraz testy regresyjne.

## Dla kogo

Repozytorium jest przeznaczone dla:

- przedsiębiorcy rozliczającego IP Box;
- księgowej lub biura rachunkowego weryfikującego rozliczenie;
- doradcy analizującego dane klienta;
- programisty lub agenta rozwijającego algorytm;
- użytkownika, który chce przekazać pliki do Claude, ChatGPT, Gemini albo lokalnego agenta i otrzymać ustrukturyzowaną analizę.

Nie trzeba znać Pythona, aby użyć projektu do analizy dokumentów w rozmowie z AI. Lokalna instalacja jest potrzebna dopiero wtedy, gdy chcesz uruchamiać testy, rozwijać algorytm albo pracować na dużym zestawie plików.

## Co robi projekt

Typowa sesja obejmuje:

1. rozpoznanie dokumentów i okresu rozliczenia;
2. zbudowanie rejestru źródeł i pytań o brakujące dane;
3. klasyfikację przychodów, kosztów, projektów i praw IP;
4. obliczenia wykonywane przez `python_helper`, a nie „w pamięci” modelu;
5. kontrole STOP i REVIEW;
6. porównanie wariantu pierwotnego z poprawionym;
7. raport z założeniami, wyliczeniami, ryzykami i listą dalszych działań;
8. ocenę, czy przypadek jest bezpośrednio pokryty testami.

Projekt nie zastępuje porady podatkowej ani decyzji użytkownika. Jego celem jest wymuszenie przejrzystej, powtarzalnej i możliwej do zweryfikowania analizy.

## Szybki start — analiza dokumentów w rozmowie z AI

### 1. Przygotuj materiały

Możesz przekazać między innymi:

- KPiR lub eksport z programu księgowego;
- faktury sprzedażowe i kosztowe;
- PIT-36L, PIT/IP albo projekt zeznania;
- ewidencję IP Box;
- zestawienie czasu pracy lub opis metody alokacji;
- umowy, aneksy, opisy projektów i praw autorskich;
- interpretację indywidualną;
- wcześniejsze wyliczenia księgowej;
- plik ZIP zawierający cały zestaw dokumentów;
- link do tego repozytorium, gdy platforma potrafi czytać GitHub.

Przed udostępnieniem danych usuń lub zamaskuj dane osobowe, numery rachunków, adresy i inne informacje, które nie są potrzebne do obliczeń.

### 2. Przekaż repozytorium albo jego kluczowe pliki

Najprościej podać agentowi link:

```text
https://github.com/paulomac1000/ipbox-wizard-ai
```

Gdy agent nie potrafi pobrać repozytorium, dołącz przynajmniej:

- `AGENTS.md`;
- `ipbox_algorytm.md`;
- katalog `python_helper`;
- własne dokumenty lub ZIP.

### 3. Użyj gotowego promptu

```text
Przeanalizuj załączone dokumenty zgodnie z repozytorium
https://github.com/paulomac1000/ipbox-wizard-ai.

Najpierw przeczytaj AGENTS.md i ipbox_algorytm.md. Traktuj je jako instrukcję
postępowania, ale wszystkie obliczenia wykonuj za pomocą kodu z python_helper.

Nie zakładaj brakujących danych. Najpierw zbuduj rejestr dokumentów i wypisz
pytania blokujące. Następnie wykonaj analizę, pokaż użyte założenia, źródła,
formuły i wyniki. Rozdziel błędy blokujące od punktów wymagających weryfikacji.

Na końcu nadaj dokładnie jeden status pokrycia przypadku:
COVERED_DIRECTLY, COVERED_PARTIALLY albo NOT_COVERED.
Jeżeli przypadek nie jest w pełni pokryty lub ujawnia błąd, przygotuj
zanonimizowaną propozycję GitHub Issue, ale nie publikuj jej bez mojej zgody.
```

Rozbudowana wersja znajduje się w [`examples/przykladowy_prompt_startowy.md`](examples/przykladowy_prompt_startowy.md).

## Jakiego wyniku oczekiwać

Dobra odpowiedź agenta powinna zawierać:

- spis przeanalizowanych dokumentów;
- listę braków i pytań;
- opis metody przypisania przychodów i kosztów;
- miesięczne lub projektowe obliczenia W;
- klasyfikację kosztów IP, MIX, NON i EXCLUDED;
- wyliczenie NEXUS z dowodami dla koszyków A, B, C i D;
- kontrole KPiR, składek, zaokrągleń, ulg i formy opodatkowania;
- listę STOP i REVIEW;
- wariant pierwotny oraz wariant po korekcie;
- wynik podatku, zaliczek i nadpłaty albo dopłaty;
- ocenę pokrycia testami;
- propozycję dalszych działań.

Każda ważna liczba powinna być możliwa do odtworzenia: źródło → dane wejściowe → funkcja → wynik.

## Status pokrycia przypadku

Każda analiza kończy się jednym statusem:

| Status | Znaczenie |
|---|---|
| `COVERED_DIRECTLY` | Istniejący scenariusz regresyjny pokrywa ten sam mechanizm i istotne warunki przypadku. |
| `COVERED_PARTIALLY` | Część mechanizmów jest testowana, ale brakuje co najmniej jednego istotnego warunku lub ich połączenia. |
| `NOT_COVERED` | Brakuje reprezentatywnego scenariusza albo przypadek ujawnia potencjalny błąd algorytmu. |

Status opisuje pokrycie przez testy repozytorium, a nie pewność prawną rozliczenia.

## Gdy przypadek nie jest pokryty

Agent powinien przygotować zanonimizowane zgłoszenie GitHub Issue zawierające:

- skrócony opis przypadku;
- oczekiwane zachowanie;
- rzeczywiste zachowanie;
- minimalne dane reprodukcyjne;
- brakujący scenariusz regresyjny;
- informację, czy problem dotyczy algorytmu, importu danych czy dokumentacji.

Formularz znajduje się tutaj:

```text
https://github.com/paulomac1000/ipbox-wizard-ai/issues/new?template=new-tax-case.yml
```

Nie umieszczaj w Issue dokumentów źródłowych ani danych pozwalających zidentyfikować podatnika. Publikacja wymaga wyraźnej zgody użytkownika.

## Uruchomienie lokalne

Lokalne środowisko jest przydatne do uruchamiania testów, przeglądania kodu i rozwijania algorytmu.

### Windows — PowerShell

```powershell
git clone https://github.com/paulomac1000/ipbox-wizard-ai.git
cd ipbox-wizard-ai
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-test.txt
pytest -q
```

Gdy PowerShell blokuje aktywację środowiska:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
```

### macOS i Linux

```bash
git clone https://github.com/paulomac1000/ipbox-wizard-ai.git
cd ipbox-wizard-ai
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-test.txt
pytest -q
```

### Pełna bramka jakości

```bash
ruff format --check .
ruff check .
python -m compileall -q python_helper tests scripts
pytest tests/unit --cov=python_helper --cov-report=term-missing --cov-fail-under=90
pytest -q
bash scripts/verify_all_models.sh
```

Nagrywanie nowych kaset LLM jest płatne i wymaga świadomego uruchomienia, klucza API oraz limitów kosztu. Zwykła praca i CI korzystają z odtwarzania offline.

## Praca z agentem programującym

Dla Codex, Claude Code lub innego agenta lokalnego punktem wejścia jest [`AGENTS.md`](AGENTS.md).

Agent powinien:

1. określić, czy pracuje nad analizą podatkową, czy nad kodem;
2. przeczytać dokumenty wskazane w `AGENTS.md`;
3. odtworzyć błąd albo brak scenariuszem;
4. wprowadzić minimalną zmianę;
5. uruchomić pełną bramkę jakości;
6. nie nagrywać płatnych odpowiedzi bez jawnej zgody i limitu;
7. nie uznawać zmiany za gotową, dopóki pełna macierz offline nie przechodzi.

## Zakres algorytmu

Silnik obejmuje między innymi:

- współczynnik W liczony na podstawie rzeczywistego czasu pracy;
- rozdzielenie kwalifikowanego i niekwalifikowanego przychodu;
- koszty IP, MIX, NON i EXCLUDED;
- miesięczne pule i zaokrąglenia zachowujące sumy groszowe;
- NEXUS z limitem do `1`;
- zwykłe opodatkowanie części dochodu IP nieobjętej preferencją;
- straty i ulgi;
- składki i kontrolę podwójnego odliczenia;
- reguły roczne;
- kody STOP i REVIEW;
- podgląd korekty bez automatycznego księgowania.

Ważne zasady:

- brak dowodu nie może być zastępowany domysłem;
- opis kosztu może prowadzić do REVIEW, ale nie powinien automatycznie przesądzać o wyłączeniu;
- NEXUS wynosi `min(1, ((A+B) × 1.3) / (A+B+C+D))`;
- część dochodu IP poza NEXUS podlega zwykłemu opodatkowaniu;
- brak dokumentu, dowodu lub znaczenia pola prowadzi do pytania, STOP-u albo REVIEW;
- wszystkie ważne kwoty muszą być odtwarzalne ze źródeł.

Szczegółowy kontrakt znajduje się w [`ipbox_algorytm.md`](ipbox_algorytm.md).

## Skąd wiadomo, że algorytm działa

Projekt nie opiera zaufania na pojedynczej odpowiedzi modelu ani na jednym przykładowym rozliczeniu. Jakość jest sprawdzana kilkoma niezależnymi warstwami.

### Deterministyczne testy Pythona

- testy jednostkowe obejmujące matematykę, reguły roczne, walidację, zaokrąglenia i przypadki brzegowe;
- ponad **90% pokrycia linii** kodu `python_helper`;
- CI na Pythonie **3.11, 3.12 i 3.13**;
- testy regresyjne zbudowane z abstrakcyjnych, zanonimizowanych przypadków odpowiadających realnym problemom rozliczeniowym.

Dokładna bieżąca liczba testów jest raportowana przez CI, aby README nie stawał się źródłem ulotnego licznika.

### Scenariusze biznesowe

Repozytorium zawiera **46 scenariuszy**, między innymi podatek liniowy i skalę, waluty, różnice kursowe, składki, koszty prywatne w KPiR, różne metody alokacji, NEXUS, ulgi, straty, korekty i historyczne lata podatkowe.

Scenariusz jest twardą granicą jakości: po dodaniu poprawnego testu algorytm nie może zostać uznany za gotowy, jeżeli ten przypadek przestaje działać.

### VCR i test przenośności między rodzinami AI

Każdy z 46 scenariuszy jest odtwarzany dla ośmiu niezależnych rodzin modeli:

| Rodzina | Model benchmarkowy |
|---|---|
| Google | `google/gemini-3-flash-preview` |
| Anthropic | `anthropic/claude-haiku-4.5` |
| DeepSeek | `deepseek/deepseek-chat-v3.1` |
| MiniMax | `minimax/minimax-m2.5` |
| Moonshot / Kimi | `moonshotai/kimi-k2.5` |
| Qwen | `qwen/qwen3.5-flash-02-23` |
| Mistral | `mistralai/mistral-small-24b-instruct-2501` |
| OpenAI | `openai/gpt-5-mini` |

Daje to **368 nagranych kaset VCR** oraz osiem manifestów. Kasety pozwalają uruchomić pełny benchmark offline, bez wysyłania danych do API i bez ponoszenia kolejnego kosztu.

Macierz nie służy do rankingu modeli. Jej zadaniem jest sprawdzenie, czy instrukcja i kontrakt są wystarczająco jednoznaczne, aby różne rodziny modeli dochodziły do zgodnego, walidowalnego wyniku.

## Granice odpowiedzialności

Projekt:

- nie składa deklaracji podatkowej;
- nie dokonuje automatycznych zapisów w KPiR;
- nie publikuje zgłoszeń bez zgody użytkownika;
- nie powinien pracować na niezanonimizowanych danych w testach i repozytorium;
- nie gwarantuje akceptacji rozliczenia przez organ podatkowy;
- wymaga ludzkiej weryfikacji dokumentów, założeń i wyniku.

## Dokumentacja

| Dokument | Zastosowanie |
|---|---|
| [`AGENTS.md`](AGENTS.md) | Punkt wejścia dla agentów i zasady pracy w repozytorium. |
| [`ipbox_algorytm.md`](ipbox_algorytm.md) | Kanoniczny opis algorytmu i bramek decyzyjnych. |
| [`docs/testing.md`](docs/testing.md) | Testy deterministyczne, VCR, nagrywanie i playback. |
| [`docs/model-diversity-benchmark.md`](docs/model-diversity-benchmark.md) | Cel i kryteria ośmiorodzinnej macierzy modeli. |
| [`docs/openai-model-family.md`](docs/openai-model-family.md) | Profil transportowy i zasady GPT-5 Mini. |
| [`CHANGELOG.md`](CHANGELOG.md) | Najważniejsze zmiany projektu. |

## Licencja

MIT. Szczegóły w [`LICENSE`](LICENSE).
