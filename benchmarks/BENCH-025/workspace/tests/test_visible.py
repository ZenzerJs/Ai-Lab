from eval import run


def test_run_smoke():
    assert run("1 + 2") == [3]


def test_assignment_smoke():
    assert run("x = 5; x") == [5, 5]
