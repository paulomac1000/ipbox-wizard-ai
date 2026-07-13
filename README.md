# 🧮 Algorytm IP Box — Wizard AI dla programistów B2B

> Operacyjna instrukcja w Markdown, którą wklejasz do agenta AI (Claude, ChatGPT, Gemini itp.), aby poprowadził Cię przez rozliczenie PIT z ulgą IP Box — od kwalifikacji, przez obliczenia, aż po gotowe dane do wpisania w formularz.

[![Licencja MIT](https://img.shields.io/badge/licencja-MIT-green)]()
[![Status](https://img.shields.io/badge/status-v1.0-brightgreen)]()
[![Prawo PL](https://img.shields.io/badge/prawo-PIT%2030ca–30cb-orange)]()

---

## ⚠️ Najpierw — zastrzeżenia

- Algorytm **nie stanowi porady prawnej ani podatkowej**. To narzędzie pomocnicze, które systematyzuje przepisy.
- Stan prawny: **kwiecień 2026**. Prawo się zmienia — zweryfikuj aktualność przed wysłaniem PIT.
- Limity kwotowe (IKZE, składki zdrowotnej, ulg) zmieniają się corocznie. Algorytm odsyła Cię do aktualnych źródeł (gov.pl, biznes.gov.pl), nie zapisuje ich na sztywno.
- **Zawsze weryfikuj wyniki z doradcą podatkowym lub księgową.** Algorytm dobrze odwali robotę przygotowawczą, ale decyzja końcowa należy do Ciebie.

---

## Co to jest

[**`ipbox_algorytm.md`**](ipbox_algorytm.md) to ~1000-linijkowa instrukcja dla agenta AI, która prowadzi użytkownika przez 10 faz:

| Faza | Co się dzieje |
|---|---|
| 0 | Kwalifikacja — pytanie o interpretację KIS, analiza umowy i KPiR |
| 1 | Zbieranie danych rocznych i ulg (w tym podinstrukcja dodawania nowych ulg) |
| 2 | Obliczenie współczynnika W dla każdego miesiąca |
| 3 | Klasyfikacja kosztów do koszyków IP / MIX / NIE / WYKLUCZONE |
| 4 | Obliczenia miesięczne (przychody, koszty, różnice kursowe) |
| 5 | Walidacja opisów projektów |
| 6 | Warunki STOP / REVIEW (fail-fast przed obliczeniami) |
| 7 | Rozliczenie roczne — kaskada odliczeń w prawidłowej kolejności |
| 8 | Weryfikacja (6 testów matematycznych) |
| 9 | Mapowanie pól formularzy PIT |
| 10 | Generowanie YAML i propozycja ewidencji XLSX |

---

## 🔌 Obsługiwani providerzy i modele AI

System korzysta z **OpenRouter** jako głównego proxy API, co pozwala na wybór spośród wielu modeli bez zmiany kodu:

| Provider | Zmienna środowiskowa | Przykładowy model |
|---|---|---|
| **OpenRouter** (rekomendowany) | `OPENROUTER_API_KEY` + `LLM_MODEL` | `google/gemini-3.5-flash` |

Domyślny model: `google/gemini-3.5-flash` przez OpenRouter.



---

## Dla kogo

| Profil | Pasuje? |
|---|---|
| Programista B2B (JDG) na podatku liniowym 19% | ✅ idealnie |
| Programista B2B na skali 12/32% | ✅ obsługiwany |
| Programista z 1–3 kontrahentami | ✅ |
| Programista z podwykonawcami (freelancerzy UI/UX, testerzy) | ✅ (NEXUS uwzględnia) |
| Programista z klientami zagranicznymi (USD/EUR) | ✅ (obsługa kursów NBP + różnic kursowych) |
| Programista zatrudniający pracowników + IP Box + ulga B+R | ✅ (blokada double-dipping) |
| Programista na ryczałcie ewidencjonowanym | ❌ IP Box nie łączy się z ryczałtem |
| Spółka z o.o. | ❌ algorytm jest pod JDG/PIT, nie CIT |
| Programista na etacie | ❌ IP Box dotyczy działalności gospodarczej |

---

## 🚀 Jak zacząć — 3 ścieżki

### Ścieżka A: Najszybsza — Claude.ai Project / ChatGPT Project

1. Załóż projekt w Claude.ai (lub Custom GPT w OpenAI, lub Gem w Google Gemini).
2. Wklej zawartość [**`ipbox_algorytm.md`**](ipbox_algorytm.md) jako **system prompt** (instrukcje / knowledge base).
3. Dodaj pliki: KPiR, ewidencję czasu, umowę, interpretację KIS (jeśli masz).
4. Napisz: *"Chcę rozliczyć IP Box za rok 2025. Poprowadź mnie przez algorytm."*
5. Agent przeprowadzi Cię przez wszystkie 10 faz.

> [!TIP]
> Rozliczenie zajmuje zwykle 15–30 wiadomości. Darmowe wersje modeli (np. Claude Free) mogą mieć zbyt małe limity, by ukończyć sesję za jednym razem. Rekomendujemy wersje płatne (Pro/Advanced).

**Rekomendowane modele** (testowane, stan 04/2026):

| Model | Uruchamianie kodu | Rekomendacja |
|---|---|---|
| Claude Opus 4.7 (Claude.ai Pro) | ✅ | ⭐⭐⭐ najlepszy do długich sesji wizard, Projects z plikami |
| GPT-5.4 (ChatGPT Plus) | ✅ | ⭐⭐⭐ Custom GPT + Advanced Data Analysis, świetna arytmetyka |
| Gemini 3.1 Pro (Google AI Studio / Google AI Pro) | ✅ | ⭐⭐ Gems, dobra obsługa plików |
| Claude Sonnet 4.6 / GPT-5.3 (darmowe) | ⚠️ ograniczone | ⭐ zadziała, ale pilnuj arytmetyki |
| Claude Haiku / GPT-5.4 mini (fallback) / Gemini 3.1 Flash | ❌ | ⭐ może zadziałać, ale nie polecam |
| Lokalne LLM (Llama 4, Qwen 3.6, Mistral Large) | ❌ zwykle | ⭐ tylko jeśli wymuszasz Python zewnętrznie |

### Ścieżka B: Z uruchamianiem kodu (rekomendowana dla precyzji)

Zamiast polegać na "matematyce w głowie" LLM, wymuszasz wykonywanie obliczeń w Pythonie:

1. Użyj Claude Opus 4.7 z Code Execution (dostępne w Claude.ai) albo Custom GPT z Advanced Data Analysis / Code Interpreter.
2. Załaduj dodatkowo plik [**`python_helper/ipbox_calculator.py`**](python_helper/ipbox_calculator.py) — zawiera gotowe funkcje do obliczeń W, NEXUS, kaskady podatkowej i weryfikacji.
3. W system prompcie dodaj linijkę: *"Przed każdym obliczeniem uruchom odpowiednią funkcję z `ipbox_calculator.py` — nie licz w głowie."*
4. Dalej jak w ścieżce A.

Zaletą: zero halucynacji arytmetycznych, powtarzalne wyniki, zobaczysz dokładne podstawienie wartości.

### Ścieżka C: Claude Skill (dla mocno zaawansowanych)

Jeśli korzystasz z Claude (Anthropic) i chcesz żeby Claude miał ten algorytm zawsze pod ręką:

1. Utwórz folder `ipbox-skill/` z plikiem `SKILL.md` (treść: zawartość `ipbox_algorytm.md` + krótkie `description` na górze wyjaśniające kiedy skill uruchamiać).
2. Dołącz `ipbox_calculator.py` jako resource skilla.
3. Upload jako custom skill w Claude (Settings → Skills — zależnie od wersji produktu).

Wtedy Claude automatycznie uruchomi skill kiedy wspomnisz o rozliczaniu IP Box.

---

## Czy fallback "LLM-only" (bez Pythona) jest ok?

**Tak, zadziała — ale z ostrożnością.** Algorytm został zaprojektowany tak, żeby działał w obu trybach:

- **Z uruchamianiem kodu (Code Execution / Advanced Data Analysis):** pełna dokładność matematyczna, tabele Pandas, testy jako assertions.
- **Bez uruchamiania kodu (tylko tekst):** agent wymuszony jest pokazywać formułę + podstawienie + wynik krok po kroku. Sumy 12 miesięcy robimy iteracyjnie z sumą częściową po każdym miesiącu.

Kiedy rekomenduję uruchamianie kodu, a kiedy tekst wystarczy:

| Sytuacja | Rekomendacja |
|---|---|
| 1 kontrahent, faktury PLN, proste koszty, ZUS w KPiR | tekst wystarczy |
| Faktury walutowe (kursy NBP) | uruchamianie kodu (API NBP) |
| Wieloprojektowość, wiele klientów | uruchamianie kodu (mniej błędów) |
| Ulga B+R + IP Box jednocześnie | uruchamianie kodu (zawiła kaskada) |
| Mieszane zaliczki (część miesięczne, część uproszczone) | uruchamianie kodu |
| Wysoki dochód, wysokie stawki | uruchamianie kodu (każdy błąd bolesny) |

---

## 📁 Struktura repozytorium

```
ipbox-wizard-ai/
├── README.md                          ← jesteś tu
├── ipbox_algorytm.md                  ← GŁÓWNY PLIK — wklej do agenta AI
├── python_helper/
│   └── ipbox_calculator.py            ← Kalkulator Pythonowy (Code Execution / Advanced Data Analysis)
├── scripts/                           ← Skrypty (vcr, pre-commit)
├── docs/                              ← Dokumentacja techniczna i testowa
│   └── testing.md                     ← Szczegółowy opis systemu testów
├── tests/                             
│   ├── unit/                          ← testy matematyki (Python)
│   └── llm/                           ← scenariusze end-to-end (VCR)
└── input/                             ← (GITIGNORE) tu wrzucaj swoje dane
```

---

## 💡 Przykładowy prompt startowy

```
Mam algorytm IP Box w pliku [**`ipbox_algorytm.md`**](ipbox_algorytm.md).
W katalogu `input/` umieściłem swoje dokumenty:
- ewidencję czasu za 2025 (`input/ewidencja.xlsx`)
- KPiR za 2025 (`input/kpir.csv`)
- umowę B2B i interpretację KIS (`input/dokumenty.pdf`)

Chcę rozliczyć PIT-36L z ulgą IP Box za rok 2025.
Dodatkowe ulgi: IKZE (limit), termomodernizacja, ulga internet, 2 dzieci.

Poprowadź mnie przez algorytm — zacznij od Fazy 0. Analizuj pliki z katalogu `input/`.
```

---

## 🔬 Na czym się opiera

### Lekcje z testów i symulacji

Algorytm ewoluował poprzez dziesiątki iteracji testowych, uwzględniając najczęstsze błędy i ryzyka:

- **Kwalifikacja kosztów**: Izolacja kosztów bezpośrednich IP od kosztów ogólnych (MIX).
- **ZUS i Zdrowotna**: Wykluczenie ryzyka podwójnego odliczania (w KPiR vs w PIT).
- **Kaskada ulg**: Prawidłowa kolejność odliczeń (IKZE przed termomodernizacją itp.).
- **Waluty**: Precyzyjna obsługa kursów NBP i przesunięcie różnic kursowych do przychodów nie-IP.
- **Współczynnik W**: Wykorzystanie faktycznego czasu pracy jako dzielnika (brak kary za urlop).
- **Weryfikacja matematyczna**: Wprowadzenie 6 testów kontrolnych (szanty/balance check).

Każda zmiana w algorytmie jest weryfikowana przez system testów LLM. Wykorzystujemy mechanizm **VCR (Virtual Cassette Recorder)**, który nagrywa odpowiedzi modeli AI (przez OpenRouter lub bezpośrednio Gemini) i porównuje je z oczekiwanymi wynikami (NEXUS, podatek, klasyfikacje). Obecnie posiadamy bazę **36 scenariuszy testowych**, co gwarantuje stabilność algorytmu nawet przy zmianach w modelach AI.

### Orzecznictwo

- NSA II FSK 61/25 — podwykonawcy nie wykluczają IP Box (pod warunkiem posiadania praw i roli koncepcyjnej).
- NSA II FSK 1350/22 — potwierdzenie wymogów dokumentacyjnych.
- WSA Poznań I SA/Po 500/21 — kwestionowanie IP Box przy pracy zespołowej bez wydzielenia utworu.

---

## 🤝 Zaproszenie do współpracy — pomóż ulepszyć algorytm

**Twój przypadek jest dla nas złotem.** Algorytm jest tak dobry, jak różnorodność przypadków, na których został przetestowany.

### Jak możesz pomóc

**1. Wrzuć swoje rozliczenie do algorytmu, nawet (zwłaszcza!) jeśli masz je już gotowe od biura rachunkowego.**

Jeśli masz zrobione rozliczenie przez księgową / doradcę podatkowego:

- Uruchom algorytm na tych samych danych.
- Porównaj wyniki — czy nadpłata się zgadza? Czy NEXUS wyszedł taki sam? Czy koszty są podobnie podzielone?
- Jeśli są **różnice** — zgłoś je w [GitHub Issues](../../issues).
- Wklej do issue anonimizowany opis: forma opodatkowania, typ kontrahenta, zakres działalności, co wyszło księgowej vs co wyszło algorytmowi, gdzie konkretnie jest różnica.

**2. Opisz swój nietypowy przypadek**

Specyficzne sytuacje, które pomogą wszystkim:

- Wieloma klientami z różnych krajów (PLN + USD + EUR + GBP)
- Leasing auta z wykupem prywatnym w połowie roku
- Współwłasność małżeńska, małżonek pracuje jako podwykonawca
- Spółka cywilna / spółka jawna z IP Box
- Przerwa w działalności w środku roku (zawieszenie)
- Pierwszy rok IP Box (brak interpretacji, pierwsze rozliczenie)
- Body leasing przez agencję IT z klientem zagranicznym
- Zmiana formy opodatkowania w trakcie roku
- Zmiana stawki / rozszerzenie zakresu prac w umowie

Otwórz issue z tagiem `edge-case` i opisem.

**3. Wrzuć output / log z sesji**

Jeśli algorytm gdzieś się pomylił, zawahał, zadał dziwne pytanie, albo wygenerował niepoprawny YAML:

- Anonimizuj dane (zmień nazwy firm, zaokrąglij kwoty).
- Wklej fragment konwersacji do issue.
- Opisz co poszło nie tak.

**4. Zgłaszaj błędy prawne**

Jeśli znasz orzecznictwo / interpretację KIS, która pokazuje, że algorytm robi coś niezgodnie z prawem — otwórz issue z tagiem `bug-legal` i linkiem do źródła.

**5. Dodawaj ulgi i scenariusze**

Jeśli skorzystałeś z ulgi spoza listy (np. darowizny, ulga na dzieci o nietypowej strukturze) i algorytm wymagał poprawek — opisz to w zgłoszeniu `enhancement`. Dzięki temu baza wiedzy algorytmu będzie rosła.

### Jak otwierać issues

Użyj jednego z tagów:

- 🐛 `bug-calc` — błąd w obliczeniach matematycznych
- ⚖️ `bug-legal` — niezgodność z prawem / orzecznictwem
- 🌍 `edge-case` — nietypowy przypadek biznesowy
- 💡 `enhancement` — propozycja rozszerzenia lub nowej ulgi
- 📋 `compare-with-advisor` — różnica w rozliczeniu vs biuro rachunkowe
- ❓ `question` — pytanie o stosowanie algorytmu
- 🧪 `tests` — błędy w infrastrukturze testowej / VCR

Każdy issue = szansa na ulepszenie algorytmu dla całej społeczności. Dzięki!

---

## 📋 Znane ograniczenia v1.0

1. Nie obsługuje CIT (spółek z o.o.) — tylko JDG na PIT.
2. Nie łączy się z ryczałtem ewidencjonowanym.
3. Podinstrukcja dla rzadkich ulg wymaga wyszukania w sieci — nie wszystko jest w katalogu domyślnym.
4. Dla bardzo skomplikowanych przypadków (podwykonawcy powiązani, spółki cywilne, zmiana formy w trakcie roku) wymaga weryfikacji z doradcą podatkowym.
5. Status UD116 (projekt zmian wymagający zatrudnienia 3 osób dla IP Box) — projekt **nie wszedł w życie 1 stycznia 2026 r.**, rozliczenie za 2025 r. jest bezpieczne na starych zasadach. Prace legislacyjne trwają (brak ogłoszonej daty wejścia w życie) — zmiany mogą objąć kolejny rok. Monitoruj stan legislacyjny, algorytm nie śledzi zmian automatycznie.
6. Numery pól formularzy PIT podawane są opisowo (nie `"poz. 40"` na sztywno), bo numery zmieniają się między latami.

---

## 🙏 Podziękowania

Algorytm powstał dzięki wsparciu społeczności programistów B2B oraz dziesiątkom godzin symulacji i audytów prowadzonych przez agentów AI. **Z góry dziękuję za każdy "issue", "pull request" czy opis przypadku, który pomoże ulepszyć narzędzie dla wszystkich.**

---

## 📄 Licencja

MIT — używaj, modyfikuj i dystrybuuj bez ograniczeń. Forki, adaptacje do innych krajów, integracje z narzędziami księgowymi — wszystko mile widziane.

---

## 🔗 Przydatne zasoby

- [Objaśnienia MF do IP Box](https://www.gov.pl/web/finanse/objasnienia-podatkowe-dot-preferencyjnego-opodatkowania-dochodow-wytwarzanych-przez-prawa-wlasnosci-intelektualnej-ip-box)
- [Eureka — wyszukiwarka interpretacji KIS](https://eureka.mf.gov.pl/)
- [SIP MF — system informacji podatkowej](https://sip.mf.gov.pl/)
- [API NBP — kursy walut](http://api.nbp.pl/)
- [Biznes.gov.pl — ulgi podatkowe](https://www.biznes.gov.pl/)

---

*Narzędzie edukacyjne. Nie zastępuje doradcy podatkowego. Autor i współpracownicy nie ponoszą odpowiedzialności za decyzje podatkowe podjęte na podstawie tego algorytmu.*
