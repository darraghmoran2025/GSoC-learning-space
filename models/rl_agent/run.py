"""
Run and visualise the RL Grid Model.

Produces three panels:
  1. Cumulative reward: Q-learner vs reactive baseline over time
  2. Exploration rate (ε) decay curve
  3. Final grid heatmap of learned Q-values (max Q per cell)

Usage:
    python run.py                   # default settings
    python run.py --steps 500       # longer training
    python run.py --no-plot         # skip matplotlib

Requires: mesa, matplotlib, numpy
    pip install mesa matplotlib numpy
"""

import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from model import RLGridModel, QLearnerAgent, RewardPatch, HazardPatch


def extract_value_map(model: RLGridModel) -> np.ndarray:
    """Build a (width × height) array of max Q-value per cell."""
    vmap = np.zeros((model.width, model.height))
    for agent in model.agents:
        if isinstance(agent, QLearnerAgent):
            for state, q_vals in agent.q_table.items():
                x, y = state
                vmap[x][y] = max(vmap[x][y], max(q_vals.values()))
    return vmap


def run(steps=300, plot=True, seed=42, **kwargs):
    model = RLGridModel(seed=seed, **kwargs)

    for _ in range(steps):
        model.step()

    df = model.datacollector.get_model_vars_dataframe()
    agent_df = model.datacollector.get_agent_vars_dataframe()

    # Summary
    learner_total = df["learner_reward"].iloc[-1]
    reactive_total = df["reactive_reward"].iloc[-1]
    print(f"\nSteps: {steps}")
    print(f"Q-learner cumulative reward:  {learner_total:.2f}")
    print(f"Reactive baseline reward:     {reactive_total:.2f}")
    improvement = (learner_total - reactive_total) / max(abs(reactive_total), 1e-6) * 100
    print(f"Learner advantage:            {improvement:+.1f}%")

    # Q-table stats
    for agent in model.agents:
        if isinstance(agent, QLearnerAgent):
            print(f"Q-table states learned:       {len(agent.q_table)}")
            print(f"Final ε (exploration rate):   {agent.epsilon:.4f}")

    if plot:
        fig, axes = plt.subplots(1, 3, figsize=(16, 5))
        fig.suptitle("Q-Learning Agent vs Reactive Baseline", fontsize=14)

        # Panel 1: cumulative reward comparison
        axes[0].plot(df.index, df["learner_reward"], label="Q-Learner",
                     color="#3498DB", linewidth=2)
        axes[0].plot(df.index, df["reactive_reward"], label="Reactive",
                     color="#E74C3C", linewidth=2, linestyle="--")
        axes[0].set_xlabel("Step")
        axes[0].set_ylabel("Cumulative Reward")
        axes[0].set_title("Cumulative Reward Over Time")
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        # Panel 2: epsilon decay
        learner_agents = agent_df[agent_df["epsilon"].notna()]
        if not learner_agents.empty:
            eps_series = learner_agents.groupby("Step")["epsilon"].mean()
            axes[1].plot(eps_series.index, eps_series.values,
                         color="#2ECC71", linewidth=2)
            axes[1].set_xlabel("Step")
            axes[1].set_ylabel("ε (exploration rate)")
            axes[1].set_title("Exploration Rate Decay")
            axes[1].set_ylim(0, 1.05)
            axes[1].grid(True, alpha=0.3)

        # Panel 3: learned value map
        vmap = extract_value_map(model)
        im = axes[2].imshow(vmap.T, origin="lower", cmap="YlOrRd",
                            interpolation="nearest")
        # Overlay reward and hazard positions
        for agent in model.agents:
            if isinstance(agent, RewardPatch):
                axes[2].plot(*agent.pos, "g*", markersize=8, alpha=0.7)
            elif isinstance(agent, HazardPatch):
                axes[2].plot(*agent.pos, "rx", markersize=8, alpha=0.7)
        plt.colorbar(im, ax=axes[2], label="Max Q-value")
        axes[2].set_title("Learned Value Map\n(★ = reward, ✗ = hazard)")
        axes[2].axis("off")

        plt.tight_layout()
        plt.savefig("rl_output.png", dpi=150, bbox_inches="tight")
        print("\nPlot saved to rl_output.png")
        plt.show()

    return model, df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RL Grid Model")
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--width", type=int, default=15)
    parser.add_argument("--height", type=int, default=15)
    parser.add_argument("--learners", type=int, default=1)
    parser.add_argument("--reactive", type=int, default=1)
    parser.add_argument("--rewards", type=int, default=20)
    parser.add_argument("--hazards", type=int, default=10)
    parser.add_argument("--alpha", type=float, default=0.1)
    parser.add_argument("--gamma", type=float, default=0.95)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-plot", action="store_true")
    args = parser.parse_args()

    run(
        steps=args.steps,
        width=args.width,
        height=args.height,
        n_learners=args.learners,
        n_reactive=args.reactive,
        n_rewards=args.rewards,
        n_hazards=args.hazards,
        alpha=args.alpha,
        gamma=args.gamma,
        seed=args.seed,
        plot=not args.no_plot,
    )
