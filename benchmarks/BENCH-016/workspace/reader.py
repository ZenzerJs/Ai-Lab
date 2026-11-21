"""Streaming CSV/JSONL readers yielding RawRecord instances."""
import csv
import json

from models import RawRecord


def iter_jsonl(stream):
    for line_no, line in enumerate(stream, 1):
        data = json.loads(line.strip())
        if not isinstance(data, dict):
            yield RawRecord(line_no, data, "not_object")
            continue
        yield RawRecord(line_no, data)


def iter_csv(stream):
    reader = csv.DictReader(stream)
    for line_no, row in enumerate(reader, 1):
        yield RawRecord(line_no, dict(row))
