"""On-demand local embeddings through Agno and Ollama; no tensor runtime in the app."""
import math
from pathlib import Path
import httpx
from .local_summary import HOST

MODEL_ID = 'embeddinggemma-2:270m'
DIMENSIONS = 768
MODEL_REVISION = 'ollama-v1'


class LocalNewsEmbeddings:
    def __init__(self, cache: Path | None = None, *, name=MODEL_ID, dimensions=DIMENSIONS, digest=''):
        self.name, self.dimensions, self.digest = name, dimensions, digest
        self.model = name if digest else None
        self.closed = False

    @property
    def fingerprint(self):
        return f'ollama-v1:{self.name}@{self.digest}:{self.dimensions}'

    def encode(self, texts, *, query=False):
        if self.closed: raise RuntimeError('Embedding client is closed')
        if not self.digest: raise RuntimeError('Choose and prepare an embedding model first')
        from agno.knowledge.embedder.ollama import OllamaEmbedder
        from ollama import Client
        # Short retention releases weights even when a request is cancelled or fails.
        class BoundedClient(Client):
            def embed(self, *args, **kwargs):
                return super().embed(*args, **kwargs, keep_alive=self.batch_retention)
        with httpx.Client(trust_env=False, timeout=5) as check:
            response = check.get(HOST+'/api/tags'); response.raise_for_status()
            current = next((m for m in response.json()['models'] if m['name']==self.name), None)
            if not current or current.get('digest') != self.digest:
                raise RuntimeError('Model changed; prepare it again before searching')
        client = BoundedClient(host=HOST, timeout=90, trust_env=False)
        client.batch_retention = 0
        adapter = OllamaEmbedder(id=self.name, dimensions=self.dimensions, ollama_client=client,
                                options={'num_thread':2})
        try:
            result = []
            for index, text in enumerate(texts):
                # Retain only between adjacent chunks; final call releases weights.
                client.batch_retention = 0 if index == len(texts)-1 else "5s"
                if self.name.startswith('embeddinggemma') and query:
                    text = 'task: search result | query: '+text
                elif self.name.startswith('nomic-embed-text'):
                    text = ('search_query: ' if query else 'search_document: ')+text
                vector = adapter.get_embedding(text)
                if len(vector)!=self.dimensions or not all(math.isfinite(x) for x in vector):
                    raise ValueError('Invalid embedding output')
                norm = math.sqrt(sum(x*x for x in vector))
                if not norm: raise ValueError('Empty embedding output')
                result.append([x/norm for x in vector])
            return result
        finally:
            client._client.close()

    def close(self):
        self.closed = True
