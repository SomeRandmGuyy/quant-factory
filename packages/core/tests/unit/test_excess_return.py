from quant_lab.backtesting.benchmark import excess_return, total_return


def test_excess_return():
    strategy = [100.0, 110.0]
    bench = [100.0, 105.0]
    assert abs(excess_return(strategy, bench) - 0.05) < 1e-9


def test_total_return():
    assert abs(total_return([100, 120]) - 0.2) < 1e-9
