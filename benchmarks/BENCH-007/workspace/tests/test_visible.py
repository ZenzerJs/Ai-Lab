"""
test_visible.py - Accessible smoke tests for BENCH-007.
"""
from decimal import Decimal
from api import BillingAPI


def test_starter_invoice_smoke():
    """Verify basic tenant creation, usage recording, and invoice preview."""
    api = BillingAPI()
    api.create_tenant("acme", tier="starter")
    api.record_usage("acme", "2026-11", "api_calls", 100, unit_rate="0.10")
    inv = api.preview_invoice("acme", "2026-11")
    assert inv["tenant_id"] == "acme"
    assert inv["period"] == "2026-11"
    assert inv["tier"] == "starter"
    assert len(inv["lines"]) == 1
    assert Decimal(str(inv["total"])) == Decimal("10.00")
