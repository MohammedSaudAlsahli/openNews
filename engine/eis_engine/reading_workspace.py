"""Local reading sessions, saved topics and quotations; no model calls."""
import json
import math
import re
from datetime import datetime, timedelta, timezone
from .contracts import Failure
from .storage import now, uid


def public_state(data):
    # Keep engine frames bounded; internal visit/seen indexes are never sent.
    return {key: data.get(key, []) for key in ('queue', 'topics', 'muted')} | {
        'quotes': data.get('quotes', [])[-40:],
        'quotes_total': len(data.get('quotes', [])),
    }


def dispatch(service, payload):
    store, db, ws = service.store, service.db, service.ws
    db.execute('CREATE TABLE IF NOT EXISTS reading_workspace(workspace_id TEXT PRIMARY KEY, data TEXT NOT NULL)')
    row = store.one('SELECT data FROM reading_workspace WHERE workspace_id=?', (ws,))
    data = json.loads(row['data']) if row else {'queue':[], 'topics':[], 'quotes':[], 'muted':[], 'visits':{}}
    action = payload.get('action', 'get')
    if action in {'queue', 'visit', 'quote'}:
        article = service.news.article(payload.get('article_id'), mark_read=False)
        identifier = article['id']
        if action == 'queue':
            data['queue'] = [x for x in data['queue'] if x != identifier]
            if payload.get('enabled') is True: data['queue'].append(identifier)
            data['queue'] = data['queue'][-200:]
        elif action == 'visit':
            history = service.news.archive.history(identifier)['revisions']
            data['visits'][identifier] = {'at':now(), 'revision':history[0]['id'] if history else None}
            data['visits'] = dict(list(data['visits'].items())[-2000:])
        else:
            text = str(payload.get('text', '')).strip()
            if not 1 <= len(text) <= 4000: raise Failure('VALIDATION_ERROR', 'Choose up to 4000 characters.')
            data['quotes'].append({'id':uid(), 'article_id':identifier, 'title':article['title'], 'url':article['url'], 'text':text, 'origin':'summary' if payload.get('origin')=='summary' else 'article', 'at':now()})
            data['quotes'] = data['quotes'][-500:]
    elif action in {'topic', 'mute'}:
        topic = str(payload.get('topic', '')).strip()[:100]
        if not topic: raise Failure('VALIDATION_ERROR', 'Enter a topic.')
        key = 'topics' if action == 'topic' else 'muted'
        data[key] = [x for x in data[key] if (x if isinstance(x,str) else x['topic']).casefold() != topic.casefold()]
        if payload.get('enabled', True):
            data[key].append(topic if key == 'topics' else {'topic':topic, 'until':(datetime.now(timezone.utc)+timedelta(days=7)).isoformat()})
        data[key] = data[key][-50:]
    elif action == 'remove_quote':
        data['quotes'] = [q for q in data['quotes'] if q['id'] != payload.get('id')]
    elif action == 'caught_up':
        identifiers = payload.get('article_ids', [])
        if not isinstance(identifiers, list) or len(identifiers)>20: raise Failure('VALIDATION_ERROR', 'Choose at most 20 articles.')
        for identifier in identifiers: service.news.article(identifier, mark_read=False)
        data['catchup_seen'] = list(dict.fromkeys(data.get('catchup_seen', []) + identifiers))[-2000:]
    elif action not in {'get', 'briefing', 'comparison'}: raise Failure('VALIDATION_ERROR', 'Unknown reading action.')
    if action not in {'get','briefing','comparison'}:
        with db:
            db.execute('INSERT INTO reading_workspace VALUES(?,?) ON CONFLICT(workspace_id) DO UPDATE SET data=excluded.data', (ws,json.dumps(data,ensure_ascii=False)))
    if action == 'comparison':
        current = service.news.article(payload.get('article_id'), mark_read=False)
        other = service.news.article(payload.get('other_id'), mark_read=False)
        # Literal excerpt comparison, explicitly not a semantic novelty claim.
        sentences = lambda a: [s.strip() for s in re.split(r'(?<=[.!?؟])\s+|\n+', a.get('text') or a.get('summary') or '') if len(s.strip())>35]
        known = set(sentences(other))
        additions = [s for s in sentences(current) if s not in known][:5]
        return {'excerpts':additions, 'against':{'title':other['title'],'id':other['id']}, 'method':'literal_excerpt_comparison'}
    if action == 'briefing':
        view = payload.get('view', 'catchup')
        if view not in {'catchup', 'five', 'queue', 'topic', 'updates'}: raise Failure('VALIDATION_ERROR', 'Unknown reading view.')
        topic = str(payload.get('topic', ''))[:100]
        rows = store.rows('''SELECT a.id,a.title,a.url,a.summary,a.text,a.published_at,a.discovered_at,a.is_read,s.title AS source_title
            FROM news_articles a JOIN news_subscriptions s ON s.id=a.subscription_id
            WHERE a.workspace_id=? AND a.id NOT IN (SELECT article_id FROM news_article_duplicates)
            ORDER BY coalesce(a.published_at,a.discovered_at) DESC LIMIT 500''', (ws,))
        if view == 'queue':
            rows = []
            for identifier in data['queue']:
                try:
                    a = service.news.article(identifier, mark_read=False)
                    rows.append(a)
                except Failure:
                    continue
        muted = [x['topic'].casefold() for x in data['muted'] if x['until'] > now()]
        results, remaining = [], 5
        for a in rows:
            searchable = ((a.get('title') or '')+' '+(a.get('summary') or '')).casefold()
            if any(x in searchable for x in muted): continue
            if view == 'queue' and a['id'] not in data['queue']: continue
            if view == 'topic' and topic.casefold() not in searchable: continue
            if view in {'catchup','five'} and a['is_read']: continue
            if view == 'catchup' and a['id'] in data.get('catchup_seen', []): continue
            visit = data['visits'].get(a['id'])
            if view == 'updates':
                if not visit or not visit['revision']: continue
                history = service.news.archive.history(a['id'])['revisions']
                if not history or history[0]['id'] == visit['revision']: continue
            minutes = max(1, math.ceil(len((a.get('text') or a.get('summary') or '').split())/220))
            if view == 'five':
                if minutes > remaining: continue
                remaining -= minutes
            summary = service.news_digest.preview(a['id']) or {}
            results.append({k:a.get(k) for k in ('id','title','url','published_at','source_title')} | {'summary':(a.get('summary') or '')[:1500], 'reading_minutes':minutes, 'saved_summary':summary.get('summary', '')[:6000]})
            if len(results)>=20 or (view=='five' and remaining<=0): break
        if view == 'topic': results.reverse()
        if view == 'queue': results.sort(key=lambda a:data['queue'].index(a['id']))
        return {'articles':results, 'scope':'Latest 500 saved articles', 'state':public_state(data)}
    return public_state(data)
