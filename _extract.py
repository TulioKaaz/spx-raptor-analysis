"""Stage 1: download raw public data (CVM daily fund reports, BCB SGS series).

Every download is cached on disk, so re-running the pipeline only fetches
what is missing (plus the current month, which CVM keeps updating).
"""

from datetime import date
from pathlib import Path

import requests

from settings import (
    CVM_DAILY_URL,
    CVM_LAST_YEARLY_ARCHIVE,
    RAW_DIR,
    SGS_SERIES,
    SGS_URL,
    START_YEAR,
)

CVM_RAW_DIR = RAW_DIR / "inf_diario"
SGS_RAW_DIR = RAW_DIR / "sgs"
# The SGS API rejects daily-series queries spanning more than 10 years.
SGS_MAX_YEARS_PER_REQUEST = 10
TIMEOUT_SECONDS = 120


def cvm_archive_names(start_year: int, today: date) -> list[str]:
    yearly = [
        f"HIST/inf_diario_fi_{year}.zip"
        for year in range(start_year, CVM_LAST_YEARLY_ARCHIVE + 1)
    ]
    monthly = [
        f"inf_diario_fi_{year}{month:02d}.zip"
        for year in range(max(start_year, CVM_LAST_YEARLY_ARCHIVE + 1), today.year + 1)
        for month in range(1, 13)
        if (year, month) <= (today.year, today.month)
    ]
    return yearly + monthly


def is_still_changing(archive_name: str, today: date) -> bool:
    return archive_name.endswith(f"{today.year}{today.month:02d}.zip")


def download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    with requests.get(url, stream=True, timeout=TIMEOUT_SECONDS) as response:
        response.raise_for_status()
        with partial.open("wb") as file:
            for chunk in response.iter_content(chunk_size=1 << 20):
                file.write(chunk)
    # Renaming only after a complete download keeps the cache free of
    # truncated files when a transfer is interrupted.
    partial.rename(destination)


def extract_cvm_daily_reports(today: date) -> list[Path]:
    paths = []
    for name in cvm_archive_names(START_YEAR, today):
        destination = CVM_RAW_DIR / Path(name).name
        if not destination.exists() or is_still_changing(name, today):
            print(f"downloading {name}")
            download_file(f"{CVM_DAILY_URL}/{name}", destination)
        paths.append(destination)
    return paths


def sgs_windows(start: date, end: date) -> list[tuple[date, date]]:
    windows = []
    window_start = start
    while window_start <= end:
        window_end = min(
            date(window_start.year + SGS_MAX_YEARS_PER_REQUEST - 1, 12, 31), end
        )
        windows.append((window_start, window_end))
        window_start = date(window_end.year + 1, 1, 1)
    return windows


def extract_sgs_series(today: date) -> list[Path]:
    paths = []
    for name, code in SGS_SERIES.items():
        for window_start, window_end in sgs_windows(date(START_YEAR, 1, 1), today):
            destination = SGS_RAW_DIR / f"{name}_{window_start.year}.json"
            params = {
                "formato": "json",
                "dataInicial": window_start.strftime("%d/%m/%Y"),
                "dataFinal": window_end.strftime("%d/%m/%Y"),
            }
            print(f"downloading SGS {code} ({name}) {window_start.year}-{window_end.year}")
            response = requests.get(
                SGS_URL.format(code=code), params=params, timeout=TIMEOUT_SECONDS
            )
            response.raise_for_status()
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(response.content)
            paths.append(destination)
    return paths


def extract(today: date) -> tuple[list[Path], list[Path]]:
    return extract_cvm_daily_reports(today), extract_sgs_series(today)


if __name__ == "__main__":
    extract(date.today())
