import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from sreboard.store import Store, Problem


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'alerts.sqlite'
        self.store = Store(self.path)
        self.payload = dict(event_id='evt-1', title='Lag above threshold',
                            pipeline='orders-etl', severity='P1')

    def create(self, **changes):
        return self.store.create(dict(self.payload, **changes))[0]

    def move(self, item, state):
        return self.store.transition(item['id'], dict(state=state, version=item['version']))

    def test_create_and_persist(self):
        item, duplicate = self.store.create(self.payload)
        self.assertFalse(duplicate)
        self.assertEqual(('P1', 'New', 1), (item['severity'], item['state'], item['version']))
        detail = Store(self.path).detail(item['id'])
        self.assertEqual(item, detail['alert'])
        self.assertEqual(['New'], [h['to_state'] for h in detail['history']])

    def test_validation_and_boundaries(self):
        for severity in ['P1', 'P2', 'P3', 'P4']:
            self.create(event_id=severity, severity=severity)
        for key, size in [('event_id', 128), ('title', 200), ('pipeline', 120)]:
            for length in [size - 1, size]:
                self.create(event_id=f'{key}-{length}', **{key: 'x' * length}) if key != 'event_id' else self.create(event_id='x' * length)
            with self.assertRaises(Problem) as ctx:
                self.create(**{key: 'x' * (size + 1)})
            self.assertEqual(400, ctx.exception.status)
        for patch in [{'severity': 'P0'}, {'title': ''}, {'pipeline': 2}, {'title': 'a\nb'}]:
            with self.subTest(patch=patch), self.assertRaises(Problem):
                self.create(**patch)
        for body in [None, [], {}, dict(self.payload, extra='bad')]:
            with self.subTest(body=body), self.assertRaises(Problem):
                self.store.create(body)

    def test_exact_duplicate_conflict_and_resolved_retry(self):
        item = self.create()
        repeat, duplicate = self.store.create(dict(self.payload, title=' Lag above threshold '))
        self.assertTrue(duplicate)
        self.assertEqual(item['id'], repeat['id'])
        with self.assertRaises(Problem) as ctx:
            self.create(severity='P2')
        self.assertEqual(409, ctx.exception.status)
        for state in ['Acknowledge', 'Investigating', 'Monitoring', 'Resolved']:
            item = self.move(item, state)
        repeat, duplicate = self.store.create(self.payload)
        self.assertTrue(duplicate)
        self.assertEqual('Resolved', repeat['state'])
        self.assertEqual(5, len(self.store.detail(item['id'])['history']))
        self.assertEqual([], self.store.active()['alerts'])

    def test_transition_matrix_independent_of_implementation(self):
        states = ['New', 'Acknowledge', 'Investigating', 'Monitoring', 'Resolved']
        allowed = {('New', 'Acknowledge'), ('Acknowledge', 'Investigating'),
                   ('Investigating', 'Monitoring'), ('Monitoring', 'Resolved')}
        for index, source in enumerate(states):
            for target in states:
                with self.subTest(source=source, target=target):
                    item = self.create(event_id=f'{source}-{target}')
                    for earlier in states[1:index + 1]:
                        item = self.move(item, earlier)
                    if (source, target) in allowed:
                        advanced = self.move(item, target)
                        self.assertEqual(('P1', target), (advanced['severity'], advanced['state']))
                    else:
                        before = self.store.detail(item['id'])
                        with self.assertRaises(Problem) as ctx:
                            self.move(item, target)
                        self.assertEqual(409, ctx.exception.status)
                        self.assertEqual(before, self.store.detail(item['id']))

    def test_concurrent_updates_have_one_winner(self):
        item = self.create()
        def act(_):
            try:
                self.move(item, 'Acknowledge')
                return 200
            except Problem as exc:
                return exc.status
        with ThreadPoolExecutor(2) as pool:
            results = sorted(pool.map(act, range(2)))
        self.assertEqual([200, 409], results)
        detail = self.store.detail(item['id'])
        self.assertEqual(2, detail['alert']['version'])
        self.assertEqual(2, len(detail['history']))

    def test_report_preserves_unresolved_low_severity_and_flags_limit(self):
        a = self.create(severity='P4')
        b = self.create(event_id='resolved', severity='P2')
        for state in ['Acknowledge', 'Investigating', 'Monitoring', 'Resolved']:
            b = self.move(b, state)
        self.assertEqual([a['id']], [r['id'] for r in self.store.active()['alerts']])
        for i in range(500):
            self.create(event_id=f'bulk-{i}')
        listing = self.store.active()
        self.assertEqual((500, 501, True), (len(listing['alerts']), listing['total'], listing['truncated']))

    def test_invalid_update_and_not_found(self):
        item = self.create()
        for data in [None, {}, {'state': 'Acknowledge', 'version': True},
                     {'state': [], 'version': 1}]:
            with self.assertRaises(Problem) as ctx:
                self.store.transition(item['id'], data)
            self.assertEqual(400, ctx.exception.status)
        with self.assertRaises(Problem) as ctx:
            self.store.detail('absent')
        self.assertEqual(404, ctx.exception.status)
