import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from sreboard.store import Store
from sreboard.migrate import migrate

LEGACY = '''CREATE TABLE alerts(id TEXT PRIMARY KEY,event_id TEXT NOT NULL UNIQUE,
title TEXT NOT NULL,pipeline TEXT NOT NULL,severity TEXT NOT NULL,state TEXT NOT NULL,
version INTEGER NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE history(seq INTEGER PRIMARY KEY,alert_id TEXT NOT NULL,from_state TEXT,
to_state TEXT NOT NULL,version INTEGER NOT NULL,at TEXT NOT NULL);'''


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'legacy.sqlite'
        self.backup = Path(self.tmp.name)/'backup.sqlite'
        with sqlite3.connect(self.path) as db:
            db.executescript(LEGACY)
            db.execute("INSERT INTO alerts VALUES ('a','event','Title','orders','P1','New',1,'2026-11-11T00:00:00+00:00','2026-11-11T00:00:00+00:00')")
            db.execute("INSERT INTO history VALUES (1,'a',NULL,'New',1,'2026-11-11T00:00:00+00:00')")

    def test_legacy_requires_explicit_upgrade_and_backup_restores_original(self):
        with self.assertRaises(RuntimeError):
            Store(self.path)
        result = migrate(self.path, self.backup)
        self.assertEqual((1,1,1), (result['schema_version'],result['alerts'],result['history']))
        self.assertEqual(1, Store(self.path).detail('a')['alert']['version'])
        with sqlite3.connect(self.backup) as db:
            self.assertEqual(0, db.execute('PRAGMA user_version').fetchone()[0])
            self.assertEqual(('a','event','Title','orders','P1','New',1,'2026-11-11T00:00:00+00:00','2026-11-11T00:00:00+00:00'),
                             db.execute('SELECT * FROM alerts').fetchone())
        restored = Path(self.tmp.name)/'restored.sqlite'
        with sqlite3.connect(self.backup) as source, sqlite3.connect(restored) as dest:
            source.backup(dest)
        self.assertEqual(1, migrate(restored, Path(self.tmp.name)/'restore-backup.sqlite')['alerts'])

    def test_invalid_data_and_existing_backup_are_not_silently_repaired(self):
        self.backup.write_bytes(b'preserve me')
        with self.assertRaises(FileExistsError):
            migrate(self.path,self.backup)
        self.assertEqual(b'preserve me',self.backup.read_bytes())
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO history VALUES (2,'orphan',NULL,'New',1,'2026-11-11T00:00:00+00:00')")
        with self.assertRaises(ValueError):
            migrate(self.path,Path(self.tmp.name)/'other.sqlite')
        with sqlite3.connect(self.path) as db:
            self.assertEqual(2,db.execute('SELECT COUNT(*) FROM history').fetchone()[0])
            self.assertEqual(0,db.execute('PRAGMA user_version').fetchone()[0])

    def test_failure_during_copy_rolls_back_schema_and_data(self):
        from sreboard.schema import create_tables
        def fail_after_create(db, suffix):
            create_tables(db,suffix)
            raise RuntimeError('controlled migration failure')
        with patch('sreboard.migrate.create_tables',side_effect=fail_after_create):
            with self.assertRaises(RuntimeError):
                migrate(self.path,self.backup)
        with sqlite3.connect(self.path) as db:
            self.assertEqual({'alerts','history'}, {r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")})
            self.assertEqual(1,db.execute('SELECT COUNT(*) FROM alerts').fetchone()[0])
            self.assertEqual(0,db.execute('PRAGMA user_version').fetchone()[0])

    def test_database_rejects_orphan_duplicate_version_and_invalid_columns(self):
        migrate(self.path,self.backup)
        store = Store(self.path)
        statements = ["INSERT INTO history VALUES (2,'missing',NULL,'New',1,'2026-11-11T00:00:00+00:00')",
                      "INSERT INTO history VALUES (2,'a',NULL,'New',1,'2026-11-11T00:00:00+00:00')",
                      "UPDATE alerts SET severity='P0'", "UPDATE alerts SET state='Invalid'",
                      "UPDATE alerts SET version=0", "UPDATE alerts SET id=NULL"]
        for sql in statements:
            with self.subTest(sql=sql):
                with self.assertRaises(sqlite3.IntegrityError):
                    with store.connection() as db:
                        db.execute(sql)
        self.assertEqual(1,store.detail('a')['alert']['version'])
