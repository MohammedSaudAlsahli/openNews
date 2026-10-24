"""Cancellation cleanup must finish before an inference lease is released."""
import asyncio


async def settled(task):
    """A second cancellation cannot abandon the owned worker's shutdown."""
    while not task.done():
        try: await asyncio.shield(task)
        except asyncio.CancelledError: continue
    return task.result()
