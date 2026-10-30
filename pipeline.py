"""Run every stage in order: extract -> transform (validated by schemas) -> load."""

from datetime import date

from _extract import extract
from _load import load
from _transform import transform_fund_quotas, transform_sgs_series
from settings import FUNDS


def run(today: date) -> None:
    cvm_archives, sgs_files = extract(today)
    fund_quotas = transform_fund_quotas(cvm_archives, set(FUNDS.values()))
    sgs_series = transform_sgs_series(sgs_files)
    for path in load(fund_quotas, sgs_series):
        print(f"wrote {path}")


if __name__ == "__main__":
    run(date.today())
