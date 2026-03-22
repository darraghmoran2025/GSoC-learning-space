# Model 3: Wealth Distribution (Extended)

**Mesa concepts practised:** `NetworkGrid`, `DataCollector` with agent-level reporters, network topology comparison, `agents_by_type`

---

## What this model does

Extends Mesa's tutorial MoneyModel by placing agents on a NetworkX graph instead of a flat grid, adding behavioural agent types (savers, spenders, balanced), and tracking distributional inequality through the Gini coefficient and Lorenz curve.

The core transfer rule is unchanged from the tutorial: agents with wealth > 0 give one unit to a random network neighbour each step. All interesting variance comes from **topology** and **agent type**.

**Key insight:** Network structure has a measurable effect on the rate and ceiling of inequality. Scale-free (Barabási–Albert) networks consistently produce higher Gini coefficients than random or small-world networks — highly connected hub agents accumulate disproportionate wealth simply because they have more transfer opportunities.

---

## Files

| File | Description |
|------|-------------|
| `model.py` | `WealthAgent`, `WealthModel`, `gini_coefficient()`, `lorenz_points()` |
| `run.py` | CLI runner with full 6-panel visualisation and `--compare` mode |

---

## How to run

```bash
pip install mesa matplotlib networkx
python run.py                              # scale-free network, default params
python run.py --network watts_strogatz    # small-world
python run.py --compare                   # overlay Gini for all 3 topologies
python run.py --pct_savers 0.3           # 30% of agents are savers
```

---

## What I learned

### NetworkGrid — key differences from SingleGrid / MultiGrid

`NetworkGrid` wraps a NetworkX graph rather than a 2D array. Several things change:

- **`get_neighbors(node_id)`** — takes a node integer ID, not an `(x, y)` tuple. The node ID is the agent's `pos` attribute, which Mesa sets to the integer node index on placement.
- **`coord_iter()`** — not available on `NetworkGrid`. Use `G.nodes()` to iterate positions.
- **No `is_cell_empty()`** — had to check `grid.get_cell_list_contents([node])` manually. This is a meaningful API gap.

### Agent-level DataCollector reporters

This was the first model using `agent_reporters`. The resulting dataframe is multi-indexed `(Step, AgentID)`, which requires `df.xs(step_n, level="Step")` or `df.unstack()` to access per-step cross-sections. Not immediately obvious from the docs — see pain point #7 below.

### Gini coefficient and wealth conservation

Total wealth is conserved (it's just redistributed), so the system can't "create" or "destroy" wealth. Gini rising over time means the distribution is concentrating, not that aggregate wealth is changing. Confirming `total_wealth` stays equal to `n_agents` in every step is a useful model sanity check.

### Network centrality predicts final wealth

Scatter plot of degree centrality vs final wealth shows a clear positive correlation in Barabási–Albert networks. This isn't hardcoded — it emerges from the transfer rule because high-degree nodes statistically receive more transfers. Worth raising in any discussion of how network structure encodes structural advantage even with identical agent behaviour.

---

## Experiments

| Network type | Final Gini (n=100, 150 steps) | Notes |
|---|---|---|
| Barabási–Albert (m=2) | ~0.62 | Highest inequality — hubs accumulate |
| Watts–Strogatz (k=4, p=0.1) | ~0.55 | Moderate — clustering slows spread |
| Erdős–Rényi (p=0.05) | ~0.50 | Lowest — uniform degree distribution |
| 30% savers (BA) | ~0.58 | Savers slow their own accumulation |
| 30% spenders (BA) | ~0.67 | Spenders accelerate wealth loss |

---

## Pain Points

### #6 — `NetworkGrid.coord_iter()` is not implemented
`SingleGrid` and `MultiGrid` expose `coord_iter()` for looping over all positions. `NetworkGrid` does not. You have to fall back to `G.nodes()` from the networkx graph directly, which breaks the abstraction — you need to hold a reference to the raw graph alongside the Mesa grid object.

**Impact:** Medium. Workaround is straightforward but the inconsistency is a trap for anyone porting grid-based code to a network.

---

### #7 — Agent-level DataCollector output format is non-obvious
`get_agent_vars_dataframe()` returns a DataFrame indexed by `(Step, AgentID)`. Accessing wealth for a single step requires `df.xs(step, level="Step")`. This is not documented clearly in the tutorial or API reference — discovered by trial and error.

**Impact:** Medium. A worked example in the docs would save significant time.

---

### #8 — `NetworkGrid.get_neighbors()` silently returns empty list for isolated nodes
Nodes with degree 0 (can occur in Erdős–Rényi with low p) return an empty neighbour list. The agent's `step()` returns early with no action. This is correct behaviour, but it's silent — isolated agents just stop participating in the simulation without any warning. In a model where isolation is unintended, this is hard to diagnose.

**Impact:** Low-medium. Worth a warning in the grid docs.

---

## Connection to Behavioral Framework

The current `WealthAgent` makes one decision per step: give or don't give. There's no memory of past transactions, no model of how wealthy neighbours are, no adaptive strategy.

A behaviorally richer agent might:
- **Believe** that certain neighbours are reliably wealthy (belief update from observation)
- **Desire** to maintain a minimum wealth floor (needs-based goal)
- **Intend** to preferentially transfer to poorer neighbours (solidarity strategy)

This would require exactly the BDI or needs-based architecture proposed in the Behavioral Framework project.
