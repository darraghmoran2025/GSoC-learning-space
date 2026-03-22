"""
Run the BDI Foraging Model.

Usage:
    python run.py                      # default parameters, animated grid
    python run.py --steps 100          # run 100 steps then show summary
    python run.py --foragers 15        # more agents
    python run.py --vision 5           # wider agent vision
    python run.py --no-plot            # headless, print stats only

Requires: mesa, matplotlib
    pip install mesa matplotlib
"""

import argparse
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import numpy as np

from model import ForagingModel, ForagerAgent, FoodPatch, ForagerDesire


# Colour map for desires
DESIRE_COLOURS = {
    "EXPLORE":     "#3498DB",   # blue
    "FORAGE":      "#2ECC71",   # green
    "RETURN_HOME": "#F39C12",   # orange
    "REST":        "#E74C3C",   # red
    None:          "#BDC3C7",   # grey (no desire yet)
}


def grid_snapshot(model: ForagingModel):
    """
    Return three 2D arrays for plotting:
      food_grid    — 1 where FoodPatch exists, 0 otherwise
      forager_grid — desire index at forager positions, -1 elsewhere
    """
    w, h = model.width, model.height
    food_grid    = np.zeros((w, h))
    forager_grid = np.full((w, h), -1.0)

    desire_order = [None, "EXPLORE", "FORAGE", "RETURN_HOME", "REST"]

    for agent in model.agents:
        x, y = agent.pos
        if isinstance(agent, FoodPatch):
            food_grid[x][y] = 1
        elif isinstance(agent, ForagerAgent):
            d = agent.current_desire.name if agent.current_desire else None
            forager_grid[x][y] = desire_order.index(d)

    return food_grid, forager_grid


def run(width=25, height=25, n_foragers=10, n_food=60,
        food_regrow_rate=0.005, vision=3, steps=120, plot=True, seed=42):

    model = ForagingModel(
        width=width, height=height,
        n_foragers=n_foragers, n_food=n_food,
        food_regrow_rate=food_regrow_rate,
        vision_range=vision,
        seed=seed,
    )

    if not plot:
        for _ in range(steps):
            if not model.running:
                break
            model.step()
        _print_summary(model)
        return model

    # ----------------------------------------------------------------
    # Animated run with live grid + time-series panels
    # ----------------------------------------------------------------
    plt.ion()
    fig = plt.figure(figsize=(16, 8))
    gs  = gridspec.GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.35)

    ax_grid    = fig.add_subplot(gs[:, 0])   # grid (tall)
    ax_collect = fig.add_subplot(gs[0, 1])   # food collected
    ax_energy  = fig.add_subplot(gs[0, 2])   # avg energy
    ax_food    = fig.add_subplot(gs[1, 1])   # food on grid
    ax_desire  = fig.add_subplot(gs[1, 2])   # desire distribution

    desire_order = [None, "EXPLORE", "FORAGE", "RETURN_HOME", "REST"]

    collect_hist, energy_hist, food_hist = [], [], []
    desire_counts = {d: [] for d in desire_order}

    for step_n in range(steps):
        if not model.running:
            break
        model.step()

        df = model.datacollector.get_model_vars_dataframe()
        collect_hist.append(df["total_collected"].iloc[-1])
        energy_hist.append(df["avg_energy"].iloc[-1])
        food_hist.append(df["food_on_grid"].iloc[-1])

        # Tally current desires
        foragers = list(model.agents_by_type[ForagerAgent])
        tally = {d: 0 for d in desire_order}
        for a in foragers:
            tally[a.current_desire.name if a.current_desire else None] += 1
        for d in desire_order:
            desire_counts[d].append(tally[d])

        if step_n % 5 == 0 or step_n == steps - 1:
            food_grid, forager_grid = grid_snapshot(model)

            # Grid
            ax_grid.cla()
            ax_grid.imshow(food_grid.T, cmap="Greens", origin="lower",
                           vmin=0, vmax=1, alpha=0.6, interpolation="nearest")
            cmap_d = plt.cm.get_cmap("tab10", 5)
            masked  = np.ma.masked_where(forager_grid.T < 0, forager_grid.T)
            ax_grid.imshow(masked, cmap=cmap_d, origin="lower",
                           vmin=0, vmax=4, alpha=0.9, interpolation="nearest")
            hx, hy = model.home_pos
            ax_grid.plot(hx, hy, "k*", markersize=12)
            ax_grid.set_title(f"Step {step_n+1}  |  Foragers: {len(foragers)}")
            ax_grid.axis("off")

            # Patches legend
            patches = [mpatches.Patch(color="#2ECC71", alpha=0.6, label="Food")]
            patches.append(mpatches.Patch(color="black", label="Home ★"))
            for i, d in enumerate(desire_order):
                label = d if d else "Idle"
                patches.append(mpatches.Patch(color=cmap_d(i), label=label))
            ax_grid.legend(handles=patches, loc="lower left",
                           fontsize=7, framealpha=0.8)

            # Time series
            xs = list(range(len(collect_hist)))

            ax_collect.cla()
            ax_collect.plot(xs, collect_hist, color="#F39C12", linewidth=2)
            ax_collect.set_title("Total Food Collected")
            ax_collect.set_xlabel("Step")
            ax_collect.grid(True, alpha=0.3)

            ax_energy.cla()
            ax_energy.plot(xs, energy_hist, color="#E74C3C", linewidth=2)
            ax_energy.set_title("Avg Agent Energy")
            ax_energy.set_xlabel("Step")
            ax_energy.set_ylim(0, 32)
            ax_energy.grid(True, alpha=0.3)

            ax_food.cla()
            ax_food.plot(xs, food_hist, color="#27AE60", linewidth=2)
            ax_food.set_title("Food Items on Grid")
            ax_food.set_xlabel("Step")
            ax_food.grid(True, alpha=0.3)

            ax_desire.cla()
            colours = [DESIRE_COLOURS[d] for d in desire_order]
            bottom  = np.zeros(len(xs))
            for d, colour in zip(desire_order, colours):
                vals = np.array(desire_counts[d])
                label = d if d else "Idle"
                ax_desire.fill_between(xs, bottom, bottom + vals,
                                       color=colour, alpha=0.8, label=label)
                bottom += vals
            ax_desire.set_title("Desire Distribution")
            ax_desire.set_xlabel("Step")
            ax_desire.set_ylabel("Agents")
            ax_desire.legend(fontsize=7, loc="upper right")
            ax_desire.grid(True, alpha=0.2)

            plt.pause(0.05)

    plt.ioff()
    _print_summary(model)
    plt.savefig("bdi_foraging_output.png", dpi=150, bbox_inches="tight")
    print("Plot saved to bdi_foraging_output.png")
    plt.show()
    return model


def _print_summary(model: ForagingModel):
    df = model.datacollector.get_model_vars_dataframe()
    foragers = list(model.agents_by_type[ForagerAgent])
    print(f"\n{'='*50}")
    print(f"BDI Foraging Model — Summary")
    print(f"  Steps run:        {len(df)}")
    print(f"  Foragers alive:   {len(foragers)}")
    print(f"  Total collected:  {df['total_collected'].iloc[-1]}")
    print(f"  Food on grid:     {df['food_on_grid'].iloc[-1]}")
    print(f"  Avg energy:       {df['avg_energy'].iloc[-1]:.1f}")
    print(f"  Avg replans:      {df['avg_replans'].iloc[-1]:.1f}")
    print(f"  Avg failed acts:  {df['avg_failed_actions'].iloc[-1]:.1f}")
    if foragers:
        top = max(foragers, key=lambda a: a.food_collected)
        print(f"  Top collector:    agent {top.unique_id} ({top.food_collected} items)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run BDI Foraging Model")
    parser.add_argument("--width",    type=int,   default=25)
    parser.add_argument("--height",   type=int,   default=25)
    parser.add_argument("--foragers", type=int,   default=10)
    parser.add_argument("--food",     type=int,   default=60)
    parser.add_argument("--regrow",   type=float, default=0.005)
    parser.add_argument("--vision",   type=int,   default=3)
    parser.add_argument("--steps",    type=int,   default=120)
    parser.add_argument("--seed",     type=int,   default=42)
    parser.add_argument("--no-plot",  action="store_true")
    args = parser.parse_args()

    run(
        width=args.width, height=args.height,
        n_foragers=args.foragers, n_food=args.food,
        food_regrow_rate=args.regrow, vision=args.vision,
        steps=args.steps, plot=not args.no_plot, seed=args.seed,
    )
