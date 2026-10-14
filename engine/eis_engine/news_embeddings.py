"""Lazy, text-only Google embeddings. No article text leaves the device."""
import math
import os
from pathlib import Path

MODEL_ID = "google/embeddinggemma-2"
DIMENSIONS = 256
MODEL_REVISION = "914f7f89142e33e77833254d9c9b90c3cef7303b"


class LocalEncoder:
    def __init__(self, cache: Path):
        self.cache = cache
        self.model = None

    def encode(self, texts, *, query=False):
        # Imported only in the worker thread, never during app launch or IPC dispatch.
        if self.model is None:
            # Plain HTTPS downloads avoid the optional Xet daemon and its retry storms.
            os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
            import torch
            from sentence_transformers import SentenceTransformer
            torch.set_num_threads(2)
            self.model = SentenceTransformer(
                MODEL_ID, revision=MODEL_REVISION, cache_folder=str(self.cache), device="cpu",
                config_kwargs={"vision_config": None, "audio_config": None},
                model_kwargs={"torch_dtype": torch.float32}, trust_remote_code=False,
            )
            self.model.max_seq_length = 2048
        inputs = [("task: search result | query: " + text) if query else text for text in texts]
        vectors = self.model.encode(inputs, batch_size=2, truncate_dim=DIMENSIONS,
                                    normalize_embeddings=True, show_progress_bar=False)
        result = [vector.tolist() for vector in vectors]
        if any(len(v) != DIMENSIONS or not all(math.isfinite(x) for x in v) for v in result):
            raise ValueError("Invalid embedding output")
        return result


class LocalNewsEmbeddings:
    """Keep tensor libraries and weights outside the long-lived IPC process."""
    def __init__(self, cache: Path):
        import threading
        self.cache = cache
        self.process = None
        self.lock = threading.Lock()
        self.closed = False

    def encode(self, texts, *, query=False):
        import json
        import select
        import subprocess
        import sys
        with self.lock:
            if self.closed: raise RuntimeError("Embedding worker is closed")
            if self.process is None or self.process.poll() is not None:
                self.close_process()
                self.process = subprocess.Popen(
                    [sys.executable, '-I', '-B', str(Path(__file__).with_name('news_embedding_worker.py')), str(self.cache)],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                )
            process = self.process
            try:
                process.stdin.write((json.dumps({'texts':texts,'query':query})+'\n').encode())
                process.stdin.flush()
                if not select.select([process.stdout], [], [], 180)[0]:
                    raise TimeoutError('Embedding worker timed out')
                response = json.loads(process.stdout.readline())
                if 'error' in response: raise RuntimeError(response['error'])
                return response['vectors']
            except Exception:
                self.close_process()
                raise

    def close_process(self):
        process, self.process = self.process, None
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=2)
                except Exception:
                    process.kill()
                    process.wait()
            for pipe in (process.stdin, process.stdout):
                if pipe: pipe.close()

    def close(self):
        self.closed = True
        self.close_process()
