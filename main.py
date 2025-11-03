import argparse
import csv
import time
import subprocess
import json
from pathlib import Path


def write_csv(row, output_file, mode="w"):
    with open(output_file, mode, newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)


def time_cmd(
    num_threads,
    k_value,
    sampling_method,
    stop_mode,
    num_samples,
    precision,
    seed,
    network,
    cwd,
):
    if stop_mode == "PRECISION":
        cmd = f"./blant -t {num_threads} -k {k_value} -s {sampling_method} -p {precision} -r {seed} {network}"
    else:
        cmd = f"./blant -t {num_threads} -k {k_value} -s {sampling_method} -n {num_samples} -r {seed} {network}"

    start = time.perf_counter()

    out = subprocess.run(cmd, cwd=cwd, capture_output=True, shell=True)
    if out.returncode != 0:
        print(f"ERROR: Failed to run command: {cmd}")
        print(out.stdout)
        return 0

    end = time.perf_counter()

    return end - start


def run_benchmarks(config):
    headers = [
        "NUM_THREADS",
        "K_VALUE",
        "SAMPLING_METHOD",
        "STOP_MODE",
        "NUM_SAMPLES",
        "PRECISION",
        "TIME",
    ]
    output_file = config["version"] + "_output.csv"
    write_csv(headers, output_file)

    options = config["options"]
    blant_path = Path(config["blantPath"])
    blant_dir = blant_path.parent

    for thread in options["NUM_THREADS"]:
        for k in options["K_VALUES"]:
            for sampling_method in options["SAMPLING_METHODS"]:
                args = [thread, k, sampling_method]
                for num_samples in options["NUM_SAMPLES"]:
                    num_samples_args = [*args, "NUM_SAMPLES", num_samples, None]
                    time = time_cmd(
                        *num_samples_args,
                        options["SEED"],
                        options["NETWORK"],
                        blant_dir,
                    )
                    write_csv([*num_samples_args, time], output_file, "a")

                for precision in options["PRECISION"]:
                    precision_args = [*args, "PRECISION", None, precision]
                    time = time_cmd(
                        *precision_args, options["SEED"], options["NETWORK"], blant_dir
                    )
                    write_csv([*precision_args, time], output_file, "a")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        type=str,
        help="Path to configuration file.",
    )
    args = parser.parse_args()
    config_path = args.c
    with open(config_path, "r") as f:
        config = json.load(f)

    run_benchmarks(config)


if __name__ == "__main__":
    main()
