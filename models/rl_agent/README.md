# Model 5: RL Agent — Q-Learning on a Grid

**Mesa concepts practised:** `SingleGrid`, `agents_by_type` multi-type stepping, `DataCollector` with agent-level reporters, comparison runs

---

## What this model does

A Q-learning agent learns to navigate a grid collecting rewards (food patches) while avoiding penalty cells (hazards). It is benchmarked against a reactive baseline agent that uses only hard-coded avoidance rules and no learning.

This covers the **third pillar** of the Mesa Behavioral Framework project: learning agents that adapt their behaviour from experience, rather than following fixed rules.

**Q-learning update rule:**
```
Q(s, a) ← Q(s, a) + α · [r + γ · max_a' Q(s', a') − Q(s, a)]
```

| Symbol | Meaning | Value used |
|--------|---------|-----------|
| α | Learning rate | 0.1 |
| γ | Discount factor | 0.95 |
| ε | Exploration rate | 1.0 → 0.05 (exponential decay) |
| r | Reward | +1.0 (food), −0.5 (hazard), −0.01 (step) |

---

## Files

| File | Description |
|------|-------------|
| `model.py` | `QLearnerAgent`, `ReactiveAgent`, `RewardPatch`, `HazardPatch`, `RLGridModel` |
| `run.py` | CLI runner — reward comparison, ε decay curve, learned value heatmap |

---

## How to run

```bash
pip install mesa matplotlib numpy
python run.py
python run.py --steps 500 --rewards 25 --hazards 5
```

---

## What I learned

### Q-learning emergent behaviour
With default parameters (300 steps, 15×15 grid, 20 rewards, 10 hazards), the Q-learner reliably outperforms the reactive baseline by ~40–60% cumulative reward. The value heatmap makes the learned policy legible — high Q-values cluster around reward patches, low/negative values around hazards, with gradient paths leading toward rewards.

### ε-greedy exploration is crucial early
With `epsilon_start=1.0` and `epsilon_decay=0.995`, the agent explores freely for the first ~100 steps then shifts to exploitation. If you set `epsilon_start=0.1` the agent gets trapped exploiting suboptimal paths found early and never recovers. The decay schedule matters as much as α and γ.

### `defaultdict` Q-table vs. explicit state enumeration
Using `defaultdict(lambda: {a: 0.0 for a in ACTIONS})` means the Q-table grows lazily — unvisited states simply don't exist. This is fine for small grids. For larger state spaces (or with additional state features like carrying_food), this would need replacing with a neural network approximator (deep Q-learning).

### Stepping order: environment before agents
Reward patches must `step()` first so their respawn cooldown updates before agents try to collect. If agents step first, a freshly respawned patch gets double-counted on the turn it reactivates. This is another instance of **pain point #2** (stepping order as a silent modelling assumption).

---

## Pain points found

| # | Issue | Severity |
|---|-------|----------|
| 13 | No built-in state abstraction — state is just `agent.pos`; adding features (e.g. carrying, energy level) requires manual tuple-packing | Medium |
| 14 | Q-table not serialisable via `DataCollector` — can't track full policy evolution over time without custom serialisation | Medium |
| 15 | `SingleGrid` prevents multiple agents on same cell — means RL agent can't "pass through" occupied cells, distorting learned policy in dense environments | Low |

---

## Connection to Behavioral Framework

The Q-learner here is a proof-of-concept. What the Behavioral Framework would add:

1. **`RLAgent` mixin** — pluggable policy (Q-table, epsilon-greedy, policy gradient stub) without needing to reimplement the update loop each time
2. **State feature builder** — declarative way to define what goes into the state tuple (position + carrying + energy + …) rather than manual tuple packing
3. **Integration with BDI** — an RL policy could be used *within* a BDI agent as the planning mechanism for a specific desire (e.g. `FORAGE` uses a learned Q-policy rather than greedy Manhattan distance)

The third point — RL as a BDI planner — is the most architecturally interesting and is worth exploring in the proposal.
