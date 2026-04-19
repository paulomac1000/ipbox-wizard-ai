import pytest
from python_helper.ipbox_calculator import aggregate_w_multiproject

class TestWMultiproject:
    """Testy wieloprojektowości w jednym miesiącu."""

    @pytest.mark.unit
    @pytest.mark.P1
    def test_weighted_average_basic(self):
        # Project 1: 10000 PLN, W=75%
        # Project 2: 5000 PLN, W=90%
        # Weighted average: (10000*75 + 5000*90) / 15000 = (750000 + 450000) / 15000 = 1200000 / 15000 = 80%
        projects = [
            {"revenue": 10000, "W": 75},
            {"revenue": 5000, "W": 90}
        ]
        assert aggregate_w_multiproject(projects) == 80.0

    @pytest.mark.unit
    @pytest.mark.P1
    def test_single_project(self):
        projects = [{"revenue": 20000, "W": 95}]
        assert aggregate_w_multiproject(projects) == 95.0

    @pytest.mark.unit
    @pytest.mark.P1
    def test_zero_revenue_total(self):
        projects = [{"revenue": 0, "W": 100}, {"revenue": 0, "W": 50}]
        assert aggregate_w_multiproject(projects) == 0.0

    @pytest.mark.unit
    @pytest.mark.P2
    def test_very_small_revenue(self):
        projects = [
            {"revenue": 0.01, "W": 100},
            {"revenue": 9999.99, "W": 50}
        ]
        assert aggregate_w_multiproject(projects) == pytest.approx(50.0, abs=0.01)

    @pytest.mark.unit
    @pytest.mark.P2
    def test_many_projects(self):
        projects = [{"revenue": 1000, "W": 10 * i} for i in range(1, 11)]
        assert aggregate_w_multiproject(projects) == 55.0

    @pytest.mark.unit
    @pytest.mark.P1
    def test_mixed_zero_and_non_zero(self):
        projects = [{"revenue": 1000, "W": 70}, {"revenue": 0, "W": 100}]
        assert aggregate_w_multiproject(projects) == 70.0
