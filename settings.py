"""Constants shared by every pipeline stage: what to fetch and where it lives."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

START_YEAR = 2010

# SPX's own feeders: the longest history (since Dec 2010) and the quota an
# investor actually holds, net of the full fee (masters charge part of it too).
FUNDS = {
    "raptor_feeder": "12809201000113",
    "nimitz_feeder": "12831360000114",
    # Investable proxies for the two markets a macro fund is judged against:
    # equities (passive Ibovespa fund) and real-rate fixed income (IMA-B fund).
    "ibovespa_index": "03370003000105",
    "imab_index": "10740658000193",
}

CVM_DAILY_URL = "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS"
# CVM keeps one yearly archive per year up to this one, monthly archives after.
CVM_LAST_YEARLY_ARCHIVE = 2020

SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
SGS_SERIES = {
    "cdi_daily_pct": 12,
    "ipca_monthly_pct": 433,
    "selic_target_pct": 432,
    "usdbrl_ptax": 1,
}
