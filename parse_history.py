import pandas as pd
import pathlib
import datetime
import re
from decimal import Decimal as D

from typing import Iterable

DATE_FORMAT = "%m/%d/%Y"

HISTORY_REPORT_HEADER_ROW = 7
HISTORY_REPORT_FIELD_NAMES = [
    "Date",
    "Description",
    "Symbol",
    "Quantity",
    "Price",
    "Amount",
    "Commission",
    "Fees",
    "Type",
]
HISTORY_REPORT_USE_FIELDS = HISTORY_REPORT_FIELD_NAMES[:-1]

OUTPUT_FIELD_NAMES = [
    "Date",
    "Time",
    "Symbol",
    "Quantity",
    "Price",
    "Buy/Sell",
    "Commission",
    "Type",
    "Expiration Date",
    "Strike Price",
    "Call or Put",
]

HISTORY_REPORT_DATA = {
    "Date": str,
    "Description": str,
    "Symbol": "category",
    "Quantity": float,
    "Price": str,
    "Amount": str,
    "Commission": str,
    "Fees": str,
    "Type": str,
}

INPUT_DIR = pathlib.Path("./raw_reports")
OUTPUT_DIR = pathlib.Path("./processed_output")


def _transform_date(date):
    output_str = DATE_FORMAT
    try:
        return date.strftime(output_str)
    except ValueError:
        return None


def _clean_currency(x):
    precision = D("0.0001")
    if isinstance(x, str):
        return D(x.replace("$", "")).quantize(precision)
    return None


def _apply_transaction_type(description):
    ignore_if_startswith = (
        "assigned",
        "electronic",
        "exercised",
        "expired",
        "interest",
        "reinvestment",
    )
    if description.startswith(ignore_if_startswith):
        return None

    split_str = " as of "
    description = description.lower()
    action, date_str = ("", None)
    if split_str in description:
        action, date_str = description.split(" as of ")
    else:
        action = description

    if action.startswith("you bought"):
        return "Buy"

    if action.startswith("you sold"):
        return "Sell"


def _split_on_text(symbol):
    """
    Splits option symbol on text eg:
        'BKSY220218C7.5'
        becomes
        ['220218', '7.5']
    """
    return list(filter(None, re.split("[A-Za-z]+", symbol)))


def _split_on_digits(symbol):
    """
    Splits option symbol on digits eg:
        'BKSY220218C10'
        becomes
        ['BKSY', 'C']
    """
    return list(filter(None, re.split("\d+", symbol)))


def _parse_strike(symbol):
    splits = _split_on_text(symbol)
    if len(splits) <= 1:
        return None
    return float(splits[1])


def _parse_call_or_put(symbol):
    splits = _split_on_digits(symbol)
    if len(splits) <= 1:
        return None
    mapping = {"C": "Call", "P": "Put"}
    return mapping.get(splits[1])


def _parse_expiration(symbol):
    splits = _split_on_text(symbol)
    if not splits:
        return None
    date_str = splits[0]
    parse_str = "%y%m%d"
    output_str = DATE_FORMAT
    try:
        d = datetime.datetime.strptime(date_str, parse_str)
        return d.strftime(output_str)
    except ValueError:
        return None


def _parse_underlying(symbol):
    splits = _split_on_digits(symbol)
    if not splits or len(symbol) == 9:
        # Either a stock symbol or CUSIP number
        return symbol
    return splits[0]


def _parse_type(symbol):
    splits = _split_on_digits(symbol)
    if len(splits) <= 1:
        return "SHARE"
    return "OPTION"


def get_reports() -> Iterable[pathlib.Path]:
    """
    Returns a list of csvs in the input directory
    """
    csv_list = sorted([f for f in INPUT_DIR.glob("*.csv") if f.is_file()])
    return reversed(csv_list)


def process():
    output_file = OUTPUT_DIR / "output.csv"

    if not output_file.exists():
        output_file.parent.mkdir(parents=True, exist_ok=True)

    reports = get_reports()

    df = (
        pd.read_csv(
            next(reports),
            header=HISTORY_REPORT_HEADER_ROW,
            names=HISTORY_REPORT_FIELD_NAMES,
            usecols=HISTORY_REPORT_USE_FIELDS,
            dtype=HISTORY_REPORT_DATA,
            parse_dates=["Date"],
            na_values=["", "NaN"],
            thousands=r",",
            keep_default_na=False,
        )
        .dropna(how="all")  # Remove rows where all values are some form of null, eg NaN
        .drop_duplicates()  # Sometimes Fidelity includes duplicate rows, remove them
    )

    out = pd.DataFrame(columns=OUTPUT_FIELD_NAMES)
    out["Date"] = pd.to_datetime(df["Date"].apply(_transform_date))
    out["Time"] = "12:00:00"
    out["Symbol"] = df["Symbol"].apply(_parse_underlying)
    out["Quantity"] = df["Quantity"].apply(int).apply(abs)
    out["Price"] = df["Price"].apply(_clean_currency)
    out["Buy/Sell"] = df["Description"].apply(_apply_transaction_type)
    out["Commission"] = df["Commission"].apply(_clean_currency) + df["Fees"].apply(
        _clean_currency
    )
    out["Type"] = df["Symbol"].apply(_parse_type)
    out["Expiration Date"] = pd.to_datetime(df["Symbol"].apply(_parse_expiration))
    out["Strike Price"] = df["Symbol"].apply(_parse_strike)
    out["Call or Put"] = df["Symbol"].apply(_parse_call_or_put)

    # Dump output removing entries where buy/sell was not given. These
    # correspond to history entries like dividend payments, mergers,
    # option expirations, etc
    out[~pd.isna(out["Buy/Sell"])].sort_values(["Date", "Symbol"]).to_csv(
        output_file, index=False, date_format=DATE_FORMAT
    )


if __name__ == "__main__":
    process()
