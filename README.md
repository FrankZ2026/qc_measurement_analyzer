# QC Measurement Capability Analyzer

A free local Streamlit web app for QC measurement capability analysis.

一个免费的本地 Streamlit 网页小程序，用于 QC 测量数据分析、Cp/Cpk 计算、正态性检验、分组比较和报告导出。

## Features / 功能

- Upload `.xlsx`, `.xls`, or `.csv` measurement data.
- 支持上传 `.xlsx`、`.xls`、`.csv` 测量数据。
- Read multiple Excel sheets and select the sheet to analyze.
- 支持多 Sheet Excel，并可选择需要分析的 Sheet。
- Automatically recommend likely numeric measurement columns while still allowing manual selection.
- 自动推荐可能的测量列，同时允许用户手动选择。
- Analyze one or multiple measurement items.
- 支持单项目或多项目分析。
- Input specifications by `Target ± Tolerance` or direct `LSL / USL`.
- 支持 `Target ± Tolerance` 或直接输入 `LSL / USL` 两种规格模式。
- Calculate sample size, mean, min, max, range, sample standard deviation, sample variance, Cp, Cpk, and Cpk grade.
- 计算样本量、均值、最小值、最大值、极差、样本标准差、样本方差、Cp、Cpk 和 Cpk 等级。
- Run Shapiro-Wilk and Anderson-Darling normality tests.
- 执行 Shapiro-Wilk 和 Anderson-Darling 正态性检验。
- Generate histogram with normal curve, box plot, and Q-Q plot.
- 生成直方图叠加正态曲线、箱线图和 Q-Q 图。
- Optional group analysis by batch, PO, SKU, supplier, date, machine, operator, sheet name, or another column.
- 支持按批次、PO、SKU、供应商、日期、机台、操作员、Sheet Name 或其他列进行可选分组分析。
- Export summary Excel, complete analysis Excel, and PNG charts ZIP.
- 支持导出汇总 Excel、完整分析 Excel 和 PNG 图表压缩包。

## Installation / 安装

Open a terminal in this project folder:

在本项目文件夹中打开终端：

```bash
pip install -r requirements.txt
```

If you want to keep dependencies isolated, create a virtual environment first:

如果你希望隔离依赖，建议先创建虚拟环境：

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run / 运行

```bash
streamlit run app.py
```

After Streamlit starts, open the local URL shown in the terminal, usually:

Streamlit 启动后，打开终端显示的本地地址，通常是：

```text
http://localhost:8501
```

## How to Upload Data / 如何上传数据

1. Go to `Page 1: Upload Data / 上传数据`.
2. Upload an Excel or CSV file.
3. If the Excel file has multiple sheets, select the sheet to analyze.
4. Preview the first 100 rows to confirm the data was read correctly.

1. 进入 `Page 1: Upload Data / 上传数据`。
2. 上传 Excel 或 CSV 文件。
3. 如果 Excel 有多个 Sheet，选择需要分析的 Sheet。
4. 预览前 100 行，确认数据读取正确。

## How to Select Measurement Columns / 如何选择测量列

Go to `Page 2: Select Measurement Columns / 选择测量列`.

进入 `Page 2: Select Measurement Columns / 选择测量列`。

The app recommends columns where more than 70% of non-empty values can be converted to numbers. Obvious ID or sequence columns are excluded from the recommendation, but they remain available for manual selection.

系统会推荐非空值中超过 70% 可转为数字的列。明显的 ID 或序号列不会自动推荐，但仍可手动选择。

## How to Input Specification / 如何输入规格

Go to `Page 3: Input Specification / 输入规格`.

进入 `Page 3: Input Specification / 输入规格`。

Two modes are available:

支持两种模式：

- `Target ± Tolerance`: enter target and tolerance. The app calculates `LSL = Target - Tolerance` and `USL = Target + Tolerance`.
- `Target ± Tolerance`：输入标准值和公差，系统自动计算 `LSL = Target - Tolerance`、`USL = Target + Tolerance`。
- `LSL / USL`: enter lower and upper specification limits directly.
- `LSL / USL`：直接输入规格下限和规格上限。

Each measurement column can have its own specification. If no valid specification is entered, basic statistics are still calculated, but Cp/Cpk will show as not available.

每个测量列都可以有独立规格。如果未输入有效规格，系统仍会计算基础统计数据，但 Cp/Cpk 会显示为不适用。

## How to Understand Cpk / 如何理解 Cpk

Cp and Cpk are calculated with sample standard deviation, equivalent to Excel `STDEV.S`.

Cp 和 Cpk 默认基于样本标准差计算，等同于 Excel `STDEV.S`。

Formulas:

公式：

```text
Cp = (USL - LSL) / (6 * sample_std)
CPU = (USL - Mean) / (3 * sample_std)
CPL = (Mean - LSL) / (3 * sample_std)
Cpk = min(CPU, CPL)
```

Cpk grade:

Cpk 等级：

- `Cpk >= 1.67`: Excellent / 优秀
- `1.33 <= Cpk < 1.67`: Good / 良好
- `1.00 <= Cpk < 1.33`: Marginal / 边缘可接受
- `Cpk < 1.00`: Poor / 高风险
- unavailable: Not Available / 不适用

## How to Understand Normality Tests / 如何理解正态性检验

The app includes:

系统包含：

- Shapiro-Wilk test: if p-value is lower than 0.05, the data may not be normally distributed.
- Shapiro-Wilk 检验：如果 p-value 低于 0.05，数据可能不符合正态分布。
- Anderson-Darling test: compares the statistic with the 5% critical value.
- Anderson-Darling 检验：将 statistic 与 5% 临界值比较。

If normality fails, Cpk should be interpreted with caution because traditional Cp/Cpk assumes a stable and roughly normal process distribution.

如果正态性检验未通过，需要谨慎解读 Cpk，因为传统 Cp/Cpk 通常假设过程稳定且数据近似正态。

## Notes / 注意事项

- Cpk is based on sample standard deviation by default.
- Cpk 默认基于样本标准差。
- If data is not normally distributed, Cpk should be interpreted carefully.
- 如果数据不符合正态分布，Cpk 需要谨慎解读。
- Small sample sizes reduce result reliability.
- 样本量过小会影响结果可靠性。
- If sample size is less than 2, standard deviation, variance, Cp, and Cpk are not calculated.
- 如果样本量小于 2，不计算标准差、方差、Cp 和 Cpk。
- If sample size is less than 3, Shapiro-Wilk normality test is not performed.
- 如果样本量小于 3，不执行 Shapiro-Wilk 正态性检验。

## Troubleshooting / 报错排查

- If Streamlit is not found, run `pip install -r requirements.txt` again in the active Python environment.
- 如果提示找不到 Streamlit，请确认当前 Python 环境中已经执行 `pip install -r requirements.txt`。
- If `.xls` files fail to read, confirm `xlrd` is installed.
- 如果 `.xls` 文件读取失败，请确认已安装 `xlrd`。
- If Excel export fails, confirm `xlsxwriter` is installed.
- 如果 Excel 导出失败，请确认已安装 `xlsxwriter`。
- If charts do not display, confirm `matplotlib` and `scipy` are installed.
- 如果图表无法显示，请确认已安装 `matplotlib` 和 `scipy`。
- If Cp/Cpk is not available, check that LSL and USL are both entered and that `LSL < USL`.
- 如果 Cp/Cpk 不适用，请检查是否同时输入 LSL 和 USL，并确保 `LSL < USL`。
- If normality results are not available, check whether the numeric sample size is at least 3.
- 如果正态性结果不适用，请检查数值样本量是否至少为 3。

