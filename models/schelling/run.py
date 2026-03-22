"""
Run and visualise the Schelling Segregation Model.

Usage:
    python run.py                    # default parameters
    python run.py --homophily 4      # stricter preference
    python run.py --steps 100        # cap at 100 steps
    python run.py --no-plot          # skip matplotlib output

Requires: mesa, matplotlib
    pip install mesa matplotlib
"""

import argparse
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

from model import SchellingModel


def grid_to_array(model: SchellingModel) -> np.ndarray:
    """Convert current grid state to a 2D numpy array for plotting."""
    grid = np.full((model.width, model.height), np.nan)
    for agent in model.agents:
        x, y = agent.pos
        grid[x][y] = agent.agent_type
    return grid


def run(width=20, height=20, density=0.8, minority_pc=0.2, homophily=3,
        max_steps=200, plot=True, seed=42):

    model = SchellingModel(
        width=width,
        height=height,
        density=density,
        minority_pc=minority_pc,
        homophily=homophily,
        seed=seed,
    )

    if plot:
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        fig.suptitle("Schelling Segregation Model", fontsize=14)

    # Capture initial state
    initial_grid = grid_to_array(model)

    # Run simulation
    step = 0
    while model.running and step < max_steps:
        model.step()
        step += 1

    final_grid = grid_to_array(model)
    df = model.datacollector.get_model_vars_dataframe()

    # Print summary
    print(f"\nParameters: {width}x{height} grid | density={density} | "
          f"minority={minority_pc} | homophily={homophily}")
    print(f"Steps to equilibrium: {step}")
    print(f"Final % happy: {df['pct_happy'].iloc[-1]:.1f}%")
    print(f"Converged: {model.running is False}")

    if plot:
        cmap = mcolors.ListedColormap(["#E74C3C", "#3498DB"])
        bounds = [-0.5, 0.5, 1.5]
        norm = mcolors.BoundaryNorm(bounds, cmap.N)

        # Initial state
        axes[0].imshow(initial_grid.T, cmap=cmap, norm=norm, origin="lower",
                       interpolation="nearest")
        axes[0].set_title("Initial State")
        axes[0].axis("off")

        # Final state
        axes[1].imshow(final_grid.T, cmap=cmap, norm=norm, origin="lower",
                       interpolation="nearest")
        axes[1].set_title(f"After {step} Steps")
        axes[1].axis("off")

        # Happiness over time
        axes[2].plot(df.index, df["pct_happy"], color="#2ECC71", linewidth=2)
        axes[2].set_xlabel("Step")
        axes[2].set_ylabel("% Happy")
        axes[2].set_title("Happiness Over Time")
        axes[2].set_ylim(0, 105)
        axes[2].grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig("schelling_output.png", dpi=150, bbox_inches="tight")
        print("\nPlot saved to schelling_output.png")
        plt.show()

    return model, df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Schelling Segregation Model")
    parser.add_argument("--width", type=int, default=20)
    parser.add_argument("--height", type=int, default=20)
    parser.add_argument("--density", type=float, default=0.8)
    parser.add_argument("--minority_pc", type=float, default=0.2)
    parser.add_argument("--homophily", type=int, default=3)
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-plot", action="store_true")
    args = parser.parse_args()

    run(
        width=args.width,
        height=args.height,
        density=args.density,
        minority_pc=args.minority_pc,
        homophily=args.homophily,
        max_steps=args.steps,
        plot=not args.no_plot,
        seed=args.seed,
    )
