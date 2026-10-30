"""Stage 3: turn raw archives into clean, validated tables.

CVM archives hold every Brazilian fund (millions of rows per year), so they
are read in chunks and filtered down to the funds of interest while reading.
"""

import json
import zipfile
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from _schemas import (
    normalize_cnpj,
    to_canonical,
    validate_fund_quotas,
    validate_sgs_series,
)

CHUNK_ROWS = 500_000
SUBCLASS_COLUMN = "ID_SUBCLASSE"


def read_fund_rows(archive: Path, cnpjs: set[str]) -> pd.DataFrame:
    selected = []
    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.namelist():
            with zipped.open(member) as csv_file:
                chunks = pd.read_csv(
                    csv_file, sep=";", encoding="latin1", dtype=str, chunksize=CHUNK_ROWS
                )
                for chunk in chunks:
                    cnpj_column = "CNPJ_FUNDO_CLASSE" if "CNPJ_FUNDO_CLASSE" in chunk else "CNPJ_FUNDO"
                    selected.append(chunk[normalize_cnpj(chunk[cnpj_column]).isin(cnpjs)])
    return pd.concat(selected, ignore_index=True) if selected else pd.DataFrame()


def drop_subclass_rows(raw: pd.DataFrame) -> pd.DataFrame:
    # After Resolution 175 a class may report one row per subclass on top of
    # the class row; the class row is the one comparable to the old layout.
    if SUBCLASS_COLUMN not in raw:
        return raw
    return raw[raw[SUBCLASS_COLUMN].isna()]


def transform_fund_quotas(archives: Iterable[Path], cnpjs: set[str]) -> pd.DataFrame:
    frames = [
        to_canonical(drop_subclass_rows(rows))
        for rows in (read_fund_rows(archive, cnpjs) for archive in archives)
        if not rows.empty
    ]
    quotas = pd.concat(frames, ignore_index=True)
    # A report can be resubmitted (rectified); the later submission wins.
    quotas = quotas.drop_duplicates(["cnpj", "date"], keep="last")
    return validate_fund_quotas(quotas.sort_values(["cnpj", "date"], ignore_index=True))


def series_name(path: Path) -> str:
    return path.stem.rsplit("_", 1)[0]


def transform_sgs_series(paths: Iterable[Path]) -> pd.DataFrame:
    frames = []
    for path in paths:
        records = pd.DataFrame(json.loads(path.read_text()))
        frames.append(
            pd.DataFrame(
                {
                    "series": series_name(path),
                    "date": pd.to_datetime(records["data"], format="%d/%m/%Y"),
                    "value": pd.to_numeric(records["valor"]),
                }
            )
        )
    series = pd.concat(frames, ignore_index=True).drop_duplicates(["series", "date"])
    return validate_sgs_series(series.sort_values(["series", "date"], ignore_index=True))
