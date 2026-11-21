"""Row routing: valid rows pass through, failures go to dead letters."""
from models import DeadLetter, PipelineResult, Summary


class Pipeline:
    def __init__(self, transformer):
        self.transformer = transformer

    def run(self, records):
        rows = []
        dead = []
        for record in records:
            if record.error is not None:
                dead.append(DeadLetter(record.line_no, record.error, record.data))
                continue
            clean, error = self.transformer.transform(record.data)
            if error is not None:
                dead.append(DeadLetter(record.line_no, error, record.data))
            else:
                rows.append(clean)
        summary = Summary(len(rows) + len(dead), len(rows), len(dead))
        return PipelineResult(rows, dead, summary)
