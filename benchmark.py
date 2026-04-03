#!/usr/bin/env python3
"""
BLANT benchmark script.

Runs BLANT under two stop modes:
  - sample-based  (-n N):  stop after exactly N samples
  - batch-based   (-p P):  stop when graphlet concentrations converge to precision P

Precision for batch mode is auto-calibrated using only powers-of-10 values (no 5s)
to find the one whose sample count is closest to the calibration target.
The sample-based run then uses the exact sample count from calibration for a fair
comparison. Both modes are repeated --runs times.

Results are written to benchmark_results.csv in the same directory as this script.

Usage:
    python3 benchmark.py [--network PATH] [--k K] [--output-mode M] [--runs N]

Defaults:
    --network   ../DEV/networks/syeast.el
    --k         5
    --output-mode f    (graphlet frequency; passed as -mf to blant)
    --runs      5
"""

import argparse
import csv
import os
import re
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BLANT_BIN  = os.path.join(SCRIPT_DIR, "..", "DEV", "blant")

# Initial calibration target; sample-based count is updated after calibration
_CALIBRATION_TARGET = 250 * 1024 ** 2  # 262,144,000

# Regex to extract total sample count from BLANT's dedicated stderr line
_SAMPLES_RE = re.compile(r'BLANT_TOTAL_SAMPLES=(\d+)')


def run_blant(cmd_args: list[str], timeout: int | None = None) -> dict:
    """
    Run BLANT, capturing stdout/stderr and wall-clock time.
    Returns a dict with keys: returncode, elapsed, stderr_tail, samples_from_output.
    """
    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd_args,
            stdout=subprocess.DEVNULL,   # output can be huge; discard
            stderr=subprocess.PIPE,
            timeout=timeout,
            text=True,
            cwd=os.path.dirname(cmd_args[0]),  # run from blant's directory so canon_maps/ is found
        )
    except subprocess.TimeoutExpired as e:
        elapsed = time.monotonic() - start
        stderr = e.stderr or ""
        return {
            "returncode": "TIMEOUT",
            "elapsed": elapsed,
            "stderr_tail": stderr[-500:] if stderr else "",
            "samples_from_output": _extract_samples(stderr),
        }
    except Exception as e:
        elapsed = time.monotonic() - start
        return {
            "returncode": "ERROR",
            "elapsed": elapsed,
            "stderr_tail": str(e),
            "samples_from_output": None,
        }

    elapsed = time.monotonic() - start
    return {
        "returncode": result.returncode,
        "elapsed": elapsed,
        "stderr_tail": result.stderr[-500:] if result.stderr else "",
        "samples_from_output": _extract_samples(result.stderr),
    }


def _extract_samples(text: str) -> int | None:
    """Parse the total sample count printed by BLANT to stderr."""
    if not text:
        return None
    matches = _SAMPLES_RE.findall(text)
    if matches:
        return int(matches[-1])
    return None


def build_cmd(blant_bin: str, network: str, k: int, threads: int,
              stop_flag: str, output_mode: str) -> list[str]:
    return [
        blant_bin,
        f"-k{k}",
        f"-t{threads}",
        f"-m{output_mode}",
        stop_flag,
        network,
    ]


def calibrate_precision(blant_bin, network, k, threads, output_mode, timeout=300):
    """
    Try powers-of-10 precision values (no 5s) and return the one whose sample
    count is closest to _CALIBRATION_TARGET, along with that sample count.
    """
    candidates = [1e-1, 1e-2, 1e-3, 1e-4, 1e-5, 1e-6]
    best_prec, best_diff, best_n = None, float('inf'), None
    for prec in candidates:
        cmd = build_cmd(blant_bin, network, k, threads, f"-p{prec}", output_mode)
        print(f"  calibrate: prec={prec}  running...")
        result = run_blant(cmd, timeout=timeout)
        n = result["samples_from_output"]
        if n is None:
            print(f"  calibrate: prec={prec}  no sample count in output (rc={result['returncode']})")
            continue
        diff = abs(n - _CALIBRATION_TARGET)
        print(f"  calibrate: prec={prec}  samples={n}  diff={diff}")
        if diff < best_diff:
            best_diff, best_prec, best_n = diff, prec, n
    return best_prec, best_n


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--network",      default=os.path.join(SCRIPT_DIR, "..", "DEV", "networks", "syeast.el"),
                        help="Path to the edge-list network file")
    parser.add_argument("--k",            type=int, default=5,
                        help="Graphlet size (default: 5)")
    parser.add_argument("--output-mode",  default="f",
                        help="BLANT output mode letter(s) passed to -m (default: f)")
    parser.add_argument("--threads",      type=int, default=8,
                        help="Number of threads (default: 8)")
    parser.add_argument("--timeout",      type=int, default=None,
                        help="Per-run timeout in seconds (default: none)")
    parser.add_argument("--runs",         type=int, default=5,
                        help="Number of timed benchmark repetitions (default: 5)")
    parser.add_argument("--out",          default=os.path.join(SCRIPT_DIR, "benchmark_results.csv"),
                        help="Output CSV path")
    args = parser.parse_args()

    network  = os.path.abspath(args.network)
    if not os.path.exists(network):
        sys.exit(f"ERROR: network file not found: {network}")

    blant_bin = os.path.abspath(BLANT_BIN)
    if not os.path.isfile(blant_bin):
        sys.exit(f"ERROR: blant binary not found: {blant_bin}")
    if not os.access(blant_bin, os.X_OK):
        sys.exit(f"ERROR: blant binary is not executable: {blant_bin}")

    # Calibrate: find the power-of-10 precision closest to the target sample count
    print("Calibrating precision (powers of 10 only, no 5s)...")
    best_prec, calib_n = calibrate_precision(
        blant_bin, network, args.k, args.threads, args.output_mode,
        timeout=args.timeout or 300)
    if best_prec is None:
        sys.exit("ERROR: calibration failed — no precision value produced parseable output")
    print(f"  → Using precision {best_prec} (calibration sample count: {calib_n})\n")

    # Build configs: sample-based uses a fixed round count for clean presentation
    sample_n = 150_000_000
    configs = [
        {
            "label":       f"n={sample_n}",
            "stop_mode":   "sample",
            "requested_n": sample_n,
            "stop_flag":   f"-n {sample_n}",
            "cmd":         build_cmd(blant_bin, network, args.k, args.threads,
                                     f"-n {sample_n}", args.output_mode),
        },
        {
            "label":       f"p={best_prec}",
            "stop_mode":   "batch",
            "requested_n": None,
            "stop_flag":   f"-p{best_prec}",
            "cmd":         build_cmd(blant_bin, network, args.k, args.threads,
                                     f"-p{best_prec}", args.output_mode),
        },
    ]

    print(f"BLANT binary : {blant_bin}")
    print(f"Network      : {network}")
    print(f"k            : {args.k}")
    print(f"Threads      : {args.threads}")
    print(f"Output mode  : -{args.output_mode}")
    print(f"Runs         : {args.runs}")
    print(f"Timeout      : {args.timeout}s" if args.timeout else "Timeout      : none")
    print(f"Output CSV   : {args.out}")
    print()

    fieldnames = ["run", "cmd", "number_of_samples", "stop_mode", "time_to_completion_s", "returncode"]
    rows = []

    for run_idx in range(1, args.runs + 1):
        print(f"=== Run {run_idx}/{args.runs} ===")
        for cfg in configs:
            cmd_str = " ".join(cfg["cmd"])
            print(f"  [{cfg['label']}] {cmd_str}")

            result = run_blant(cfg["cmd"], timeout=args.timeout)

            if cfg["stop_mode"] == "sample":
                reported_n = cfg["requested_n"]
            else:
                reported_n = result["samples_from_output"] if result["samples_from_output"] else "N/A (batch)"

            elapsed_str = f"{result['elapsed']:.3f}"
            print(f"    Done in {elapsed_str}s  |  rc={result['returncode']}  |  samples={reported_n}")
            if result["returncode"] not in (0, "TIMEOUT"):
                print(f"    stderr tail: {result['stderr_tail']}")

            rows.append({
                "run":                   run_idx,
                "cmd":                   cmd_str,
                "number_of_samples":     reported_n,
                "stop_mode":             cfg["stop_mode"],
                "time_to_completion_s":  elapsed_str,
                "returncode":            result["returncode"],
            })
        print()

    # Write CSV
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Results written to {args.out}  ({len(rows)} rows)")


if __name__ == "__main__":
    main()
