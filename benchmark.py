#!/usr/bin/env python3
"""
BLANT benchmark script.

Runs BLANT under two stop modes across three sampling methods:
  - sample-based  (-n N):  stop after exactly N samples
  - batch-based   (-p P):  stop when graphlet concentrations converge to precision P

Sampling methods tested: EBE, NBE, MCMC (passed via -s METHOD)

Hardcoded values:
  PRECISION      = 1e-4              (batch mode convergence threshold, targets ~100M samples)
  SAMPLE_N       = 100_000_000       (sample-based stop count, exactly 100M)
  THREAD_COUNTS  = [1, 2, 4, 8, 16]  (all thread counts to test)
  SAMPLE_METHODS = [EBE, NBE, MCMC]  (sampling methods to test)

All combinations of stop mode × thread count × sampling method are repeated --runs times.

Results are written to output.csv in the same directory as this script.

Usage:
    python3 benchmark.py [--network PATH] [--k K] [--output-mode M] [--runs N]

Defaults:
    --network   DEV/networks/syeast.el
    --k         5
    --output-mode f    (graphlet frequency; passed as -mf to blant)
    --runs      3
"""

import argparse
import csv
import os
import re
import subprocess
import sys
import time

SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))
BLANT_BIN      = os.path.join(SCRIPT_DIR, "DEV", "blant")

PRECISION      = 0.00001               # batch-mode convergence threshold (~90M samples)
SAMPLE_N       = 90_000_000        # sample-mode count (exactly 90M)
THREAD_COUNTS  = [1, 2, 4, 8, 16]  # thread counts to benchmark
SAMPLE_METHODS = ["EBE", "NBE", "MCMC"]  # sampling methods to benchmark

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
        stderr = e.stderr or b""
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
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
              stop_flag: str, output_mode: str, sample_method: str) -> list[str]:
    return [
        blant_bin,
        f"-k{k}",
        f"-t{threads}",
        f"-m{output_mode}",
        f"-s{sample_method}",
        stop_flag,
        network,
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--network",      default=os.path.join(SCRIPT_DIR, "DEV", "networks", "syeast.el"),
                        help="Path to the edge-list network file")
    parser.add_argument("--k",            type=int, default=5,
                        help="Graphlet size (default: 5)")
    parser.add_argument("--output-mode",  default="f",
                        help="BLANT output mode letter(s) passed to -m (default: f)")
    parser.add_argument("--timeout",      type=int, default=None,
                        help="Per-run timeout in seconds (default: none)")
    parser.add_argument("--runs",         type=int, required=True,
                        help="Number of timed benchmark repetitions")
    parser.add_argument("--out",          default=os.path.join(SCRIPT_DIR, "output.csv"),
                        help="Output CSV path")
    parser.add_argument("--methods",      default=None,
                        help="Comma-separated sampling methods to run (default: all). E.g. MCMC or EBE,NBE")
    parser.add_argument("--append",       action="store_true",
                        help="Append to existing CSV instead of overwriting (skips writing header)")
    args = parser.parse_args()

    network  = os.path.abspath(args.network)
    if not os.path.exists(network):
        sys.exit(f"ERROR: network file not found: {network}")

    blant_bin = os.path.abspath(BLANT_BIN)
    if not os.path.isfile(blant_bin):
        sys.exit(f"ERROR: blant binary not found: {blant_bin}")
    if not os.access(blant_bin, os.X_OK):
        sys.exit(f"ERROR: blant binary is not executable: {blant_bin}")

    methods = [m.strip().upper() for m in args.methods.split(",")] if args.methods else SAMPLE_METHODS

    print(f"BLANT binary    : {blant_bin}")
    print(f"Network         : {network}")
    print(f"k               : {args.k}")
    print(f"Sampling methods: {methods}")
    print(f"Threads         : {THREAD_COUNTS}")
    print(f"Output mode     : -{args.output_mode}")
    print(f"Runs            : {args.runs}")
    print(f"Timeout         : {args.timeout}s" if args.timeout else "Timeout         : none")
    print(f"Output CSV      : {args.out}")
    print()

    fieldnames = [
        "run", "sampling_method", "threads", "stop_mode",
        "number_of_samples", "time_to_completion_s", "returncode", "cmd",
    ]
    stop_configs = [
        ("num_samples", f"-n{SAMPLE_N}"),
        ("precision",   f"-p{PRECISION}"),
    ]

    file_mode = "a" if args.append else "w"
    with open(args.out, file_mode, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not args.append:
            writer.writeheader()
            f.flush()

        row_count = 0
        for run_idx in range(1, args.runs + 1):
            print(f"=== Run {run_idx}/{args.runs} ===")
            for method in methods:
                for t in THREAD_COUNTS:
                    for stop_mode, stop_flag in stop_configs:
                        cmd = build_cmd(blant_bin, network, args.k, t,
                                        stop_flag, args.output_mode, method)
                        cmd_str = " ".join(cmd)
                        print(f"  [{method} t={t} {stop_flag}] {cmd_str}")

                        result = run_blant(cmd, timeout=args.timeout)

                        reported_n = (SAMPLE_N if stop_mode == "num_samples"
                                      else result["samples_from_output"] or "N/A")

                        elapsed_str = f"{result['elapsed']:.3f}"
                        print(f"    Done in {elapsed_str}s  |  rc={result['returncode']}  |  samples={reported_n}")
                        if result["returncode"] not in (0, "TIMEOUT"):
                            print(f"    stderr tail: {result['stderr_tail']}")

                        writer.writerow({
                            "run":                  run_idx,
                            "sampling_method":      method,
                            "threads":              t,
                            "stop_mode":            stop_mode,
                            "number_of_samples":    reported_n,
                            "time_to_completion_s": elapsed_str,
                            "returncode":           result["returncode"],
                            "cmd":                  cmd_str,
                        })
                        f.flush()
                        row_count += 1
            print()

    print(f"Results written to {args.out}  ({row_count} rows)")


if __name__ == "__main__":
    main()
