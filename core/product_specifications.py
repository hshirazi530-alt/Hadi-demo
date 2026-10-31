"""Extract display-only feature rows from the existing CKEditor field.

The original HTML remains stored unchanged. This parser never returns HTML.
"""
from html.parser import HTMLParser
import re


class _SpecificationsParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.tag = None
        self.text = []
        self.in_table = False
        self.in_row = False
        self.cell = None
        self.cells = []
        self.ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.ignored += 1
            return
        if self.ignored:
            return
        if tag == 'table': self.in_table = True
        elif tag == 'tr' and self.in_table: self.in_row, self.cells = True, []
        elif tag in ('td', 'th') and self.in_row: self.cell = []
        elif tag in ('li', 'p') and not self.in_table and not self.tag:
            self.tag, self.text = tag, []
        elif tag == 'br':
            if self.cell is not None: self.cell.append(' ')
            elif self.tag: self.text.append(' ')

    def handle_data(self, data):
        if self.ignored: return
        if self.cell is not None: self.cell.append(data)
        elif self.tag: self.text.append(data)

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.ignored:
            self.ignored -= 1
            return
        if self.ignored: return
        if tag in ('td', 'th') and self.cell is not None:
            self.cells.append(self.clean(''.join(self.cell)))
            self.cell = None
        elif tag == 'tr' and self.in_row:
            if len(self.cells) >= 2 and self.cells[0] and any(self.cells[1:]):
                self.rows.append((self.cells[0], '، '.join(x for x in self.cells[1:] if x)))
            self.in_row = False
        elif tag == 'table': self.in_table = False
        elif self.tag == tag:
            text = self.clean(''.join(self.text))
            if text:
                parts = re.split(r'\s*[:：]\s*', text, maxsplit=1)
                if len(parts) == 2 and parts[0] and parts[1] and len(parts[0]) <= 80:
                    self.rows.append((parts[0], parts[1]))
                else: self.rows.append(('ویژگی', text))
            self.tag, self.text = None, []

    @staticmethod
    def clean(value): return re.sub(r'\s+', ' ', value).strip()


def specification_rows(value):
    if not value: return []
    parser = _SpecificationsParser()
    parser.feed(str(value))
    if not parser.rows and '<' not in str(value):
        for line in str(value).splitlines():
            line = line.strip()
            if line:
                parts = re.split(r'\s*[:：]\s*', line, maxsplit=1)
                parser.rows.append((parts[0], parts[1]) if len(parts) == 2 and all(parts) else ('ویژگی', line))
    return [{'label': label, 'value': text} for label, text in parser.rows]
