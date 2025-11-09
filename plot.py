import pandas as pd
import matplotlib.pyplot as plt

# Read CSV
df = pd.read_csv("fast-test_output.csv")

# Group by STOP_MODE and NUM_THREADS and take mean TIME
grouped = df.groupby(["STOP_MODE", "NUM_THREADS"])["TIME"].mean().reset_index()

# Compute baseline (1-thread) mean for each STOP_MODE
baselines = (
    grouped[grouped["NUM_THREADS"] == 1].set_index("STOP_MODE")["TIME"].to_dict()
)

# Compute speedup
grouped["speedup"] = grouped.apply(
    lambda row: baselines[row["STOP_MODE"]] / row["TIME"], axis=1
)

# Plot
plt.figure(figsize=(8, 5))
for stop_mode, data in grouped.groupby("STOP_MODE"):
    plt.plot(data["NUM_THREADS"], data["speedup"], marker="o", label=stop_mode)

plt.xlabel("Number of Threads")
plt.ylabel("Speedup (vs. 1 Thread)")
plt.title("Speedup vs Threads")
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend(title="STOP_MODE")
plt.tight_layout()
plt.savefig("speedup.png", dpi=300)
