"""Real SQLite persistence for the local SRE Board pilot; contract D1-D5/D7/D9."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4
from sreboard.schema import initialize


class Problem(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)


def normalized(data):
    limits = {'event_id': 128, 'title': 200, 'pipeline': 120, 'severity': 2}
    if not isinstance(data, dict) or set(data) != set(limits):
        raise Problem(400, 'Required fields: event_id, title, pipeline, severity')
    result = {}
    for field, limit in limits.items():
        value = data[field]
        if not isinstance(value, str) or not 1 <= len(value.strip()) <= limit:
            raise Problem(400, f'Invalid {field}')
        value = value.strip()
        if not value.isprintable():
            raise Problem(400, f'Non-printable character in {field}')
        result[field] = value
    if result['severity'] not in ('P1', 'P2', 'P3', 'P4'):
        raise Problem(400, 'Severity must be P1, P2, P3 or P4')
    return result


class Store:
    def __init__(self, path):
        self.path = str(path)
        with self.connection() as db:
            initialize(db)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def create(self, data):
        data = normalized(data)
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            prior = db.execute('SELECT * FROM alerts WHERE event_id=?',
                               (data['event_id'],)).fetchone()
            if prior:
                if any(prior[k] != v for k, v in data.items()):
                    raise Problem(409, 'event_id already exists with different content')
                return dict(prior), True
            now = datetime.now(timezone.utc).isoformat()
            item = dict(id=str(uuid4()), **data, state='New', version=1,
                        created_at=now, updated_at=now)
            db.execute('INSERT INTO alerts VALUES (?,?,?,?,?,?,?,?,?)', tuple(item.values()))
            db.execute('INSERT INTO history(alert_id,to_state,version,at) VALUES (?,?,?,?)',
                       (item['id'], 'New', 1, now))
            return item, False

    def active(self, resolved=False):
        with self.connection() as db:
            db.execute('BEGIN')
            predicate = "state='Resolved'" if resolved else "state!='Resolved'"
            ordering = 'updated_at' if resolved else 'created_at'
            rows = db.execute(f'SELECT * FROM alerts WHERE {predicate} '
                              f'ORDER BY {ordering} DESC,id DESC LIMIT 500').fetchall()
            total = db.execute(f'SELECT COUNT(*) FROM alerts WHERE {predicate}').fetchone()[0]
            return dict(alerts=[dict(row) for row in rows], total=total,
                        truncated=total > len(rows))

    def detail(self, alert_id):
        with self.connection() as db:
            db.execute('BEGIN')
            row = db.execute('SELECT * FROM alerts WHERE id=?', (alert_id,)).fetchone()
            if not row:
                raise Problem(404, 'Alert not found')
            history = db.execute('SELECT from_state,to_state,version,at FROM history '
                                 'WHERE alert_id=? ORDER BY seq', (alert_id,)).fetchall()
            return dict(alert=dict(row), history=[dict(h) for h in history])

    def transition(self, alert_id, data):
        if not isinstance(data, dict) or set(data) != {'state', 'version'}:
            raise Problem(400, 'Required fields: state, version')
        if type(data['version']) is not int or data['version'] < 1 or not isinstance(data['state'], str):
            raise Problem(400, 'Invalid state or version')
        path = {'New': 'Acknowledge', 'Acknowledge': 'Investigating',
                'Investigating': 'Monitoring', 'Monitoring': 'Resolved'}
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM alerts WHERE id=?', (alert_id,)).fetchone()
            if not row:
                raise Problem(404, 'Alert not found')
            if row['version'] != data['version']:
                raise Problem(409, 'Stale version; refresh before retrying')
            if path.get(row['state']) != data['state']:
                raise Problem(409, 'Only the next sequential state is allowed')
            now = datetime.now(timezone.utc).isoformat()
            db.execute('UPDATE alerts SET state=?,version=version+1,updated_at=? WHERE id=?',
                       (data['state'], now, alert_id))
            db.execute('INSERT INTO history(alert_id,from_state,to_state,version,at) '
                       'VALUES (?,?,?,?,?)', (alert_id, row['state'], data['state'],
                                              row['version'] + 1, now))
            return dict(row, state=data['state'], version=row['version'] + 1, updated_at=now)
