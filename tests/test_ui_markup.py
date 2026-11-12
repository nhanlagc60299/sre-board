import unittest
from html.parser import HTMLParser
from pathlib import Path


class MarkupTests(unittest.TestCase):
    def test_severity_filter_has_exactly_five_valid_options(self):
        class Options(HTMLParser):
            def __init__(self):
                super().__init__()
                self.in_filter = False
                self.current = None
                self.options = []
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == 'select':
                    self.in_filter = attrs.get('id') == 'severity'
                if tag == 'option' and self.in_filter:
                    self.current = [attrs.get('value'), '']
            def handle_data(self, text):
                if self.current is not None:
                    self.current[1] += text
            def handle_endtag(self, tag):
                if tag == 'option' and self.current is not None:
                    self.options.append(tuple(self.current))
                    self.current = None
                if tag == 'select':
                    self.in_filter = False
        parsed = Options()
        parsed.feed((Path(__file__).resolve().parents[1] / 'static/index.html').read_text())
        self.assertEqual([('', 'All severities'), ('P1','P1'), ('P2','P2'),
                          ('P3','P3'), ('P4','P4')], parsed.options)
