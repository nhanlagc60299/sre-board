import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from sreboard.server import make_server

WEBHOOK = 'test-webhook-only-credential'
OPERATOR = 'test-operator-only-credential'


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.server = make_server(Path(self.tmp.name) / 'test.sqlite', WEBHOOK, OPERATOR)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'
        self.payload = dict(event_id='http-1', title='ETL delayed', pipeline='orders', severity='P2')

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def request(self, path, data=None, token=OPERATOR, raw=None, content_type='application/json'):
        body = raw if raw is not None else json.dumps(data).encode() if data is not None else None
        headers = {'Content-Type': content_type}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        request = Request(self.url + path, body, headers)
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as exc:
            response = exc
        with response:
            return response.status, json.loads(response.read())

    def test_real_http_create_duplicate_active_history(self):
        code, created = self.request('/api/webhook', self.payload, WEBHOOK)
        self.assertEqual(201, code)
        item = created['alert']
        self.assertFalse(created['duplicate'])
        self.assertEqual(200, self.request('/api/webhook', self.payload, WEBHOOK)[0])
        self.assertEqual(1, len(self.request('/api/alerts')[1]['alerts']))
        for version, state in enumerate(['Acknowledge', 'Investigating', 'Monitoring', 'Resolved'], 1):
            code, body = self.request(f"/api/alerts/{item['id']}/state", dict(state=state, version=version))
            self.assertEqual(200, code)
            self.assertEqual('P2', body['alert']['severity'])
        self.assertEqual([], self.request('/api/alerts')[1]['alerts'])
        code, detail = self.request('/api/alerts/' + item['id'])
        self.assertEqual(200, code)
        self.assertEqual(['New', 'Acknowledge', 'Investigating', 'Monitoring', 'Resolved'],
                         [h['to_state'] for h in detail['history']])
        self.assertEqual('Resolved', self.request('/api/webhook', self.payload, WEBHOOK)[1]['alert']['state'])

    def test_authentication_separates_ingestion_and_operator(self):
        for token in [None, 'wrong', OPERATOR]:
            self.assertEqual(401, self.request('/api/webhook', self.payload, token)[0])
        for token in [None, 'wrong', WEBHOOK]:
            self.assertEqual(401, self.request('/api/alerts', token=token)[0])
        self.assertEqual([], self.request('/api/alerts')[1]['alerts'])
        self.assertEqual(200, self.request('/health', token=None)[0])

    def test_invalid_json_body_media_and_field_types(self):
        for raw in [b'{', b'null', b'[]', b'{"a":1,"a":2}', b'{"a":NaN}']:
            self.assertEqual(400, self.request('/api/webhook', token=WEBHOOK, raw=raw)[0])
        self.assertEqual(413, self.request('/api/webhook', token=WEBHOOK, raw=b'x' * 16385)[0])
        self.assertEqual(415, self.request('/api/webhook', self.payload, WEBHOOK, content_type='text/plain')[0])
        self.assertEqual(400, self.request('/api/webhook', dict(self.payload, severity=2), WEBHOOK)[0])
        self.assertEqual(0, self.request('/api/alerts')[1]['total'])

    def test_conflicts_missing_and_stale_updates_do_not_mutate_history(self):
        item = self.request('/api/webhook', self.payload, WEBHOOK)[1]['alert']
        endpoint = f"/api/alerts/{item['id']}/state"
        self.assertEqual(409, self.request(endpoint, dict(state='Resolved', version=1))[0])
        self.assertEqual(200, self.request(endpoint, dict(state='Acknowledge', version=1))[0])
        self.assertEqual(409, self.request(endpoint, dict(state='Investigating', version=1))[0])
        self.assertEqual(409, self.request('/api/webhook', dict(self.payload, title='Changed'), WEBHOOK)[0])
        self.assertEqual(2, len(self.request('/api/alerts/' + item['id'])[1]['history']))
        self.assertEqual(404, self.request('/api/alerts/missing')[0])
        self.assertEqual(404, self.request('/api/alerts/missing/state', dict(state='Acknowledge', version=1))[0])

    def test_configuration_fails_closed(self):
        for a, b in [('', ''), ('short', OPERATOR), (OPERATOR, OPERATOR)]:
            with self.assertRaises(ValueError):
                make_server(Path(self.tmp.name) / 'invalid.sqlite', a, b)
