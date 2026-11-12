"""Run with the pilot stopped: python -m sreboard.migrate DB --backup NEW_FILE."""
import argparse
import json
import sqlite3
from pathlib import Path
from sreboard.schema import preflight, create_tables, COLUMNS, VERSION


def connect(path):
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db


def migrate(path, backup):
    path, backup = Path(path).resolve(), Path(backup).resolve()
    if not path.is_file() or path == backup:
        raise ValueError('Existing database and distinct new backup file required')
    db = connect(path)
    try:
        preflight(db)
        # Exclusive creation preserves every existing backup, including failed ones.
        with backup.open('xb'):
            pass
        copy = connect(backup)
        try:
            db.backup(copy)
            if copy.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Backup failed integrity check')
            saved = preflight(copy)
        finally:
            copy.close()
        db.execute('BEGIN IMMEDIATE')
        original = preflight(db)
        if original != saved:
            raise ValueError('Database changed after backup; stop writers and retry with a new backup')
        create_tables(db, '_v1')
        for table, columns in COLUMNS.items():
            names = ','.join(columns)
            db.execute(f'INSERT INTO {table}_v1 ({names}) SELECT {names} FROM {table}')
        db.execute('DROP TABLE history')
        db.execute('DROP TABLE alerts')
        db.execute('ALTER TABLE alerts_v1 RENAME TO alerts')
        db.execute('ALTER TABLE history_v1 RENAME TO history')
        if db.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Foreign-key validation failed')
        for index, table in enumerate(COLUMNS):
            order = 'id' if table == 'alerts' else 'seq'
            actual = [dict(r) for r in db.execute(f'SELECT * FROM {table} ORDER BY {order}')]
            if actual != original[index]:
                raise ValueError('Migrated content differs from the backup')
        db.execute(f'PRAGMA user_version={VERSION}')
        db.commit()
        return {'schema_version':VERSION, 'alerts':len(original[0]),
                'history':len(original[1]), 'backup':str(backup)}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database')
    parser.add_argument('--backup', required=True)
    args = parser.parse_args()
    print(json.dumps(migrate(args.database, args.backup)))
