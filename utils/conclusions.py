from __future__ import annotations

import math
from typing import Dict, List

import numpy as np
import pandas as pd


def _is_available(value) -> bool:
    try:
        return bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def classify_cpk(cpk) -> Dict[str, str]:
    if not _is_available(cpk):
        return {
            "grade": "Not Available / 不适用",
            "level": "info",
            "en": "Cpk is not available because valid specification limits and variation are required.",
            "cn": "Cpk 不适用，因为需要有效规格限和有效波动数据。",
        }

    value = float(cpk)
    if value >= 1.67:
        return {
            "grade": "Excellent / 优秀",
            "level": "success",
            "en": f"Cpk = {value:.4f}, the process capability is excellent.",
            "cn": f"Cpk = {value:.4f}，过程能力优秀。",
        }
    if value >= 1.33:
        return {
            "grade": "Good / 良好",
            "level": "success",
            "en": f"Cpk = {value:.4f}, the process capability is good.",
            "cn": f"Cpk = {value:.4f}，过程能力良好。",
        }
    if value >= 1.00:
        return {
            "grade": "Marginal / 边缘可接受",
            "level": "warning",
            "en": f"Cpk = {value:.4f}, the process capability is marginal. Further process improvement is recommended.",
            "cn": f"Cpk = {value:.4f}，过程能力处于边缘可接受水平，建议继续改善过程稳定性。",
        }
    return {
        "grade": "Poor / 高风险",
        "level": "error",
        "en": f"Cpk = {value:.4f}, the process capability is poor and requires priority improvement.",
        "cn": f"Cpk = {value:.4f}，过程能力高风险，需要优先改善。",
    }


def _normality_lookup(normality_df: pd.DataFrame | None) -> Dict[tuple[str, str], bool]:
    lookup: Dict[tuple[str, str], bool] = {}
    if normality_df is None or normality_df.empty:
        return lookup

    for _, row in normality_df.iterrows():
        key = (str(row.get("Measurement / 测量项目")), str(row.get("Group / 分组")))
        value = row.get("Normality Pass / 正态性通过")
        if pd.isna(value):
            lookup[key] = np.nan
        else:
            lookup[key] = bool(value)
    return lookup


def attach_capability_grades(stats_df: pd.DataFrame, normality_df: pd.DataFrame | None = None) -> pd.DataFrame:
    if stats_df is None or stats_df.empty:
        return pd.DataFrame() if stats_df is None else stats_df

    normality = _normality_lookup(normality_df)
    enriched = stats_df.copy()
    grades = []
    levels = []
    conclusions_en = []
    conclusions_cn = []

    for _, row in enriched.iterrows():
        cpk_info = classify_cpk(row.get("Cpk"))
        key = (str(row.get("Measurement / 测量项目")), str(row.get("Group / 分组")))
        normality_pass = normality.get(key)
        en = cpk_info["en"]
        cn = cpk_info["cn"]

        if normality_pass is False and _is_available(row.get("Cpk")):
            en += " Since the normality test failed, the Cpk result may not fully represent the real process capability."
            cn += " 由于正态性检验未通过，Cpk 结果可能不能完全代表真实过程能力。"

        grades.append(cpk_info["grade"])
        levels.append(cpk_info["level"])
        conclusions_en.append(en)
        conclusions_cn.append(cn)

    enriched["Cpk Grade / Cpk 等级"] = grades
    enriched["Action Level / 行动级别"] = levels
    enriched["Capability Conclusion EN / 能力英文结论"] = conclusions_en
    enriched["Capability Conclusion CN / 能力中文结论"] = conclusions_cn
    return enriched


def build_overall_conclusion(
    stats_df: pd.DataFrame,
    normality_df: pd.DataFrame | None = None,
    group_df: pd.DataFrame | None = None,
) -> List[Dict[str, str]]:
    conclusions: List[Dict[str, str]] = []
    if stats_df is None or stats_df.empty:
        return conclusions

    overall = stats_df[stats_df["Group / 分组"].astype(str).str.contains("Overall", regex=False)].copy()
    if overall.empty:
        overall = stats_df.copy()

    valid_cpk = overall[pd.to_numeric(overall["Cpk"], errors="coerce").notna()]
    if not valid_cpk.empty:
        idx = pd.to_numeric(valid_cpk["Cpk"], errors="coerce").idxmin()
        row = valid_cpk.loc[idx]
        conclusions.append(
            {
                "English": f"The lowest Cpk is {row['Cpk']} for {row['Measurement / 测量项目']}.",
                "中文": f"Cpk 最低的项目是 {row['Measurement / 测量项目']}，Cpk = {row['Cpk']}。",
            }
        )
    else:
        conclusions.append(
            {
                "English": "Cp/Cpk is not available for the selected items because specification limits or variation are missing.",
                "中文": "所选项目暂无法计算 Cp/Cpk，原因可能是未输入规格限或数据波动无效。",
            }
        )

    valid_std = overall[pd.to_numeric(overall["Standard Deviation / 标准差"], errors="coerce").notna()]
    if not valid_std.empty:
        idx = pd.to_numeric(valid_std["Standard Deviation / 标准差"], errors="coerce").idxmax()
        row = valid_std.loc[idx]
        conclusions.append(
            {
                "English": f"The largest variation is in {row['Measurement / 测量项目']} with standard deviation {row['Standard Deviation / 标准差']}.",
                "中文": f"波动最大的项目是 {row['Measurement / 测量项目']}，标准差 = {row['Standard Deviation / 标准差']}。",
            }
        )

    valid_distance = overall[pd.to_numeric(overall["Nearest Spec Distance / 最近规格边界距离"], errors="coerce").notna()]
    if not valid_distance.empty:
        idx = pd.to_numeric(valid_distance["Nearest Spec Distance / 最近规格边界距离"], errors="coerce").idxmin()
        row = valid_distance.loc[idx]
        conclusions.append(
            {
                "English": f"The mean closest to a specification boundary is {row['Measurement / 测量项目']}.",
                "中文": f"平均值最接近规格边界的项目是 {row['Measurement / 测量项目']}。",
            }
        )

    failed_items: list[str] = []
    if normality_df is not None and not normality_df.empty:
        overall_normality = normality_df[
            normality_df["Group / 分组"].astype(str).str.contains("Overall", regex=False)
        ]
        failed = overall_normality[overall_normality["Normality Pass / 正态性通过"] == False]  # noqa: E712
        failed_items = sorted(failed["Measurement / 测量项目"].astype(str).unique().tolist())
        if failed_items:
            conclusions.append(
                {
                    "English": "Normality check failed for: " + ", ".join(failed_items) + ".",
                    "中文": "正态性检验未通过的项目：" + "，".join(failed_items) + "。",
                }
            )

    priority = []
    for _, row in overall.iterrows():
        cpk = row.get("Cpk")
        item = str(row.get("Measurement / 测量项目"))
        if (_is_available(cpk) and float(cpk) < 1.33) or item in failed_items:
            priority.append(item)
    if priority:
        unique_priority = sorted(set(priority))
        conclusions.append(
            {
                "English": "Priority improvement is recommended for: " + ", ".join(unique_priority) + ".",
                "中文": "建议优先改善的项目：" + "，".join(unique_priority) + "。",
            }
        )

    if group_df is not None and not group_df.empty and "Group Comparison / 组别比较" in group_df.columns:
        risky = group_df[group_df["Group Comparison / 组别比较"].astype(str).str.contains("Highest risk", regex=False)]
        if not risky.empty:
            pairs = [f"{row['Measurement / 测量项目']} - {row['Group / 分组']}" for _, row in risky.iterrows()]
            conclusions.append(
                {
                    "English": "Highest-risk groups identified: " + "; ".join(pairs) + ".",
                    "中文": "识别出的高风险组别：" + "；".join(pairs) + "。",
                }
            )

    return conclusions
