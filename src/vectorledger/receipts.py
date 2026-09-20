from __future__ import annotations

import hashlib
import hmac
import json

from vectorledger.models import Receipt


class ReceiptSigner:
    """HMAC signer for tamper-evident receipts. KMS-backed signers can use the same interface."""

    def __init__(self, secret: str) -> None:
        if len(secret) < 16:
            raise ValueError("receipt signing secret must contain at least 16 characters")
        self.secret = secret.encode()

    @staticmethod
    def canonical_payload(receipt: Receipt) -> bytes:
        return json.dumps(receipt.payload(), sort_keys=True, separators=(",", ":")).encode()

    def sign(self, receipt: Receipt) -> str:
        return hmac.new(self.secret, self.canonical_payload(receipt), hashlib.sha256).hexdigest()

    def verify(self, receipt: Receipt) -> bool:
        return hmac.compare_digest(receipt.signature, self.sign(receipt))
