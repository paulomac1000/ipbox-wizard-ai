# Przykładowy prompt startowy

Poniżej kilka gotowych promptów, którymi możesz rozpocząć sesję z agentem AI.

---

## Wariant 1 — proste rozliczenie z dokumentami

```
W załączniku / knowledge base mam algorytm IP Box (ipbox_algorytm.md)
oraz opcjonalnie helper Python (ipbox_calculator.py).

Przesyłam pliki z rozliczenia za 2025:
- kpir_2025.xlsx
- ewidencja_czasu_2025.xlsx
- umowa_b2b.pdf
- interpretacja_KIS.pdf (sygnatura: 0115-KDIT3.4011.XXX.2024.2.MK)

Cel: rozliczenie PIT-36L z ulgą IP Box za rok 2025.

Dodatkowe ulgi, z których chcę skorzystać:
- IKZE: wpłacone 9 388,80 zł (limit 2024)
- Termomodernizacja: pozostało 23 481,53 zł z puli
- Ulga internet: tak
- Dwoje dzieci (urodzeni 2015 i 2019)

ZUS społeczne: ~15 000 zł (księgowa wrzuca jako koszt w KPiR — potwierdź w KPiR)
Składka zdrowotna: w KPiR jako koszt (liniowy, w limicie)

Zaliczki: miesięczne, łącznie 36 000 zł
Dochody dodatkowe (UoP/zlecenie): brak

Poprowadź mnie przez algorytm od Fazy 0. Używaj Code Interpreter
(jeśli masz) do wszystkich obliczeń. Podsumowuj stan co 3 fazy.
```

---

## Wariant 2 — bez interpretacji KIS (pierwsze rozliczenie)

```
Jestem programistą B2B, rozważam pierwsze rozliczenie z IP Box za 2025.
Nie mam jeszcze interpretacji KIS.

Załączam:
- umowę B2B (jeden klient, software house)
- KPiR za 2025 (CSV z systemu księgowego)
- prowadzę ewidencję czasu (XLSX)

Forma: liniowy 19%
ZUS: w KPiR jako koszt

Chcę wiedzieć:
1. Czy w ogóle kwalifikuję się do IP Box?
2. Jeśli tak — ile zaoszczędzę?
3. Co muszę poprawić zanim złożę PIT?
4. Czy warto złożyć interpretację i o co w niej poprosić?

Poprowadź mnie przez algorytm z ipbox_algorytm.md.
```

---

## Wariant 3 — weryfikacja rozliczenia od biura rachunkowego

```
Moja księgowa zrobiła już rozliczenie IP Box za 2025.
Chcę żebyś ROBIĆ RÓWNOLEGLE to samo rozliczenie zgodnie z algorytmem 
ipbox_algorytm.md i porównał wyniki na końcu.

Dane od księgowej (wyniki, które chcę zweryfikować):
- Przychód IP: 180 000 zł
- Koszty IP: 12 500 zł
- Dochód IP: 167 500 zł
- NEXUS: 1.0
- Podstawa IP: 167 500 zł
- Podatek IP (5%): 8 375 zł
- Dochód NIE: 35 000 zł
- Po kaskadzie dochód NIE = 0 (ZUS + IKZE + termo)
- Podatek NIE: 0 zł
- Podatek łączny: 8 375 zł
- Nadpłata: 27 625 zł (zaliczki 36 000)

Załączam źródłowe dane (KPiR, ewidencja, umowa, interpretacja).

Poprowadź mnie przez algorytm i na końcu wskaż:
1. Czy Twoje wyniki zgadzają się z księgową?
2. Jeśli są różnice — gdzie dokładnie i dlaczego?
3. Czy któraś strona robi coś źle (Ty czy księgowa)?
4. Czy są obszary gdzie warto pójść konserwatywniej / bardziej optymalnie?

Jeśli znajdziesz istotne różnice — mogę je zgłosić jako issue do repozytorium.
```

---

## Wariant 4 — przypadek edge-case (wiele walut + podwykonawca)

```
Nietypowe rozliczenie 2025:

- 3 klientów: PL (PLN), US (USD), DE (EUR)
- Zatrudniam freelancera UI na B2B (~30 000 zł rocznie)
- Klientka US płaci z opóźnieniem 2-3 tygodnie (różnice kursowe)
- W lipcu miałem 4 tygodnie urlopu (nie fakturowałem)
- Zmieniłem klienta DE z SaaS na przeniesienie praw we wrześniu

Przesyłam dokumenty. Zakładam że: liniowy, ZUS w KPiR, metoda memoriałowa,
interpretacja KIS mam (sygnatura w pliku).

Chcę pełne rozliczenie z uwzględnieniem:
- różnic kursowych (zawsze do NIE, nie IP Box)
- NEXUS z B (freelancer = podwykonawca niepowiązany)
- W w miesiącu urlopowym (dzielnik = faktyczny czas pracy, czyli 0 → pomiń miesiąc)
- zmiany modelu z SaaS na przeniesienie (oba kwalifikują się do IP Box)

Po rozliczeniu chciałbym żebyś wygenerował YAML i zaproponował ewidencję XLSX.
To jest dokładnie ten typ przypadku, który chcę potem zgłosić 
jako `edge-case` do repozytorium — więc zapisz gdzie algorytm miał 
trudności albo zadawał dziwne pytania.
```
