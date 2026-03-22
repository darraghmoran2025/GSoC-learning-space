"""
Run and visualise the Wolf-Sheep Predator-Prey Model.

Usage:
    python run.py                         # default parameters, 300 steps
    python run.py --steps 500             # longer run
    python run.py --wolves 5              # stress test: near-extinction start
    python run.py --sheep_reproduce 0.06  # faster sheep reproduction
    python run.py --no-plot               # skip matplotlib output

Requires: mesa, matplotlib, numpy
    pip install mesa matplotlib numpy
"""

import argparse
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

from model import WolfSheepModel, Wolf, Sheep, GrassPatch


# ---------------------------------------------------------------------------
# Grid renderer
# ---------------------------------------------------------------------------

def grid_snapshot(model: WolfSheepModel) -> np.ndarray:
    """
    Encode the grid as a 2D array for imshow:
        0 = empty / no grass
        1 = grass only
        2 = sheep (on grass or not)
        3 = wolf
    Priority: wolf > sheep > grass > empty
    """
    arr = np.zeros((model.width, model.height), dtype=int)

    for agent in model.agents_by_type[GrassPatch]:
        if agent.fully_grown:
            x, y = agent.pos
            arr[x][y] = max(arr[x][y], 1)

    for agent in model.agents_by_type[Sheep]:
        x, y = agent.pos
        arr[x][y] = max(arr[x][y], 2)

    for agent in model.agents_by_type[Wolf]:
        x, y = agent.pos
        arr[x][y] = max(arr[x][y], 3)

    return arr


# ---------------------------------------------------------------------------
# Main run function
# ---------------------------------------------------------------------------

def run(
    width=20,
    height=20,
    initial_sheep=100,
    initial_wolves=25,
    sheep_reproduce=0.04,
    wolf_reproduce=0.05,
    wolf_gain_from_food=20,
    sheep_gain_from_food=4,
    grass_regrowth_time=30,
    max_steps=300,
    plot=True,
    seed=42,
):
    model = WolfSheepModel(
        width=width,
        height=height,
        initial_sheep=initial_sheep,
        initial_wolves=initial_wolves,
        sheep_reproduce=sheep_reproduce,
        wolf_reproduce=wolf_reproduce,
        wolf_gain_from_food=wolf_gain_from_food,
        sheep_gain_from_food=sheep_gain_from_food,
        grass_regrowth_time=grass_regrowth_time,
        seed=seed,
    )

    initial_snap = grid_snapshot(model)
    midpoint_snap = None

    step = 0
    while model.running and step < max_steps:
        model.step()
        step += 1
        if step == max_steps // 2:
            midpoint_snap = grid_snapshot(model)

    if midpoint_snap is None:
        midpoint_snap = grid_snapshot(model)

    final_snap = grid_snapshot(model)
    df = model.datacollector.get_model_vars_dataframe()

    # ----------------------------------------------------------------
    # Summary
    # ----------------------------------------------------------------
    final_wolves = len(model.agents_by_type[Wolf])
    final_sheep = len(model.agents_by_type[Sheep])
    extinct = "wolves" if final_wolves == 0 else ("sheep" if final_sheep == 0 else None)

    print(f"\n{'='*55}")
    print(f"  Wolf-Sheep Model — Run Summary")
    print(f"{'='*55}")
    print(f"  Steps run       : {step}")
    print(f"  Final wolves    : {final_wolves}")
    print(f"  Final sheep     : {final_sheep}")
    print(f"  Peak wolves     : {int(df['wolves'].max())}")
    print(f"  Peak sheep      : {int(df['sheep'].max())}")
    if extinct:
        print(f"  *** {extinct.upper()} WENT EXTINCT at step ~{step} ***")
    else:
        print(f"  Model still running at step cap.")
    print(f"{'='*55}\n")

    if not plot:
        return model, df

    # ----------------------------------------------------------------
    # Plot layout:
    #   Row 0: three grid snapshots (initial / mid / final)
    #   Row 1: population time series
    # ----------------------------------------------------------------
    fig = plt.figure(figsize=(16, 10))
    fig.suptitle("Wolf-Sheep Predator-Prey Model", fontsize=15, fontweight="bold")

    cmap = mcolors.ListedColormap(["#D5D8DC", "#2ECC71", "#85C1E9", "#E74C3C"])
    bounds = [-0.5, 0.5, 1.5, 2.5, 3.5]
    norm = mcolors.BoundaryNorm(bounds, cmap.N)

    def draw_grid(ax, data, title):
        im = ax.imshow(data.T, cmap=cmap, norm=norm, origin="lower",
                       interpolation="nearest")
        ax.set_title(title, fontsize=11)
        ax.axis("off")
        return im

    ax1 = fig.add_subplot(2, 3, 1)
    ax2 = fig.add_subplot(2, 3, 2)
    ax3 = fig.add_subplot(2, 3, 3)
    ax_pop = fig.add_subplot(2, 1, 2)

    draw_grid(ax1, initial_snap, "Step 0")
    draw_grid(ax2, midpoint_snap, f"Step {max_steps // 2}")
    im = draw_grid(ax3, final_snap, f"Step {step}")

    # Colour legend
    from matplotlib.patches import Patch
    legend_handles = [
        Patch(facecolor="#D5D8DC", label="Empty / no grass"),
        Patch(facecolor="#2ECC71", label="Grass"),
        Patch(facecolor="#85C1E9", label="Sheep"),
        Patch(facecolor="#E74C3C", label="Wolf"),
    ]
    ax3.legend(
        handles=legend_handles,
        loc="lower right",
        bbox_to_anchor=(1.55, 0),
        framealpha=0.9,
        fontsize=8,
    )

    # Population time series
    ax_pop.plot(df.index, df["wolves"], color="#E74C3C", linewidth=2, label="Wolves")
    ax_pop.plot(df.index, df["sheep"], color="#85C1E9", linewidth=2, label="Sheep")
    ax_pop.plot(df.index, df["grass_patches"], color="#2ECC71", linewidth=1.5,
                linestyle="--", alpha=0.7, label="Grass patches (grown)")
    ax_pop.set_xlabel("Step", fontsize=11)
    ax_pop.set_ylabel("Count", fontsize=11)
    ax_pop.set_title("Population Dynamics", fontsize=11)
    ax_pop.legend(fontsize=10)
    ax_pop.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("wolf_sheep_output.png", dpi=150, bbox_inches="tight")
    print("Plot saved to wolf_sheep_output.png")
    plt.show()

    return model, df


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Wolf-Sheep Predator-Prey Model")
    parser.add_argument("--width", type=int, default=20)
    parser.add_argument("--height", type=int, default=20)
    parser.add_argument("--sheep", type=int, default=100, dest="initial_sheep")
    parser.add_argument("--wolves", type=int, default=25, dest="initial_wolves")
    parser.add_argument("--sheep_reproduce", type=float, default=0.04)
    parser.add_argument("--wolf_reproduce", type=float, default=0.05)
    parser.add_argument("--wolf_gain", type=int, default=20, dest="wolf_gain_from_food")
    parser.add_argument("--sheep_gain", type=int, default=4, dest="sheep_gain_from_food")
    parser.add_argument("--grass_regrowth", type=int, default=30, dest="grass_regrowth_time")
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-plot", action="store_true")
    args = parser.parse_args()

    run(
        width=args.width,
        height=args.height,
        initial_sheep=args.initial_sheep,
        initial_wolves=args.initial_wolves,
        sheep_reproduce=args.sheep_reproduce,
        wolf_reproduce=args.wolf_reproduce,
        wolf_gain_from_food=args.wolf_gain_from_food,
        sheep_gain_from_food=args.sheep_gain_from_food,
        grass_regrowth_time=args.grass_regrowth_time,
        max_steps=args.steps,
        plot=not args.no_plot,
        seed=args.seed,
    )
