"""Stage 2: data contracts.

CVM changed the daily report layout with Resolution 175 (fund -> class and
subclass). Both layouts are mapped onto one canonical schema here, and every
frame is validated before it reaches the metrics, so a corrupted file fails
loudly instead of silently skewing a return.
"""

import pandas as pd

CANONICAL_COLUMNS = {
    "cnpj": "string",
    "date": "datetime64[ns]",
    "quota": "float64",
    "net_assets": "float64",
    "inflows": "float64",
    "outflows": "float64",
    "shareholders": "Int64",
}

CVM_COLUMN_ALIASES = {
    "CNPJ_FUNDO": "cnpj",
    "CNPJ_FUNDO_CLASSE": "cnpj",
    "DT_COMPTC": "date",
    "VL_QUOTA": "quota",
    "VL_PATRIM_LIQ": "net_assets",
    "CAPTC_DIA": "inflows",
    "RESG_DIA": "outflows",
    "NR_COTST": "shareholders",
}

# Catches data errors (quota split, wrong decimal), which jump 50% or more.
# Lower limits reject real moves: the Ibovespa fund fell 14% in a day in March
# 2020, and Raptor reported a monthly quota until 2024, so a single quota change
# carries a whole month of return (up to 17% in the data).
MAX_PLAUSIBLE_QUOTA_CHANGE = 0.30


class SchemaError(ValueError):
    pass


def normalize_cnpj(cnpj: pd.Series) -> pd.Series:
    return cnpj.astype("string").str.replace(r"\D", "", regex=True)


def to_canonical(raw: pd.DataFrame) -> pd.DataFrame:
    renamed = raw.rename(columns=CVM_COLUMN_ALIASES)
    missing = set(CANONICAL_COLUMNS) - set(renamed.columns)
    if missing:
        raise SchemaError(f"CVM report missing columns: {sorted(missing)}")
    canonical = renamed[list(CANONICAL_COLUMNS)].copy()
    canonical["cnpj"] = normalize_cnpj(canonical["cnpj"])
    canonical["date"] = pd.to_datetime(canonical["date"], format="%Y-%m-%d")
    return canonical.astype(CANONICAL_COLUMNS)


def validate_fund_quotas(quotas: pd.DataFrame) -> pd.DataFrame:
    if (quotas["quota"] <= 0).any():
        raise SchemaError("non-positive quota found")
    if quotas.duplicated(["cnpj", "date"]).any():
        raise SchemaError("duplicated (cnpj, date) rows; deduplicate before validating")
    quota_changes = quotas.sort_values("date").groupby("cnpj")["quota"].pct_change()
    implausible = quotas.loc[quota_changes.abs() > MAX_PLAUSIBLE_QUOTA_CHANGE]
    if not implausible.empty:
        raise SchemaError(f"implausible quota changes:\n{implausible}")
    return quotas


def validate_sgs_series(series: pd.DataFrame) -> pd.DataFrame:
    if series["value"].isna().any():
        raise SchemaError(f"SGS series with missing values: {series['series'].unique()}")
    if series.duplicated(["series", "date"]).any():
        raise SchemaError("duplicated (series, date) rows in SGS data")
    return series
