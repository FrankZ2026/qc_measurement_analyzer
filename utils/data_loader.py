from __future__ import annotations

import io
import re
from typing import Dict, List

import pandas as pd


ID_KEYWORDS_CN = ("编号", "序号", "样本号", "样本编号", "流水号")
ID_PATTERN = re.compile(
    r"(^|\b)(id|no|no\.|number|serial|seq|sequence|index|sample id|sample no|record)(\b|$)",
    re.IGNORECASE,
)


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with non-empty, unique column names."""
    cleaned = df.copy()
    seen: dict[str, int] = {}
    names: List[str] = []

    for idx, column in enumerate(cleaned.columns, start=1):
        name = "" if column is None else str(column).strip()
        if not name or name.lower().startswith("unnamed:"):
            name = f"Column {idx}"

        count = seen.get(name, 0)
        seen[name] = count + 1
        if count:
            name = f"{name}_{count + 1}"
        names.append(name)

    cleaned.columns = names
    return cleaned


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Drop fully empty rows/columns and normalize headers."""
    if df is None:
        return pd.DataFrame()

    cleaned = df.dropna(how="all").dropna(axis=1, how="all")
    cleaned = normalize_column_names(cleaned)
    return cleaned.reset_index(drop=True)


def _read_csv(raw: bytes) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "latin1"):
        try:
            return pd.read_csv(io.BytesIO(raw), encoding=encoding, sep=None, engine="python")
        except UnicodeDecodeError as exc:
            last_error = exc
        except pd.errors.EmptyDataError:
            raise ValueError("Uploaded CSV is empty / 上传的 CSV 为空")
    raise ValueError(f"Unable to read CSV file / 无法读取 CSV 文件: {last_error}")


def read_uploaded_file(uploaded_file) -> Dict[str, pd.DataFrame]:
    """Read CSV/XLS/XLSX upload into a dictionary of sheet name to DataFrame."""
    if uploaded_file is None:
        return {}

    name = uploaded_file.name.lower()
    raw = uploaded_file.getvalue()
    if not raw:
        raise ValueError("Uploaded file is empty / 上传文件为空")

    if name.endswith(".csv"):
        return {"CSV Data": clean_dataframe(_read_csv(raw))}

    if name.endswith((".xlsx", ".xls")):
        engine = "openpyxl" if name.endswith(".xlsx") else "xlrd"
        excel_file = pd.ExcelFile(io.BytesIO(raw), engine=engine)
        sheets: Dict[str, pd.DataFrame] = {}
        for sheet_name in excel_file.sheet_names:
            sheets[sheet_name] = clean_dataframe(pd.read_excel(excel_file, sheet_name=sheet_name))
        return sheets

    raise ValueError("Unsupported file type / 不支持的文件类型")


def is_id_like_column(column_name: str, numeric_values: pd.Series | None = None) -> bool:
    """Flag obvious ID/sequence columns while keeping manual selection possible."""
    raw = str(column_name)
    normalized = re.sub(r"[\s_\-\\/]+", " ", raw).strip().lower()

    if any(keyword in raw for keyword in ID_KEYWORDS_CN):
        return True
    if ID_PATTERN.search(normalized):
        return True

    if numeric_values is None:
        return False

    values = pd.to_numeric(numeric_values, errors="coerce").dropna()
    if len(values) < 3:
        return False

    unique_ratio = values.nunique() / len(values)
    integer_like = (values % 1 == 0).all()
    if unique_ratio < 0.95 or not integer_like:
        return False

    sorted_values = values.sort_values().to_numpy()
    diffs = pd.Series(sorted_values).diff().dropna()
    return bool((diffs.abs() == 1).mean() > 0.9)


def numeric_profile(df: pd.DataFrame, threshold: float = 0.70) -> pd.DataFrame:
    """Profile columns and recommend likely measurement columns."""
    records = []
    if df is None or df.empty:
        return pd.DataFrame(records)

    for column in df.columns:
        series = df[column].replace(r"^\s*$", pd.NA, regex=True)
        non_empty = int(series.notna().sum())
        numeric = pd.to_numeric(series, errors="coerce")
        numeric_count = int(numeric.notna().sum())
        ratio = numeric_count / non_empty if non_empty else 0.0
        id_like = is_id_like_column(str(column), numeric)
        recommended = bool(ratio >= threshold and numeric_count >= 2 and not id_like)

        if recommended:
            reason = "High numeric ratio / 数值比例高"
        elif id_like:
            reason = "Looks like ID or sequence / 类似 ID 或序号"
        elif numeric_count < 2:
            reason = "Not enough numeric values / 数值数量不足"
        else:
            reason = "Numeric ratio below threshold / 数值比例低于阈值"

        records.append(
            {
                "Column / 列名": str(column),
                "Non-empty Count / 非空数量": non_empty,
                "Numeric Count / 数值数量": numeric_count,
                "Numeric Ratio / 数值比例": round(ratio, 4),
                "ID-like / 类似ID": id_like,
                "Recommended / 推荐": recommended,
                "Reason / 原因": reason,
            }
        )

    return pd.DataFrame(records)


def coerce_numeric(series: pd.Series) -> pd.Series:
    """Convert a series to numeric values and remove invalid entries."""
    return pd.to_numeric(series, errors="coerce").dropna()

