"""Batch processing utilities for efficient telemetry export."""

from __future__ import annotations

import atexit
import logging
import threading
import time
from typing import Any, Callable, Generic, Optional, Sequence, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

DEFAULT_BATCH_SIZE = 512
DEFAULT_FLUSH_INTERVAL = 5.0  # seconds
DEFAULT_MAX_QUEUE_SIZE = 10000


class BatchProcessor(Generic[T]):
    """Accumulates items and flushes them in batches.

    Items are collected in an internal buffer and flushed either when the
    batch size is reached or when the flush interval elapses, whichever
    comes first. A background thread handles periodic flushing.

    Args:
        export_fn: Callable that receives a list of items to export.
        batch_size: Maximum items per batch.
        flush_interval: Maximum seconds between flushes.
        max_queue_size: Maximum items in the buffer before dropping.
    """

    def __init__(
        self,
        export_fn: Callable[[list[T]], Any],
        batch_size: int = DEFAULT_BATCH_SIZE,
        flush_interval: float = DEFAULT_FLUSH_INTERVAL,
        max_queue_size: int = DEFAULT_MAX_QUEUE_SIZE,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if flush_interval <= 0:
            raise ValueError("flush_interval must be positive")

        self._export_fn = export_fn
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._max_queue_size = max_queue_size

        self._buffer: list[T] = []
        self._lock = threading.Lock()
        self._shutdown = False
        self._dropped_count = 0
        self._exported_count = 0

        # Start background flush thread
        self._flush_thread = threading.Thread(
            target=self._periodic_flush,
            daemon=True,
            name="acme-batch-flusher",
        )
        self._flush_thread.start()

        # Register shutdown handler
        atexit.register(self.shutdown)

    def add(self, item: T) -> bool:
        """Add an item to the batch buffer.

        Args:
            item: The item to add.

        Returns:
            True if the item was added, False if the buffer is full.
        """
        with self._lock:
            if self._shutdown:
                logger.warning("Cannot add items after shutdown")
                return False

            if len(self._buffer) >= self._max_queue_size:
                self._dropped_count += 1
                logger.warning(
                    "Buffer full (%d items), dropping item (total dropped: %d)",
                    self._max_queue_size,
                    self._dropped_count,
                )
                return False

            self._buffer.append(item)

            # Flush if batch size reached
            if len(self._buffer) >= self._batch_size:
                self._flush_locked()

        return True

    def add_many(self, items: Sequence[T]) -> int:
        """Add multiple items to the batch buffer.

        Args:
            items: Sequence of items to add.

        Returns:
            Number of items actually added.
        """
        added = 0
        for item in items:
            if self.add(item):
                added += 1
        return added

    def flush(self) -> int:
        """Manually flush the current buffer.

        Returns:
            Number of items flushed.
        """
        with self._lock:
            return self._flush_locked()

    def _flush_locked(self) -> int:
        """Flush the buffer while holding the lock.

        Returns:
            Number of items flushed.
        """
        if not self._buffer:
            return 0

        batch = self._buffer[:]
        self._buffer.clear()

        try:
            self._export_fn(batch)
            self._exported_count += len(batch)
            logger.debug("Flushed batch of %d items", len(batch))
            return len(batch)
        except Exception as exc:
            logger.error("Failed to export batch of %d items: %s", len(batch), exc)
            # Re-add items to buffer for retry (if there's space)
            if len(self._buffer) + len(batch) <= self._max_queue_size:
                self._buffer.extend(batch)
                logger.debug("Re-queued %d items for retry", len(batch))
            else:
                self._dropped_count += len(batch)
                logger.warning("Dropped %d items after export failure", len(batch))
            return 0

    def _periodic_flush(self) -> None:
        """Background thread that periodically flushes the buffer."""
        while not self._shutdown:
            time.sleep(self._flush_interval)
            if not self._shutdown:
                self.flush()

    def shutdown(self, timeout: Optional[float] = None) -> None:
        """Shut down the batch processor and flush remaining items.

        Args:
            timeout: Maximum seconds to wait for the final flush.
                Defaults to flush_interval * 2.
        """
        if self._shutdown:
            return

        logger.info("Shutting down batch processor...")
        self._shutdown = True

        # Final flush
        with self._lock:
            remaining = len(self._buffer)
            if remaining > 0:
                logger.info("Flushing %d remaining items on shutdown", remaining)
                self._flush_locked()

        # Wait for flush thread to finish
        if self._flush_thread.is_alive():
            wait_time = timeout if timeout is not None else self._flush_interval * 2
            self._flush_thread.join(timeout=wait_time)

        logger.info(
            "Batch processor shut down (exported=%d, dropped=%d)",
            self._exported_count,
            self._dropped_count,
        )

    @property
    def pending_count(self) -> int:
        """Number of items waiting in the buffer."""
        with self._lock:
            return len(self._buffer)

    @property
    def stats(self) -> dict[str, int]:
        """Return processing statistics."""
        return {
            "exported": self._exported_count,
            "dropped": self._dropped_count,
            "pending": self.pending_count,
        }

    def __repr__(self) -> str:
        return (
            f"BatchProcessor(batch_size={self._batch_size}, "
            f"flush_interval={self._flush_interval}s, "
            f"pending={self.pending_count})"
        )

    def __del__(self) -> None:
        if not self._shutdown:
            self.shutdown(timeout=1.0)


def _ensure_flush_on_shutdown(processor: BatchProcessor) -> None:
    """Ensure final flush happens before interpreter exit.

    This is registered as an atexit handler and ensures that the
    background flush thread completes before the interpreter exits.
    """
    if not processor._shutdown:
        processor.shutdown(timeout=processor._flush_interval * 3)
