import pandas as pd
import matplotlib.pyplot as plt
import argparse
from pathlib import Path


def plot(csv_path):
    with open(csv_path, "r") as f:
        df = pd.read_csv(csv_path)

    # Filter by stop mode
    df_num_samples = df[df["STOP_MODE"] == "NUM_SAMPLES"]
    df_precision = df[df["STOP_MODE"] == "PRECISION"]

    # Plot
    plt.figure(figsize=(8, 5))
    plt.plot(
        df_num_samples["NUM_THREADS"],
        df_num_samples["TIME"],
        "o-r",
        label="NUM_SAMPLES",
    )
    plt.plot(
        df_precision["NUM_THREADS"], df_precision["TIME"], "o-b", label="PRECISION"
    )

    plt.xlabel("Number of Threads")
    plt.ylabel("Time (seconds)")
    plt.title("Performance vs Number of Threads (Stop Modes)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    output_path = Path(csv_path).stem + "_plot.png"
    print("Saved plot to", output_path)
    plt.savefig(output_path, dpi=300)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        type=str,
        help="Path to CSV file.",
    )
    args = parser.parse_args()
    csv_path = args.i
    plot(csv_path)


if __name__ == "__main__":
    main()
