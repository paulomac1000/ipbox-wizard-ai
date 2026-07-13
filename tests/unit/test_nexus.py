import pytest

from python_helper.ipbox_calculator import calculate_nexus


class TestNexus:
    """Testy współczynnika NEXUS (Faza 7.3)."""

    @pytest.mark.unit
    @pytest.mark.P1
    def test_nexus_basic_jdg(self):
        # A=10000, B=0, C=0, D=0 -> NEXUS = (10000*1.3)/10000 = 1.3 -> min(1.0, 1.3) = 1.0
        res = calculate_nexus(A=10000)
        assert res["nexus"] == 1.0

    @pytest.mark.unit
    @pytest.mark.P1
    def test_nexus_with_unrelated_subcontractor(self):
        # A=1000, B=1000 (freelancer), C=0, D=0
        # NEXUS = (1000*1.3 + 1000) / 2000 = 2300 / 2000 = 1.15 -> 1.0
        res = calculate_nexus(A=1000, B=1000)
        assert res["nexus"] == 1.0

    @pytest.mark.unit
    @pytest.mark.P1
    def test_nexus_with_related_subcontractor(self):
        # A=1000, B=0, C=1000 (family/related)
        # NEXUS = (1000*1.3) / 2000 = 1300 / 2000 = 0.65
        res = calculate_nexus(A=1000, C=1000)
        assert res["nexus"] == 0.65

    @pytest.mark.unit
    @pytest.mark.P1
    def test_nexus_with_ip_acquisition(self):
        # A=1000, D=1000 (buying IP)
        # NEXUS = (1000*1.3) / 2000 = 0.65
        res = calculate_nexus(A=1000, D=1000)
        assert res["nexus"] == 0.65

    @pytest.mark.unit
    @pytest.mark.P2
    def test_nexus_all_paths(self):
        # A=1000, B=500, C=200, D=300
        # NEXUS = (1000*1.3 + 500) / (1000+500+200+300) = 1800 / 2000 = 0.9
        res = calculate_nexus(A=1000, B=500, C=200, D=300)
        assert res["nexus"] == 0.9

    @pytest.mark.unit
    @pytest.mark.P1
    def test_nexus_zero_denominator(self):
        # A=0, B=0, C=0, D=0
        res = calculate_nexus(A=0)
        assert res["nexus"] == 0
        assert "REVIEW_03" in res["message"]

    @pytest.mark.unit
    @pytest.mark.P2
    def test_nexus_only_B_subcontractors(self):
        # A=0, B=1000, C=0, D=0
        # NEXUS = (0 + 1000) / 1000 = 1.0
        res = calculate_nexus(A=0, B=1000)
        assert res["nexus"] == 1.0

    @pytest.mark.unit
    @pytest.mark.P2
    def test_nexus_only_C_subcontractors(self):
        # A=0, B=0, C=1000, D=0
        # NEXUS = 0 / 1000 = 0
        res = calculate_nexus(A=0, C=1000)
        assert res["nexus"] == 0.0

    @pytest.mark.unit
    @pytest.mark.P1
    def test_nexus_rounding(self):
        # A=100, B=0, C=200
        # NEXUS = 130 / 300 = 0.433333...
        res = calculate_nexus(A=100, C=200)
        assert res["nexus"] == 0.4333
