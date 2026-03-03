

def _ensure_flush_on_shutdown(processor: BatchProcessor) -> None:
    """Ensure final flush happens before interpreter exit.

    This is registered as an atexit handler and ensures that the
    background flush thread completes before the interpreter exits.
    """
    if not processor._shutdown:
        processor.shutdown(timeout=processor._flush_interval * 3)
