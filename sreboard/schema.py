"""Versioned SQLite schema; legacy upgrades are explicit, never startup side effects."""
from datetime import datetime, timedelta

VERSION = 1
COLUMNS = {
    'alerts': ['id', 'event_id', 'title', 'pipeline', 'severity', 'state',
               'version', 'created_at', 'updated_at'],
    'history': ['seq', 'alert_id', 'from_state', 'to_state', 'version', 'at'],
}
STATES = ('New', 'Acknowledge', 'Investigating', 'Monitoring', 'Resolved')


def create_tables(db, suffix=''):
    if suffix not in ('', '_v1'):
        raise ValueError('Unsupported schema suffix')
    statements = [f'''CREATE TABLE alerts{suffix} (
        id TEXT NOT NULL PRIMARY KEY, event_id TEXT NOT NULL UNIQUE
            CHECK(length(event_id) BETWEEN 1 AND 128),
        title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 200),
        pipeline TEXT NOT NULL CHECK(length(pipeline) BETWEEN 1 AND 120),
        severity TEXT NOT NULL CHECK(severity IN ('P1','P2','P3','P4')),
        state TEXT NOT NULL CHECK(state IN {STATES}),
        version INTEGER NOT NULL CHECK(typeof(version)='integer' AND version>0),
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL)''',
        f'''CREATE TABLE history{suffix} (
        seq INTEGER PRIMARY KEY, alert_id TEXT NOT NULL
            REFERENCES alerts{suffix}(id),
        from_state TEXT CHECK(from_state IS NULL OR from_state IN {STATES}),
        to_state TEXT NOT NULL CHECK(to_state IN {STATES}),
        version INTEGER NOT NULL CHECK(typeof(version)='integer' AND version>0),
        at TEXT NOT NULL, UNIQUE(alert_id,version))''']
    for sql in statements:
        db.execute(sql)


def tables(db):
    return {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' "
                                    "AND name NOT LIKE 'sqlite_%'")}


def initialize(db):
    version = db.execute('PRAGMA user_version').fetchone()[0]
    if version == 0 and not tables(db):
        db.execute('BEGIN IMMEDIATE')
        create_tables(db)
        db.execute(f'PRAGMA user_version={VERSION}')
    elif version != VERSION or tables(db) != set(COLUMNS):
        raise RuntimeError('Unsupported or legacy database; run the explicit migration first')


def preflight(db):
    """Reject incompatible legacy rows without changing any value."""
    if db.execute('PRAGMA user_version').fetchone()[0] != 0 or tables(db) != set(COLUMNS):
        raise ValueError('Expected the original two-table version-0 schema')
    for table, columns in COLUMNS.items():
        if [r[1] for r in db.execute(f'PRAGMA table_info({table})')] != columns:
            raise ValueError('Unknown legacy columns')
    if db.execute("SELECT 1 FROM sqlite_master WHERE type IN ('trigger','view') "
                  "OR (type='index' AND sql IS NOT NULL)").fetchone():
        raise ValueError('Unknown legacy schema objects require manual review')
    alerts = [dict(r) for r in db.execute('SELECT * FROM alerts ORDER BY id')]
    history = [dict(r) for r in db.execute('SELECT * FROM history ORDER BY seq')]
    owners = {a['id']: a for a in alerts}
    if len(owners) != len(alerts) or len({a['event_id'] for a in alerts}) != len(alerts):
        raise ValueError('Invalid alert identities')
    for row in history:
        if row['alert_id'] not in owners:
            raise ValueError('Orphan history; no automatic repair')
    for value in [a[k] for a in alerts for k in ('created_at','updated_at')] + [h['at'] for h in history]:
        try:
            if datetime.fromisoformat(value).utcoffset() != timedelta(0):
                raise ValueError('UTC timestamp required')
        except (TypeError, ValueError) as exc:
            raise ValueError('Invalid legacy UTC timestamp') from exc
    for a in alerts:
        if not isinstance(a['id'], str) or not a['id']:
            raise ValueError('Missing alert id')
        for field, limit in [('event_id',128), ('title',200), ('pipeline',120)]:
            value = a[field]
            if (not isinstance(value, str) or not 1 <= len(value) <= limit
                    or value.strip() != value or not value.isprintable()):
                raise ValueError('Invalid legacy text; no automatic normalization')
        if a['severity'] not in ('P1','P2','P3','P4') or a['state'] not in STATES:
            raise ValueError('Invalid legacy severity/state')
        rows = [h for h in history if h['alert_id'] == a['id']]
        expected = list(STATES[:STATES.index(a['state']) + 1])
        if (a['version'] != len(expected) or [h['to_state'] for h in rows] != expected
                or [h['version'] for h in rows] != list(range(1,len(expected)+1))
                or [h['from_state'] for h in rows] != [None] + expected[:-1]
                or not rows or rows[0]['at'] != a['created_at']
                or rows[-1]['at'] != a['updated_at']):
            raise ValueError('Inconsistent legacy history; no automatic repair')
    return alerts, history
