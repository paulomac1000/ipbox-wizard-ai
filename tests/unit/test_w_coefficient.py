import pytest

from python_helper.ipbox_calculator import calculate_w_coefficient


class TestWCoefficient:
    """Testy współczynnika W (art. 30ca PIT)."""

    @pytest.mark.unit
    @pytest.mark.P0
    @pytest.mark.parametrize(
        "work_hours,non_ip_hours,invoice_percentage,expected_w",
        [
            (168, 16, 100, 90.48),  # TC-W-001
            (80, 0, 100, 100.0),  # TC-W-010 (vacation)
            (160, 80, 100, 50.0),  # TC-W-003
            (160, 0, 80, 80.0),  # TC-W-004 (% invoice)
            (100, 50, 50, 25.0),  # TC-W-005 (% invoice + non-IP)
            (160, 160, 100, 0.0),  # TC-W-006 (all non-IP)
            (160, 0, 0, 0.0),  # TC-W-007 (0% invoice IP)
            (1, 0, 100, 100.0),  # TC-W-008 (min time)
            (160, 1, 100, 99.38),  # TC-W-009 (nearly 100%)
            (40, 20, 100, 50.0),  # TC-W-011 (L4 half month)
            (160, 40, 75, 56.25),  # TC-W-012 (mixed)
            (168, 8, 100, 95.24),  # TC-W-013 (>95%)
            (168, 85, 100, 49.4),  # TC-W-014 (<50%)
        ],
    )
    def test_w_formula(self, work_hours, non_ip_hours, invoice_percentage, expected_w):
        """Basic W formula."""
        result = calculate_w_coefficient(
            work_hours=work_hours, non_ip_hours=non_ip_hours, invoice_percentage=invoice_percentage
        )
        assert result["W"] == pytest.approx(expected_w, abs=0.01)

    @pytest.mark.unit
    @pytest.mark.P0
    def test_vacation_does_not_penalize(self):
        """TC-W-010: Vacation must not lower W."""
        # 2 weeks vacation = 80h work, 0h admin
        result = calculate_w_coefficient(work_hours=80, non_ip_hours=0, invoice_percentage=100)
        assert result["W"] == 100.0  # NOT 50%!
        assert "REVIEW_01" in result["status"]  # W>95% → REVIEW

    @pytest.mark.unit
    @pytest.mark.P1
    def test_zero_work_hours(self):
        """Month entirely free."""
        result = calculate_w_coefficient(work_hours=0, non_ip_hours=0)
        assert result["W"] == 0.0
        assert result["status"] == "ERROR"

    @pytest.mark.unit
    @pytest.mark.P1
    def test_invalid_hours(self):
        """More non-IP hours than total work hours."""
        result = calculate_w_coefficient(work_hours=100, non_ip_hours=120)
        assert result["W"] == -1
        assert result["status"] == "ERROR"

    @pytest.mark.unit
    @pytest.mark.P2
    def test_invoice_percentage_over_100_gives_error(self):
        """invoice_percentage > 100 raises ValueError."""
        with pytest.raises(ValueError, match="invoice_percentage must be between 0 and 100"):
            calculate_w_coefficient(work_hours=160, non_ip_hours=0, invoice_percentage=150)
