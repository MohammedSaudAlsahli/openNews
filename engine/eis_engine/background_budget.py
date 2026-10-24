"""Persisted processing policy and conservative, fresh native device signals."""
import time
from .contracts import Failure


class BackgroundBudget:
    def __init__(self, store=None):
        self.store = store
        self.updated = 0.0
        self.thermal, self.memory_pressure = 'unknown', 'unknown'
        self.low_power, self.on_battery = False, None
        self.next_at = 0.0
        self.mode, self.index_on_battery, self.paused = 'quiet', False, False
        self.metrics = {}
        if store:
            store.db.execute('''CREATE TABLE IF NOT EXISTS news_local_policy(workspace_id TEXT PRIMARY KEY,
                mode TEXT NOT NULL, index_on_battery INTEGER NOT NULL, paused INTEGER NOT NULL)''')
            row = store.one('SELECT * FROM news_local_policy WHERE workspace_id=?',(store.workspace,))
            if row: self.mode,self.index_on_battery,self.paused = row['mode'],bool(row['index_on_battery']),bool(row['paused'])
            store.db.commit()

    def configure(self, payload):
        if not payload or set(payload)-{'mode','index_on_battery','paused'}:
            raise Failure('VALIDATION_ERROR','Invalid local processing policy.')
        mode = payload.get('mode',self.mode)
        battery, paused = payload.get('index_on_battery',self.index_on_battery),payload.get('paused',self.paused)
        if mode not in {'quiet','balanced'} or type(battery) is not bool or type(paused) is not bool:
            raise Failure('VALIDATION_ERROR','Invalid local processing policy.')
        if self.store:
            with self.store.db:
                self.store.db.execute('INSERT OR REPLACE INTO news_local_policy VALUES(?,?,?,?)',
                    (self.store.workspace,mode,int(battery),int(paused)))
        self.mode,self.index_on_battery,self.paused = mode,battery,paused
        return self.status()

    def update(self, payload):
        thermal, low_power = payload.get('thermal'), payload.get('low_power')
        pressure, battery = payload.get('memory_pressure','unknown'),payload.get('on_battery')
        if thermal not in {'nominal','fair','serious','critical','unknown'} or type(low_power) is not bool or pressure not in {'normal','warning','critical','unknown'} or battery is not None and type(battery) is not bool:
            raise Failure('VALIDATION_ERROR', 'Invalid device energy state.')
        self.thermal,self.low_power,self.memory_pressure,self.on_battery = thermal,low_power,pressure,battery
        self.updated = time.monotonic()
        return self.status()

    def phase(self):
        if self.paused: return 'paused'
        if time.monotonic()-self.updated > 30 or self.thermal=='unknown' or self.memory_pressure=='unknown' or self.on_battery is None:
            return 'waiting_device'
        if self.memory_pressure!='normal': return 'memory_pressure'
        if self.thermal in {'serious','critical'} or self.thermal=='fair' and self.mode=='quiet': return 'cooling'
        if self.low_power: return 'low_power'
        if self.on_battery and not self.index_on_battery: return 'waiting_charger'
        if time.monotonic()<self.next_at: return 'resting'
        return ''

    @property
    def batch_size(self):
        return 4 if self.mode=='quiet' else 12

    def finished(self, elapsed):
        # Bounded duty cycle without unloading/reloading between every small batch.
        rest = min(8,max(.5,elapsed)) if self.mode=='quiet' else min(2,max(.1,elapsed*.25))
        self.next_at = time.monotonic()+rest
        self.metrics.update(last_batch_ms=round(elapsed*1000),rest_ms=round(rest*1000))

    def status(self):
        return {'mode':self.mode,'index_on_battery':self.index_on_battery,'paused':self.paused,
            'phase':self.phase() or 'ready','thermal':self.thermal,'low_power':self.low_power,
            'on_battery':self.on_battery,'memory_pressure':self.memory_pressure,'metrics':dict(self.metrics)}
