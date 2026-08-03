---
description: Decyzja o adaptacji ci-cd-architect, afds-doc-writer i agents-md-architect do ipbox-wizard-ai.
doc_id: decision.ai-skills-adoption
type: decision
status: evolving
rigor: operational
owners: [repository-maintainers]
verification: Uruchom make full, python scripts/check_workflow_policy.py oraz przypięte upstreamowe validatory w Deterministic CI; sprawdź GitHub Actions na dokładnym SHA i uzyskaj niezależne review.
upstream: [https://github.com/paulomac1000/ai-skills/tree/5fdd72d8cbd06e7358d4f585f7cd06cbd43d82f2]
downstream: [AGENTS.md, docs/agent-tax-analysis.md, docs/agent-development.md, Makefile, requirements.txt, requirements-test.txt, .github/workflows/deterministic-ci.yml, .github/workflows/llm-benchmark.yml]
review_triggers: [nowa wersja ai-skills, zmiana przypiętej rewizji, zmiana profilu repozytorium, zmiana CI, zmiana AGENTS.md, dodanie publikacji artefaktów]
---

# Adaptacja AI Skills 1.2.0

## Decyzja

Repozytorium adaptuje wymagania trzech skills z `paulomac1000/ai-skills` na dokładnej rewizji `5fdd72d8cbd06e7358d4f585f7cd06cbd43d82f2`:

- `ci-cd-architect` 1.2.0;
- `afds-doc-writer` 1.2.0;
- `agents-md-architect` 1.2.0.

Rewizja jest niezmiennym źródłem tej adaptacji. Przesunięcie brancha upstream nie zmienia automatycznie kontraktu tego repozytorium; aktualizacja wymaga osobnego review, zmiany pinu i ponownej pełnej weryfikacji.

Adaptacja jest selektywna i związana z architekturą tego repozytorium. Nie vendorujemy całego `ai-skills`, nie kopiujemy jego katalogu kontraktów i nie deklarujemy zatwierdzonej pełnej adopcji bez provider-backed evidence oraz niezależnego review dokładnego SHA.

## Kontekst

`ipbox-wizard-ai` jest pojedynczym repozytorium aplikacyjnym o profilu safety-critical. Nie publikuje paczki ani obrazu produkcyjnego. Ma dwie odrębne ścieżki:

1. bezpłatną, deterministyczną bramkę pull requestu;
2. ręcznie potwierdzany i płatny benchmark wielu modeli.

Największe ryzyka to błędna reguła podatkowa, niejawne założenie, wyciek danych podatnika, live request podczas playbacku, niekontrolowany koszt LLM oraz zależność CI od mutowalnego tagu akcji.

## Zastosowane wymagania

### CI/CD

- Wszystkie zewnętrzne GitHub Actions są przypięte do pełnych SHA, z czytelnym komentarzem wersji.
- `actions/checkout` nie utrzymuje poświadczeń i pobiera dokładną ocenianą rewizję.
- Workflow używają konkretnego obrazu runnera zamiast mutowalnego aliasu `*-latest`.
- Pull request CI ma wyłącznie `contents: read`; kod pull requestu nie otrzymuje sekretów ani uprawnień zapisu.
- Każdy job ma timeout, workflow ma concurrency, a artefakty mają jawny retention i zachowanie braku plików.
- Dodano wykonywalną politykę `scripts/check_workflow_policy.py`, uruchamianą przez lokalną i zdalną bramkę.
- Pull request CI wykonuje statyczny skan bezpieczeństwa i audyt podatności zależności runtime.
- Płatne wywołania pozostają poza zwykłym CI i wymagają potwierdzenia oraz limitów kosztu.

### Dokumentacja AFDS

- Nowe procedury mają jednego właściciela, typ dokumentu, status, ownera, weryfikację i review triggers.
- Odpowiedź operacyjna znajduje się przed tłem.
- Wymagania, fakty, ograniczenia i ryzyka są rozdzielone.
- Dokumenty linkują do `README.md`, `ipbox_algorytm.md`, `Makefile` i `docs/testing.md` zamiast kopiować ich pełną treść.
- Zmiana kontraktu wskazuje konsumentów przez `upstream` i `downstream`.
- Oryginalny validator AFDS z przypiętej rewizji jest uruchamiany w CI na dokumentach objętych governance.

### AGENTS.md

- Wybrano layout `single`, profil `safety-critical` i język `pl`.
- Root `AGENTS.md` jest routerem mieszczącym zasady potrzebne w większości zadań.
- Szczegółową analizę danych podatnika i rozwój repozytorium przeniesiono do osobnych procedur ładowanych według zadania.
- Usunięto z trwałej instrukcji ulotne liczniki scenariuszy i kaset.
- Dodano jawne pierwszeństwo, tryb read-only, kanonicznych właścicieli, granice danych, płatnych działań i kryteria ukończenia.
- Komendy jakości kierują do `Makefile`, a nie do kolejnej skopiowanej definicji pipeline.
- Oryginalne `audit_agents_md.py` i `validate_agents_md.py` z przypiętej rewizji są uruchamiane w trybie strict w CI.
- Wymagane przez upstream `PyYAML>=6.0.3,<7` jest spełnione przez przypiętą zależność projektu.

## Adaptacje i reguły nieaplikowalne

- Reguły budowy, smoke-testu i publikacji tego samego artefaktu są obecnie nieaplikowalne, ponieważ repozytorium niczego automatycznie nie publikuje. Należy je ponownie ocenić przed dodaniem paczki, obrazu lub release workflow.
- Macierz Pythona projektu pozostaje 3.11–3.13. Upstreamowe validatory uruchamiają się na wspieranym Pythonie 3.12; macierz kompatybilności samego `ai-skills` 3.12–3.14 nie zastępuje kontraktu runtime projektu.
- Nie dodano nested `AGENTS.md`, ponieważ podkatalogi nie mają odrębnej technologii, ownership ani bezpiecznych komend uzasadniających dziedziczenie.
- Nie dodano YAML frontmatter do `README.md` ani `ipbox_algorytm.md`. Pozostają istniejącymi kanonicznymi właścicielami; AFDS zastosowano do nowych dokumentów operacyjnych i tej decyzji bez przebudowy prezentacji produktu.
- Nie skopiowano validatorów do drzewa projektu. CI pobiera dokładną przypiętą rewizję do izolowanego katalogu tymczasowego, potwierdza jej SHA i dopiero wtedy wykonuje validatory na ocenianym drzewie.

## Znalezione problemy w źródle i poprzedniej adaptacji

### Ruchomy branch nie jest pinem

Pierwsza adaptacja wskazywała wcześniejszy commit brancha. Od tego czasu branch przesunął się o kolejne poprawki validatorów i dodał jawny kontrakt `PyYAML>=6.0.3,<7`. Traktowanie nazwy brancha jako wersji prowadziłoby do niedeterministycznej adopcji.

Decyzja: przypinamy aktualny, dokładny commit, zapisujemy go w kontrakcie i sprawdzamy w CI przed uruchomieniem narzędzi.

### Status wydania jest niejednoznaczny

Branch źródłowy deklaruje wersję 1.2.0 i `maturity: stable`, ale odpowiadający mu pull request upstream pozostaje niepołączony i wymaga końcowego review. Rewizja jest zweryfikowanym kandydatem na źródło, lecz nie jest tym samym co zaakceptowane wydanie z domyślnego brancha.

Decyzja: nie opisujemy adaptacji jako certyfikowanej adopcji stable i zachowujemy jawny trigger review po zmianie statusu upstream.

### Pełna adopcja nie może zatwierdzać sama siebie

Skills wymagają provider-backed evidence i niezależnego review zewnętrznego względem ocenianej rewizji. Tego warunku nie może spełnić sam commit adaptacyjny ani ręcznie wpisana deklaracja PASS.

Decyzja: lokalne testy są diagnostyczne, a CI wykonuje oryginalne validatory na dokładnym SHA. Finalny status nadal wymaga zielonego GitHub Actions i niezależnego review.

### Koszt pełnego frameworka adopcyjnego jest nieproporcjonalny

Skopiowanie katalogów `contracts/`, katalogu reguł i zewnętrznego verifiera utworzyłoby drugi system governance większy niż zmiana potrzebna temu repozytorium. Dodatkowo kandydat nie może być własnym autorytatywnym verifierem.

Decyzja: zapisujemy mapowanie zasad i ryzyka w tym dokumencie, egzekwujemy wymagania repozytoryjnymi testami oraz upstreamowymi validatorami, ale nie udajemy zgodności z pełnym assessment schema.

## Ryzyka resztkowe

- Rewizja upstream pochodzi z niepołączonego jeszcze pull requestu; pin chroni przed zmianą treści, lecz wymaga ponownej oceny po finalnym merge lub wydaniu.
- Lokalne `make full` nie pobiera kodu upstream i dlatego nie zastępuje provider-backed wykonania oryginalnych validatorów w CI.
- Niezależny review pozostaje warunkiem zatwierdzonej adopcji.
- Audyt podatności zależności runtime działa w pull request CI, ale repozytorium nie ma odrębnego cyklicznego skanu pełnego środowiska deweloperskiego.
- Piny akcji ograniczają ryzyko przesunięcia tagu, ale nie dowodzą zaufania do kodu akcji.

## Kryterium akceptacji

1. `make full` przechodzi bez płatnych requestów i bez sekretu.
2. `python scripts/check_workflow_policy.py` przechodzi na finalnym drzewie.
3. Przypięte upstreamowe validatory AGENTS.md i AFDS przechodzą w trybie strict na dokładnym SHA.
4. GitHub Actions przechodzi na dokładnym SHA brancha.
5. Niezależny reviewer potwierdza zgodność root `AGENTS.md`, dokumentów operacyjnych i workflow z implementacją.
6. Nowe istotne ustalenia z review są naprawione albo zapisane jako jawne, owned ryzyko.
