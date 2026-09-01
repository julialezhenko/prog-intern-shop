"""Pluggable payment gateways.

`get_gateway()` returns the provider selected by ``settings.PAYMENT_GATEWAY``. The default *simulated* gateway
behaves like a real card processor (Luhn validation, deterministic test cards, synchronous result) without moving
money, and the webhook view in ``sales.storefront_views.payment_webhook`` lets asynchronous providers confirm a
PENDING payment later. Adding a real provider = subclass ``PaymentGateway`` and register it in ``GATEWAYS``.
"""
import uuid
from dataclasses import dataclass

from django.conf import settings
from rest_framework.exceptions import ValidationError

TEST_CARDS = {
    "4242424242424242": ("SUCCEEDED", "Approved"),
    "4000000000000002": ("FAILED", "Card declined by the issuer"),
    "4000000000009995": ("FAILED", "Insufficient funds"),
    "4000000000000069": ("FAILED", "Card expired"),
    "4000000000000077": ("PENDING", "Authorisation pending — the provider will confirm asynchronously"),
}


@dataclass
class ChargeResult:
    status: str            # SUCCEEDED | FAILED | PENDING
    reference: str
    message: str = ""
    card_last4: str = ""

    @property
    def succeeded(self):
        return self.status == "SUCCEEDED"


def luhn_valid(number: str) -> bool:
    digits = [int(d) for d in number if d.isdigit()]
    if len(digits) < 12:
        return False
    checksum = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


class PaymentGateway:
    name = "abstract"

    def charge(self, order, card: dict) -> ChargeResult:  # pragma: no cover - interface
        raise NotImplementedError

    def verify_webhook(self, request) -> bool:
        secret = settings.PAYMENT_WEBHOOK_SECRET
        return bool(secret) and request.headers.get("X-Webhook-Secret") == secret


class SimulatedGateway(PaymentGateway):
    """Deterministic card processor used for local development, tests and the internship."""

    name = "simulated"

    def charge(self, order, card: dict) -> ChargeResult:
        number = "".join(ch for ch in str(card.get("number", "")) if ch.isdigit())
        if not luhn_valid(number):
            raise ValidationError({"number": "Enter a valid card number (e.g. 4242 4242 4242 4242)."})
        status, message = TEST_CARDS.get(number, ("SUCCEEDED", "Approved"))
        return ChargeResult(status=status, reference=f"sim_{uuid.uuid4().hex}", message=message, card_last4=number[-4:])


class OutcomeGateway(PaymentGateway):
    """Used by the simulator and the legacy ``pay(order, succeed)`` API: the caller decides the outcome."""

    name = "simulated"

    def __init__(self, succeed=True):
        self.succeed = succeed

    def charge(self, order, card: dict) -> ChargeResult:
        return ChargeResult(status="SUCCEEDED" if self.succeed else "FAILED", reference=uuid.uuid4().hex,
                            message="Approved" if self.succeed else "Declined (simulated)")


GATEWAYS = {"simulated": SimulatedGateway}


def get_gateway() -> PaymentGateway:
    name = getattr(settings, "PAYMENT_GATEWAY", "simulated")
    try:
        return GATEWAYS[name]()
    except KeyError as exc:
        raise ValueError(f"Unknown PAYMENT_GATEWAY '{name}'. Available: {', '.join(GATEWAYS)}") from exc
