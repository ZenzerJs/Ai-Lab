"""Row routing: valid rows pass through, failures are skipped."""
from models import PipelineResult, Summary


class Pipeline:
    def __init__(self, transformer):
        self.transformer = transformer

    def run(self, records):
        rows = []
        dead = []
        for record in records:
            if record.error is not None:
                continue
            try:
                clean, error = self.transformer.transform(record.data)
            except Exception:
                continue
            if error is not None:
                continue
            rows.append(clean)
        summary = Summary(len(rows), len(rows), len(dead))
        return PipelineResult(rows, dead, summary)
