from __future__ import annotations

from typing import Literal, Optional

PaymentKind = Literal["sbp", "card"]
PaymentFilter = Literal["all", "sbp", "card"]


def order_payment_kind(order: dict) -> Optional[PaymentKind]:
    pst = (order.get("paymentSystemType") or "").strip().lower()
    if pst == "by_mobile":
        return "sbp"
    if pst == "by_card":
        return "card"
    if order.get("phoneBankName") and not order.get("cardBankName"):
        return "sbp"
    if order.get("cardBankName") and not order.get("phoneBankName"):
        return "card"
    if "mobile" in pst or pst == "sbp":
        return "sbp"
    if "card" in pst:
        return "card"
    return None


def matches_payment_filter(order: dict, payment_filter: str) -> bool:
    if payment_filter == "all":
        return True
    kind = order_payment_kind(order)
    if kind is None:
        return False
    return kind == payment_filter


def payment_filter_label(payment_filter: str) -> str:
    return {
        "all":  "все заявки",
        "sbp":  "только СБП (телефон)",
        "card": "только карта",
    }.get(payment_filter, payment_filter)
