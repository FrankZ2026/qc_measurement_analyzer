from __future__ import annotations

from typing import Dict, Iterable, Tuple

import numpy as np
import pandas as pd


OVERALL_GROUP = "Overall / 总体"


def round4(value):
    if value is None:
        return np.nan
    try:
        number = float(value)
    except (TypeError, ValueError):
        return np.nan
    if not np.isfinite(number):
        return np.nan
    return round(number, 4)


def _spec_values(spec: Dict | None) -> Tuple[float | None, float | None, str]:
    if not spec:
        return None, None, "Specification limits are required for Cp/Cpk calculation / 需要输入规格上下限才能计算 Cp/Cpk"

    lsl = spec.get("lsl")
    usl = spec.get("usl")
    if lsl is None or usl is None:
        return None, None, "Specification limits are required for Cp/Cpk calculation / 需要输入规格上下限才能计算 Cp/Cpk"

    try:
        lsl_value = float(lsl)
        usl_value = float(usl)
    except (TypeError, ValueError):
        return None, None, "Invalid specification limits / 规格限无效"

    if not np.isfinite(lsl_value) or not np.isfinite(usl_value):
        return None, None, "Invalid specification limits / 规格限无效"
    if lsl_value >= usl_value:
        return None, None, "Invalid specification: LSL must be lower than USL / 规格错误：LSL 必须小于 USL"

    return lsl_value, usl_value, "OK / 有效"


def calculate_statistics(
    series: pd.Series,
    item_name: str,
    spec: Dict | None = None,
    group_name: str = OVERALL_GROUP,
) -> Dict:
    data = pd.to_numeric(series, errors="coerce").dropna()
    sample_size = int(len(data))
    lsl, usl, spec_status = _spec_values(spec)

    mean = data.mean() if sample_size else np.nan
    minimum = data.min() if sample_size else np.nan
    maximum = data.max() if sample_size else np.nan
    value_range = maximum - minimum if sample_size else np.nan

    if sample_size >= 2:
        std = data.std(ddof=1)
        variance = data.var(ddof=1)
    else:
        std = np.nan
        variance = np.nan

    cp = cpu = cpl = cpk = np.nan
    cpk_status = spec_status
    if sample_size < 2:
        cpk_status = "Not Available: sample size is less than 2 / 不适用：样本量小于 2"
    elif not np.isfinite(std) or std == 0:
        cpk_status = "Not Available: standard deviation is zero or invalid / 不适用：标准差为 0 或无效"
    elif lsl is not None and usl is not None:
        cp = (usl - lsl) / (6 * std)
        cpu = (usl - mean) / (3 * std)
        cpl = (mean - lsl) / (3 * std)
        cpk = min(cpu, cpl)

    nearest_spec_distance = np.nan
    if lsl is not None and usl is not None and np.isfinite(mean):
        nearest_spec_distance = min(abs(mean - lsl), abs(usl - mean))

    return {
        "Measurement / 测量项目": item_name,
        "Group / 分组": group_name,
        "Sample Size / 样本量": sample_size,
        "Mean / 平均值": round4(mean),
        "Min / 最小值": round4(minimum),
        "Max / 最大值": round4(maximum),
        "Range / 极差": round4(value_range),
        "Standard Deviation / 标准差": round4(std),
        "Variance / 方差": round4(variance),
        "LSL / 下限": round4(lsl),
        "USL / 上限": round4(usl),
        "Cp": round4(cp),
        "CPU": round4(cpu),
        "CPL": round4(cpl),
        "Cpk": round4(cpk),
        "Pp / Ppk": "Future Enhancement / 后续增强",
        "Nearest Spec Distance / 最近规格边界距离": round4(nearest_spec_distance),
        "Cp/Cpk Status / Cp/Cpk 状态": cpk_status,
    }


def analyze_measurements(
    df: pd.DataFrame,
    measurement_columns: Iterable[str],
    specs: Dict[str, Dict] | None = None,
    group_column: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    specs = specs or {}
    overall_records = []
    group_records = []

    for column in measurement_columns:
        overall_records.append(calculate_statistics(df[column], column, specs.get(column), OVERALL_GROUP))

        if group_column and group_column in df.columns:
            grouped = df[[group_column, column]].dropna(subset=[group_column])
            for group_value, group_data in grouped.groupby(group_column, dropna=True):
                group_records.append(
                    calculate_statistics(
                        group_data[column],
                        column,
                        specs.get(column),
                        str(group_value),
                    )
                )

    return pd.DataFrame(overall_records), pd.DataFrame(group_records)


def rank_group_results(group_df: pd.DataFrame, unstable_sample_size: int = 5) -> pd.DataFrame:
    if group_df is None or group_df.empty or "Cpk" not in group_df.columns:
        return pd.DataFrame() if group_df is None else group_df

    ranked = group_df.copy()
    ranked["Group Comparison / 组别比较"] = ""

    for measurement, indexer in ranked.groupby("Measurement / 测量项目").groups.items():
        subset = ranked.loc[list(indexer)]
        valid = subset[pd.to_numeric(subset["Cpk"], errors="coerce").notna()]
        if not valid.empty:
            best_idx = pd.to_numeric(valid["Cpk"], errors="coerce").idxmax()
            risk_idx = pd.to_numeric(valid["Cpk"], errors="coerce").idxmin()
            ranked.loc[best_idx, "Group Comparison / 组别比较"] += "Best group / 最佳组别"
            ranked.loc[risk_idx, "Group Comparison / 组别比较"] += "Highest risk group / 风险最高组别"

        small_sample = subset["Sample Size / 样本量"] < unstable_sample_size
        for idx in subset[small_sample].index:
            current = ranked.loc[idx, "Group Comparison / 组别比较"]
            separator = "; " if current else ""
            ranked.loc[idx, "Group Comparison / 组别比较"] = (
                f"{current}{separator}Small sample, result may be unstable / 样本量偏小，结果可能不稳定"
            )

    ranked["_Cpk Sort"] = pd.to_numeric(ranked["Cpk"], errors="coerce")
    ranked = ranked.sort_values(
        by=["Measurement / 测量项目", "_Cpk Sort"],
        ascending=[True, False],
        na_position="last",
    ).drop(columns=["_Cpk Sort"])
    return ranked.reset_index(drop=True)

