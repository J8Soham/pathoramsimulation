import json
import matplotlib.pyplot as plt


def plot_results():
    with open("results.json", "r") as f:
        results = json.load(f)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    title_map = {"crime": "Chicago Crime", "tpch": "TPC-H Orders"}

    for col, (dataset_name, dataset_results) in enumerate(results.items()):
        x_values = sorted(set(v["x"] for v in dataset_results.values()))
        alpha_values = sorted(set(v["alpha"] for v in dataset_results.values()))

        ax_qr = axes[0][col]
        for x in x_values:
            rates = []
            for a in alpha_values:
                key = f"a{a}_x{x}"
                rates.append(dataset_results[key]["query_recovery"])
            ax_qr.plot(alpha_values, rates, 'o-', label=f"x={x}", linewidth=2, markersize=7)
        ax_qr.set_title(f"{title_map.get(dataset_name, dataset_name)} — Query Recovery", fontsize=12)
        ax_qr.set_xlabel("α", fontsize=11)
        ax_qr.set_ylabel("Attack Success Rate", fontsize=11)
        ax_qr.set_ylim(-0.05, 1.05)
        ax_qr.set_xticks(alpha_values)
        ax_qr.legend(fontsize=10)
        ax_qr.grid(True, alpha=0.3)

        ax_dr = axes[1][col]
        for x in x_values:
            rates = []
            for a in alpha_values:
                key = f"a{a}_x{x}"
                rates.append(dataset_results[key]["database_recovery"])
            ax_dr.plot(alpha_values, rates, 's--', label=f"x={x}", linewidth=2, markersize=7)
        ax_dr.set_title(f"{title_map.get(dataset_name, dataset_name)} — Database Recovery", fontsize=12)
        ax_dr.set_xlabel("α", fontsize=11)
        ax_dr.set_ylabel("Attack Success Rate", fontsize=11)
        ax_dr.set_ylim(-0.05, 1.05)
        ax_dr.set_xticks(alpha_values)
        ax_dr.legend(fontsize=10)
        ax_dr.grid(True, alpha=0.3)

    fig.suptitle("SEAL (α, x) vs Path ORAM (α=0, x=1): Attack Success Rates", fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig("seal_vs_pathoram.png", dpi=150)
    print("plot saved")


if __name__ == "__main__":
    plot_results()
