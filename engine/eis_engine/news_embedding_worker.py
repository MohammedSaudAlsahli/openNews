"""Private local inference worker. EOF or 30 seconds without work releases all RAM."""
import contextlib
import json
from pathlib import Path
import select
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from eis_engine.news_embeddings import LocalEncoder


def main():
    encoder = LocalEncoder(Path(sys.argv[1]))
    while select.select([sys.stdin], [], [], 30)[0]:
        line = sys.stdin.readline()
        if not line: break
        try:
            request = json.loads(line)
            # Library progress must never corrupt the JSON protocol.
            with contextlib.redirect_stdout(sys.stderr):
                vectors = encoder.encode(request['texts'], query=request.get('query', False))
            response = {'vectors': vectors}
        except Exception as error:
            response = {'error': str(error)}
        print(json.dumps(response), flush=True)


if __name__ == '__main__':
    main()
