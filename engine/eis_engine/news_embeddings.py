"""Bounded, cancellable Ollama embeddings; no tensor runtime in the app."""
import asyncio
import math
import time
from pathlib import Path
import httpx
from .local_summary import HOST
from .local_inference import settled

MODEL_ID = 'embeddinggemma-2:270m'
DIMENSIONS = 768
MODEL_REVISION = 'ollama-v1'


class LocalNewsEmbeddings:
    def __init__(self, cache: Path | None = None, *, name=MODEL_ID, dimensions=DIMENSIONS, digest=''):
        self.name, self.dimensions, self.digest = name, dimensions, digest
        self.model = name if digest else None
        self.closed = False
        self.last_used = 0.0
        self.metrics = {}
        self.stop = None

    @property
    def fingerprint(self):
        return f'ollama-v1:{self.name}@{self.digest}:{self.dimensions}'

    def inputs(self, texts, query):
        if self.closed: raise RuntimeError('Embedding client is closed')
        if not self.digest: raise RuntimeError('Choose and prepare an embedding model first')
        if not texts or len(texts)>16 or any(not isinstance(t,str) or len(t)>8000 for t in texts):
            raise ValueError('Embedding batch exceeds its bounded input budget')
        if self.name.startswith('embeddinggemma') and query:
            return ['task: search result | query: '+t for t in texts]
        if self.name.startswith('nomic-embed-text'):
            return [('search_query: ' if query else 'search_document: ')+t for t in texts]
        return list(texts)

    def vectors(self, data, count):
        vectors = data.get('embeddings')
        if not isinstance(vectors,list) or len(vectors)!=count: raise ValueError('Invalid embedding count')
        result = []
        for vector in vectors:
            if not isinstance(vector,list) or len(vector)!=self.dimensions or any(type(x) not in (float,int) or not math.isfinite(x) for x in vector):
                raise ValueError('Invalid embedding output')
            norm = math.sqrt(sum(x*x for x in vector))
            if not norm or not math.isfinite(norm): raise ValueError('Empty embedding output')
            result.append([x/norm for x in vector])
        return result

    async def aencode(self, texts, *, query=False):
        inputs = self.inputs(texts,query)
        started = time.monotonic()
        submitted = False
        try:
            async with httpx.AsyncClient(trust_env=False, timeout=httpx.Timeout(90,connect=3)) as client:
                tags = await client.get(HOST+'/api/tags'); tags.raise_for_status()
                current = next((m for m in tags.json()['models'] if m['name']==self.name),None)
                if not current or current.get('digest')!=self.digest:
                    raise RuntimeError('Model changed; prepare it again before searching')
                submitted = True
                response = await client.post(HOST+'/api/embed',json={'model':self.name,'input':inputs,
                    'dimensions':self.dimensions,'keep_alive':'30s','truncate':False,
                    'options':{'num_thread':2,'num_ctx':2048,'num_batch':128}})
                response.raise_for_status()
                data = response.json()
                result = self.vectors(data,len(inputs))
                self.last_used = time.monotonic()
                # Ollama reports nanoseconds. These diagnostics contain no input text.
                self.metrics = {'items':len(inputs),'elapsed_ms':round((self.last_used-started)*1000),
                    'load_ms':round(data.get('load_duration',0)/1e6),
                    'inference_ms':round(max(0,data.get('total_duration',0)-data.get('load_duration',0))/1e6)}
                return result
        except BaseException:
            if submitted and self.stop:
                await settled(asyncio.create_task(self.stop(self.name)))
            raise

    def encode(self, texts, *, query=False):
        """Compatibility for non-async integrations; production uses aencode."""
        return asyncio.run(self.aencode(texts,query=query))

    def close(self):
        self.closed = True
