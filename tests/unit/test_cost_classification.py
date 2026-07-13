import pytest

from python_helper.ipbox_calculator import CostItem, classify_cost


class TestCostClassification:
    """Testy klasyfikacji kosztów (Faza 3)."""

    @pytest.mark.unit
    @pytest.mark.P0
    @pytest.mark.parametrize("description,amount,social_security_in_kpir,expected_basket", [
        ("Kawa ziarnista", 50.0, True, "NON"),
        ("Herbata czarna", 20.0, True, "NON"),
        ("Środki czystości", 35.0, True, "NON"),
        ("Mydło w płynie", 15.0, True, "NON"),
        ("Ręczniki papierowe", 10.0, True, "NON"),
        ("Obiad z klientem", 120.0, True, "NON"),
        ("Kurs Udemy Python", 49.0, True, "MIX"),
        ("Licencja JetBrains", 119.0, True, "MIX"),
        ("Serwer VPS", 200.0, True, "MIX"),
        ("Abonament Internet", 60.0, True, "MIX"),
        ("Leasing operacyjny BMW", 2500.0, True, "MIX"),
        ("Paliwo do auta", 300.0, True, "MIX"),
        ("Księgowość", 250.0, True, "MIX"),
        ("ZUS społeczne", 1600.0, True, "MIX"),
        ("Składka zdrowotna", 300.0, True, "MIX"),
        ("Składki społeczne", 1600.0, False, "EXCLUDED"),
        ("Mandat karny", 500.0, True, "EXCLUDED"),
        ("Odsetki od mandatu", 15.0, True, "EXCLUDED"),
        ("Kwiaty do biura", 45.0, True, "NON"),
        ("Kosmetyczka", 150.0, True, "NON"),
        ("Abonament LuxMed", 100.0, True, "NON"),
        ("Fryzjer męski", 60.0, True, "NON")
    ])
    def test_basic_classification(self, description, amount, social_security_in_kpir, expected_basket):
        item = CostItem(description=description, amount=amount)
        result = classify_cost(item, social_security_in_kpir=social_security_in_kpir, health_insurance_in_kpir=True)
        assert result.basket == expected_basket

    @pytest.mark.unit
    @pytest.mark.P1
    def test_large_cost_requires_review(self):
        """Koszty > 10k wymagają review (fixed assets)."""
        item = CostItem(description="MacBook Pro", amount=15000.0)
        result = classify_cost(item, social_security_in_kpir=True, health_insurance_in_kpir=True)
        assert result.basket == "?"
        assert "depreciation" in result.note

    @pytest.mark.unit
    @pytest.mark.P1
    def test_health_insurance_not_in_kpir(self):
        """Składka zdrowotna poza KPiR → EXCLUDED."""
        item = CostItem(description="Składka zdrowotna", amount=900)
        result = classify_cost(item, social_security_in_kpir=True, health_insurance_in_kpir=False)
        assert result.basket == "EXCLUDED"

    @pytest.mark.unit
    @pytest.mark.P0
    def test_social_security_paths(self):
        """TC-VT-011: Różne ścieżki ujęcia ZUS."""
        # Path A: Social Security in KPiR
        item1 = CostItem(description="ZUS społeczne", amount=1000)
        res1 = classify_cost(item1, social_security_in_kpir=True, health_insurance_in_kpir=True)
        assert res1.basket == "MIX"

        # Path B: Social Security in PIT
        item2 = CostItem(description="ZUS społeczne", amount=1000)
        res2 = classify_cost(item2, social_security_in_kpir=False, health_insurance_in_kpir=True)
        assert res2.basket == "EXCLUDED"
