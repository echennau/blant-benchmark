import pandas as pd
import matplotlib.pyplot as plt
import argparse
from pathlib import Path


def plot_comparison(base_path=None, dev_path=None):
    # Load CSVs if provided
    df_base = pd.read_csv(base_path) if base_path else None
    df_dev = pd.read_csv(dev_path) if dev_path else None

    for stop_mode in ["NUM_SAMPLES", "PRECISION"]:
        plt.figure(figsize=(8, 5))

        if df_base is not None:
            df_b = df_base[df_base["STOP_MODE"] == stop_mode]
            plt.plot(
                df_b["NUM_THREADS"],
                df_b["TIME"],
                "o-r",
                label=f"Base (master branch)"
            )

        if df_dev is not None:
            df_d = df_dev[df_dev["STOP_MODE"] == stop_mode]
            plt.plot(
                df_d["NUM_THREADS"],
                df_d["TIME"],
                "o-b",
                label=f"Dev (dev-sebas branch)"
            )

        plt.xlabel("Thread count")
        plt.ylabel("Runtime (seconds)")
        ARGS = "k=6, s=EBE, -t=[x-axis]"
        plt.title(
            f"Fast Config, Runtime x Thread Count for ({'-p=5' if stop_mode == "PRECISION" else '-n=1,000,000,000'})\n{ARGS}")
        plt.legend()
        plt.grid(True, which="both", linestyle="--", linewidth=0.5)

        # Logarithmic x-axis (base 2)
        plt.xscale("log", base=2)
        plt.xticks([1, 2, 4, 8, 16, 32, 64], labels=[1, 2, 4, 8, 16, 32, 64])

        plt.tight_layout()

        # Save plot using one of the paths or generic name
        stem = "unknown"
        if base_path and dev_path:
            stem = "combined"
        else:
            if base_path:
                stem = Path(base_path).stem
            elif dev_path:
                stem = Path(dev_path).stem

        output_path = f"{stem}_{stop_mode}_plot.png"
        plt.savefig(output_path, dpi=300)
        plt.close()
        print("Saved plot to", output_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-b",
        type=str,
        help="Path to CSV file for base.",
    )
    parser.add_argument(
        "-d",
        type=str,
        help="Path to CSV file for dev.",
    )
    args = parser.parse_args()

    if not args.b and not args.d:
        print("No CSV files provided, nothing to plot.")
        return

    plot_comparison(base_path=args.b, dev_path=args.d)


if __name__ == "__main__":
    main()
