"""Protected deterministic checks for BENCH-016."""
import io
import sys


def rejected(error, callback):
    try:
        callback()
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def run_checks():
    try:
        from models import DeadLetter, PipelineResult, RawRecord, Summary
        from reader import iter_csv, iter_jsonl
        from transformer import Transformer
        from pipeline import Pipeline
    except Exception as exc:
        fail("import_error", exc)

    def model_checks():
        assert RawRecord(1, {"a": 1}).error is None
        assert RawRecord(2).data is None
        for line_no in (0, -1, True, "1", 1.0):
            rejected(ValueError, lambda: RawRecord(line_no))
            rejected(ValueError, lambda: DeadLetter(line_no, "e", None))
        rejected(ValueError, lambda: RawRecord(1, None, 5))
        rejected(ValueError, lambda: DeadLetter(1, "", None))
        rejected(ValueError, lambda: DeadLetter(1, 7, None))
        assert DeadLetter(3, "bad", {"x": 1}).raw == {"x": 1}
        assert Summary(4, 3, 1).total == 4
        Summary(0, 0, 0)
        for values in ((3, 3, 1), (4, 3, 0), (5, 3, 3)):
            rejected(ValueError, lambda: Summary(*values))
        for values in ((-1, 0, 0), (1, -1, 2), (True, 1, 0), ("3", 3, 0)):
            rejected(ValueError, lambda: Summary(*values))
        result = PipelineResult([{"a": 1}], [DeadLetter(2, "e", None)], Summary(2, 1, 1))
        assert isinstance(result.rows, tuple) and isinstance(result.dead_letters, tuple)
        rejected(ValueError, lambda: PipelineResult([], [], Summary(1, 0, 0)))
        rejected(ValueError, lambda: PipelineResult([5], [], Summary(1, 1, 0)))
        rejected(ValueError, lambda: PipelineResult([], ["x"], Summary(1, 0, 1)))
        rejected(ValueError, lambda: PipelineResult([], [], "x"))

    def reader_checks():
        stream = io.StringIO(
            '{"a": 1}\n\n   \nnot json\n[1, 2]\n{"b": 2}\n"str"\n'
            '{"x": NaN}\n{"y": Infinity}\n')
        records = list(iter_jsonl(stream))
        assert [(r.line_no, r.error) for r in records] == [
            (1, None), (4, "invalid_json"), (5, "not_object"),
            (6, None), (7, "not_object"), (8, "invalid_json"),
            (9, "invalid_json"),
        ]
        assert records[0].data == {"a": 1}
        assert records[1].data == "not json"
        assert records[2].data == [1, 2]
        assert records[3].data == {"b": 2}
        assert list(iter_jsonl(io.StringIO(""))) == []
        assert list(iter_jsonl(io.StringIO("\n\n"))) == []
        records = list(iter_jsonl(iter(['{"x": 1}\n', 'bad\n'])))
        assert [r.line_no for r in records] == [1, 2]
        stream = io.StringIO("name,count\na,2\nb,\nc,5\n")
        records = list(iter_csv(stream))
        assert [(r.line_no, r.data) for r in records] == [
            (2, {"name": "a", "count": "2"}),
            (3, {"name": "b", "count": ""}),
            (4, {"name": "c", "count": "5"}),
        ]
        assert list(iter_csv(io.StringIO("name\n"))) == []

    def transformer_checks():
        t = Transformer({"name": "str", "count": "int", "ratio": "float"})
        clean, err = t.transform({"name": "a", "count": "42", "ratio": 1, "extra": "x"})
        assert err is None and clean == {"name": "a", "count": 42, "ratio": 1.0}
        clean, err = t.transform({"name": "a", "count": "-7", "ratio": "0.5"})
        assert clean == {"name": "a", "count": -7, "ratio": 0.5}
        for data, expected in (
            ({"name": "a", "count": True, "ratio": 1.0}, "bad_type:count"),
            ({"name": "a", "count": 1.5, "ratio": 1.0}, "bad_type:count"),
            ({"name": "a", "count": "x", "ratio": 1.0}, "bad_type:count"),
            ({"name": "a", "count": "4.5", "ratio": 1.0}, "bad_type:count"),
            ({"name": "a", "count": 1, "ratio": "nan"}, "bad_type:ratio"),
            ({"name": "a", "count": 1, "ratio": "inf"}, "bad_type:ratio"),
            ({"name": "a", "count": 1, "ratio": float("inf")}, "bad_type:ratio"),
            ({"name": "a", "count": 1, "ratio": True}, "bad_type:ratio"),
            ({"name": "a", "count": 1, "ratio": 10 ** 400}, "bad_type:ratio"),
            ({"name": 5, "count": 1, "ratio": 1.0}, "bad_type:name"),
            ({"name": "a", "ratio": 1.0}, "missing_field:count"),
            ({"name": "a", "count": None, "ratio": 1.0}, "missing_field:count"),
        ):
            clean, err = t.transform(data)
            assert clean is None and err == expected, (data, err)
        clean, err = t.transform([1, 2])
        assert (clean, err) == (None, "not_mapping")
        clean, err = Transformer({"s": "str"}).transform({"s": "", "x": 1})
        assert clean == {"s": ""}
        clean, err = Transformer({"f": "float"}).transform({"f": "2"})
        assert clean == {"f": 2.0}
        rejected(ValueError, lambda: Transformer({"a": "date"}))
        rejected(ValueError, lambda: Transformer({"": "str"}))
        rejected(ValueError, lambda: Transformer({"a": 1}))

    def pipeline_checks():
        t = Transformer({"name": "str", "count": "int"})
        stream = io.StringIO(
            '{"name": "a", "count": "3"}\nbad line\n{"name": "b"}\n'
            '{"name": "c", "count": 5, "extra": 1}\n[9]\n')
        result = Pipeline(t).run(iter_jsonl(stream))
        assert result.rows == (
            {"name": "a", "count": 3}, {"name": "c", "count": 5})
        assert [d.line_no for d in result.dead_letters] == [2, 3, 5]
        assert result.dead_letters[0].error == "invalid_json"
        assert result.dead_letters[1].error == "missing_field:count"
        assert result.dead_letters[2].error == "not_object"
        assert result.dead_letters[1].raw == {"name": "b"}
        assert (result.summary.total, result.summary.processed,
                result.summary.dead_lettered) == (5, 2, 3)
        result = Pipeline(t).run(iter_csv(io.StringIO("name,count\na,2\nb,x\n")))
        assert result.rows == ({"name": "a", "count": 2},)
        assert result.dead_letters[0].error == "bad_type:count"
        assert (result.summary.processed, result.summary.dead_lettered) == (1, 1)
        result = Pipeline(t).run(iter([RawRecord(1, {"name": "a", "count": 1}),
                                     RawRecord(2, "raw", "parse_fail"),
                                     RawRecord(3, {"name": "b", "count": 2})]))
        assert len(result.rows) == 2 and result.dead_letters[0].error == "parse_fail"
        empty = Pipeline(t).run(iter([]))
        assert (empty.summary.total, empty.summary.processed,
                empty.summary.dead_lettered) == (0, 0, 0)

    for check in (model_checks, reader_checks, transformer_checks, pipeline_checks):
        try:
            check()
        except Exception as exc:
            fail("etl_invariant_violation",
                 f"{check.__name__}: {type(exc).__name__}: {exc}")
    print("ALL CHECKS PASSED")


def fail(reason, detail):
    print(f"REASON: {reason}", file=sys.stderr)
    print(detail, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    run_checks()
