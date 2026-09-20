from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from vectorledger.service import VectorLedgerService

logger = logging.getLogger(__name__)


async def anti_entropy_loop(
    service: VectorLedgerService, interval_seconds: int, stop: asyncio.Event
) -> None:
    while not stop.is_set():
        try:
            receipts = await service.reconcile_all()
            failures = sum(receipt.status == "failed" for receipt in receipts)
            logger.info(
                "anti-entropy pass complete documents=%d failures=%d", len(receipts), failures
            )
        except Exception:
            logger.exception("anti-entropy pass failed")
        with suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=interval_seconds)
