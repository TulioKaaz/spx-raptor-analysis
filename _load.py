"""Stage 4: persist clean tables for the analysis stage.

Parquet keeps dtypes (dates, nullable integers) intact between stages, which
CSV would lose.
"""

from pathlib import Path

import pandas as pd

from settings import FUNDS, PROCESSED_DIR


def load(fund_quotas: pd.DataFrame, sgs_series: pd.DataFrame) -> list[Path]:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    fund_names = {cnpj: name for name, cnpj in FUNDS.items()}
    fund_quotas = fund_quotas.assign(fund=fund_quotas["cnpj"].map(fund_names))
    outputs = {
        PROCESSED_DIR / "fund_quotas.parquet": fund_quotas,
        PROCESSED_DIR / "sgs_series.parquet": sgs_series,
    }
    for path, frame in outputs.items():
        frame.to_parquet(path, index=False)
    return list(outputs)
