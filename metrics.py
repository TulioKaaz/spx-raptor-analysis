"""Performance and risk metrics on monthly data.

Everything is monthly because Raptor only reported a month-end quota until
2024; daily data would compare a smoothed fund against daily-marked markets.
Returns are before income tax (quotas are net of fees, gross of tax).
"""

import numpy as np
import pandas as pd

from settings import PROCESSED_DIR

WINDOW_START = "2010-11-30"  # base date: funds start at quota 1.0 on 2010-12-01
WINDOW_END = "2026-09-30"  # last month with IPCA published
MONTHS_PER_YEAR = 12
ASSETS = ["raptor_feeder", "nimitz_feeder", "ibovespa_index", "imab_index", "cdi"]


def load_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    quotas = pd.read_parquet(PROCESSED_DIR / "fund_quotas.parquet")
    series = pd.read_parquet(PROCESSED_DIR / "sgs_series.parquet")
    return quotas, series


def sgs(series: pd.DataFrame, name: str) -> pd.Series:
    return series[series["series"] == name].set_index("date")["value"]


def monthly_index(quotas: pd.DataFrame, series: pd.DataFrame) -> pd.DataFrame:
    """Month-end index levels for every asset, CDI and IPCA, rebased to 1."""
    prices = quotas.pivot(index="date", columns="fund", values="quota")
    month_end = prices.resample("ME").last()
    # The funds' first quota (1.0 on 2010-12-01) is the November base.
    month_end.loc[pd.Timestamp(WINDOW_START)] = prices.loc["2010-12-01"]
    cdi_daily = 1 + sgs(series, "cdi_daily_pct") / 100
    month_end["cdi"] = cdi_daily.cumprod().resample("ME").last()
    ipca = 1 + sgs(series, "ipca_monthly_pct") / 100
    ipca.index = ipca.index + pd.offsets.MonthEnd(0)
    month_end["ipca"] = ipca.cumprod()
    window = month_end.sort_index().loc[WINDOW_START:WINDOW_END]
    return window / window.iloc[0]


def real_index(index: pd.DataFrame) -> pd.DataFrame:
    """Purchasing power (Fisher): nominal index divided by the IPCA index."""
    return index[ASSETS].div(index["ipca"], axis=0)


def annualized_return(index: pd.Series) -> float:
    years = (len(index) - 1) / MONTHS_PER_YEAR
    return (index.iloc[-1] / index.iloc[0]) ** (1 / years) - 1


def max_drawdown(index: pd.Series) -> dict:
    drawdown = index / index.cummax() - 1
    trough = drawdown.idxmin()
    peak = index.loc[:trough].idxmax()
    recovered = index.loc[trough:][index.loc[trough:] >= index.loc[peak]]
    recovery = recovered.index[0] if not recovered.empty else None
    return {
        "max_drawdown": drawdown.min(),
        "peak": peak.date(),
        "trough": trough.date(),
        "recovery": recovery.date() if recovery is not None else "not recovered",
    }


def risk_table(index: pd.DataFrame) -> pd.DataFrame:
    returns = index.pct_change().dropna()
    excess = returns.sub(returns["cdi"], axis=0)
    real = real_index(index)
    rows = {}
    for asset in ASSETS:
        rows[asset] = {
            "annual_return": annualized_return(index[asset]),
            "annual_real_return": annualized_return(real[asset]),
            "volatility": returns[asset].std() * np.sqrt(MONTHS_PER_YEAR),
            "sharpe": excess[asset].mean() / excess[asset].std() * np.sqrt(MONTHS_PER_YEAR)
            if asset != "cdi"
            else np.nan,
            "worst_12m": index[asset].pct_change(12).min(),
            "months_above_cdi": (excess[asset] > 0).mean() if asset != "cdi" else np.nan,
            **max_drawdown(index[asset]),
        }
    return pd.DataFrame(rows).T


def calendar_excess(index: pd.DataFrame) -> pd.DataFrame:
    """Calendar-year return minus CDI, in percentage points (not "% of CDI")."""
    yearly = index.resample("YE").last()
    yearly.loc[pd.Timestamp(WINDOW_START)] = index.iloc[0]
    returns = yearly.sort_index().pct_change().dropna()
    returns.index = returns.index.year
    return returns[ASSETS].sub(returns["cdi"], axis=0).drop(columns="cdi")


def trailing_windows(index: pd.DataFrame, months: tuple[int, ...] = (12, 36, 60)) -> pd.DataFrame:
    rows = {}
    for length in months:
        rows[f"{length}m"] = index[ASSETS].iloc[-length - 1 :].apply(annualized_return)
    rows["since_inception"] = index[ASSETS].apply(annualized_return)
    return pd.DataFrame(rows)


def correlations(index: pd.DataFrame, series: pd.DataFrame) -> pd.DataFrame:
    returns = index.pct_change().dropna()
    usd = sgs(series, "usdbrl_ptax").resample("ME").last().pct_change()
    returns["usdbrl"] = usd.reindex(returns.index)
    excess = returns.drop(columns=["cdi", "ipca"]).sub(returns["cdi"], axis=0)
    excess["usdbrl"] = returns["usdbrl"]
    return excess.corr().loc[
        ["raptor_feeder", "nimitz_feeder"], ["nimitz_feeder", "ibovespa_index", "imab_index", "usdbrl"]
    ]


def raptor_vs_nimitz(index: pd.DataFrame) -> dict:
    """How many Nimitz is one Raptor: OLS of monthly excess returns over CDI."""
    returns = index.pct_change().dropna()
    raptor = returns["raptor_feeder"] - returns["cdi"]
    nimitz = returns["nimitz_feeder"] - returns["cdi"]
    beta, alpha = np.polyfit(nimitz, raptor, 1)
    r_squared = np.corrcoef(nimitz, raptor)[0, 1] ** 2
    return {
        "beta": beta,
        "alpha_annual": alpha * MONTHS_PER_YEAR,
        "r_squared": r_squared,
        "volatility_ratio": raptor.std() / nimitz.std(),
    }


def stress_months(index: pd.DataFrame, worst: int = 10) -> pd.DataFrame:
    """Fund returns in the Ibovespa's worst months: does it protect in a crash?"""
    returns = index.pct_change().dropna()
    crash_months = returns["ibovespa_index"].nsmallest(worst).index
    table = returns.loc[crash_months, ["ibovespa_index", "raptor_feeder", "nimitz_feeder", "imab_index", "cdi"]]
    table.index = table.index.strftime("%Y-%m")
    return table


def daily_event(quotas: pd.DataFrame, day: str) -> pd.Series:
    prices = quotas.pivot(index="date", columns="fund", values="quota")
    return prices.pct_change().loc[day]


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    pd.set_option("display.float_format", lambda value: f"{value:.4f}")
    quotas, series = load_tables()
    index = monthly_index(quotas, series)
    print("Risk table\n", risk_table(index), "\n")
    print("Calendar excess over CDI (pp)\n", calendar_excess(index), "\n")
    print("Trailing annualized returns\n", trailing_windows(index), "\n")
    print("Correlations of monthly excess returns\n", correlations(index, series), "\n")
    print("Raptor vs Nimitz\n", raptor_vs_nimitz(index), "\n")
    print("Ibovespa's 10 worst months\n", stress_months(index), "\n")
    print("2026-10-26 daily returns\n", daily_event(quotas, "2026-10-26"))
