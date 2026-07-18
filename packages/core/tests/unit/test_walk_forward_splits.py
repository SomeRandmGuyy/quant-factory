from datetime import date
from quant_lab.backtesting.walk_forward import generate_splits


def test_generate_rolling_splits_no_overlap_issues():
    splits = generate_splits(
        date(2020, 1, 1),
        date(2020, 12, 31),
        train_days=30,
        test_days=10,
        step_days=10,
        mode="rolling",
    )
    assert len(splits) >= 1
    for s in splits:
        assert s.train_end < s.test_start
        assert s.test_start <= s.test_end


def test_expanding_train_grows():
    splits = generate_splits(
        date(2020, 1, 1),
        date(2020, 6, 30),
        train_days=20,
        test_days=10,
        step_days=15,
        mode="expanding",
    )
    assert len(splits) >= 2
    assert splits[0].train_start == splits[1].train_start
    assert splits[1].train_end > splits[0].train_end


def test_empty_range_raises():
    try:
        generate_splits(date(2020, 1, 1), date(2020, 1, 1), train_days=10, test_days=5, step_days=5)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
