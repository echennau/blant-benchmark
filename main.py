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
        print(out.stdout.decode())
        print(out.stderr.decode())
        return 0

    end = time.perf_counter()
    return end - start


def run_benchmarks(config):
    output_file = f"{config['configName']}_output.csv"
    args = config["args"]
    blant_path = Path(config["blantPath"])
    blant_dir = blant_path.parent

    for network in args["NETWORKS"]:
        for seed in args["SEEDS"]:
            for thread in args["NUM_THREADS"]:
                for k in args["K_VALUES"]:
                    for sampling_method in args["SAMPLING_METHODS"]:

                        # Run NUM_SAMPLES mode
                        for num_samples in args["NUM_SAMPLES"]:
                            stop_mode = "NUM_SAMPLES"
                            elapsed = time_cmd(
                                thread,
                                k,
                                sampling_method,
                                stop_mode,
                                num_samples,
                                None,
                                seed,
                                network,
                                blant_dir,
                            )
                            write_csv(
                                [
                                    thread,
                                    k,
                                    sampling_method,
                                    stop_mode,
                                    num_samples,
                                    None,
                                    seed,
                                    network,
                                    elapsed,
                                ],
                                output_file,
                                "a",
                            )

                        # Run PRECISION mode
                        for precision in args["PRECISIONS"]:
                            stop_mode = "PRECISION"
                            elapsed = time_cmd(
                                thread,
                                k,
                                sampling_method,
                                stop_mode,
                                None,
                                precision,
                                seed,
                                network,
                                blant_dir,
                            )
                            write_csv(
                                [
                                    thread,
                                    k,
                                    sampling_method,
                                    stop_mode,
                                    None,
                                    precision,
                                    seed,
                                    network,
                                    elapsed,
                                ],
                                output_file,
                                "a",
                            )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", type=str, help="Path to configuration file.")
    args = parser.parse_args()
    config_path = args.c

    with open(config_path, "r") as f:
        config = json.load(f)

    headers = [
        "NUM_THREADS",
        "K_VALUE",
        "SAMPLING_METHOD",
        "STOP_MODE",
        "NUM_SAMPLES",
        "PRECISION",
        "SEED",
        "NETWORK",
        "TIME",
    ]

    output_file = f"{config['configName']}_output.csv"
    write_csv(headers, output_file)

    for _ in range(config["numRuns"]):
        run_benchmarks(config)


if __name__ == "__main__":
    main()
