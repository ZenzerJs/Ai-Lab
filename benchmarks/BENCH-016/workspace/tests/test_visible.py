import io

from reader import iter_jsonl, iter_csv
from transformer import Transformer
from pipeline import Pipeline


def test_jsonl_smoke():
    stream = io.StringIO('{"name": "a", "count": "3"}\n')
    result = Pipeline(Transformer({"name": "str", "count": "int"})).run(iter_jsonl(stream))
    assert result.summary.processed == 1
    assert result.rows[0] == {"name": "a", "count": 3}


def test_csv_smoke():
    stream = io.StringIO("name,count\na,2\n")
    result = Pipeline(Transformer({"name": "str", "count": "int"})).run(iter_csv(stream))
    assert result.rows[0]["count"] == 2
