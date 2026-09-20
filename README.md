# Predictive Cloud Resource Optimizer

Forecasting a cloud server's load five minutes ahead with an LSTM, so that extra
capacity can be started **before** a traffic spike arrives instead of after it.

Ordinary auto-scaling is reactive: it waits until CPU crosses a threshold, then starts
another server — which takes 60–90 seconds to become ready, by which time users have
already felt the slowdown. This project predicts the next five minutes from the last five
hours of CPU, memory and network readings, so the new capacity is ready when the spike
lands. The end goal is one comparison: **proactive scaling (acts on the forecast) versus
reactive scaling (acts on the current reading)**, measured on spike response time,
over-provisioning and false alarms.

This repository currently contains **Phase 1, Steps 1.1–1.3**: the environment, the data
pipeline and the preprocessing that feeds the model. The LSTM itself is the next step.

---

## Setup

Requires **Python 3.10+**. Everything runs offline on a laptop CPU — no cloud account and
no GPU.

```bash
git clone https://github.com/KshCompiler/predictive-cloud-resource-optimizer.git
cd predictive-cloud-resource-optimizer

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
```

## Getting the data

The dataset is **not** in this repository — it is about 128 MB, which GitHub rejects.

1. Download the **GWA-T-12 Bitbrains** trace from
   <http://gwa.ewi.tudelft.nl/datasets/gwa-t-12-bitbrains>
2. Use the **fastStorage** part (1,250 VMs, one CSV per VM, semicolon-delimited).
3. Unzip the CSV files directly into `data/raw/`, so the paths look like
   `data/raw/270.csv`.

**Attribution — required in any report using this data:**

> Shen, S., van Beek, V., & Iosup, A. (2015). *Statistical Characterization of
> Business-Critical Workloads Hosted in Cloud Datacenters.* 15th IEEE/ACM International
> Symposium on Cluster, Cloud and Grid Computing (CCGrid), Shenzhen, China.
> Data courtesy of Bitbrains IT Services, published by TU Delft.

---

## What runs, and how

Run these from the project root, in order. Each file also works on its own.

### 1. Survey every VM and pick one

```bash
python -m utils.explore          # top 6 candidates
python -m utils.explore 10       # top 10
```

Measures all 1,250 VMs (about 45 seconds) and ranks them by five rules:

1. at least 2,000 readings (~7 days)
2. mean CPU between 20% and 60% — below is idle, above is always full, and either teaches
   the model one constant answer
3. highest CPU standard deviation first — the load must actually move
4. all three time splits (train / validation / test) must move, so the model is never
   tested on a flat line
5. memory and network must not be stuck on one value, since the model predicts them too

Rows where the VM was **switched off** (memory capacity of 0, every other number 0 too)
are skipped before anything is measured — counting them drags averages down and puts
unqualified VMs at the top of the ranking.

**Outputs:** `data/processed/vm_survey.csv`, `plots/top_vms.png`,
`plots/cpu_distribution.png`.

### 2. Clean the chosen VM

```bash
python -m utils.load_data data/raw/270.csv
```

Turns one raw file into the canonical four columns — `datetime, cpu, mem, net` — on a
strict 5-minute grid. Memory becomes a percentage of what the VM was given, network is
received plus transmitted. Gaps of up to 15 minutes are forward-filled; longer gaps are
deleted rather than invented.

**Outputs:** `data/processed/270_clean.csv`, `plots/270_week.png`.

### 3. Prepare the data for the model

```bash
python -m utils.preprocessing
```

In this exact order: chronological 70/15/15 split → MinMax scaling **fitted on training
data only** → 60-step sliding windows built inside each split → DataLoaders → checks.

**Outputs:** `models/scaler.joblib`, `plots/verify_pipeline.png`.

### 4. Rebuild the PDF reports (optional)

```bash
python report/build_report.py
```

---

## Current result

| | |
|---|---|
| VMs surveyed | 1,250 → 1,177 with enough data → 158 in band → **138 candidates** |
| Selected VM | **270** — mean CPU 46.81%, std 48.36, never switched off |
| Clean readings | 8,640 — exactly 30.0 days, no rows deleted, no time gaps |
| Windows | 5,988 train / 1,236 validation / 1,236 test |
| Batches of 64 | 94 / 20 / 20 |
| Pipeline check | shapes `(64, 60, 3)` and `(64, 3)`; scale round-trip error 0.00024 |
| No-leakage proof | training scales to 0.00–1.00 while test reaches **1.91** — only possible if the scaler never saw the test data |

Known limits, stated openly: VM 270 is a batch machine (47% of readings at 0–2%, 36%
above 98%), the top candidates are near-copies of each other, and only one VM and one
month of data are used.

---

## Documentation

Three PDFs are committed at the repository root, all generated from `report/`:

| File | Pages | For |
|---|---|---|
| `Quick_Summary.pdf` | 7 | Every point from the idea through preprocessing, in brief |
| `Phase1_Progress_Report.pdf` | 14 | What is built, with results and figures |
| `Project_Explained_Simply.pdf` | 23 | Every decision and **why**, in plain language, plus likely questions |

---

## Repository layout

```
data/raw/            1,250 original VM files  (not in git — download separately)
data/processed/      survey table and clean CSV  (not in git — regenerated in seconds)
models/              scaler.joblib, later the trained model  (not in git)
plots/               every figure the scripts produce  (not in git - regenerated)
report/              HTML sources, SVG diagrams and the PDF build script
utils/
  explore.py         survey all VMs, rank them, draw the comparison plots
  load_data.py       one raw VM file → clean 4-column table
  preprocessing.py   split, scale, window, batch, and verify
```

## What comes next

Step 1.4 builds the multivariate LSTM (input 60×3, output 3), then evaluation against a
naive baseline (1.5), the proactive-vs-reactive scaling engine (1.6), a Streamlit
dashboard (1.7) and integration (1.8).

**Phase 2** (next semester) inserts a 4-qubit PennyLane circuit between the LSTM's hidden
state and the final output layer, and compares it against this classical baseline — which
is why Phase 1 is kept clean and unchanged. PennyLane is deliberately **not** in
`requirements.txt` yet.

Still outstanding in Phase 1: `utils/generate_data.py`, the synthetic data generator with
spikes at known times, needed for the controlled comparison in Step 1.6.
