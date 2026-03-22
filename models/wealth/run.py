"""
Run the Extended Wealth Distribution Model.

Usage:
    python run.py                                 # default (scale-free network)
    python run.py --network erdos_renyi           # random network
    python run.py --network watts_strogatz        # small-world
    python run.py --pct_savers 0.3                # 30% savers
    python run.py --compare                       # run all 3 network types and compare
    python run.py --steps 200 --no-plot           # headless run

Requires: mesa, matplotlib, networkx
    pip install mesa matplotlib networkx
"""

import argparse
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import networkx as nx

from model import WealthModel, gini_coefficient, lorenz_points, NETWORK_TYPES


def run_single(network_type="barabasi_albert", n_agents=100, steps=150,
               pct_savers=0.0, pct_spenders=0.0, plot=True, seed=42):

    model = WealthModel(
        n_agents=n_agents,
        network_type=network_type,
        pct_savers=pct_savers,
        pct_spenders=pct_spenders,
        seed=seed,
    )

    for _ in range(steps):
        model.step()

    df_model = model.datacollector.get_model_vars_dataframe()
    df_agents = model.datacollector.get_agent_vars_dataframe()

    print(f"\n{'='*55}")
    print(f"Network: {network_type}  |  Agents: {n_agents}  |  Steps: {steps}")
    print(f"  Savers: {pct_savers:.0%}   Spenders: {pct_spenders:.0%}")
    print(f"  Final Gini:        {df_model['gini'].iloc[-1]:.4f}")
    print(f"  Final mean wealth: {df_model['mean_wealth'].iloc[-1]:.2f}")
    print(f"  Final max wealth:  {df_model['max_wealth'].iloc[-1]}")
    print(f"  Agents at zero:    {df_model['n_zero_wealth'].iloc[-1]}")
    print(f"  Total wealth:      {df_model['total_wealth'].iloc[-1]}  (conserved: {model.n_agents})")

    if plot:
        _plot_single(model, df_model, df_agents, network_type, steps)

    return model, df_model


def _plot_single(model, df_model, df_agents, network_type, steps):
    fig = plt.figure(figsize=(16, 10))
    fig.suptitle(f"Wealth Distribution — {network_type} network", fontsize=13)
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.4, wspace=0.35)

    # 1. Gini over time
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(df_model.index, df_model["gini"], color="#E74C3C", linewidth=2)
    ax1.set_title("Gini Coefficient Over Time")
    ax1.set_xlabel("Step")
    ax1.set_ylabel("Gini")
    ax1.set_ylim(0, 1)
    ax1.grid(True, alpha=0.3)

    # 2. Lorenz curve (final state)
    ax2 = fig.add_subplot(gs[0, 1])
    final_wealth = [a.wealth for a in model.agents]
    x, y = lorenz_points(final_wealth)
    ax2.plot(x, y, color="#3498DB", linewidth=2, label="Actual")
    ax2.plot([0, 1], [0, 1], "k--", alpha=0.4, linewidth=1, label="Perfect equality")
    ax2.fill_between(x, x, y, alpha=0.15, color="#E74C3C")
    ax2.set_title(f"Lorenz Curve (step {steps})\nGini = {gini_coefficient(final_wealth):.3f}")
    ax2.set_xlabel("Cumulative population share")
    ax2.set_ylabel("Cumulative wealth share")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    # 3. Wealth distribution histogram
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.hist(final_wealth, bins=30, color="#2ECC71", edgecolor="white", alpha=0.85)
    ax3.set_title("Wealth Distribution (final)")
    ax3.set_xlabel("Wealth")
    ax3.set_ylabel("Count")
    ax3.grid(True, alpha=0.3)

    # 4. Network: node colour = wealth
    ax4 = fig.add_subplot(gs[1, 0])
    G = model.G
    wealth_map = {agent.pos: agent.wealth for agent in model.agents}
    node_colours = [wealth_map.get(n, 0) for n in G.nodes()]
    pos_layout = nx.spring_layout(G, seed=42, k=0.3)
    nx.draw_networkx(
        G, pos=pos_layout, ax=ax4,
        node_color=node_colours, cmap="YlOrRd",
        node_size=30, with_labels=False, edge_color="#cccccc", width=0.3
    )
    ax4.set_title("Network (colour = wealth)")
    ax4.axis("off")

    # 5. Wealth vs degree centrality scatter
    ax5 = fig.add_subplot(gs[1, 1])
    cent_wealth = model.wealth_by_centrality()
    cents = [c for c, _ in cent_wealth]
    wealths = [w for _, w in cent_wealth]
    ax5.scatter(cents, wealths, alpha=0.4, s=20, color="#9B59B6")
    ax5.set_title("Wealth vs Network Centrality")
    ax5.set_xlabel("Degree centrality")
    ax5.set_ylabel("Wealth")
    ax5.grid(True, alpha=0.3)

    # 6. Mean wealth and zero-wealth count over time
    ax6 = fig.add_subplot(gs[1, 2])
    ax6_twin = ax6.twinx()
    ax6.plot(df_model.index, df_model["mean_wealth"], color="#F39C12",
             linewidth=2, label="Mean wealth")
    ax6_twin.plot(df_model.index, df_model["n_zero_wealth"], color="#95A5A6",
                  linewidth=1.5, linestyle="--", label="Agents at zero")
    ax6.set_title("Mean Wealth & Zero-Wealth Agents")
    ax6.set_xlabel("Step")
    ax6.set_ylabel("Mean wealth", color="#F39C12")
    ax6_twin.set_ylabel("# at zero wealth", color="#95A5A6")
    ax6.grid(True, alpha=0.3)
    lines1, labels1 = ax6.get_legend_handles_labels()
    lines2, labels2 = ax6_twin.get_legend_handles_labels()
    ax6.legend(lines1 + lines2, labels1 + labels2, fontsize=8)

    plt.savefig(f"wealth_{network_type}.png", dpi=150, bbox_inches="tight")
    print(f"Plot saved to wealth_{network_type}.png")
    plt.show()


def run_comparison(n_agents=100, steps=150, seed=42):
    """Run all three main network types and compare Gini trajectories."""
    networks = ["barabasi_albert", "erdos_renyi", "watts_strogatz"]
    colours  = ["#E74C3C", "#3498DB", "#2ECC71"]
    results  = {}

    for nt in networks:
        model = WealthModel(n_agents=n_agents, network_type=nt, seed=seed)
        for _ in range(steps):
            model.step()
        results[nt] = model.datacollector.get_model_vars_dataframe()

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Network Topology Comparison", fontsize=13)

    for nt, colour in zip(networks, colours):
        df = results[nt]
        axes[0].plot(df.index, df["gini"], color=colour, linewidth=2, label=nt)
        final_wealth = [
            WealthModel(n_agents=n_agents, network_type=nt, seed=seed)
        ]  # just for lorenz — reuse last model
        x, y = lorenz_points(results[nt]["mean_wealth"].tolist())
        axes[1].plot(x, y, color=colour, linewidth=2, label=nt)

    axes[0].set_title("Gini Coefficient by Network Type")
    axes[0].set_xlabel("Step")
    axes[0].set_ylabel("Gini")
    axes[0].legend(fontsize=9)
    axes[0].grid(True, alpha=0.3)

    axes[1].set_title("Final Gini Summary")
    for i, (nt, colour) in enumerate(zip(networks, colours)):
        final_gini = results[nt]["gini"].iloc[-1]
        axes[1].bar(nt, final_gini, color=colour, alpha=0.8)
        axes[1].text(i, final_gini + 0.005, f"{final_gini:.3f}", ha="center",
                     fontsize=9, fontweight="bold")
    axes[1].set_ylabel("Final Gini")
    axes[1].set_ylim(0, 1)
    axes[1].grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    plt.savefig("wealth_comparison.png", dpi=150, bbox_inches="tight")
    print("Comparison plot saved to wealth_comparison.png")
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Extended Wealth Distribution Model")
    parser.add_argument("--network",      default="barabasi_albert",
                        choices=list(NETWORK_TYPES.keys()))
    parser.add_argument("--n_agents",     type=int,   default=100)
    parser.add_argument("--steps",        type=int,   default=150)
    parser.add_argument("--pct_savers",   type=float, default=0.0)
    parser.add_argument("--pct_spenders", type=float, default=0.0)
    parser.add_argument("--seed",         type=int,   default=42)
    parser.add_argument("--compare",      action="store_true",
                        help="Run all network types and compare Gini")
    parser.add_argument("--no-plot",      action="store_true")
    args = parser.parse_args()

    if args.compare:
        run_comparison(n_agents=args.n_agents, steps=args.steps, seed=args.seed)
    else:
        run_single(
            network_type=args.network,
            n_agents=args.n_agents,
            steps=args.steps,
            pct_savers=args.pct_savers,
            pct_spenders=args.pct_spenders,
            plot=not args.no_plot,
            seed=args.seed,
        )
