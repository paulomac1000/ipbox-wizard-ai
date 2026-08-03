---
description: Decyzja o adaptacji ci-cd-architect, afds-doc-writer i agents-md-architect do ipbox-wizard-ai.
doc_id: decision.ai-skills-adoption
type: decision
status: evolving
rigor: operational
owners: [repository-maintainers]
verification: Uruchom make full i python scripts/check_workflow_policy.py, sprawdź GitHub Actions na dokładnym SHA oraz uzyskaj niezależne review.
upstream: [https://github.com/paulomac1000/ai-skills/tree/5d22dbd476bc1dc452927859c182f33b659ffa43]
downstream: [AGENTS.md, docs/agent-tax-analysis.md, docs/agent-development.md, Makefile, .github/workflows/deterministic-ci.yml, .github/workflows/llm-benchmark.yml]
review_triggers: [nowa wersja ai-skills, zmiana profilu repozytorium, zmiana CI, zmiana AGENTS.md, dodanie publikacji artefaktów]
---

# Adaptacja AI Skills 1.2.0

## Decyzja

Repozytorium adaptuje wymagania trzech skills z `paulomac1000/ai-skills` na dokładnej rewizji `5d22dbd476bc1dc452927859c182f33b659ffa43`:

- `ci-cd-architect` 1.2.0;
- `afds-doc-writer` 1.2.0;
- `agents-md-architect` 1.2.0.

Adaptacja jest selektywna i związana z architekturą tego repozytorium. Nie vendorujemy całego `ai-skills`, nie kopiujemy jego katalogu kontraktów i nie deklarujemy zatwierdzonej pełnej adopcji bez provider-backed evidence oraz niezależnego review dokładnego SHA.

## Kontekst

`ipbox-wizard-ai` jest pojedynczym repozytorium aplikacyjnym o profilu safety-critical. Nie publikuje paczki ani obrazu produkcyjnego. Ma dwie odrębne ścieżki:

1. bezpłatną, deterministyczną bramkę pull requestu;
2. ręcznie potwierdzany i płatny benchmark wielu modeli.

Największe ryzyka to błędna reguła podatkowa, niejawne założenie, wyciek danych podatnika, live request podczas playbacku, niekontrolowany koszt LLM oraz zależność CI od mutowalnego tagu akcji.

## Zastosowane wymagania

### CI/CD

- Wszystkie zewnętrzne GitHub Actions są przypięte do pełnych SHA, z czytelnym komentarzem wersji.
- `actions/checkout` nie utrzymuje poświadczeń.
- Pull request CI ma wyłącznie `contents: read`; usunięto nieużywane `checks: write`.
- Każdy job ma timeout, workflow ma concurrency, a artefakty mają jawny retention i zachowanie braku plików.
- Dodano wykonywalną politykę `scripts/check_workflow_policy.py`, uruchamianą przez lokalną i zdalną bramkę.
- Płatne wywołania pozostają poza zwykłym CI i wymagają potwierdzenia oraz limitów kosztu.

### Dokumentacja AFDS

- Nowe procedury mają jednego właściciela, typ dokumentu, status, ownera, weryfikację i review triggers.
- Odpowiedź operacyjna znajduje się przed tłem.
- Wymagania, fakty, ograniczenia i ryzyka są rozdzielone.
- Dokumenty linkują do `README.md`, `ipbox_algorytm.md`, `Makefile` i `docs/testing.md` zamiast kopiować ich pełną treść.
- Zmiana kontraktu wskazuje konsumentów przez `upstream` i `downstream`.

### AGENTS.md

- Wybrano layout `single`, profil `safety-critical` i język `pl`.
- Root `AGENTS.md` jest routerem mieszczącym zasady potrzebne w większości zadań.
- Szczegółową analizę danych podatnika i rozwój repozytorium przeniesiono do osobnych procedur ładowanych według zadania.
- Usunięto z trwałej instrukcji ulotne liczniki scenariuszy i kaset.
- Dodano jawne pierwszeństwo, tryb read-only, kanonicznych właścicieli, granice danych, płatnych działań i kryteria ukończenia.
- Komendy jakości kierują do `Makefile`, a nie do kolejnej skopiowanej definicji pipeline.

## Adaptacje i reguły nieaplikowalne

- Reguły budowy, smoke-testu i publikacji tego samego artefaktu są obecnie nieaplikowalne, ponieważ repozytorium niczego automatycznie nie publikuje. Należy je ponownie ocenić przed dodaniem paczki, obrazu lub release workflow.
- Macierz Pythona projektu pozostaje 3.11–3.13. Macierz kompatybilności samego `ai-skills` 3.12–3.14 nie jest automatycznie kontraktem runtime projektu.
- Nie dodano nested `AGENTS.md`, ponieważ podkatalogi nie mają odrębnej technologii, ownership ani bezpiecznych komend uzasadniających dziedziczenie.
- Nie dodano YAML frontmatter do `README.md` ani `ipbox_algorytm.md`. Pozostają istniejącymi kanonicznymi właścicielami; AFDS zastosowano do nowych dokumentów operacyjnych i tej decyzji bez przebudowy prezentacji produktu.
- Nie skopiowano validatorów `ai-skills`. Repozytorium ma własną, węższą politykę workflow, a zgodność instrukcji wymaga osobnego uruchomienia upstreamowych narzędzi podczas niezależnego review.

## Znalezione problemy w źródle

### Status wydania jest niejednoznaczny

Branch źródłowy deklaruje wersję 1.2.0 i `maturity: stable`, ale PR #18 pozostaje niepołączony i jego własny opis wymaga jeszcze niezależnego finalnego review. To oznacza, że branch jest zweryfikowanym kandydatem na źródło, lecz nie jest tym samym co zaakceptowane wydanie z domyślnego brancha.

Decyzja: pinujemy dokładny commit wskazany przez użytkownika i nie opisujemy adaptacji jako certyfikowanej adopcji stable.

### Pełna adopcja nie może zatwierdzać sama siebie

Skills wymagają provider-backed evidence i niezależnego review zewnętrznego względem ocenianej rewizji. To sensowna bariera, ale nie może zostać spełniona przez sam commit adaptacyjny ani przez plik w ocenianym repozytorium.

Decyzja: lokalne testy i nowy skrypt są diagnostyczne. Finalny status wymaga zielonego GitHub Actions na dokładnym SHA i niezależnego review.

### Koszt pełnego frameworka adopcyjnego jest nieproporcjonalny

Skopiowanie katalogów `contracts/`, katalogu reguł i zewnętrznego verifiera utworzyłoby drugi system governance większy niż zmiana potrzebna temu repozytorium. Dodatkowo kandydat nie może być własnym autorytatywnym verifierem.

Decyzja: zapisujemy mapowanie zasad i ryzyka w tym dokumencie, ale nie udajemy zgodności z pełnym assessment schema.

## Ryzyka resztkowe

- Upstreamowe narzędzia `agents-md-architect` i AFDS nie zostały jeszcze uruchomione na finalnym branchu.
- Nie ma jeszcze provider-backed wyniku GitHub Actions dla dokładnego SHA zmian.
- Nie ma niezależnego review.
- Repozytorium nie ma okresowego skanu podatności zależności; dodanie takiej bramki wymaga osobnej decyzji o narzędziu, wersjonowaniu i obsłudze wyjątków.
- Piny akcji ograniczają ryzyko przesunięcia tagu, ale nie dowodzą zaufania do kodu akcji.

## Kryterium akceptacji

1. `make full` przechodzi bez płatnych requestów i bez sekretu.
2. `python scripts/check_workflow_policy.py` przechodzi na finalnym drzewie.
3. GitHub Actions przechodzi na dokładnym SHA brancha.
4. Niezależny reviewer potwierdza zgodność root `AGENTS.md`, dokumentów operacyjnych i workflow z implementacją.
5. Nowe istotne ustalenia z review są naprawione albo zapisane jako jawne, owned ryzyko.
