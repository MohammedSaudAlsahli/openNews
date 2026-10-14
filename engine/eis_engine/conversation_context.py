"""Bounded, replayable context over the application's authoritative session history.

Agno receives one frozen history window, never a second auto-injected history.
Older messages remain queryable through a session-scoped tool, including on retry.
"""
import json
from .storage import encode

HISTORY_BYTES = 32000


class ConversationContext:
    def __init__(self, store, workspace, conversation, through=None):
        self.store, self.workspace, self.conversation = store, workspace, conversation
        row = store.one('SELECT max(rowid) AS marker FROM chat_messages WHERE workspace_id=? AND conversation_id=?', (workspace, conversation))
        self.through = through if through is not None else (row['marker'] or 0)

    def snapshot(self):
        scope = (self.workspace, self.conversation, self.through)
        total = self.store.one('SELECT count(*) AS count FROM chat_messages WHERE workspace_id=? AND conversation_id=? AND rowid<=?', scope)['count']
        rows = self.store.rows('SELECT role,content,citations_json FROM chat_messages WHERE workspace_id=? AND conversation_id=? AND rowid<=? ORDER BY rowid DESC LIMIT 16', scope)
        history, size, shortened = [], 0, False
        for row in rows:
            message = {'role': row['role'], 'content': row['content'], 'citations': json.loads(row['citations_json'])}
            cost = len(encode(message).encode('utf-8'))
            if size + cost > HISTORY_BYTES:
                if history: break
                # Preserve a useful recent excerpt and explicitly disclose it.
                message['citations'] = message['citations'][:4]
                message['content'] = row['content'].encode('utf-8')[:8000].decode('utf-8', errors='ignore')
                message['truncated'] = True
                shortened = True
                cost = len(encode(message).encode('utf-8'))
            history.append(message)
            size += cost
        return {'history': list(reversed(history)), 'through': self.through,
                'context_info': {'total_messages': total, 'included_messages': len(history),
                                 'history_bytes': size, 'history_budget_bytes': HISTORY_BYTES,
                                 'has_older_context': total > len(history) or shortened}}

    def search(self, query='', before_message_id=''):
        """Return exact historical excerpts, never generated or cross-session memories."""
        marker = self.through + 1
        if before_message_id:
            row = self.store.one('SELECT rowid FROM chat_messages WHERE workspace_id=? AND conversation_id=? AND id=? AND rowid<=?',
                                 (self.workspace, self.conversation, before_message_id, self.through))
            if not row: return {'error': 'Unknown message in this conversation.'}
            marker = row['rowid']
        rows = self.store.rows('SELECT id,role,content,citations_json,created_at FROM chat_messages WHERE workspace_id=? AND conversation_id=? AND rowid<? AND instr(lower(content),lower(?))>0 ORDER BY rowid DESC LIMIT 9',
                               (self.workspace, self.conversation, marker, query[:200]))
        messages = []
        for row in rows[:8]:
            content = row['content']
            index = content.casefold().find(query.casefold()) if query else 0
            start = max(0, index - 600)
            messages.append({**row, 'content': content[start:start+1800], 'truncated': start > 0 or len(content) > 1800,
                             'citations': json.loads(row.pop('citations_json'))[:4]})
            messages[-1].pop('citations_json', None)
        return {'messages': list(reversed(messages)), 'has_more': len(rows) > 8,
                'next_before_message_id': rows[7]['id'] if len(rows) > 8 else None,
                'scope': 'This conversation only. Exact excerpts, not verified factual evidence. Use citations to reread sources.'}
