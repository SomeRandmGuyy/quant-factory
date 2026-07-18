import numpy as np
from quant_lab.backtesting.metrics import historical_var, historical_cvar


def test_cvar_not_worse_than_var():
    returns = np.array([-0.05, -0.02, 0.01, 0.02, -0.08, 0.0, 0.01, -0.03])
    var = historical_var(returns, alpha=0.95)
    cvar = historical_cvar(returns, alpha=0.95)
    assert cvar <= var + 1e-12
    assert var <= 0
    assert cvar <= 0


def test_var_empty():
    assert historical_var([]) == 0.0
