# IP Box Wizard AI

**Asystent do przygotowania i niezależnego sprawdzenia rozliczenia IP Box dla programisty B2B.**

[![Deterministic CI](https://github.com/paulomac1000/ipbox-wizard-ai/actions/workflows/deterministic-ci.yml/badge.svg)](https://github.com/paulomac1000/ipbox-wizard-ai/actions/workflows/deterministic-ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11–3.13-blue.svg)](pyproject.toml)
[![Release](https://img.shields.io/badge/release-0.2-informational.svg)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

IP Box Wizard AI łączy instrukcję dla agenta AI z deterministycznym kodem Python. Użytkownik przekazuje dokumenty w zwykłej rozmowie z Claude, ChatGPT lub Gemini, a agent:

1. odczytuje dokumenty i pokazuje rozpoznane dane;
2. pyta o braki i niejasności;
3. uruchamia kod projektu do obliczeń;
4. porównuje wynik z KPiR, ewidencją IP Box i PIT;
5. wskazuje błędy, ryzyka oraz potrzebne korekty.

> [!IMPORTANT]
> Projekt jest narzędziem pomocniczym. Nie stanowi porady podatkowej i nie zastępuje księgowej, doradcy podatkowego ani interpretacji indywidualnej. Przed wysłaniem zeznania zweryfikuj wynik z profesjonalistą.

## Dlaczego ten projekt istnieje

Rozliczenie IP Box nie sprowadza się do pomnożenia dochodu przez 5%. Trzeba zachować spójność między dokumentami i osobno ustalić między innymi:

- które przychody dotyczą kwalifikowanego prawa;
- jak rozdzielić działalność IP i pozostałą;
- które wydatki są kosztem podatkowym;
- jak alokować koszty wspólne;
- które koszty należą do NEXUS A/B/C/D;
- jak zastosować składki, ulgi, straty i zaokrąglenia;
- czy ewidencja, KPiR i formularze PIT mówią to samo.

Projekt porządkuje ten proces i oddziela rozmowę z AI od krytycznej matematyki. **Model pomaga czytać dokumenty i prowadzić użytkownika, ale wynik oblicza i kontroluje Python.**

## Dla kogo

| Użytkownik | Typowe zastosowanie |
|---|---|
| Programista prowadzący JDG | Przygotowanie danych do pierwszego rozliczenia IP Box |
| Księgowa lub biuro rachunkowe | Niezależna kontrola ewidencji, alokacji i formularzy |
| Doradca lub audytor | Odtworzenie sposobu obliczeń i identyfikacja rozbieżności |
| Osoba z gotowym PIT | Porównanie rozliczenia z dokumentami źródłowymi |
| Maintainer projektu | Dodawanie kolejnych reguł, lat i przypadków regresyjnych |

Nie trzeba być programistą. Najprostsza ścieżka nie wymaga terminala ani ręcznego przygotowania YAML-a.

## Szybki start — zwykła rozmowa z AI

To jest główny sposób użycia projektu.

### 1. Przekaż agentowi projekt

Najwygodniejsza kolejność:

1. **Archiwum ZIP repozytorium** — najlepsze, gdy okno rozmowy przyjmuje archiwa.
2. **Link do publicznego repozytorium** — gdy agent potrafi otworzyć lub sklonować GitHub.
3. **Wybrane pliki** — gdy obowiązuje limit rozmiaru:
   - `README.md`,
   - `ipbox_algorytm.md`,
   - katalog `python_helper/`,
   - `examples/przykladowy_prompt_startowy.md`.

Pełne archiwum zawiera także testy i kasety odpowiedzi modeli. Podczas zwykłego rozliczenia agent powinien skupić się na algorytmie, kodzie Python i dokumentach podatnika.

### 2. Dodaj dokumenty

Prześlij materiały, które posiadasz. Najczęściej są to:

- KPiR albo miesięczne i roczne zestawienia przychodów i kosztów;
- ewidencja czasu pracy lub dotychczasowa ewidencja IP Box;
- faktury albo zestawienie faktur;
- umowy B2B i aneksy dotyczące praw autorskich;
- interpretacja indywidualna KIS;
- rozliczenie przygotowane przez księgową;
- PIT-36L/PIT-36, PIT/IP, PIT/B, PIT/O i UPO;
- potwierdzenia ZUS, składki zdrowotnej, IKZE, termomodernizacji, strat i zaliczek.

Nie publikuj prywatnych dokumentów w repozytorium. Przekazuj je wyłącznie w prywatnej rozmowie albo trzymaj lokalnie w ignorowanym katalogu `input/`.

### 3. Wklej prompt startowy

```text
Chcę przygotować albo sprawdzić rozliczenie IP Box za rok [ROK].

Przeczytaj README.md i ipbox_algorytm.md. Przeanalizuj załączone dokumenty,
a do wszystkich krytycznych obliczeń używaj kodu z katalogu python_helper.
Nie licz podatku w głowie i nie zgaduj brakujących danych.

Najpierw:
1. zrób listę otrzymanych dokumentów;
2. wypisz dane odczytane z każdego dokumentu wraz ze stroną, arkuszem lub wierszem;
3. wskaż braki i zadaj pytania;
4. pokaż mi dane wejściowe do potwierdzenia;
5. dopiero potem wykonaj obliczenia.

Na końcu pokaż:
- przychody i koszty IP oraz NIE-IP;
- sposób obliczenia W i alokacji kosztów wspólnych;
- koszty wykluczone z KUP;
- NEXUS i dowody jego składników;
- podatek, ulgi, nadpłatę albo dopłatę;
- porównanie z KPiR, ewidencją i PIT;
- błędy, STOP-y, REVIEW i potrzebne korekty;
- listę rzeczy do potwierdzenia z księgową;
- informację, czy mój przypadek ma bezpośredni test regresyjny w repozytorium.

Nie zmieniaj kodu, chyba że wyraźnie o to poproszę.
```

Więcej wariantów znajduje się w [`examples/przykladowy_prompt_startowy.md`](examples/przykladowy_prompt_startowy.md).

## Jak wygląda dobra sesja

Agent powinien pracować w tej kolejności:

```text
inwentaryzacja dokumentów
        ↓
odczyt PDF/XLSX/CSV
        ↓
tabela danych wraz ze źródłami
        ↓
pytania i potwierdzenie użytkownika
        ↓
obliczenia w Pythonie
        ↓
uzgodnienie z KPiR, ewidencją i PIT
        ↓
raport, różnice, korekty i zakres testów
```

Użytkownik nie powinien ręcznie przepisywać dokumentów do YAML-a. Znormalizowane dane są wewnętrznym kontraktem silnika i mogą zostać przygotowane przez agenta. Przed finalnym wynikiem agent musi jednak pokazać, co odczytał z dokumentów — poprawny kalkulator nie naprawi błędnej ekstrakcji.

## Co otrzymasz

Dla kompletnych danych projekt potrafi przygotować lub sprawdzić:

- podział przychodów na IP i NIE-IP;
- miesięczny współczynnik czasu `W` z jawną metodą;
- klasyfikację kosztów jako IP, NIE, MIX albo WYKLUCZONE;
- alokację kosztów wspólnych z zachowaniem każdego grosza;
- koszyki NEXUS A/B/C/D oraz współczynnik NEXUS;
- dochód objęty stawką 5% i część opodatkowaną zwykłą stawką;
- kaskadę podatku i ulg dla lat 2019–2026;
- kontrolę podwójnego odliczenia ZUS i składki zdrowotnej;
- uzgodnienie KPiR, ewidencji i formularzy PIT;
- podgląd skutków korekty;
- listę brakujących dokumentów, dowodów i pytań do księgowej.

Wynik nie jest wyłącznie końcową liczbą. Raport ma pokazać, **skąd pochodzi każda ważna kwota i dlaczego została zaklasyfikowana w określony sposób**.

## Drugi sposób — Codex, Claude Code lub inny agent programistyczny

Ta ścieżka jest wygodna, gdy agent ma terminal, dostęp do całego repozytorium i może sam uruchamiać Python.

1. Otwórz albo sklonuj repozytorium w wybranym narzędziu.
2. Umieść prywatne dokumenty w katalogu `input/`.
3. Upewnij się, że `input/` pozostaje ignorowany przez Git.
4. Poproś agenta o przeczytanie `README.md`, `AGENTS.md` i `ipbox_algorytm.md`.
5. Napisz wyraźnie, czy chcesz tylko sprawdzić rozliczenie, czy także rozwijać kod.

Gotowy prompt:

```text
Pracuj na tym repozytorium jako narzędziu do analizy mojego rozliczenia IP Box.
Przeczytaj README.md, AGENTS.md i ipbox_algorytm.md.

Dokumenty prywatne znajdują się w input/. Nie commituj ich, nie kopiuj do testów
i nie ujawniaj danych osobowych w logach ani raportach.

Najpierw zinwentaryzuj i odczytaj dokumenty. Potem pokaż wyekstrahowane dane,
zapytaj o braki i uruchom deterministyczne obliczenia w Pythonie. Porównaj wynik
z KPiR, ewidencją i PIT. Nie zmieniaj kodu ani nie twórz commitów.

Na końcu wskaż, które istniejące testy bezpośrednio pokrywają mój przypadek.
Jeżeli przypadek nie jest pokryty albo ujawnia możliwy błąd algorytmu, przygotuj
zanonimizowany minimalny przykład oraz propozycję zgłoszenia GitHub Issue.
```

Zasady pracy agentów programistycznych opisuje [`AGENTS.md`](AGENTS.md).

## Uruchomienie lokalne

Zwykły użytkownik i księgowa mogą korzystać z projektu przez rozmowę z AI bez instalowania czegokolwiek. Poniższa instrukcja jest przydatna dla osób, które chcą odtworzyć testy lokalnie albo pracować z agentem terminalowym.

### Wymagania

- Python 3.11, 3.12 albo 3.13;
- Git lub pobrane archiwum ZIP;
- terminal: PowerShell, Terminal albo powłoka Linux.

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-test.txt
python -m pytest tests/unit -q
```

### macOS / Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-test.txt
python -m pytest tests/unit -q
```

Repozytorium nie ma jeszcze samodzielnej aplikacji okienkowej ani uniwersalnego importera każdego PDF/XLSX. W lokalnym użyciu rolę operatora pełni Codex, Claude Code lub inny agent z dostępem do plików i Pythona.

## Jak działa silnik

Projekt rozdziela odpowiedzialności:

```text
Dokumenty użytkownika
        ↓
Agent: odczyt, pytania, źródła i wyjaśnienia
        ↓
Znormalizowane dane robocze
        ↓
Python: W, przychód, koszty, MIX, NEXUS, ulgi i podatek
        ↓
Kontrole spójności oraz STOP / REVIEW
        ↓
Raport dla użytkownika i księgowej
```

Najważniejsze zasady:

- przychód IP/NIE, `W`, alokacja MIX i NEXUS są odrębnymi decyzjami;
- `W` nie jest automatycznie kluczem wszystkich kosztów wspólnych;
- koszt prywatny lub `KUP: NIE` nie trafia ani do IP, ani do NIE-IP;
- koszt obniżający dochód IP nie musi należeć do NEXUS A/B/C/D;
- NEXUS wynosi `min(1, ((A+B) × 1,3)/(A+B+C+D))`;
- część dochodu IP poza NEXUS podlega zwykłemu opodatkowaniu;
- brak dokumentu, dowodu lub znaczenia pola prowadzi do pytania, STOP-u albo REVIEW;
- wszystkie ważne kwoty muszą być odtwarzalne ze źródeł.

Szczegółowy kontrakt znajduje się w [`ipbox_algorytm.md`](ipbox_algorytm.md).

## Skąd wiadomo, że algorytm działa

Projekt nie opiera zaufania na pojedynczej odpowiedzi modelu ani na jednym przykładowym rozliczeniu. Wydanie 0.2 zostało sprawdzone kilkoma niezależnymi warstwami.

### Deterministyczne testy Pythona

- **391 testów jednostkowych** obejmujących matematykę, reguły roczne, walidację, zaokrąglenia i przypadki brzegowe;
- ponad **90% pokrycia linii** kodu `python_helper`;
- CI na Pythonie **3.11, 3.12 i 3.13**;
- testy regresyjne zbudowane z abstrakcyjnych, zanonimizowanych przypadków odpowiadających realnym problemom rozliczeniowym.

### Scenariusze biznesowe

Repozytorium zawiera **46 scenariuszy**, między innymi:

- podatek liniowy i skala;
- jedna lub wiele umów;
- waluty i różnice kursowe;
- składki i ryzyko podwójnego odliczenia;
- koszty prywatne w KPiR;
- różne metody alokacji kosztów;
- NEXUS z podmiotami powiązanymi i niepowiązanymi;
- ulgi, straty, korekty i historyczne lata podatkowe;
- niespójność między ewidencją a zeznaniem.

Scenariusz jest twardą granicą jakości: po dodaniu poprawnego testu algorytm nie może zostać uznany za gotowy, jeżeli ten przypadek przestaje działać.

### VCR i test przenośności między rodzinami AI

Każdy z 46 scenariuszy został zweryfikowany na siedmiu niezależnych rodzinach modeli:

- Google Gemini,
- Anthropic Claude,
- DeepSeek,
- MiniMax,
- Moonshot Kimi,
- Qwen,
- Mistral.

Łącznie repozytorium utrzymuje **322 zweryfikowane kasety VCR**. Testy celowo używają ekonomicznych, mniej uprzywilejowanych modeli każdej rodziny. Sprawdzają, czy kontrakt jest na tyle jednoznaczny, że różne architektury potrafią zwrócić ten sam ograniczony wynik bez zmiany matematyki ustalonej przez Python.

To jest dowód przenośności protokołu i przewidywalności integracji, a nie obietnica, że każdy model zawsze poprawnie odczyta każdy dokument. Mocniejszy model ma zwykle większy margines na analizę plików i kontekstu, ale nadal musi korzystać z deterministycznego silnika i tych samych kontroli.

VCR pozwala odtwarzać zaakceptowane odpowiedzi offline i wykrywać zmianę zachowania modelu, promptu, schemy albo algorytmu. Szczegóły znajdują się w [`docs/testing.md`](docs/testing.md) i [`docs/model-diversity-benchmark.md`](docs/model-diversity-benchmark.md).

## Czy mój przypadek jest przetestowany

Na końcu analizy agent powinien podać jeden z dwóch komunikatów:

1. **Pokryty bezpośrednio** — wskazać nazwy testów lub scenariuszy odpowiadających Twojej sytuacji.
2. **Niepokryty bezpośrednio** — wyjaśnić, które elementy są nowe i czy wynik wymaga dodatkowej weryfikacji.

Nowy, poprawnie opisany przypadek pomaga utrzymywać jakość projektu w czasie. Należy go odtworzyć na minimalnych danych syntetycznych i dodać jako test regresyjny.

[**Zgłoś nowy lub nieobsłużony przypadek przez gotowy formularz GitHub Issue**](https://github.com/paulomac1000/ipbox-wizard-ai/issues/new?template=new-tax-case.yml)

Jeżeli agent ma dostęp do GitHuba, może — po Twojej zgodzie — utworzyć zgłoszenie samodzielnie. Jeżeli nie ma dostępu, powinien przygotować opis i podać powyższy link. Zgłoszenie nie może zawierać danych osobowych, nazw kontrahentów, numerów dokumentów ani prywatnych plików.

## Ograniczenia

- Projekt wspiera przygotowanie i kontrolę danych, nie składa formularza do urzędu.
- Reguły są przypisane do lat 2019–2026; kolejny rok wymaga aktualizacji źródeł i testów.
- Odczyt surowych dokumentów wykonuje agent, dlatego istotne wartości trzeba potwierdzić przed obliczeniem.
- Interpretacja indywidualna chroni wyłącznie w zakresie zgodnego stanu faktycznego; algorytm nie zastępuje oceny prawnej.
- Nietypowy przypadek bez bezpośredniego testu wymaga ostrożności i może ujawnić potrzebę rozwoju algorytmu.

## Mapa repozytorium

| Ścieżka | Rola |
|---|---|
| [`README.md`](README.md) | pierwszy kontakt i sposób użycia |
| [`ipbox_algorytm.md`](ipbox_algorytm.md) | kontrakt domenowy i kolejność decyzji |
| [`python_helper/`](python_helper/) | deterministyczne obliczenia i walidacja |
| [`examples/przykladowy_prompt_startowy.md`](examples/przykladowy_prompt_startowy.md) | gotowe prompty do rozmowy |
| [`AGENTS.md`](AGENTS.md) | instrukcje dla agentów analizujących i rozwijających projekt |
| [`tests/unit/`](tests/unit/) | testy matematyki, reguł i regresji |
| [`tests/llm/scenarios/`](tests/llm/scenarios/) | abstrakcyjne scenariusze biznesowe |
| [`tests/llm/vcr/`](tests/llm/vcr/) | zweryfikowane odpowiedzi rodzin modeli i playback offline |
| [`docs/testing.md`](docs/testing.md) | procedura testów i wydania |
| [`CHANGELOG.md`](CHANGELOG.md) | najważniejsze zmiany między wydaniami |

## Rozwój projektu

Zmiany w regułach lub matematyce powinny zaczynać się od minimalnego testu odtwarzającego problem. Dopiero potem należy zmienić implementację, scenariusze i dokumentację.

Pełna bramka maintenera:

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
```

Standardowy CI nie wykonuje płatnych zapytań do modeli. Procedurę zmian, VCR i nagrywania opisują [`AGENTS.md`](AGENTS.md) oraz [`docs/testing.md`](docs/testing.md).

## Prywatność

- nie commituj KPiR, PIT-ów, faktur, umów, interpretacji ani danych podatnika;
- przechowuj lokalne dokumenty w ignorowanym katalogu `input/`;
- realny błąd odtwarzaj syntetycznym przypadkiem;
- usuń dane osobowe i tajemnice kontrahentów przed publikacją raportu lub Issue;
- nie umieszczaj sekretów API w zgłoszeniach, logach ani kasetach.

## Licencja

Projekt jest dostępny na licencji [MIT](LICENSE).
