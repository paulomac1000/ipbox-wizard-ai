# Onboarding agenta

1. Przeczytaj `AGENTS.md`, `ipbox_algorytm.md` i `docs/testing.md`.
2. Uruchom bezpłatny zestaw testów.
3. Przy zmianie semantyki najpierw popraw kalkulator/oracle i test jednostkowy.
4. Potem popraw scenariusz lub prompt — nigdy odwrotnie pod konkretną odpowiedź modelu.
5. Nagrywanie LLM wykonuj dopiero po zielonym deterministycznym CI.
6. Używaj trzech modeli z `tests/llm/models.py`; model ID musi być dokładny.
7. Po nieudanym nagraniu analizuj `/tmp/ipbox_llm_rejected/<model>/`, popraw kod i nagraj wyłącznie brakujące scenariusze.
