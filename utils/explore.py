"""
Look at many VM files and find a good one to train on.

Why we need this:
The dataset has 1250 VMs but most of them are almost idle. Their CPU looks like
2%, 2%, 3%, 2%, 1%. If we train an LSTM on that, it learns to always answer "2%".
It will get a great score, because the answer really is almost always 2%,
but it has learned nothing about how load actually changes.

So we rank the VMs by how much their CPU moves (standard deviation) and
pick a busy one.

We want a VM with:
  - high standard deviation  (the CPU actually moves)
  - mean CPU around 20-60%   (not idle, not stuck at 100%)
  - a clear daily pattern    (busy in the day, quiet at night)

Run it once, by hand:
    python -m utils.explore
"""

import glob
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from utils.load_data import load_vm, ensure_folder, STEPS_IN_ONE_WEEK

HOW_MANY_FILES = 1250    # how many VM files to check (there are 1250 total)
MIN_ROWS = 2000          # skip VMs with too little data to see a pattern
HOW_MANY_TO_PLOT = 6     # how many of the best candidates to draw
MIN_SPLIT_STD = 10       # each of train/val/test must move at least this much
MAX_FLAT_SHARE = 0.90    # a metric stuck on one value this often counts as dead


def read_cpu(filepath):
    """
    Read the 'CPU usage [%]' column of one raw VM file, skipping the rows
    where the VM was switched off.

    Returns (cpu, off_rows): the readings, and how many rows were skipped.

    Why skip them:
    When a VM is switched off, the datacenter still writes a row every 5
    minutes, but every number in it is 0 - including the amount of memory the
    VM was given. Those rows do not mean "the VM was 0% busy", they mean "the
    VM was not running at all".

    Counting them drags the average down. VM 214 was off for its last 4.6 days,
    which made its average CPU look like 44% when the machine was really
    running at 68% while it was on. That is the difference between landing
    inside our 20-60% band and outside it, so these rows must go before we
    measure anything.
    """
    # Bitbrains files use ';' as the separator, not ','.
    df = pd.read_csv(filepath, sep=";")

    # Column names have extra spaces/tabs around them, so clean them up.
    df.columns = [c.strip() for c in df.columns]

    # "Memory given to the VM = 0" is the marker of a switched-off row.
    # (Checked across the dataset: in every such row, all the other numbers
    # are 0 too.)
    is_on = df["Memory capacity provisioned [KB]"] > 0
    off_rows = int((~is_on).sum())

    return df.loc[is_on, "CPU usage [%]"].dropna(), off_rows


def read_metrics(filepath):
    """
    Read all three metrics of one VM - cpu, mem, net - skipping the rows where
    the VM was switched off. Returns (table, off_rows).

    Same three columns load_data.py produces, so what we measure here is what
    the model will actually be trained on.
    """
    df = pd.read_csv(filepath, sep=";")
    df.columns = [c.strip() for c in df.columns]

    is_on = df["Memory capacity provisioned [KB]"] > 0
    off_rows = int((~is_on).sum())
    d = df[is_on]

    out = pd.DataFrame({
        "cpu": d["CPU usage [%]"],
        "mem": d["Memory usage [KB]"] / d["Memory capacity provisioned [KB]"] * 100,
        "net": (d["Network received throughput [KB/s]"]
                + d["Network transmitted throughput [KB/s]"]),
    }).dropna()

    return out, off_rows


def is_alive(series):
    """
    Is this metric actually carrying information, or is it stuck?

    A metric is "dead" if it never changes, or if one single value covers
    almost every reading. We check this because the model predicts all three
    metrics: a VM can have perfect CPU movement while its memory or network
    column is one flat line, and then we would be training the model to
    predict a column with nothing in it.

    The 90% line is not a guess. Measured on this dataset: healthy VMs repeat
    their most common value 20-47% of the time, while stuck ones reach 85%+.
    """
    if series.std() == 0:
        return False
    most_common_share = series.round(2).value_counts(normalize=True).iloc[0]
    return most_common_share <= MAX_FLAT_SHARE


def split_three_ways(series):
    """
    Cut a series into train / validation / test by position, the same
    70% / 15% / 15% that preprocessing.py uses later.
    """
    n = len(series)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)
    return series[:train_end], series[train_end:val_end], series[val_end:]


def survey(how_many=HOW_MANY_FILES):
    """Read the first N VM files and measure the CPU of each one."""

    files = sorted(glob.glob("data/raw/*.csv"))[:how_many]

    if len(files) == 0:
        print("No files found in data/raw/")
        print("Download the Bitbrains fastStorage data and unzip it there.")
        return None

    print(f"Checking {len(files)} VM files...\n")

    results = []
    for filepath in files:
        # Switched-off rows are skipped, so "rows" below means rows where the
        # VM was actually running.
        metrics, off_rows = read_metrics(filepath)
        cpu = metrics["cpu"]
        if len(cpu) < MIN_ROWS:
            continue

        # The whole-VM numbers can hide a dead patch. VM 200 looked perfect
        # (mean 43%, the highest std of all) but its last 4.5 days are flat
        # zero - and that is exactly the part we keep back for testing. A
        # model tested on a flat line tells us nothing. So measure the three
        # parts the way preprocessing.py will cut them, and check each one
        # actually moves.
        train, val, test = split_three_ways(cpu)

        results.append({
            "vm": filepath.split("\\")[-1].split("/")[-1],
            "rows": len(cpu),
            "off_rows": off_rows,
            "cpu_mean": round(cpu.mean(), 2),
            "cpu_std": round(cpu.std(), 2),
            "cpu_max": round(cpu.max(), 2),
            "train_std": round(train.std(), 2),
            "val_std": round(val.std(), 2),
            "test_std": round(test.std(), 2),
            # the model predicts all three metrics, so all three must be alive
            "mem_alive": is_alive(metrics["mem"]),
            "net_alive": is_alive(metrics["net"]),
        })

    table = pd.DataFrame(results)

    # Mark the VMs that are in the range we want (not idle, not maxed out).
    table["good_range"] = (table["cpu_mean"] >= 20) & (table["cpu_mean"] <= 60)

    # Every part must have real movement in it, or training / validating /
    # testing on that part is pointless.
    table["splits_ok"] = (table[["train_std", "val_std", "test_std"]].min(axis=1)
                          > MIN_SPLIT_STD)

    # A VM we would actually train on has to pass every check:
    # busy enough, moving, moving in all three parts, and with memory and
    # network that are not stuck on one value.
    table["candidate"] = (table["good_range"] & table["splits_ok"]
                          & table["mem_alive"] & table["net_alive"])

    # Sort so the most variable VM is at the top.
    table = table.sort_values("cpu_std", ascending=False)

    return table.reset_index(drop=True)


def plot_top_vms(table, how_many=HOW_MANY_TO_PLOT, save_path=None):
    """
    Draw the most variable VMs that are in the 20-60% range, so we can pick
    one by eye.

    The table tells us two things (busy? moving?), but not the third thing we
    want: a daily pattern. Only a picture shows that. So for each VM we draw:
      - left:  one week of CPU  (does it look like real, changing load?)
      - right: average CPU for each hour of the day  (busy in the day,
               quiet at night? A flat line here means no daily pattern.)
    """
    top = table[table["candidate"]].head(how_many)

    fig, axes = plt.subplots(len(top), 2, figsize=(15, 2.3 * len(top)),
                             gridspec_kw={"width_ratios": [4, 1]}, squeeze=False)

    for row, (_, vm) in enumerate(top.iterrows()):
        print(f"\nloading {vm['vm']} for the plot...")
        # save=False: we only want to look at it, not write a clean CSV yet.
        df = load_vm(f"data/raw/{vm['vm']}", save=False)
        week = df.iloc[:STEPS_IN_ONE_WEEK]

        # Left: one week of CPU, with the standard deviation drawn on it.
        left = axes[row][0]
        mean = vm["cpu_mean"]
        std = vm["cpu_std"]

        # The shaded band is mean - std to mean + std: where the CPU "normally"
        # swings. A near-idle VM would have a thin band hugging the bottom.
        # A wide band means the load really moves - that is what we want to learn.
        # (CPU can't go below 0 or above 100, so the band is cut off there.)
        band_low = max(mean - std, 0)
        band_high = min(mean + std, 100)
        left.axhspan(band_low, band_high, color="#2a78d6", alpha=0.10,
                     label=f"mean ± 1 std  ({band_low:.0f}% to {band_high:.0f}%)")
        left.axhline(mean, color="#eb6834", linewidth=1.5, linestyle="--",
                     label=f"mean = {mean}%")
        left.plot(week.index, week["cpu"], color="#2a78d6", linewidth=0.7)

        # A double arrow from the mean up by one std, so the size of the std
        # can be read straight off the y-axis.
        # Widen the x-axis a little past the week so the arrow and label fit inside.
        week_length = week.index[-1] - week.index[0]
        arrow_x = week.index[-1] + week_length * 0.015
        left.set_xlim(week.index[0], week.index[-1] + week_length * 0.11)
        left.annotate("", xy=(arrow_x, mean + std), xytext=(arrow_x, mean),
                      arrowprops=dict(arrowstyle="<->", color="black", lw=1.4))
        left.text(arrow_x, mean + std / 2, f"  std = {std}", va="center",
                  fontsize=9, fontweight="bold")

        left.set_ylim(-5, 105)
        left.set_ylabel("CPU %")
        left.set_title(f"{vm['vm']}   mean {mean}%   std {std}",
                       loc="left", fontsize=10)
        left.legend(loc="lower left", fontsize=8, framealpha=0.9)
        left.grid(alpha=0.3)

        # Right: the average day. groupby(hour) puts all the 9am readings
        # together, all the 10am readings together, and so on.
        by_hour = df["cpu"].groupby(df.index.hour).mean()
        right = axes[row][1]
        right.bar(by_hour.index, by_hour.values, color="#2a78d6", width=0.8)
        right.set_ylim(0, 105)
        right.set_xticks([0, 6, 12, 18, 23])
        right.set_title("average day", loc="left", fontsize=10)
        right.grid(alpha=0.3, axis="y")

    axes[-1][1].set_xlabel("hour of day")
    fig.tight_layout()
    if save_path:
        ensure_folder(save_path)
        fig.savefig(save_path, dpi=130)
        print(f"\nsaved: {save_path}")
    return fig


def pick_best_average_worst(table):
    """
    Pick three VMs to compare:
      best    - the top of our shortlist (highest std with mean CPU in 20-60%)
      average - the VM whose std is closest to the median std of ALL VMs,
                i.e. what you would get if you grabbed a VM at random
      worst   - the lowest std of all (ties broken by the most rows):
                a VM whose CPU practically never changes
    """
    best = table[table["candidate"]].iloc[0]

    median_std = table["cpu_std"].median()
    distance = (table["cpu_std"] - median_std).abs()
    average = table.loc[distance.idxmin()]

    worst = table.sort_values(["cpu_std", "rows"], ascending=[True, False]).iloc[0]

    return best, average, worst


def plot_distribution(table, save_path=None):
    """
    Compare how the CPU readings are spread out for the best, an average and
    the worst VM.

    The bars are the REAL data: for each CPU value, how often it actually
    happened. We deliberately do NOT draw a bell curve here. A bell curve
    would only show what the spread WOULD look like if the data were
    bell-shaped, and our data is not: VM 214 sits at 0% or 100% almost all
    the time, so its real shape has two peaks, not one hump.

    Standard deviation is still shown, drawn on top of the real bars:
      - the orange dashed line is the mean
      - the blue band is mean - 1 std to mean + 1 std, i.e. how far the
        readings normally swing
      - the arrow shows the length of 1 std on the CPU axis

    Read it as: a WIDE band over spread-out bars = the CPU moves a lot;
    a narrow band over one tall bar = the CPU hardly moves.
    """
    best, average, worst = pick_best_average_worst(table)
    panels = [
        ("BEST", best, "readings spread across the whole range - a lot to learn", "#1baf7a"),
        ("AVERAGE", average, "a typical VM - nearly every reading is the same", "#eda100"),
        ("WORST", worst, "every reading is the same: nothing to learn", "#e34948"),
    ]

    fig, axes = plt.subplots(3, 1, figsize=(13, 7), sharex=True)
    bins = np.arange(0, 110, 2)

    for ax, (name, vm, meaning, badge_color) in zip(axes, panels):
        cpu, _ = read_cpu(f"data/raw/{vm['vm']}")
        mean = vm["cpu_mean"]
        std = vm["cpu_std"]

        # The bars: what share of all readings falls in each 2% bin.
        counts, edges = np.histogram(cpu, bins=bins)
        share = counts / len(cpu) * 100
        ax.bar(edges[:-1], share, width=2, align="edge", color="#2a78d6",
               label="real readings")

        # Anything above 100% is a recording quirk of the dataset.
        ax.axvspan(100, 108, color="lightgrey", alpha=0.45, zorder=0)

        # The spread, drawn on top of the real bars.
        if std > 0:
            ax.axvspan(max(mean - std, 0), min(mean + std, 108),
                       color="#2a78d6", alpha=0.13, zorder=0,
                       label=f"mean ± 1 std")
        top = max(share.max() * 1.4, 5)
        ax.set_ylim(0, top)
        ax.axvline(mean, color="#eb6834", linestyle="--", linewidth=1.6,
                   label=f"mean = {mean}%")

        arrow_y = top * 0.62
        if std > 0:
            ax.annotate("", xy=(min(mean + std, 108), arrow_y), xytext=(mean, arrow_y),
                        arrowprops=dict(arrowstyle="<->", color="black", lw=1.4))
            if std > 5:
                ax.text((mean + min(mean + std, 108)) / 2, arrow_y + top * 0.04,
                        f"1 std = {std}", ha="center", va="bottom",
                        fontsize=10, fontweight="bold")
            else:
                # the arrow is too short to write on: label it to the right
                ax.text(mean + std + 3, arrow_y, f"1 std = {std}  (very narrow)",
                        ha="left", va="center", fontsize=10, fontweight="bold")
        else:
            ax.text(mean + 3, arrow_y, "1 std = 0.0  (no spread at all)",
                    ha="left", va="center", fontsize=10, fontweight="bold")

        # Write the size of the tallest bars on them, so the shape is
        # impossible to misread.
        for value, left_edge in sorted(zip(share, edges[:-1]), reverse=True)[:2]:
            if value < 5:
                continue
            # Keep the label inside the axes: bars at the far left or right
            # get their text pushed inwards instead of centred on the bar.
            if left_edge < 8:
                x, align = left_edge + 3, "left"
            elif left_edge > 92:
                x, align = left_edge - 1, "right"
            else:
                x, align = left_edge + 1, "center"
            ax.text(x, value + top * 0.03,
                    f"{value:.0f}% of readings\nat {left_edge:.0f}-{left_edge + 2:.0f}%",
                    ha=align, va="bottom", fontsize=8.5)

        ax.set_title(f"  {name}  ", loc="left", fontsize=12, fontweight="bold",
                     color="white", backgroundcolor=badge_color)
        ax.set_title(f"{vm['vm']}   mean {mean}%   std {std}   -   {meaning}",
                     loc="center", fontsize=11)
        ax.set_ylabel("share of\nreadings (%)")
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(alpha=0.3, axis="y")

    axes[-1].set_xlim(-2, 108)
    axes[-1].set_xlabel("CPU usage (%)        (grey: above 100% - a recording quirk of the dataset)")
    fig.tight_layout()
    if save_path:
        ensure_folder(save_path)
        fig.savefig(save_path, dpi=130)
        print(f"saved: {save_path}")
    return fig


if __name__ == "__main__":
    # "python -m utils.explore 10" plots the top 10 instead of the default.
    if len(sys.argv) > 1:
        how_many = int(sys.argv[1])
    else:
        how_many = HOW_MANY_TO_PLOT

    table = survey()

    if table is not None:
        print("VMs sorted by CPU standard deviation (most variable first):\n")
        print(table.head(25).to_string(index=False))

        in_band = table[table["good_range"]]
        usable = table[table["candidate"]]
        print(f"\n{len(in_band)} VMs have mean CPU between 20% and 60%.")
        print(f"{len(usable)} of those also move in all three parts "
              f"(train / validation / test) - the real candidates.")
        flat_part = in_band[~in_band["splits_ok"]]
        dead_mem = in_band[~in_band["mem_alive"]]
        dead_net = in_band[~in_band["net_alive"]]
        print(f"Rejected from the band: {len(flat_part)} with a flat "
              f"train/val/test part, {len(dead_mem)} with dead memory, "
              f"{len(dead_net)} with dead network.")

        ensure_folder("data/processed/vm_survey.csv")
        table.to_csv("data/processed/vm_survey.csv", index=False)
        print("saved: data/processed/vm_survey.csv")

        plot_top_vms(table, how_many)
        plot_distribution(table)

        print("\nNow look at plots/top_vms.png and plots/cpu_distribution.png,")
        print("pick a VM, and run:")
        print("  python -m utils.load_data data/raw/<vm>.csv")
        plt.show()
