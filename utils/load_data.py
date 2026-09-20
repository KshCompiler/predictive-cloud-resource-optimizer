"""
This file takes one raw Bitbrains file (a messy CSV with 11 columns) and
turns it into a clean, simple table with just 4 columns:

    datetime (index) | cpu (0-100) | mem (0-100) | net (KB/s)

The clean table gets saved to data/processed/<vm>_clean.csv

Run it like this:
    python -m utils.load_data data/raw/270.csv
"""

import os
import sys

import pandas as pd
import matplotlib.pyplot as plt

# The raw file has long, awkward column names.
# This dictionary says: "if you see this long name, rename it to this short one".
def ensure_folder(filepath):
    """
    Make the folder a file is about to be written into, if it is missing.

    data/processed, models and plots are all left out of git - they only hold
    generated files - so a fresh clone does not have them and saving would
    fail. This creates them on demand.
    """
    folder = os.path.dirname(filepath)
    if folder:
        os.makedirs(folder, exist_ok=True)


COLUMN_NAMES = {
    "Timestamp [ms]": "timestamp",
    "CPU usage [%]": "cpu_percent",
    "Memory capacity provisioned [KB]": "mem_total",
    "Memory usage [KB]": "mem_used",
    "Network received throughput [KB/s]": "net_in",
    "Network transmitted throughput [KB/s]": "net_out",
}

# The data is recorded every 5 minutes.
STEPS_IN_ONE_DAY = 288     # 24 hours has 288 five-minute slots
STEPS_IN_ONE_WEEK = 2016   # 7 days
MAX_GAP_TO_FIX = 3         # if up to 3 slots (15 minutes) are missing, we fix them


def load_vm(filepath, save=True):
    """
    Take the path to one raw VM file (like 'data/raw/214.csv')
    and return a clean table with just cpu, mem, net.
    """

    # STEP 1: Open the file.
    # Normal CSV files use a comma (,) to separate columns.
    # This dataset uses a semicolon (;) instead.
    df = pd.read_csv(filepath, sep=";")

    # STEP 2: Clean up and rename the column names.
    # Some column names have extra spaces around them, so remove those first.
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns=COLUMN_NAMES)

    # STEP 3: Fix the timestamp column and turn it into real dates.
    # The column is called "Timestamp [ms]" (milliseconds), but the numbers
    # inside it are actually in seconds, not milliseconds. We can tell because
    # a millisecond number would be about 1000x bigger than what is in the file.
    if df["timestamp"].max() < 1e11:
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
    else:
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")

    # Make the date column the index (the "label" for each row),
    # and put the rows in time order.
    df = df.set_index("datetime")
    df = df.sort_index()

    # STEP 4: Build the 3 columns we actually care about.
    clean = pd.DataFrame(index=df.index)

    # cpu: this is already a percentage (0 to 100), so just copy it.
    # A few rows go slightly above 100 by mistake in the raw data,
    # so we push any value back down to 100 if it goes over.
    clean["cpu"] = df["cpu_percent"].clip(0, 100)

    # mem: the raw file gives memory in KB, which is a huge number
    # (millions), while cpu is a small number (0 to 100).
    # If we mixed those scales, the model would think memory matters
    # way more than cpu, just because its numbers are bigger.
    # So we turn memory into a percentage too: used / total * 100.
    clean["mem"] = (df["mem_used"] / df["mem_total"] * 100).clip(0, 100)

    # net: add the incoming and outgoing network traffic together.
    # We only care about how much total activity there is, not the direction.
    clean["net"] = df["net_in"] + df["net_out"]

    # STEP 5: Put every row exactly 5 minutes apart.
    # The raw timestamps are not perfectly spaced (sometimes 4 minutes,
    # sometimes 6). Resampling snaps every row onto a clean 5-minute
    # timeline. If a time slot has no data, it becomes an empty (blank) row.
    clean = clean.resample("5min").mean()

    # A row counts as "blank" if ANY of the 3 columns is empty - not just cpu.
    # (This matters: sometimes cpu has a real number but mem or net is empty,
    # for example when a VM's memory capacity reads 0 near the end of its
    # life and mem = used/total breaks. dropna() below removes a row if any
    # column is empty, so we must count blanks the same way, or this report
    # will under-count what actually got deleted.)
    blanks_before = clean.isna().any(axis=1).sum()

    # Fix SHORT blanks (up to 15 minutes) by copying the last known value
    # forward. This is a small, safe guess.
    clean = clean.ffill(limit=MAX_GAP_TO_FIX)

    # Any blank row still left is a LONG gap (the monitoring was broken for
    # a while). We do not guess those values - we just delete those rows.
    # Guessing hours of fake data would teach the model the wrong thing.
    blanks_after = clean.isna().any(axis=1).sum()
    clean = clean.dropna()

    print(f"rows: {len(clean)}   ({len(clean) / STEPS_IN_ONE_DAY:.1f} days)")
    print(f"from: {clean.index.min()}   to: {clean.index.max()}")
    print(f"short gaps fixed: {blanks_before - blanks_after}")
    print(f"long-gap rows deleted: {blanks_after}")

    # STEP 6: Save the clean table to a new file.
    if save:
        # Turn "data/raw/214.csv" into just "214"
        vm_name = filepath.split("/")[-1].split("\\")[-1].replace(".csv", "")
        out_path = f"data/processed/{vm_name}_clean.csv"
        ensure_folder(out_path)
        clean.to_csv(out_path)
        print(f"saved: {out_path}")

    return clean


def load_clean(filepath):
    """Read an already-clean CSV file back into a table."""
    return pd.read_csv(filepath, index_col=0, parse_dates=True)


def plot_week(df, title, save_path=None):
    """
    Draw 3 charts (cpu, mem, net) for the first week of data.

    Nothing is written to disk unless save_path is given. The figures belong
    in the PDFs, which embed their own copies, so we do not leave PNG files
    lying around the project folder.
    """

    week = df.iloc[:STEPS_IN_ONE_WEEK]

    fig, axes = plt.subplots(3, 1, figsize=(14, 8), sharex=True)

    axes[0].plot(week.index, week["cpu"], color="blue", linewidth=0.8)
    axes[0].set_ylabel("CPU %")

    axes[1].plot(week.index, week["mem"], color="orange", linewidth=0.8)
    axes[1].set_ylabel("Memory %")

    axes[2].plot(week.index, week["net"], color="green", linewidth=0.8)
    axes[2].set_ylabel("Network KB/s")

    for ax in axes:
        ax.grid(alpha=0.3)
    axes[0].set_title(f"{title} - one week")

    fig.tight_layout()
    if save_path:
        ensure_folder(save_path)
        fig.savefig(save_path, dpi=130)
        print(f"saved: {save_path}")
    return fig


if __name__ == "__main__":
    # If someone runs "python -m utils.load_data data/raw/105.csv",
    # use that file. Otherwise, use 270.csv (the VM we picked) by default.
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        filepath = "data/raw/270.csv"

    df = load_vm(filepath)

    print("\n--- first 5 rows ---")
    print(df.head())

    print("\n--- column info ---")
    df.info()

    print("\n--- basic statistics ---")
    print(df.describe())

    vm_name = filepath.split("/")[-1].replace(".csv", "")
    plot_week(df, f"VM {vm_name}")
    plt.show()
