"""Small, diverse RSS context; full-library search remains available to Agno."""
from collections import defaultdict, deque


def diverse_articles(rows, limit=12):
    groups = defaultdict(deque)
    for row in rows: groups[row.get('source_title') or row.get('subscription_id') or row['id']].append(row)
    result, seen = [], set()
    while groups and len(result) < limit:
        for key in list(groups):
            row = groups[key].popleft()
            if not groups[key]: del groups[key]
            if row['url'] not in seen:
                result.append(row)
                seen.add(row['url'])
            if len(result) == limit: break
    return result
