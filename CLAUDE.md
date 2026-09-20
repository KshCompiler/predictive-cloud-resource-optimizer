# Predictive Cloud Resource Optimizer — Build Brief (Steps 1.1 to 1.3)

---

## What this project is and why it exists

Cloud servers run applications whose load varies over time — CPU usage, memory consumption,
and network traffic go up and down depending on how many users are hitting the system and
what jobs are running.

Traditional auto-scaling is **reactive**: it watches live CPU, and when it crosses a
threshold (say 75%) it triggers a scale-up. The problem is that by the time the spike is
detected, a new server is requested, and it boots and joins the pool — 60 to 90 seconds have
passed. The spike has already hit users.

This project builds a **proactive** system: instead of watching what is happening now, it
forecasts what is about to happen 5 minutes ahead using an LSTM neural network, and scales
resources before the spike arrives.

The central result this whole project exists to produce is a comparison table:

    Proactive scaling (acts on forecast) vs Reactive scaling (acts on actual values)
    → measured on: spike response time, over-provisioning %, false positive rate

Everything built — the data pipeline, the LSTM, the dashboard — exists to make that
comparison credible and demonstrable.

---

## Two-phase structure

**Phase 1 (current, this semester, mini project):** fully working classical LSTM system,
end-to-end, with a Streamlit dashboard. This is what Steps 1.1–1.8 build.

**Phase 2 (next semester, BTP):** a 4-qubit PennyLane quantum circuit is inserted between
the LSTM output and the final prediction layer. The Phase 1 classical system becomes the
permanent comparison baseline. Nothing from Phase 1 is thrown away or restructured.

Write every module with this in mind: the quantum layer will slot in at one specific point
(LSTM hidden state → quantum circuit → Dense prediction layer). Keep that seam clean.

---

## Environment constraints

- Python 3.10+, venv, local laptop CPU. No cloud account. No GPU. No quantum hardware.
- Everything runs offline on the developer's machine.
- Core libraries: numpy, pandas, matplotlib, scikit-learn, torch, streamlit, plotly, joblib
- Phase 2 will add: pennylane, pennylane-lightning (do not install yet)

---

## The dataset

### What Bitbrains is

Bitbrains was a Dutch managed hosting company whose clients were major enterprises — banks,
insurance companies, financial institutions. They ran heavy workloads: end-of-quarter
solvency reports, risk calculations, large batch jobs, transactional databases.

Researchers at Delft University collected real telemetry logs from Bitbrains' datacenter,
anonymised them, and published them as **GWA-T-12 Bitbrains** — an open dataset used
extensively in cloud resource management research.

Download: `gwa.ewi.tudelft.nl/datasets/gwa-t-12-bitbrains`
Use the **fastStorage** trace: 1,250 VMs, ~128MB, 5-minute intervals.

Required attribution in the report:
> Shen, van Beek & Iosup, "Statistical Characterization of Business-Critical Workloads
> Hosted in Cloud Datacenters", CCGrid 2015. Data courtesy of Bitbrains IT Services.

### Physical structure of the dataset

One CSV file per VM, semicolon-delimited. Filenames are anonymised VM IDs (e.g. 105.csv).
Columns:

    Timestamp [ms]                         <- Unix time in milliseconds
    CPU cores                              <- how many cores allocated
    CPU capacity provisioned [MHZ]         <- total CPU power allocated
    CPU usage [MHZ]                        <- actual CPU consumed
    CPU usage [%]                          <- USE THIS → your `cpu` column
    Memory capacity provisioned [KB]       <- total RAM allocated → USE FOR DENOMINATOR
    Memory usage [KB]                      <- actual RAM used → USE THIS
    Disk read throughput [KB/s]            <- ignore
    Disk write throughput [KB/s]           <- ignore
    Network received throughput [KB/s]     <- USE THIS
    Network transmitted throughput [KB/s]  <- USE THIS

### The four-column output format

Every downstream module — preprocessing, model, scaling engine, dashboard — works with
exactly this structure:

    datetime (index)  |  cpu (float, 0–100)  |  mem (float, 0–100)  |  net (float, KB/s)

- `cpu` = CPU usage [%], taken directly
- `mem` = (Memory usage [KB] / Memory capacity provisioned [KB]) × 100
  Reason: memory usage in raw KB is in the millions; CPU is a small percentage. They need
  the same scale or the LSTM's loss function treats memory as far more important.
- `net` = Network received + Network transmitted, summed
  Reason: for load forecasting, total network activity is the signal; direction doesn't
  matter here.

Both the real data loader and the synthetic generator must output this identical format.
Everything downstream is then source-agnostic.

### Why the three metrics are used together

In real systems, when a financial batch job fires:
- CPU climbs because the calculation is running
- Memory climbs because data is loaded into RAM
- Network climbs because data is pulled from databases or results are sent out

They don't move identically — memory responds slower, network may lag CPU by a few steps —
but they move together. A multivariate LSTM that sees all three simultaneously has more
signal than three separate single-metric models. It learns the correlations between channels,
not just each channel's own history.

### VM selection problem

1,250 VMs sounds like a lot of training data. It is not — most VMs in this dataset are
near-idle. A near-idle VM produces a trace like: 2%, 2%, 3%, 2%, 1%, 2%...

An LSTM trained on that learns to predict "approximately 2%" every time. It will score
excellent RMSE because the answer is almost always 2%, but it has learned nothing about real
load dynamics. This is the most common mistake when working with this dataset.

You need a VM with:
- High CPU standard deviation (volatile, not flat)
- Mean CPU roughly in the 20–60% band (not near-idle, not pegged at 100%)
- Visible daily rhythm when plotted — peaks in business hours, troughs at night

### Synthetic data (secondary, not a fallback)

Keep a synthetic generator alongside the real data loader. They output the same four-column
format so everything downstream treats them identically.

The synthetic generator exists for one specific reason: the reactive-vs-proactive comparison
in Step 1.6 needs deliberate, controllable traffic spikes to demonstrate the proactive
advantage clearly. Real traces give you whatever spikes happened to occur naturally, which
may be sparse or mild. The synthetic generator lets you construct the exact stress scenario
you need.

Real data proves the system works on realistic workloads. Synthetic data proves the
mechanism in a controlled demonstration.

---

## Repository structure

    cloud-optimizer/
    ├── data/
    │   ├── raw/                 # Bitbrains CSVs — never modified, gitignored
    │   └── processed/           # cleaned four-column CSVs — gitignored
    ├── models/                  # trained .pt checkpoints — gitignored
    ├── notebooks/               # exploration only, never the source of truth
    ├── dashboard/               # Streamlit app (Step 1.7, do not build yet)
    ├── utils/
    │   ├── __init__.py
    │   ├── explore.py           # VM survey and selection
    │   ├── load_data.py         # Bitbrains CSV → clean 4-column DataFrame
    │   ├── generate_data.py     # synthetic data generator
    │   └── preprocessing.py    # scaling, windowing, DataLoaders
    ├── requirements.txt
    ├── .gitignore
    └── README.md

The data folders are gitignored because the fastStorage trace is ~128MB and GitHub will
reject it. Document the download URL in the README so anyone cloning the repo knows where to
get it.

---

## Step 1.1 — Environment and repo skeleton

### Goal
A clean, reproducible project structure that anyone can clone and run without asking
questions.

### What to do

1. Install Python 3.10+. Create and activate a virtual environment:
       python -m venv venv
       source venv/bin/activate          # Windows: venv\Scripts\activate

2. Create the full folder structure shown above.

3. Create `utils/__init__.py` (empty file — makes utils a proper Python package).

4. Write `.gitignore` BEFORE the first commit:
       venv/
       __pycache__/
       .ipynb_checkpoints/
       data/raw/*
       data/processed/*
       *.pt
       *.joblib

5. Install all libraries:
       pip install numpy pandas matplotlib scikit-learn torch streamlit plotly joblib
       pip freeze > requirements.txt

6. Write README.md containing:
   - Project title
   - One paragraph: what the project does and why (forecasts cloud VM load using LSTM,
     enables proactive auto-scaling, proves it beats reactive scaling)
   - Setup instructions: clone, create venv, pip install -r requirements.txt
   - Dataset section: where to download Bitbrains fastStorage, which folder to unzip into,
     attribution requirement
   - What runs and how (will grow as modules are added)

7. git init, create GitHub repo, make first commit, push.

### Done when
A fresh clone of the repo, followed by `pip install -r requirements.txt`, gives a fully
working environment. The README tells a stranger exactly where to get the data and how to
set up.

---

## Step 1.2 — Data acquisition and preparation

### Goal
A clean four-column time series ready for preprocessing. A verified real VM with interesting
load. A synthetic generator producing the same format for controlled experiments.

### File: utils/explore.py

Purpose: survey the dataset so you can pick a good VM rather than just grabbing the first
file.

What it does:
- Loops over ALL VM files in data/raw/ (not just the first 100–200 — see note below)
- For each file: reads the CSV, parses CPU usage [%], computes mean, standard deviation, and
  row count
- Prints a table sorted by standard deviation descending — highest volatility at the top
- Saves the full table to data/processed/vm_survey.csv

Target: high std deviation, mean roughly 20–60%, visible daily peaks and troughs when
plotted. Reject near-idle VMs (flat trace), reject constantly-pegged VMs (always at 90%+).

**Correction from the original brief (learned by actually running this):** scanning only
"the first 100–200 files" does not give a representative sample. VM filenames sort
alphabetically, not numerically (`1.csv, 10.csv, 100.csv, 1000.csv, ... , 11.csv, 110.csv...`),
so "the first 150 files" by that ordering turned out to be a biased slice of the dataset —
on this dataset it produced zero VMs in the 20–60% mean band. Scanning all 1,250 files found
152 good candidates and took about a minute (no real cost), so scan everything rather than a
partial sample.

**Correction #2:** dropped the "plot top 5 candidates" step. The ranked table (mean, std,
good_range) is enough on its own to pick a VM — a plot of the winning VM's data still happens
later, in load_data.py, where it's a required deliverable (see Step 1.2 "Done when" below).

This script is run once manually. It produces a ranked table. The developer picks a VM
filename from the output. That filename is then hardcoded into a config or passed as an
argument to load_data.py.

### File: utils/load_data.py

Purpose: convert one raw Bitbrains VM CSV into the clean four-column format.

Function signature:
    def load_vm(filepath: str, save: bool = True) -> pd.DataFrame

What it does, in order:
1. Read the semicolon-delimited CSV into a DataFrame
2. Rename columns to short internal names for easy access
3. Convert Timestamp [ms] from Unix milliseconds to pandas datetime
4. Set datetime as the DataFrame index
5. Compute cpu: take CPU usage [%] directly, clip to 0–100
6. Compute mem: (Memory usage [KB] / Memory capacity provisioned [KB]) × 100, clip to 0–100
7. Compute net: Network received [KB/s] + Network transmitted [KB/s]
8. Keep only cpu, mem, net columns
9. Resample to a strict 5-minute DatetimeIndex using .resample('5min'):
   - Forward-fill gaps of up to 3 consecutive missing steps (15 minutes)
   - For longer gaps: log a warning with the gap duration, do not silently interpolate
   - Reason: real traces have gaps from monitoring outages. Short gaps are fine to fill.
     Long gaps (hours) would fabricate data and corrupt the time series.
10. If save=True: write to data/processed/<vm_id>_clean.csv
11. Return the clean DataFrame

The __main__ block: when run as a script, load the chosen VM, print head(), print info(),
print describe(), and show a Matplotlib plot of one full week of all three metrics.

### File: utils/generate_data.py

Purpose: generate synthetic CPU/Memory/Network time series in the exact same four-column
format as load_data.py output.

The synthetic data must be correlated across the three channels. Independent random metrics
are the giveaway of a naive simulation:
- cpu: base_load + daily_sine + optional_weekly_sine + gaussian_noise + injected_spikes
- mem: damped function of cpu with a small lag — mem[t] = 0.7 × cpu[t-1] + 15 + small_noise
  Reason: memory responds to what CPU just did, not what it's doing right now
- net: lags cpu by 2–3 steps — net[t] = 0.9 × cpu[t-3] + gaussian_noise
  Reason: network activity follows computation, not simultaneous with it

Spike injection: at random intervals, add a sharp step increase lasting 10–60 timesteps.
This is what the reactive-vs-proactive comparison needs — a deliberate, known spike where
you can measure how early the proactive system acted.

Fixed random seed (default: 42) so results are reproducible across runs.

Output: saves to data/processed/synthetic.csv in the same four-column format.

The __main__ block: generate 60 days, plot two weeks, save the CSV.

### Done when
- explore.py scans all VM files, prints a ranked table, and a VM has been selected from it
- load_data.py produces a clean CSV for the chosen VM, and the one-week plot of all three
  metrics shows clear daily rhythm — peaks in business hours, troughs at night
- generate_data.py produces a CSV that looks visually similar to the real trace when plotted
- Both CSVs have identical column structure: datetime index, cpu (0–100), mem (0–100),
  net (float)
- Save the load_data.py and generate_data.py plots — they go in the project report as
  evidence of data quality

---

## Step 1.3 — Preprocessing pipeline

### Goal
Convert either CSV (real or synthetic) into batched PyTorch tensors the LSTM can train on.
Output: three DataLoaders (train, val, test) and a saved scaler.

### File: utils/preprocessing.py

**The operation order is critical. The original project roadmap has the order wrong.
Follow this order exactly:**

#### Step A: Chronological split FIRST

Split the raw time series into train / val / test by position, not randomly:
- Train: first 70% of timesteps
- Val:   next 15%
- Test:  final 15%

Never shuffle the raw series before splitting. Never use train_test_split with shuffle=True
on time series data. The model must only ever see the past — if any future data leaks into
training, every evaluation metric becomes a lie.

#### Step B: Fit the scaler on TRAINING data only

    from sklearn.preprocessing import MinMaxScaler
    scaler = MinMaxScaler()
    train_scaled = scaler.fit_transform(train)   # fit AND transform
    val_scaled   = scaler.transform(val)         # transform only
    test_scaled  = scaler.transform(test)        # transform only

Why: if you fit the scaler on the full series before splitting, it uses the minimum and
maximum values from the test set to set the scaling parameters. The model has then
indirectly seen test set information during training. This is data leakage. Evaluation
metrics will be optimistically wrong. Examiners specifically test for this.

Save the fitted scaler:
    import joblib
    joblib.dump(scaler, 'models/scaler.joblib')

The dashboard (Step 1.7) needs this to inverse-transform the model's 0–1 predictions back
into readable CPU%, memory%, and KB/s values for display.

#### Step C: Build sliding windows INSIDE each split independently

Window size: 60 timesteps (= 5 hours at 5-minute intervals)
Target: 1 timestep ahead

For each split, produce:
- X: shape (samples, 60, 3) — each sample is 60 consecutive timesteps of all 3 metrics
- y: shape (samples, 3)     — the single next timestep for all 3 metrics

The windowing function:
    def make_windows(data: np.ndarray, window: int = 60):
        X, y = [], []
        for i in range(len(data) - window):
            X.append(data[i : i + window])
            y.append(data[i + window])
        return np.array(X), np.array(y)

Call this separately on train_scaled, val_scaled, test_scaled. Never window across the
boundary between splits — a window that contains both training and test timesteps is another
form of leakage.

#### Step D: DataLoaders

    import torch
    from torch.utils.data import TensorDataset, DataLoader

    def to_loader(X, y, batch_size=64, shuffle=False):
        X_t = torch.FloatTensor(X)
        y_t = torch.FloatTensor(y)
        return DataLoader(TensorDataset(X_t, y_t), batch_size=batch_size, shuffle=shuffle)

    train_loader = to_loader(X_train, y_train, shuffle=True)   # shuffle windows, not series
    val_loader   = to_loader(X_val,   y_val,   shuffle=False)
    test_loader  = to_loader(X_test,  y_test,  shuffle=False)

Note: shuffle=True on the training DataLoader shuffles the order of windows presented to the
model during training. This is correct and helpful. It is not the same as shuffling the raw
time series. Val and test are never shuffled — they must be evaluated in chronological order.

#### Step E: Verification check (mandatory, not optional)

Write this as a runnable function called verify_pipeline():

1. Print shapes of one batch from each loader:
       for X_batch, y_batch in train_loader:
           print(X_batch.shape)   # should be torch.Size([64, 60, 3])
           print(y_batch.shape)   # should be torch.Size([64, 3])
           break

2. Inverse-transform check: take window index 0 from X_train, inverse-transform it using
   the saved scaler, and plot it against the original CSV rows 0–59. The two lines should
   sit exactly on top of each other. If they don't, the windowing or scaling logic has a
   bug.

3. Print a data summary: how many windows in each split, what the CPU mean and std are
   after inverse-transforming the test set.

Windowing bugs are silent. They don't raise exceptions. They just quietly produce a dataset
the model cannot learn from, and you'll spend days blaming the model architecture when the
problem is here. Run this check and confirm it passes before proceeding to Step 1.4.

### Public API of preprocessing.py

Other modules should be able to call:

    from utils.preprocessing import build_pipeline

    train_loader, val_loader, test_loader, scaler = build_pipeline(
        filepath='data/processed/105_clean.csv',
        window=60,
        batch_size=64
    )

This one function does the full split → scale → window → DataLoader pipeline and returns
everything needed for training and evaluation.

### Done when
- build_pipeline() runs without errors on both the real VM CSV and the synthetic CSV
- verify_pipeline() prints correct batch shapes: torch.Size([64, 60, 3]) and
  torch.Size([64, 3])
- Inverse-transform plot of window 0 overlays exactly on the source CSV rows
- scaler.joblib is saved to models/
- The __main__ block demonstrates the full pipeline running standalone in under 30 seconds

---

## Working rules for Claude Code

- Complete each step's "done when" criteria before starting the next step.
- Every module must have a `if __name__ == "__main__":` block that demonstrates it working
  standalone. Viva examiners ask "show me this part running independently."
- Commit after each completed step with a message describing what was built and verified.
- Prefer readable, explainable code over clever code. Every design choice — window size of
  60, batch size of 64, memory lag of 1 step — must be justifiable out loud in a viva.
- Do not install pennylane yet. Do not stub out Phase 2 code. Build only what is listed here.
- If the Bitbrains data is not yet downloaded, build and verify with the synthetic generator
  first, then swap in the real data. The format is identical so nothing changes downstream.

---

## What comes next (do not build yet)

Step 1.4: Multivariate LSTM model (input: 60×3, output: 3) — build, train, save checkpoint
Step 1.5: Evaluation — RMSE/MAE/MAPE per metric, naive baseline comparison, plots
Step 1.6: Auto-scaling engine — proactive (forecast-driven) vs reactive (actual-driven)
Step 1.7: Streamlit dashboard — predicted vs actual charts, KPI cards, scaling event log
Step 1.8: Integration, end-to-end testing, documentation, mini-project report

