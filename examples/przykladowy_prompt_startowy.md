# Przykładowe prompty startowe

Poniższe prompty są przeznaczone do zwykłej rozmowy z agentem AI. Do rozmowy dodaj repozytorium jako ZIP, potrzebne pliki projektu albo link do GitHuba oraz swoje dokumenty podatkowe.

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

Nie zmieniaj kodu repozytorium.
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
- jakie kwestie wymagają potwierdzenia przez księgową albo doradcę.

Nie zmieniaj kodu repozytorium.
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

Nie zmieniaj kodu i nie twórz commitów. Gdy znajdziesz możliwy błąd algorytmu,
opisz go osobno jako minimalny syntetyczny przypadek odtwarzający.
```

## Wariant 5 — rozwój algorytmu po znalezieniu błędu

Używaj dopiero po zakończeniu analizy dokumentów i wyraźnym potwierdzeniu, że problem leży w kodzie.

```text
Przejdź w tryb maintenera projektu opisany w AGENTS.md.

Najpierw zredukuj znaleziony problem do minimalnego syntetycznego przypadku,
bez danych podatnika. Dodaj test regresyjny, który obecnie nie przechodzi.
Następnie popraw właściwy moduł, uruchom testy celowane i pełną bramkę jakości.

Nie dopasowuj testu do istniejącego błędnego wyniku. W raporcie końcowym podaj
branch, SHA, zmienione pliki, wykonane testy i wszystkie ograniczenia weryfikacji.
```