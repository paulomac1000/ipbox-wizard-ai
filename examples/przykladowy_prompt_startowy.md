# Przykładowe prompty startowe

Poniższe prompty są przeznaczone do zwykłej rozmowy z agentem AI. Do rozmowy dodaj repozytorium jako ZIP, potrzebne pliki projektu albo link do GitHuba oraz swoje dokumenty podatkowe.

## Wspólny kontrakt pokrycia

Każdy wariant analizy powinien zakończyć się dokładnie jednym statusem:

- `COVERED_DIRECTLY`;
- `COVERED_PARTIALLY`;
- `NOT_COVERED`.

`COVERED_DIRECTLY` wymaga łącznie: bezpośredniego scenariusza biznesowego, sprawdzenia tego samego istotnego invariantu, kompletnej i aktualnej macierzy VCR wszystkich wymaganych rodzin oraz playbacku przechodzącego bez sekretu i bez sieci. Jeżeli choć jeden warunek nie jest potwierdzony, użyj `COVERED_PARTIALLY` albo `NOT_COVERED` i wyjaśnij brak.

W benchmarku Python buduje autorytatywną kopertę `expected_decision`. Model ma zwrócić gotowe `status`, `stops` i `reviews` bez ponownego liczenia podatku i bez reinterpretacji klasyfikacji.

## Wariant 1 — przygotowanie rozliczenia z dokumentów

```text
Chcę przygotować rozliczenie IP Box za rok [ROK].

Przeczytaj README.md i ipbox_algorytm.md. Samodzielnie przeanalizuj załączone
KPiR, ewidencję czasu, faktury, umowy, interpretację KIS i pozostałe dokumenty.
Do wszystkich krytycznych obliczeń używaj kodu z katalogu python_helper.
Nie licz podatku w głowie i nie zgaduj brakujących danych.

Najpierw pokaż:
1. listę otrzymanych dokumentów;
2. dane odczytane z każdego dokumentu wraz ze stroną, arkuszem albo wierszem;
3. niespójności i brakujące informacje;
4. pytania, na które muszę odpowiedzieć.

Dopiero po potwierdzeniu danych wykonaj rozliczenie. Na końcu pokaż przychody
i koszty IP/NIE, W, MIX, NEXUS, ulgi, podatek, nadpłatę lub dopłatę,
STOP-y, REVIEW-y oraz listę rzeczy do potwierdzenia z księgową.

Podaj dokładnie jeden status: COVERED_DIRECTLY, COVERED_PARTIALLY albo
NOT_COVERED. Wskaż pasujące testy i scenariusze. COVERED_DIRECTLY zadeklaruj
tylko przy bezpośrednim scenariuszu, zgodnym invariancie, kompletnej aktualnej
macierzy VCR wszystkich wymaganych rodzin i playbacku bez sekretu oraz sieci.
Nie zmieniaj kodu.
```

## Wariant 2 — sprawdzenie rozliczenia przygotowanego przez księgową

```text
Moja księgowa przygotowała rozliczenie IP Box za rok [ROK]. Chcę je niezależnie
sprawdzić.

Przeczytaj README.md i ipbox_algorytm.md. Załączam dokumenty źródłowe oraz
formularze PIT. Samodzielnie odczytaj dane, a wszystkie obliczenia wykonaj
kodem z python_helper.

Nie zaczynaj od przepisywania wyniku księgowej. Najpierw odtwórz rozliczenie
ze źródeł, a następnie porównaj oba wyniki pole po polu.

Na końcu wskaż:
- które wartości są zgodne;
- wszystkie różnice i ich dokładne źródło;
- czy problem leży w dokumentach, księgowaniu, PIT czy algorytmie;
- jakie korekty są potrzebne;
- jakie kwestie wymagają potwierdzenia przez księgową albo doradcę;
- dokładnie jeden status COVERED_DIRECTLY, COVERED_PARTIALLY albo NOT_COVERED;
- testy, scenariusze, zgodny invariant, stan macierzy VCR i wynik playbacku.

COVERED_DIRECTLY zadeklaruj wyłącznie po potwierdzeniu wszystkich czterech
warunków dowodowych opisanych na początku pliku. Jeżeli przypadek nie jest
bezpośrednio pokryty, przygotuj minimalny syntetyczny opis do GitHub Issue,
ale nie zmieniaj kodu repozytorium.
```

## Wariant 3 — niekompletne dokumenty albo pierwsze rozliczenie

```text
Rozważam rozliczenie IP Box za rok [ROK], ale nie wiem, czy mam kompletne dane.

Przeczytaj README.md i ipbox_algorytm.md. Przeanalizuj przesłane dokumenty,
nie zakładaj korzystnych odpowiedzi i nie traktuj braków jako zera.

Najpierw oceń:
- czy istnieje kwalifikowane IP i działalność B+R;
- czy umowy i ewidencja są wystarczające;
- jakich dokumentów brakuje;
- które koszty i przychody wymagają wyjaśnienia;
- czy potrzebna jest interpretacja KIS albo dodatkowa dokumentacja.

Następnie wykonaj tylko te obliczenia, które są możliwe na potwierdzonych danych.
Wynik niepełny oznacz jako wstępny i pokaż listę kroków potrzebnych do finalnego
rozliczenia.

Podaj dokładnie COVERED_DIRECTLY, COVERED_PARTIALLY albo NOT_COVERED. Wskaż
pasujące testy, scenariusze i invariant oraz stan VCR i playbacku. Nie używaj
COVERED_DIRECTLY, jeżeli brakuje bezpośredniego scenariusza, zgodnego invariantu,
kompletnej aktualnej macierzy albo playbacku bez sekretu i sieci.
```

## Wariant 4 — lokalna praca w Codex lub Claude Code

```text
Pracuj na tym repozytorium jako narzędziu do analizy mojego rozliczenia IP Box.
Przeczytaj README.md, AGENTS.md i ipbox_algorytm.md.

Moje prywatne dokumenty znajdują się w input/. Nie commituj ich, nie kopiuj
do testów i nie ujawniaj danych osobowych w logach ani raporcie.

Najpierw zinwentaryzuj i samodzielnie odczytaj dokumenty. Przygotuj dane robocze
i uruchom deterministyczne obliczenia w Pythonie. Pokaż źródło każdej ważnej
kwoty i zapytaj o braki. Porównaj wynik z KPiR, ewidencją i PIT.

Nie zmieniaj kodu i nie twórz commitów. Podaj dokładnie COVERED_DIRECTLY,
COVERED_PARTIALLY albo NOT_COVERED oraz wskaż testy, scenariusze, invariant,
kompletność macierzy VCR i wynik playbacku bez sekretu. COVERED_DIRECTLY wymaga
spełnienia wszystkich tych warunków. Gdy znajdziesz możliwy błąd albo brak
pokrycia, opisz minimalny syntetyczny przypadek i przygotuj treść GitHub Issue.
```

## Wariant 5 — przygotowanie zgłoszenia bez zmiany kodu

```text
Mój przypadek nie jest bezpośrednio pokryty przez testy albo ujawnia możliwy błąd.
Nie zmieniaj jeszcze kodu.

Przygotuj zanonimizowany, minimalny przypadek odtwarzający:
- stan faktyczny;
- dane wejściowe;
- rzeczywisty wynik algorytmu;
- wynik oczekiwany;
- uzasadnienie i źródła;
- status COVERED_DIRECTLY, COVERED_PARTIALLY albo NOT_COVERED;
- istniejące testy podobne do tego przypadku;
- brakujący warunek pokrycia: scenariusz, invariant, macierz VCR lub playback.

Usuń dane osobowe, nazwy kontrahentów, numery faktur i prywatne sygnatury.
Jeżeli masz dostęp do GitHuba, zapytaj mnie o zgodę i utwórz Issue przez formularz
new-tax-case.yml. Jeżeli nie masz dostępu, podaj mi gotową treść i bezpośredni link.
```

## Wariant 6 — rozwój algorytmu po znalezieniu błędu

Używaj dopiero po zakończeniu analizy dokumentów i wyraźnym potwierdzeniu, że problem leży w kodzie.

```text
Przejdź w tryb maintenera projektu opisany w AGENTS.md.

Najpierw zredukuj znaleziony problem do minimalnego syntetycznego przypadku,
bez danych podatnika. Dodaj test regresyjny, który obecnie nie przechodzi.
Następnie popraw właściwy moduł, uruchom testy celowane i pełną bramkę jakości.

Jeżeli zmiana dotyczy kontraktu LLM, sprawdź wpływ na expected_decision,
scenariusze i macierz VCR. Nie dopasowuj testu do istniejącego błędnego wyniku.
W raporcie końcowym podaj:
- branch i SHA;
- zmienione pliki;
- wykonane testy i coverage;
- scenariusze pokrywające przypadek;
- stan VCR dla wymaganych rodzin modeli;
- wynik playbacku bez sekretu;
- wszystkie ograniczenia weryfikacji.
```
