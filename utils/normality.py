from __future__ import annotations

import warnings
from typing import Iterable

import numpy as np
import pandas as pd
from scipy import stats

from .statistics import OVERALL_GROUP, round4


def _critical_value_at_5_percent(anderson_result) -> float:
    levels = np.asarray(anderson_result.significance_level, dtype=float)
    critical_values = np.asarray(anderson_result.critical_values, dtype=float)
    index = int(np.argmin(np.abs(levels - 5.0)))
    return float(critical_values[index])


def normality_tests(series: pd.Series, item_name: str, group_name: str = OVERALL_GROUP) -> dict:
    data = pd.to_numeric(series, errors="coerce").dropna()
    sample_size = int(len(data))

    record = {
        "Measurement / 测量项目": item_name,
        "Group / 分组": group_name,
        "Sample Size / 样本量": sample_size,
        "Shapiro Statistic": np.nan,
        "Shapiro P-value": np.nan,
        "Shapiro Result / Shapiro 结论": "Not Available / 不适用",
        "Anderson Statistic": np.nan,
        "Anderson Critical Value 5% / AD 5%临界值": np.nan,
        "Anderson Result / AD 结论": "Not Available / 不适用",
        "Normality Pass / 正态性通过": np.nan,
        "Notes / 备注": "",
        "Conclusion EN / 英文结论": "",
        "Conclusion CN / 中文结论": "",
    }

    if sample_size < 3:
        record["Notes / 备注"] = "Sample size is less than 3 / 样本量小于 3"
        record["Conclusion EN / 英文结论"] = "Normality test is not available because sample size is less than 3."
        record["Conclusion CN / 中文结论"] = "样本量小于 3，无法进行正态性检验。"
        return record

    shapiro_data = data
    if sample_size > 5000:
        shapiro_data = data.sample(n=5000, random_state=42)
        record["Notes / 备注"] = (
            "Shapiro-Wilk was run on a 5000-point sample because large samples may be unstable / "
            "样本量大于 5000，Shapiro-Wilk 使用 5000 点抽样，避免大样本不稳定"
        )

    try:
        shapiro_stat, shapiro_p = stats.shapiro(shapiro_data)
        record["Shapiro Statistic"] = round4(shapiro_stat)
        record["Shapiro P-value"] = round4(shapiro_p)
        if shapiro_p >= 0.05:
            record["Shapiro Result / Shapiro 结论"] = "Data may be approximately normal / 数据可能近似正态"
        else:
            record["Shapiro Result / Shapiro 结论"] = "Data may not be normally distributed / 数据可能不符合正态分布"
    except Exception as exc:  # scipy can fail on pathological data
        record["Shapiro Result / Shapiro 结论"] = f"Not Available / 不适用: {exc}"
        shapiro_p = np.nan

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            ad_result = stats.anderson(data, dist="norm")
        ad_stat = float(ad_result.statistic)
        ad_critical = _critical_value_at_5_percent(ad_result)
        record["Anderson Statistic"] = round4(ad_stat)
        record["Anderson Critical Value 5% / AD 5%临界值"] = round4(ad_critical)
        if ad_stat < ad_critical:
            record["Anderson Result / AD 结论"] = "Pass normality check at 5% level / 5% 显著性水平下可接受正态性"
            ad_pass = True
        else:
            record["Anderson Result / AD 结论"] = "Fail normality check at 5% level / 5% 显著性水平下不满足正态性"
            ad_pass = False
    except Exception as exc:
        record["Anderson Result / AD 结论"] = f"Not Available / 不适用: {exc}"
        ad_pass = np.nan

    shapiro_pass = bool(shapiro_p >= 0.05) if np.isfinite(shapiro_p) else np.nan
    if isinstance(ad_pass, bool) and isinstance(shapiro_pass, bool):
        normality_pass = bool(ad_pass and shapiro_pass)
    elif isinstance(shapiro_pass, bool):
        normality_pass = shapiro_pass
    elif isinstance(ad_pass, bool):
        normality_pass = ad_pass
    else:
        normality_pass = np.nan

    record["Normality Pass / 正态性通过"] = normality_pass

    if np.isfinite(record["Shapiro P-value"]):
        p_value = record["Shapiro P-value"]
        if p_value >= 0.05:
            record["Conclusion EN / 英文结论"] = (
                f"P-value = {p_value:.4f}, which is not lower than 0.05. "
                "The data may be approximately normal."
            )
            record["Conclusion CN / 中文结论"] = f"P-value = {p_value:.4f}，不低于 0.05，数据可能近似正态。"
        else:
            record["Conclusion EN / 英文结论"] = (
                f"P-value = {p_value:.4f}, which is lower than 0.05. "
                "The data may not be normally distributed, so the Cpk result should be used with caution."
            )
            record["Conclusion CN / 中文结论"] = (
                f"P-value = {p_value:.4f}，低于 0.05，数据可能不符合正态分布，因此 Cpk 结果需要谨慎参考。"
            )

    return record


def analyze_normality_for_columns(
    df: pd.DataFrame,
    measurement_columns: Iterable[str],
    group_column: str | None = None,
) -> pd.DataFrame:
    records = []
    for column in measurement_columns:
        records.append(normality_tests(df[column], column, OVERALL_GROUP))

        if group_column and group_column in df.columns:
            grouped = df[[group_column, column]].dropna(subset=[group_column])
            for group_value, group_data in grouped.groupby(group_column, dropna=True):
                records.append(normality_tests(group_data[column], column, str(group_value)))

    return pd.DataFrame(records)
