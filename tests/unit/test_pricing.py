"""Tests unitaires des règles de prix — POINT DE DÉPART (Atelier 1).

Complétez ce fichier : objectif >= 90 % de couverture sur minishop/pricing.py.
"""

from decimal import Decimal
from unittest.mock import patch

import pytest

from minishop.pricing import line_total, money, quote, Line
from minishop.catalog import Product

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_catalog():
    with patch("minishop.pricing.get_product") as mock_get:
        def side_effect(product_id):
            if product_id == "P1":
                return Product(id="P1", name="P1", price=Decimal("10.00"), stock=100)
            if product_id == "P2":
                return Product(id="P2", name="P2", price=Decimal("20.00"), stock=100)
            raise KeyError(f"Product {product_id} not found")
        mock_get.side_effect = side_effect
        yield mock_get


def test_money_arrondi_commercial():
    """0.125 s'arrondit à 0.13 (ROUND_HALF_UP), pas 0.12."""
    assert money("0.125") == Decimal("0.13")


def test_line_total_sans_remise():
    assert line_total(Decimal("12.50"), 2) == Decimal("25.00")


def test_quote_panier_vide():
    """Un panier vide coûte 0 € : pas de frais de livraison."""
    q = quote([])
    assert q.total == Decimal("0.00")
    assert q.shipping == Decimal("0.00")


def test_remise_volume():
    # 9 units: no discount
    assert line_total(Decimal("10.00"), 9) == Decimal("90.00")
    # 10 units: 5% discount
    assert line_total(Decimal("10.00"), 10) == Decimal("95.00")


@pytest.mark.parametrize("qty", [0, -1, 100, "2", True])
def test_quantite_invalide(qty):
    with pytest.raises(ValueError):
        line_total(Decimal("10.00"), qty)


def test_coupons_welcome10(mock_catalog):
    # WELCOME10: -10% if subtotal >= 20
    # Item 1: 20€, qty 1 -> subtotal 20, discount 2
    q = quote([{"product_id": "P1", "qty": 2}], coupon="WELCOME10")
    assert q.discount == Decimal("2.00")

    # Item 1: 19.99€, qty 1 -> subtotal 19.99, discount 0
    with patch("minishop.pricing.get_product", return_value=Product(id="P1", name="P1", price=Decimal("19.99"), stock=100)):
        q = quote([{"product_id": "P1", "qty": 1}], coupon="WELCOME10")
        assert q.discount == Decimal("0.00")


def test_coupons_fixed5(mock_catalog):
    # FIXED5: -5€ if subtotal >= 30
    q = quote([{"product_id": "P1", "qty": 3}], coupon="FIXED5")  # 30€
    assert q.discount == Decimal("5.00")


def test_coupons_freeship(mock_catalog):
    # FREESHIP: shipping 0
    q = quote([{"product_id": "P1", "qty": 1}], coupon="FREESHIP")
    assert q.shipping == Decimal("0.00")


def test_coupon_student15(mock_catalog):
    # STUDENT15: -15% on non-volume-discounted lines
    # Line 1: 10€, qty 1 -> total 10 (no volume discount)
    # Line 2: 10€, qty 10 -> total 9 (volume discount)
    # Subtotal = 19. Discount = 15% of 10 = 1.50.
    items = [
        {"product_id": "P1", "qty": 1},  # 10€
        {"product_id": "P1", "qty": 10},  # 10€ * 0.9 = 9€
    ]
    q = quote(items, coupon="STUDENT15")
    assert q.subtotal == Decimal("19.00")
    assert q.discount == Decimal("1.50")
    assert q.total == Decimal("17.50")


def test_coupon_inconnu(mock_catalog):
    with pytest.raises(ValueError, match="Coupon inconnu"):
        quote([{"product_id": "P1", "qty": 1}], coupon="INVALID")


def test_coupon_casse(mock_catalog):
    # Case insensitive check
    q = quote([{"product_id": "P1", "qty": 2}], coupon="welcome10")
    assert q.discount == Decimal("2.00")


def test_livraison_offerte(mock_catalog):
    # Total after discount >= 50 -> shipping 0
    # Item 1: 60€, qty 1 -> subtotal 60, discount 0, total 60, shipping 0
    q = quote([{"product_id": "P2", "qty": 3}], coupon=None)  # 60€
    assert q.shipping == Decimal("0.00")

    # Total after discount < 50 -> shipping 4.90
    q = quote([{"product_id": "P1", "qty": 4}], coupon=None)  # 40€
    assert q.shipping == Decimal("4.90")


def test_produit_inconnu(mock_catalog):
    with pytest.raises(KeyError):
        quote([{"product_id": "UNKNOWN", "qty": 1}])
