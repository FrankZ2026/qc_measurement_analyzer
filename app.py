from __future__ import annotations

import math
from typing import Dict, Tuple

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from utils.charts import box_plot, fig_to_png_bytes, histogram_with_normal_curve, qq_plot
from utils.conclusions import attach_capability_grades, build_overall_conclusion
from utils.data_loader import numeric_profile, read_uploaded_file
from utils.normality import analyze_normality_for_columns
from utils.report_exporter import (
    create_summary_report as create_summary_excel,
    create_complete_analysis_excel,
    create_charts_zip,
)
from utils.statistics import analyze_measurements, rank_group_results


PAGE_OPTIONS = [
    "1. Upload Data / 上传数据",
    "2. Select Measurement Columns / 选择测量列",
    "3. Input Specification / 输入规格",
    "4. Analysis Dashboard / 分析仪表盘",
    "5. Download Report / 下载报告",
]


def init_state() -> None:
    defaults = {
        "sheets": {},
        "current_df": None,
        "current_sheet": None,
        "measurement_columns": [],
        "group_column": None,
        "specs": {},
        "analysis": None,
        "uploaded_file_id": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def page_shell() -> str:
    st.set_page_config(page_title="QC Measurement Capability Analyzer", layout="wide")
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.5rem; }
        h1, h2, h3 { color: #1f2937; }
        div[data-testid="stMetric"] {
            background: #f8fafc;
            border: 1px solid #e5e7eb;
            padding: 0.75rem;
            border-radius: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("QC Measurement Capability Analyzer")
    st.caption("Local Streamlit QC measurement analysis / 本地 Streamlit QC 测量能力分析")
    st.sidebar.header("Navigation / 页面")
    return st.sidebar.radio("Go to / 跳转", PAGE_OPTIONS)


def parse_optional_float(raw: str) -> Tuple[float | None, str | None]:
    text = (raw or "").strip()
    if text == "":
        return None, None
    try:
        value = float(text)
    except ValueError:
        return None, "Please enter a numeric value / 请输入数字"
    if not math.isfinite(value):
        return None, "Please enter a finite numeric value / 请输入有限数字"
    return value, None


def valid_spec_limits(spec: Dict | None) -> tuple[float | None, float | None]:
    if not spec:
        return None, None
    lsl = spec.get("lsl")
    usl = spec.get("usl")
    try:
        lsl_value = float(lsl)
        usl_value = float(usl)
    except (TypeError, ValueError):
        return None, None
    if math.isfinite(lsl_value) and math.isfinite(usl_value) and lsl_value < usl_value:
        return lsl_value, usl_value
    return None, None


def specs_to_dataframe(specs: Dict[str, Dict]) -> pd.DataFrame:
    records = []
    for column, spec in specs.items():
        records.append(
            {
                "Measurement / 测量项目": column,
                "Mode / 模式": spec.get("mode", ""),
                "Target / 标准值": spec.get("target"),
                "Tolerance / 公差": spec.get("tolerance"),
                "LSL / 下限": spec.get("lsl"),
                "USL / 上限": spec.get("usl"),
                "Status / 状态": spec.get("status", ""),
            }
        )
    return pd.DataFrame(records)


def require_data() -> pd.DataFrame | None:
    df = st.session_state.get("current_df")
    if df is None or df.empty:
        st.info("Please upload and select data first. / 请先上传并选择数据。")
        return None
    return df


def require_measurements() -> list[str] | None:
    columns = st.session_state.get("measurement_columns", [])
    if not columns:
        st.info("Please select at least one measurement column. / 请至少选择一个测量列。")
        return None
    return columns


def run_analysis() -> Dict | None:
    df = st.session_state.get("current_df")
    columns = st.session_state.get("measurement_columns", [])
    if df is None or df.empty or not columns:
        return None

    group_column = st.session_state.get("group_column")
    specs = st.session_state.get("specs", {})

    stats_df, group_df = analyze_measurements(df, columns, specs, group_column)
    normality_df = analyze_normality_for_columns(df, columns, group_column)
    stats_df = attach_capability_grades(stats_df, normality_df)
    if group_df is not None and not group_df.empty:
        group_df = rank_group_results(group_df)
        group_df = attach_capability_grades(group_df, normality_df)

    conclusions = build_overall_conclusion(stats_df, normality_df, group_df)
    cleaned_data = df.copy()
    for column in columns:
        cleaned_data[f"{column} (numeric)"] = pd.to_numeric(df[column], errors="coerce")

    analysis = {
        "stats_df": stats_df,
        "group_df": group_df,
        "normality_df": normality_df,
        "conclusions": conclusions,
        "cleaned_data": cleaned_data,
        "specs_df": specs_to_dataframe(specs),
    }
    st.session_state["analysis"] = analysis
    return analysis


def render_upload_page() -> None:
    st.subheader("Page 1: Upload Data / 上传数据")
    uploaded = st.file_uploader(
        "Upload Excel or CSV / 上传 Excel 或 CSV",
        type=["xlsx", "xls", "csv"],
        accept_multiple_files=False,
    )

    if uploaded is not None:
        file_id = f"{uploaded.name}:{uploaded.size}"
        if st.session_state.get("uploaded_file_id") != file_id:
            try:
                sheets = read_uploaded_file(uploaded)
                if not sheets:
                    st.error("No readable data found. / 未读取到可用数据。")
                    return
                st.session_state["sheets"] = sheets
                st.session_state["uploaded_file_id"] = file_id
                st.session_state["measurement_columns"] = []
                st.session_state["group_column"] = None
                st.session_state["specs"] = {}
                st.session_state["analysis"] = None
            except Exception as exc:
                st.error(f"Failed to read file / 文件读取失败: {exc}")
                return

    sheets = st.session_state.get("sheets", {})
    if not sheets:
        st.info("Supported formats: .xlsx, .xls, .csv / 支持格式：.xlsx、.xls、.csv")
        return

    sheet_names = list(sheets.keys())
    if len(sheet_names) > 1:
        selected_sheet = st.selectbox("Select Sheet / 选择工作表", sheet_names)
    else:
        selected_sheet = sheet_names[0]
        st.success(f"Loaded sheet / 已加载工作表: {selected_sheet}")

    raw_df = sheets[selected_sheet]
    df = raw_df.copy()
    if "Sheet Name" not in df.columns:
        df.insert(0, "Sheet Name", selected_sheet)

    st.session_state["current_sheet"] = selected_sheet
    st.session_state["current_df"] = df

    if df.empty:
        st.error("The selected sheet has no data. / 所选工作表为空。")
        return

    st.write(f"Rows / 行数: **{len(df)}**  |  Columns / 列数: **{len(df.columns)}**")
    st.dataframe(df.head(100), use_container_width=True)


def render_select_columns_page() -> None:
    st.subheader("Page 2: Select Measurement Columns / 选择测量列")
    df = require_data()
    if df is None:
        return

    profile = numeric_profile(df)
    recommended = profile.loc[profile["Recommended / 推荐"], "Column / 列名"].tolist() if not profile.empty else []

    st.markdown("**System Recommended Numeric Columns / 系统推荐数值列**")
    st.dataframe(profile, use_container_width=True, hide_index=True)

    current_selection = [col for col in st.session_state.get("measurement_columns", []) if col in df.columns]
    default_selection = current_selection or recommended
    measurement_columns = st.multiselect(
        "Measurement Columns / 测量列",
        options=list(df.columns),
        default=default_selection,
        help="Recommended columns are pre-selected, but every column remains available for manual selection.",
    )

    group_options = ["None / 不分组"] + [col for col in df.columns if col not in measurement_columns]
    current_group = st.session_state.get("group_column")
    group_index = group_options.index(current_group) if current_group in group_options else 0
    group_choice = st.selectbox(
        "Optional Group Column / 可选分组列",
        options=group_options,
        index=group_index,
    )
    group_column = None if group_choice == "None / 不分组" else group_choice

    st.session_state["measurement_columns"] = measurement_columns
    st.session_state["group_column"] = group_column
    st.session_state["analysis"] = None

    if measurement_columns:
        st.success(f"Selected {len(measurement_columns)} measurement column(s). / 已选择 {len(measurement_columns)} 个测量列。")
    else:
        st.warning("No measurement column selected. / 尚未选择测量列。")


def render_specification_page() -> None:
    st.subheader("Page 3: Input Specification / 输入规格")
    columns = require_measurements()
    if not columns:
        return

    spec_mode = st.radio(
        "Specification Input Mode / 规格输入模式",
        ["Target ± Tolerance", "LSL / USL"],
        horizontal=True,
    )

    specs: Dict[str, Dict] = {}
    for idx, column in enumerate(columns):
        key_prefix = f"{idx}_{safe_filename(column)}"
        with st.expander(f"{column}", expanded=True):
            if spec_mode == "Target ± Tolerance":
                left, right = st.columns(2)
                target_raw = left.text_input("Target / 标准值", key=f"target_{key_prefix}")
                tolerance_raw = right.text_input("Tolerance / 公差", key=f"tol_{key_prefix}")
                target, target_error = parse_optional_float(target_raw)
                tolerance, tolerance_error = parse_optional_float(tolerance_raw)

                lsl = usl = None
                status = "Specification limits are required for Cp/Cpk calculation / 需要输入规格上下限才能计算 Cp/Cpk"
                if target_error or tolerance_error:
                    st.error(target_error or tolerance_error)
                    status = target_error or tolerance_error
                elif target is not None or tolerance is not None:
                    if target is None or tolerance is None:
                        st.warning("Both Target and Tolerance are required for this mode. / 该模式需要同时输入标准值和公差。")
                        status = "Incomplete specification / 规格输入不完整"
                    elif tolerance < 0:
                        st.error("Tolerance must be non-negative. / 公差不能为负数。")
                        status = "Invalid tolerance / 公差无效"
                    else:
                        lsl = target - tolerance
                        usl = target + tolerance
                        if lsl >= usl:
                            st.error("LSL must be lower than USL. / LSL 必须小于 USL。")
                            status = "Invalid specification / 规格无效"
                        else:
                            status = "OK / 有效"
                            st.info(f"Calculated LSL / 自动计算下限: {lsl:.4f} | USL / 上限: {usl:.4f}")

                specs[column] = {
                    "mode": spec_mode,
                    "target": target,
                    "tolerance": tolerance,
                    "lsl": lsl,
                    "usl": usl,
                    "status": status,
                }
            else:
                left, right = st.columns(2)
                lsl_raw = left.text_input("LSL / Lower Specification Limit / 下限", key=f"lsl_{key_prefix}")
                usl_raw = right.text_input("USL / Upper Specification Limit / 上限", key=f"usl_{key_prefix}")
                lsl, lsl_error = parse_optional_float(lsl_raw)
                usl, usl_error = parse_optional_float(usl_raw)
                status = "Specification limits are required for Cp/Cpk calculation / 需要输入规格上下限才能计算 Cp/Cpk"

                if lsl_error or usl_error:
                    st.error(lsl_error or usl_error)
                    status = lsl_error or usl_error
                elif lsl is not None or usl is not None:
                    if lsl is None or usl is None:
                        st.warning("Both LSL and USL are required. / 需要同时输入 LSL 和 USL。")
                        status = "Incomplete specification / 规格输入不完整"
                    elif lsl >= usl:
                        st.error("LSL must be lower than USL. / LSL 必须小于 USL。")
                        status = "Invalid specification: LSL >= USL / 规格无效：LSL >= USL"
                    else:
                        status = "OK / 有效"
                        st.info(f"LSL / 下限: {lsl:.4f} | USL / 上限: {usl:.4f}")

                specs[column] = {
                    "mode": spec_mode,
                    "target": None,
                    "tolerance": None,
                    "lsl": lsl,
                    "usl": usl,
                    "status": status,
                }

    st.session_state["specs"] = specs
    st.session_state["analysis"] = None
    st.markdown("**Specification Table / 规格表**")
    st.dataframe(specs_to_dataframe(specs), use_container_width=True, hide_index=True)


def show_level_message(level: str, text: str) -> None:
    if level == "success":
        st.success(text)
    elif level == "warning":
        st.warning(text)
    elif level == "error":
        st.error(text)
    else:
        st.info(text)


def render_dashboard_page() -> None:
    st.subheader("Page 4: Analysis Dashboard / 分析仪表盘")
    if require_data() is None or not require_measurements():
        return

    analysis = run_analysis()
    if analysis is None:
        st.error("Analysis cannot be generated. / 无法生成分析。")
        return

    stats_df = analysis["stats_df"]
    normality_df = analysis["normality_df"]
    group_df = analysis["group_df"]
    conclusions = analysis["conclusions"]

    cpk_values = pd.to_numeric(stats_df["Cpk"], errors="coerce")
    risk_count = int((cpk_values < 1.33).sum())
    normality_fail_count = int((normality_df["Normality Pass / 正态性通过"] == False).sum())  # noqa: E712
    col1, col2, col3 = st.columns(3)
    col1.metric("Items / 项目数", len(stats_df))
    col2.metric("Cpk Risk Items / Cpk 风险项", risk_count)
    col3.metric("Normality Failures / 正态性未通过", normality_fail_count)

    st.markdown("**Statistical Summary / 统计汇总**")
    st.dataframe(stats_df, use_container_width=True, hide_index=True)

    st.markdown("**Capability Conclusions / 能力结论**")
    for _, row in stats_df.iterrows():
        message = (
            f"**{row['Measurement / 测量项目']}**: {row['Capability Conclusion EN / 能力英文结论']}\n\n"
            f"{row['Capability Conclusion CN / 能力中文结论']}"
        )
        show_level_message(str(row.get("Action Level / 行动级别")), message)

    st.markdown("**Normality Test Results / 正态性检验结果**")
    st.dataframe(normality_df, use_container_width=True, hide_index=True)

    if group_df is not None and not group_df.empty:
        st.markdown("**Group Comparison / 组别比较**")
        st.dataframe(group_df, use_container_width=True, hide_index=True)

    st.markdown("**Auto Summary / 自动综合结论**")
    for item in conclusions:
        st.write(f"- {item['English']}")
        st.write(f"  {item['中文']}")

    st.markdown("**Charts / 图表**")
    df = st.session_state["current_df"]
    specs = st.session_state.get("specs", {})
    for column in st.session_state["measurement_columns"]:
        lsl, usl = valid_spec_limits(specs.get(column))
        with st.expander(f"{column}", expanded=True):
            st.caption(
                "Histogram shows distribution and normal curve; box plot helps inspect outliers; Q-Q plot helps judge normality. / "
                "直方图显示分布和正态曲线；箱线图用于观察离群值；Q-Q 图用于判断是否接近正态。"
            )
            chart_cols = st.columns(3)
            fig = histogram_with_normal_curve(df[column], column, lsl, usl)
            chart_cols[0].pyplot(fig, use_container_width=True)
            plt.close(fig)
            fig = box_plot(df[column], column)
            chart_cols[1].pyplot(fig, use_container_width=True)
            plt.close(fig)
            fig = qq_plot(df[column], column)
            chart_cols[2].pyplot(fig, use_container_width=True)
            plt.close(fig)


def build_chart_files() -> Dict[str, bytes]:
    df = st.session_state["current_df"]
    specs = st.session_state.get("specs", {})
    files: Dict[str, bytes] = {}
    for column in st.session_state.get("measurement_columns", []):
        lsl, usl = valid_spec_limits(specs.get(column))
        base = safe_filename(column)
        files[f"{base}_histogram_normal_curve.png"] = fig_to_png_bytes(
            histogram_with_normal_curve(df[column], column, lsl, usl)
        )
        files[f"{base}_box_plot.png"] = fig_to_png_bytes(box_plot(df[column], column))
        files[f"{base}_qq_plot.png"] = fig_to_png_bytes(qq_plot(df[column], column))
    return files


def render_download_page() -> None:
    st.subheader("Page 5: Download Report / 下载报告")
    if require_data() is None or not require_measurements():
        return

    analysis = run_analysis()
    if analysis is None:
        st.error("No analysis result is available. / 暂无分析结果。")
        return

    summary_bytes = create_summary_report(
        analysis["stats_df"],
        analysis["normality_df"],
        analysis["conclusions"],
        analysis["group_df"],
    )
    complete_bytes = create_complete_analysis_excel(
        analysis["cleaned_data"],
        analysis["stats_df"],
        analysis["specs_df"],
        analysis["normality_df"],
        analysis["group_df"],
    )
    chart_zip = create_charts_zip(build_chart_files())

    col1, col2, col3 = st.columns(3)
    col1.download_button(
        "Excel Summary Report / Excel 汇总报告",
        data=summary_bytes,
        file_name="qc_summary_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    col2.download_button(
        "Complete Analysis Excel / 完整分析 Excel",
        data=complete_bytes,
        file_name="qc_complete_analysis.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    col3.download_button(
        "PNG Charts ZIP / PNG 图表压缩包",
        data=chart_zip,
        file_name="qc_charts.zip",
        mime="application/zip",
        use_container_width=True,
    )


def main() -> None:
    init_state()
    selected_page = page_shell()
    if selected_page == PAGE_OPTIONS[0]:
        render_upload_page()
    elif selected_page == PAGE_OPTIONS[1]:
        render_select_columns_page()
    elif selected_page == PAGE_OPTIONS[2]:
        render_specification_page()
    elif selected_page == PAGE_OPTIONS[3]:
        render_dashboard_page()
    elif selected_page == PAGE_OPTIONS[4]:
        render_download_page()


if __name__ == "__main__":
    main()

