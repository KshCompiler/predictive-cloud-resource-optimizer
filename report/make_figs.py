"""
Generate every figure the PDFs need, into the folder given as the first
argument (default: a folder called "plots").

    python report/make_figs.py <folder>

build_report.py passes a temporary folder and deletes it afterwards, so no
image files are left in the project - the PDFs carry their own copies.
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Validated categorical palette (dataviz reference instance, light mode)
BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#a3a29b"
SURFACE = "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": "#d6d5cf",
    "axes.labelcolor": INK2,
    "text.color": INK,
    "xtick.color": INK2,
    "ytick.color": INK2,
    "font.size": 10,
    "axes.grid": True,
    "grid.color": "#e6e5df",
    "grid.linewidth": 0.7,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

OUT = sys.argv[1] if len(sys.argv) > 1 else "plots"
os.makedirs(OUT, exist_ok=True)

# this file lives in report/, so the project root has to be on the import path
# before "from utils... import ..." further down can work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SURVEY_CSV = "data/processed/vm_survey.csv"
CLEAN_CSV = "data/processed/270_clean.csv"
for needed in (SURVEY_CSV, CLEAN_CSV):
    if not os.path.exists(needed):
        raise SystemExit(f"missing {needed} - run utils.explore and utils.load_data first")

survey = pd.read_csv(SURVEY_CSV)
clean = pd.read_csv(CLEAN_CSV, index_col=0, parse_dates=True)


# --- FIG 1: why VM selection is needed --------------------------------------
fig, ax = plt.subplots(figsize=(11, 3.6))
bins = np.arange(0, 105, 2.5)
counts, edges = np.histogram(survey["cpu_mean"], bins=bins)
centers = (edges[:-1] + edges[1:]) / 2
colors = [BLUE if 20 <= c <= 60 else MUTED for c in centers]
ax.bar(centers, counts, width=2.2, color=colors)
ax.axvspan(20, 60, color=BLUE, alpha=0.06, zorder=0)
ax.set_yscale("symlog", linthresh=10)
ax.set_yticks([0, 5, 10, 100, 900])
ax.set_yticklabels(["0", "5", "10", "100", "900"])
ax.set_xlabel("Mean CPU usage of the VM  (%)")
ax.set_ylabel("Number of VMs  (log scale)")
ax.set_title("Most of the 1,177 usable VMs are near-idle and useless for training",
             loc="left", fontsize=12, color=INK, pad=14)
ax.annotate("889 VMs sit below 5% mean CPU.\nAn LSTM trained here just learns\nto answer \"about 2%\".",
            xy=(2.5, 900), xytext=(11, 260), fontsize=9, color=INK2,
            arrowprops=dict(arrowstyle="->", color=MUTED, lw=1.2))
ax.annotate("158 VMs land in the 20-60% target band",
            xy=(40, 12), xytext=(46, 90), fontsize=9, color=BLUE,
            arrowprops=dict(arrowstyle="->", color=BLUE, lw=1.4))
ax.set_xlim(-2, 100)
fig.tight_layout()
fig.savefig(f"{OUT}/fig_vm_landscape.png", dpi=170)
plt.close(fig)
print("saved fig_vm_landscape.png")


# --- FIG 2: the selection scatter -------------------------------------------
fig, ax = plt.subplots(figsize=(11, 4.0))
rej = survey[~survey["good_range"]]
good = survey[survey["good_range"]]
chosen = survey[survey["vm"] == "270.csv"]

ax.scatter(rej["cpu_mean"], rej["cpu_std"], s=16, color=MUTED, alpha=0.55,
           linewidths=0, label="Rejected (mean outside 20-60%)")
ax.scatter(good["cpu_mean"], good["cpu_std"], s=26, color=BLUE, alpha=0.85,
           linewidths=0, label="Candidate (158 VMs in band)")
ax.scatter(chosen["cpu_mean"], chosen["cpu_std"], s=190, facecolor=ORANGE,
           edgecolor=SURFACE, linewidth=2, zorder=5, label="Selected: VM 270")

ax.axvspan(20, 60, color=BLUE, alpha=0.05, zorder=0)
ax.annotate("VM 270 - mean 46.8%, std 48.4\nthe top candidate that passes every check",
            xy=(46.8, 48.4), xytext=(19, 56), fontsize=9.5, color=INK,
            arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.6,
                            connectionstyle="arc3,rad=-0.15"))
ax.annotate("near-idle cluster\n(flat traces, nothing to learn)",
            xy=(3.5, 3), xytext=(7, 16), fontsize=9, color=INK2,
            arrowprops=dict(arrowstyle="->", color=MUTED, lw=1.2))
ax.set_ylim(-3, 64)
ax.set_xlabel("Mean CPU usage  (%)   →  is the VM actually busy?")
ax.set_ylabel("CPU standard deviation   →  does the load move?")
ax.set_title("VM selection: rank 1,177 VMs by volatility, keep only the 20-60% mean band",
             loc="left", fontsize=12, color=INK, pad=14)
ax.legend(frameon=False, fontsize=9, loc="upper right")
fig.tight_layout()
fig.savefig(f"{OUT}/fig_vm_scatter.png", dpi=170)
plt.close(fig)
print("saved fig_vm_scatter.png")


# --- FIG 3: chronological split over the real series ------------------------
n = len(clean)
tr_end = int(n * 0.70)
va_end = int(n * 0.85)
fig, ax = plt.subplots(figsize=(11, 3.5))
ax.plot(clean.index, clean["cpu"], color=BLUE, linewidth=0.45)
ax.axvspan(clean.index[0], clean.index[tr_end - 1], color=BLUE, alpha=0.07, zorder=0)
ax.axvspan(clean.index[tr_end], clean.index[va_end - 1], color=ORANGE, alpha=0.10, zorder=0)
ax.axvspan(clean.index[va_end], clean.index[-1], color=AQUA, alpha=0.12, zorder=0)

for x, label, sub, col in [
    (tr_end // 2, "TRAIN  70%", "6,048 rows\n5,988 windows", BLUE),
    ((tr_end + va_end) // 2, "VAL  15%", "1,296 rows\n1,236 windows", ORANGE),
    ((va_end + n) // 2, "TEST  15%", "1,296 rows\n1,236 windows", AQUA),
]:
    ax.text(clean.index[min(x, n - 1)], 148, label, ha="center", va="top",
            fontsize=10.5, color=col, fontweight="bold")
    ax.text(clean.index[min(x, n - 1)], 133, sub, ha="center", va="top",
            fontsize=8.5, color=INK2, linespacing=1.35)

for b in (tr_end, va_end):
    ax.axvline(clean.index[b], color=INK, linewidth=1.4, linestyle="--", alpha=0.65)

ax.set_ylim(-4, 152)
ax.set_yticks([0, 20, 40, 60, 80, 100])
ax.set_ylabel("CPU %")
ax.set_title("Step A — the split is by time position, never random",
             loc="left", fontsize=12, color=INK, pad=14)
fig.tight_layout()
fig.savefig(f"{OUT}/fig_split.png", dpi=170)
plt.close(fig)
print("saved fig_split.png")


# --- FIG 4: the three channels move together (correlation evidence) ---------
seg = clean.iloc[1550:1900]
fig, axes = plt.subplots(3, 1, figsize=(11, 4.2), sharex=True)
for ax, col, color, unit in zip(axes, ["cpu", "mem", "net"],
                                [BLUE, ORANGE, AQUA],
                                ["CPU %", "Memory %", "Network KB/s"]):
    ax.fill_between(seg.index, seg[col], color=color, alpha=0.16, linewidth=0)
    ax.plot(seg.index, seg[col], color=color, linewidth=1.4)
    ax.set_ylabel(unit, fontsize=9.5)
axes[0].set_title("Why all three metrics together: a batch job lights up CPU, memory and network at once",
                  loc="left", fontsize=12, color=INK, pad=12)
axes[2].set_xlabel("29 hours of VM 270")
fig.tight_layout()
fig.savefig(f"{OUT}/fig_channels.png", dpi=170)
plt.close(fig)
print("saved fig_channels.png")


# --- FIG 5: distribution of VM 214 — honest look at the trace shape ---------
fig, ax = plt.subplots(figsize=(11, 2.9))
ax.hist(clean["cpu"], bins=50, color=BLUE, alpha=0.9)
ax.set_xlabel("CPU %")
ax.set_ylabel("Number of 5-minute samples")
ax.set_title("VM 270 is bimodal: a batch machine that is either idle or saturated",
             loc="left", fontsize=12, color=INK, pad=12)
ax.annotate("idle between jobs", xy=(2, 2400), xytext=(14, 2600),
            fontsize=9, color=INK2, arrowprops=dict(arrowstyle="->", color=MUTED, lw=1.2))
ax.annotate("job running at 100%", xy=(99, 3400), xytext=(62, 3000),
            fontsize=9, color=INK2, arrowprops=dict(arrowstyle="->", color=MUTED, lw=1.2))
fig.tight_layout()
fig.savefig(f"{OUT}/fig_cpu_hist.png", dpi=170)
plt.close(fig)
print("saved fig_cpu_hist.png")


# --- FIG 6: do the metrics really move together? ---------------------------
fig, axes = plt.subplots(1, 2, figsize=(11, 4.0))
pairs = [("mem", "Memory %", "#eb6834", None),
         ("net", "Network KB/s", AQUA, 1500)]

for ax, (col, ylab, color, ycap) in zip(axes, pairs):
    r = clean["cpu"].corr(clean[col])
    ax.scatter(clean["cpu"], clean[col], s=5, color=color, alpha=0.12, linewidths=0)

    # average value of the other metric inside each 10%-wide CPU slice
    bins = np.arange(0, 110, 10)
    mids = bins[:-1] + 5
    avg = [clean.loc[(clean.cpu >= a) & (clean.cpu < a + 10), col].mean()
           for a in bins[:-1]]
    ax.plot(mids, avg, color=INK, linewidth=2, marker="o", markersize=5,
            label="average per 10% CPU slice")

    if ycap:
        above = (clean[col] > ycap).sum()
        ax.set_ylim(-ycap * 0.04, ycap)
        ax.text(0.99, 0.72, f"{above} readings go above {ycap:,}\n(cut off to keep the shape visible)",
                transform=ax.transAxes, ha="right", fontsize=8, color=INK2)

    ax.set_xlabel("CPU %")
    ax.set_ylabel(ylab)
    ax.set_title(f"CPU vs {ylab.split()[0]}   -   correlation r = {r:.2f}",
                 loc="left", fontsize=12, color=INK, pad=10)
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    ax.grid(alpha=0.3)

fig.tight_layout()
fig.savefig(f"{OUT}/fig_correlation.png", dpi=170)
plt.close(fig)
print("saved fig_correlation.png")


# --- the remaining figures come from the pipeline modules themselves --------
# (drawn here so that one command produces everything the PDFs embed)
from utils.explore import plot_top_vms, plot_distribution      # noqa: E402
from utils.load_data import load_clean, plot_week              # noqa: E402
from utils.preprocessing import verify_pipeline                # noqa: E402

plot_top_vms(survey, save_path=f"{OUT}/top_vms.png")
plt.close("all")

plot_distribution(survey, save_path=f"{OUT}/cpu_distribution.png")
plt.close("all")

plot_week(load_clean(CLEAN_CSV), "VM 270", save_path=f"{OUT}/270_week.png")
plt.close("all")

verify_pipeline(CLEAN_CSV, show=False, save_path=f"{OUT}/verify_pipeline.png")
plt.close("all")
