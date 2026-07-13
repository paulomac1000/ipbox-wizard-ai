import pytest

from python_helper.ipbox_calculator import CostItem, aggregate_nexus_costs, nexus_classify


class TestNexusClassification:
    """Testy klasyfikacji NEXUS (Faza 4.2)."""

    # ------------------------------------------------------------------
    # Individual source → basket mapping
    # ------------------------------------------------------------------

    @pytest.mark.unit
    @pytest.mark.P1
    def test_own_br_basket_a(self):
        """Własne B+R → koszyk A."""
        item = CostItem("Wynagrodzenie programisty", 10_000.0, basket="IP")
        result = nexus_classify(item, nexus_source="own_br")
        assert result.nexus_basket == "A"

    @pytest.mark.unit
    @pytest.mark.P0
    def test_unrelated_br_contractor_basket_b(self):
        """Podwykonawca B2B (niepowiązany) → koszyk B."""
        item = CostItem("Faktura za UI/UX", 5_000.0, basket="IP")
        result = nexus_classify(item, nexus_source="unrelated_br_contractor")
        assert result.nexus_basket == "B"

    @pytest.mark.unit
    @pytest.mark.P1
    def test_related_br_contractor_basket_c(self):
        """Podmiot powiązany -> koszyk C."""
        item = CostItem("Usługa testingowa - spółka powiązana", 3_000.0, basket="IP")
        result = nexus_classify(item, nexus_source="related_br_contractor")
        assert result.nexus_basket == "C"

    @pytest.mark.unit
    @pytest.mark.P1
    def test_ip_acquisition_basket_d(self):
        """Nabycie IP → koszyk D."""
        item = CostItem("Zakup patentu", 20_000.0, basket="IP")
        result = nexus_classify(item, nexus_source="ip_acquisition")
        assert result.nexus_basket == "D"

    @pytest.mark.unit
    @pytest.mark.P1
    def test_indirect_or_general_basket_poza_nexus(self):
        """Koszty pośrednie/ogólne → poza_nexus."""
        item = CostItem("Czynsz za biuro", 2_000.0, basket="MIX")
        item.allocation_key = 0.80
        result = nexus_classify(item, nexus_source="indirect_or_general")
        assert result.nexus_basket == "poza_nexus"

    @pytest.mark.unit
    @pytest.mark.P1
    def test_unknown_source_sets_note_and_poza_nexus(self):
        """Nieznane źródło → poza_nexus + REVIEW_NEXUS_UNKNOWN w notatce."""
        item = CostItem("Kawa i herbata", 150.0, basket="NON")
        result = nexus_classify(item, nexus_source="unknown")
        assert result.nexus_basket == "poza_nexus"
        assert "REVIEW_NEXUS_UNKNOWN" in result.note

    # ------------------------------------------------------------------
    # aggregate_nexus_costs
    # ------------------------------------------------------------------

    @pytest.mark.unit
    @pytest.mark.P0
    def test_aggregate_nexus_costs_sums_correctly(self):
        """aggregate_nexus_costs sumuje kwoty poprawnie we wszystkich koszykach."""
        items = [
            nexus_classify(CostItem("Dev A", 1_000.0, basket="IP"), nexus_source="own_br"),
            nexus_classify(CostItem("Dev B", 2_000.0, basket="IP"), nexus_source="own_br"),
            nexus_classify(CostItem("UI/UX B2B", 4_000.0, basket="IP"),
                          nexus_source="unrelated_br_contractor"),
            nexus_classify(CostItem("Test spółka powiązana", 3_000.0, basket="IP"),
                          nexus_source="related_br_contractor"),
            nexus_classify(CostItem("Licencja IP", 1_500.0, basket="IP"),
                          nexus_source="ip_acquisition"),
            nexus_classify(CostItem("Czynsz", 2_500.0, basket="MIX"),
                          nexus_source="indirect_or_general"),
            nexus_classify(CostItem("Inne nieznane", 500.0, basket="NON"),
                          nexus_source="unknown"),
            nexus_classify(CostItem("Więcej ogólnych", 1_200.0, basket="MIX"),
                          nexus_source="indirect_or_general"),
        ]

        aggregated = aggregate_nexus_costs(items)

        assert aggregated["A"] == 3_000.0  # 1000 + 2000
        assert aggregated["B"] == 4_000.0
        assert aggregated["C"] == 3_000.0
        assert aggregated["D"] == 1_500.0
        assert aggregated["poza_nexus"] == 4_200.0  # 2500 + 500 + 1200
