"""
This file takes the clean CSV (like 214_clean.csv) and turns it into batches
of numbers that the LSTM can actually train on.

5 steps happen here, IN THIS ORDER:

    A. Split the data by time (train / validation / test)
    B. Scale the numbers to 0-1 (using the training data only)
    C. Cut each part into 60-step windows
    D. Wrap everything into DataLoaders (so PyTorch can read it in batches)
    E. Check that everything above actually worked

The order matters a lot. If you scale before splitting, the scaler "sees"
the test data's numbers, and the model indirectly cheats. If you window
across the train/test boundary, the same kind of cheating happens.
So: split first, always.

Run it:
    python -m utils.preprocessing
    python -m utils.preprocessing data/processed/270_clean.csv
"""

import sys

import joblib
import numpy as np
import torch
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from torch.utils.data import TensorDataset, DataLoader

from utils.load_data import load_clean

WINDOW_SIZE = 60     # look at 60 rows (5 hours) of history
BATCH_SIZE = 64
TRAIN_SHARE = 0.70   # first 70% of days = training
VAL_SHARE = 0.15     # next 15% = validation, and the last 15% = test


# ---------------------------------------------------------------- STEP A ---
def split_by_time(df):
    """
    Cut the table into 3 pieces, by POSITION (time order), not randomly.

    Example with 100 rows:
        rows 0-69   -> train
        rows 70-84  -> validation
        rows 85-99  -> test

    We never shuffle here. The model must only ever learn from the past.
    """
    total_rows = len(df)
    train_end = int(total_rows * TRAIN_SHARE)
    val_end = int(total_rows * (TRAIN_SHARE + VAL_SHARE))

    train = df.iloc[:train_end]
    val = df.iloc[train_end:val_end]
    test = df.iloc[val_end:]

    return train, val, test


# ---------------------------------------------------------------- STEP C ---
def make_windows(data, window_size=WINDOW_SIZE):
    """
    Turn a table of numbers into training examples.

    X = 60 rows in a row          -> shape (samples, 60, 3)
    y = the very next row after   -> shape (samples, 3)

    Small example with window_size=3 and rows [a, b, c, d, e]:
        X[0] = [a, b, c]     y[0] = d
        X[1] = [b, c, d]     y[1] = e

    We call this once for train, once for val, once for test - separately.
    A window that starts in train and ends in test would let the model
    peek at the future, which is exactly what we are trying to avoid.
    """
    X = []
    y = []
    for i in range(len(data) - window_size):
        X.append(data[i : i + window_size])
        y.append(data[i + window_size])

    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


# ---------------------------------------------------------------- STEP D ---
def to_loader(X, y, batch_size=BATCH_SIZE, shuffle=False):
    """Wrap the arrays so PyTorch can hand them out in batches."""
    X_tensor = torch.FloatTensor(X)
    y_tensor = torch.FloatTensor(y)
    dataset = TensorDataset(X_tensor, y_tensor)
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)


# ------------------------------------------------------------ MAIN STEPS ---
def build_pipeline(filepath, window_size=WINDOW_SIZE, batch_size=BATCH_SIZE):
    """
    Run all 5 steps and hand back what the training script needs:
    train_loader, val_loader, test_loader, scaler
    """
    df = load_clean(filepath)

    # A. split first, before touching the numbers at all
    train, val, test = split_by_time(df)

    # B. learn the scaling from train only, then apply it to all 3 parts
    scaler = MinMaxScaler()
    train_scaled = scaler.fit_transform(train)   # LEARNS min/max, then scales
    val_scaled = scaler.transform(val)           # only scales, does not relearn
    test_scaled = scaler.transform(test)         # only scales, does not relearn

    # Save the scaler. Later, the dashboard needs this exact scaler to turn
    # the model's 0-1 predictions back into real CPU%, memory%, and KB/s.
    joblib.dump(scaler, "models/scaler.joblib")

    # C. cut each part into windows, one at a time
    X_train, y_train = make_windows(train_scaled, window_size)
    X_val, y_val = make_windows(val_scaled, window_size)
    X_test, y_test = make_windows(test_scaled, window_size)

    # D. wrap into DataLoaders.
    # shuffle=True only for training: this shuffles the ORDER of the windows,
    # not the 60 rows inside a window, and not the raw time series.
    # Validation and test stay in time order, so we can later plot
    # predictions next to real dates.
    train_loader = to_loader(X_train, y_train, batch_size, shuffle=True)
    val_loader = to_loader(X_val, y_val, batch_size, shuffle=False)
    test_loader = to_loader(X_test, y_test, batch_size, shuffle=False)

    return train_loader, val_loader, test_loader, scaler


# ---------------------------------------------------------------- STEP E ---
def verify_pipeline(filepath, window_size=WINDOW_SIZE, batch_size=BATCH_SIZE, show=True):
    """
    Prove that steps A-D actually worked, before we waste time training a model.

    A mistake in windowing or scaling does NOT crash the program - it just
    quietly gives the model a broken dataset. This function catches that.
    """
    df = load_clean(filepath)
    train, val, test = split_by_time(df)

    scaler = MinMaxScaler()
    train_scaled = scaler.fit_transform(train)
    test_scaled = scaler.transform(test)

    X_train, y_train = make_windows(train_scaled, window_size)
    train_loader = to_loader(X_train, y_train, batch_size, shuffle=True)

    print("=" * 60)
    print(f"CHECKING PIPELINE FOR: {filepath}")
    print("=" * 60)

    # --- CHECK 1: are the batch shapes correct? ---
    print("\n[1] batch shapes")
    for X_batch, y_batch in train_loader:
        print(f"    X shape: {tuple(X_batch.shape)}   (should be (64, 60, 3))")
        print(f"    y shape: {tuple(y_batch.shape)}   (should be (64, 3))")
        break

    # --- CHECK 2: does un-scaling give back the original numbers? ---
    # Take window 0, undo the scaling, and compare it to the first 60 real
    # rows of the CSV. They must match almost exactly.
    print("\n[2] undo the scaling on window 0, compare to the real CSV rows")
    recovered = scaler.inverse_transform(X_train[0])
    original = df.iloc[:window_size].values
    biggest_difference = np.abs(recovered - original).max()
    print(f"    biggest difference found: {biggest_difference:.10f}   (should be ~0)")

    fig, axes = plt.subplots(3, 1, figsize=(12, 7), sharex=True)
    column_names = ["cpu", "mem", "net"]
    for i, name in enumerate(column_names):
        axes[i].plot(original[:, i], linewidth=3, alpha=0.4,
                     color="blue", label="original CSV")
        axes[i].plot(recovered[:, i], linewidth=1.2, linestyle="--",
                     color="red", label="window 0, un-scaled")
        axes[i].set_ylabel(name)
        axes[i].legend(fontsize=8)
        axes[i].grid(alpha=0.3)
    axes[0].set_title("These two lines should sit exactly on top of each other")
    axes[2].set_xlabel("step number inside the window")
    fig.tight_layout()
    fig.savefig("plots/verify_pipeline.png", dpi=130)
    print("    saved: plots/verify_pipeline.png")

    # --- CHECK 3: a summary of how much data ended up where ---
    print("\n[3] data summary")
    print(f"    total rows : {len(df)}")
    print(f"    train      : {len(train)} rows -> {len(train) - window_size} windows")
    print(f"    val        : {len(val)} rows -> {len(val) - window_size} windows")
    print(f"    test       : {len(test)} rows -> {len(test) - window_size} windows")

    # Un-scale the test set to see real units again (sanity check).
    test_real = scaler.inverse_transform(test_scaled)
    print("\n    test set, in real units:")
    for i, name in enumerate(column_names):
        print(f"      {name}: mean {test_real[:, i].mean():8.2f}   "
              f"std {test_real[:, i].std():8.2f}")

    # The scaler only ever saw the training data. So training values land
    # exactly inside 0 to 1, but test values are allowed to fall outside
    # that range. Seeing test values slightly outside 0-1 is actually GOOD -
    # it proves the scaler did not peek at the test data.
    print(f"\n    scaled train range: {train_scaled.min():.2f} to {train_scaled.max():.2f}"
          f"   (should be exactly 0.00 to 1.00)")
    print(f"    scaled test range:  {test_scaled.min():.2f} to {test_scaled.max():.2f}"
          f"   (going outside 0-1 here is normal and correct)")

    print("\n" + "=" * 60)

    if show:
        plt.show()
    else:
        plt.close(fig)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        filepath = "data/processed/270_clean.csv"

    verify_pipeline(filepath, show=False)

    # Show how the training script (Step 1.4) will actually use this file.
    print("\nUsing build_pipeline(), the way the training script will:")
    train_loader, val_loader, test_loader, scaler = build_pipeline(filepath)
    print(f"    train batches: {len(train_loader)}")
    print(f"    val batches:   {len(val_loader)}")
    print(f"    test batches:  {len(test_loader)}")
    print("    scaler saved to models/scaler.joblib")
