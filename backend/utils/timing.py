import time

from backend.logger import logger


def log_timing(stage: str, started_at: float):
    elapsed = time.time() - started_at
    logger.info("[Timing] %s -> %.2fs", stage, elapsed)
    return elapsed
