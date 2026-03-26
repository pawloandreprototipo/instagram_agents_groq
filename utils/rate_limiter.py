from __future__ import annotations
import time
import random


def jitter_sleep(min_s: float = 2.0, max_s: float = 5.0) -> None:
    """Pausa por um tempo aleatório entre min_s e max_s segundos.

    O jitter evita padrões regulares que o Instagram detecta como bot.
    """
    delay = random.uniform(min_s, max_s)
    logger_msg = f"Rate limit: aguardando {delay:.1f}s..."
    try:
        from loguru import logger
        logger.debug(logger_msg)
    except Exception:
        pass
    time.sleep(delay)
