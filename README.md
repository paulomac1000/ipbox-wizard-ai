# IP Box Wizard AI

**Wrzuć dokumenty do rozmowy z Claude, ChatGPT albo Gemini i poproś agenta o przygotowanie lub sprawdzenie rozliczenia IP Box.**

Projekt łączy instrukcję dla agenta z deterministycznym kodem Python. Agent odczytuje dokumenty, zadaje pytania i wyjaśnia wynik, a Python wykonuje krytyczne obliczenia i kontrole.

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11–3.13-blue.svg)](pyproject.toml)

> [!IMPORTANT]
> To narzędzie pomocnicze, nie porada podatkowa ani automatyczny generator zeznania. Przed wysłaniem PIT sprawdź wynik z księgową albo doradcą podatkowym.

## Najprostszy sposób: użyj projektu w zwykłej rozmowie

Nie musisz samodzielnie uruchamiać repozytorium ani przygotowywać YAML-a.

### 1. Przekaż agentowi projekt

Możesz użyć jednej z trzech form:

1. **Archiwum ZIP repozytorium** — najpewniejsza opcja, gdy okno rozmowy przyjmuje archiwa.
2. **Wybrane pliki projektu** — co najmniej:
   - `README.md`,
   - `ipbox_algorytm.md`,
   - katalog `python_helper/`,
   - `examples/przykladowy_prompt_startowy.md`.
3. **Link do publicznego repozytorium GitHub** — działa tylko wtedy, gdy używany agent potrafi otworzyć albo sklonować repozytorium. Jeżeli nie potrafi, prześlij ZIP.

Pełne archiwum zawiera także testy i kasety modeli. Przy zwykłym rozliczeniu agent powinien skupić się na `ipbox_algorytm.md`, `python_helper/` i Twoich dokumentach. Katalog `tests/llm/vcr/` jest potrzebny głównie przy rozwijaniu projektu.

### 2. Dodaj dokumenty podatkowe

Prześlij tyle materiałów, ile masz. Najczęściej przydadzą się:

- KPiR lub roczne i miesięczne zestawienia przychodów i kosztów;
- ewidencja czasu pracy albo dotychczasowa ewidencja IP Box;
- faktury lub zestawienie faktur;
- umowy B2B i aneksy dotyczące praw autorskich;
- interpretacja indywidualna KIS, jeżeli ją masz;
- rozliczenie przygotowane przez księgową, jeśli chcesz je sprawdzić;
- PIT-36L/PIT-36, PIT/IP, PIT/B, PIT/O i UPO;
- informacje o ZUS, składce zdrowotnej, IKZE, termomodernizacji, stratach i zaliczkach.

Nie publikuj tych dokumentów w repozytorium. Przekazuj je wyłącznie w prywatnej rozmowie albo trzymaj lokalnie w ignorowanym katalogu `input/`.

### 3. Wklej ten prompt

```text
Chcę przygotować albo sprawdzić rozliczenie IP Box za rok [ROK].

Przeczytaj README.md i ipbox_algorytm.md. Przeanalizuj załączone dokumenty,
a do wszystkich krytycznych obliczeń używaj kodu z katalogu python_helper.
Nie licz podatku w głowie i nie zgaduj brakujących danych.

Najpierw:
1. zrób listę otrzymanych dokumentów;
2. wypisz dane, które z nich odczytałeś, wraz ze źródłem, stroną lub arkuszem;
3. wskaż braki i zadaj mi pytania;
4. dopiero po potwierdzeniu danych wykonaj obliczenia.

Na końcu pokaż:
- przychody i koszty IP oraz NIE-IP;
- sposób obliczenia W i alokacji kosztów MIX;
- koszty wykluczone z KUP;
- NEXUS i dowody jego składników;
- podatek, ulgi, nadpłatę albo dopłatę;
- porównanie z KPiR i złożonym PIT;
- błędy, STOP-y, obszary REVIEW i potrzebne korekty;
- listę rzeczy do potwierdzenia z księgową.

Nie zmieniaj kodu repozytorium, chyba że wyraźnie o to poproszę.
```

Więcej gotowych wariantów znajduje się w [`examples/przykladowy_prompt_startowy.md`](examples/przykladowy_prompt_startowy.md).

## Jak powinna wyglądać sesja

Agent powinien przejść przez proces w tej kolejności:

1. **Inwentaryzacja dokumentów** — co otrzymał i za jaki okres.
2. **Samodzielne odczytanie danych** — PDF, XLSX, CSV i inne załączniki.
3. **Tabela danych źródłowych** — kwoty, daty, klasyfikacje i wskazanie miejsca w dokumencie.
4. **Pytania o braki** — brak danych nie jest zerem ani korzystnym założeniem.
5. **Obliczenia w Pythonie** — przychód, `W`, koszty, MIX, NEXUS, ulgi i podatek.
6. **Uzgodnienie** — porównanie z KPiR, ewidencją IP Box i formularzami PIT.
7. **Raport końcowy** — wynik, ślad obliczeń, wykryte problemy i lista decyzji do potwierdzenia.

Agent nie powinien wymagać od użytkownika ręcznego tworzenia pliku YAML. Znormalizowane dane są wewnętrznym kontraktem silnika i mogą zostać przygotowane przez agenta na podstawie dokumentów.

## Co otrzymasz

Dla kompletnych danych projekt potrafi przygotować lub sprawdzić:

- podział przychodów na IP i NIE-IP;
- miesięczny współczynnik `W` z jawną metodą;
- klasyfikację kosztów jako IP, NIE, MIX albo WYKLUCZONE;
- alokację kosztów pośrednich z zachowaniem każdego grosza;
- koszyki NEXUS A/B/C/D i współczynnik NEXUS;
- dochód kwalifikowany i część opodatkowaną zwykłą stawką;
- kaskadę podatku i ulg właściwą dla lat 2019–2026;
- kontrolę ZUS i składki zdrowotnej pod kątem podwójnego odliczenia;
- audyt KPiR, ewidencji i zeznania;
- podgląd skutków korekty;
- listę brakujących dowodów i pytań do księgowej.

## Co jest automatyczne, a co nie

### Agent rozmowy

Agent może odczytać przesłane PDF-y, arkusze i inne dokumenty, przygotować z nich dane wejściowe oraz poprowadzić użytkownika przez brakujące informacje.

### Kod projektu

Kod Python odpowiada za matematykę, reguły roczne, walidację i kontrole. Model językowy nie powinien samodzielnie ustalać krytycznych liczb ani korzystnie interpretować braków.

### Ważna granica

Repozytorium nie zawiera jeszcze samodzielnego, uniwersalnego programu, który bez udziału agenta importuje każdy możliwy PDF lub XLSX. Dlatego przed finalnym wynikiem agent musi pokazać, co odczytał z dokumentów, a użytkownik powinien potwierdzić istotne kwoty i klasyfikacje.

## Drugi punkt wejścia: Codex, Claude Code lub inny agent programistyczny

Ta ścieżka jest przydatna, gdy agent ma dostęp do terminala i całego repozytorium.

### Szybki start

1. Otwórz albo sklonuj repozytorium w narzędziu.
2. Skopiuj prywatne dokumenty do lokalnego katalogu `input/` i upewnij się, że pozostaje ignorowany przez Git.
3. Poproś agenta o przeczytanie `README.md`, `AGENTS.md` i `ipbox_algorytm.md`.
4. Zaznacz, czy chcesz tylko rozliczenie, czy także zmianę kodu.
5. Przy samym rozliczeniu agent nie powinien tworzyć commitów ani modyfikować silnika.

Gotowy prompt:

```text
Pracuj na tym repozytorium jako narzędziu do analizy mojego rozliczenia IP Box.
Przeczytaj README.md, AGENTS.md i ipbox_algorytm.md.

Dokumenty prywatne znajdują się w katalogu input/. Nie commituj ich, nie kopiuj
do testów i nie ujawniaj danych osobowych w logach ani raporcie.

Najpierw zinwentaryzuj i samodzielnie odczytaj dokumenty. Następnie przygotuj
znormalizowane dane robocze i uruchom deterministyczne obliczenia w Pythonie.
Pokaż źródło każdej ważnej kwoty i zapytaj o braki. Porównaj wynik z KPiR,
ewidencją oraz PIT.

Nie zmieniaj kodu i nie twórz commitów. Gdy odkryjesz możliwy błąd algorytmu,
opisz go osobno wraz z minimalnym przypadkiem odtwarzającym.
```

Jeżeli zadaniem jest rozwój kodu, agent powinien przejść w tryb maintenera opisany w [`AGENTS.md`](AGENTS.md): najpierw test regresyjny, następnie poprawka, pełna bramka jakości i dopiero potem commit.

## Najważniejsze pliki

| Ścieżka | Do czego służy |
|---|---|
| [`README.md`](README.md) | pierwszy kontakt i sposób użycia |
| [`ipbox_algorytm.md`](ipbox_algorytm.md) | właściwa kolejność decyzji podatkowych |
| [`python_helper/`](python_helper/) | deterministyczne obliczenia i walidacja |
| [`examples/przykladowy_prompt_startowy.md`](examples/przykladowy_prompt_startowy.md) | gotowe prompty do rozmowy |
| [`AGENTS.md`](AGENTS.md) | instrukcja dla Codex, Claude Code i agentów rozwijających repozytorium |
| [`tests/unit/`](tests/unit/) | testy matematyki i regresji |
| [`tests/llm/scenarios/`](tests/llm/scenarios/) | syntetyczne przypadki biznesowe |
| [`docs/testing.md`](docs/testing.md) | techniczna procedura testów i wydania |

## Najważniejsze zasady obliczeń

- kwalifikacja przychodu, `W`, alokacja kosztów MIX i NEXUS są osobnymi decyzjami;
- `W` nie jest automatycznie kluczem wszystkich kosztów;
- koszt prywatny lub `KUP: NIE` nie trafia ani do IP, ani do NIE-IP;
- koszt obniżający dochód IP nie musi automatycznie należeć do NEXUS A/B/C/D;
- NEXUS wynosi `min(1, ((A+B) × 1,3)/(A+B+C+D))`;
- część dochodu IP poza NEXUS podlega zwykłemu opodatkowaniu, a nie znika;
- brak dokumentu, dowodu albo znaczenia pola prowadzi do pytania, STOP-u lub REVIEW;
- wszystkie ważne kwoty muszą dać się odtworzyć ze źródeł.

Szczegółowy kontrakt znajduje się w [`ipbox_algorytm.md`](ipbox_algorytm.md).

## Dla osób rozwijających projekt

Zwykły użytkownik nie musi wykonywać poniższych poleceń. Są przeznaczone dla maintainerów i agentów programistycznych.

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

Pełna procedura VCR, playbacku i wydania znajduje się w [`docs/testing.md`](docs/testing.md). Zasady pracy z kodem znajdują się w [`AGENTS.md`](AGENTS.md).

## Prywatność

- nie commituj KPiR, PIT-ów, umów, faktur, interpretacji ani danych osobowych;
- nie twórz testów zawierających rzeczywiste kwoty lub identyfikatory podatnika;
- realny błąd odtwarzaj syntetycznym, minimalnym przypadkiem;
- przed udostępnieniem raportu usuń dane osobowe i tajemnice kontrahentów.

## Licencja

Projekt jest dostępny na licencji [MIT](LICENSE).