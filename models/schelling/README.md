# Model 1: Schelling Segregation

**Mesa concepts practised:** `SingleGrid`, `DataCollector`, `AgentSet.shuffle_do`, `model.running`

---

## What this model does

Thomas Schelling's 1971 model shows that even mild individual preferences for living near similar neighbours produce dramatic residential segregation at the macro level — a classic example of emergent behaviour from simple local rules.

Each agent on a grid has a `homophily` threshold: the minimum number of same-type neighbours they need to be "happy". Unhappy agents move to a random empty cell. The simulation runs until everyone is happy (or a step cap is hit).

**Key insight:** With `homophily=3` on a Moore neighbourhood of 8, an agent only requires 37.5% similarity to be content — a seemingly mild preference. Yet the system consistently self-organises into heavily segregated clusters.

---

## Files

| File | Description |
|------|-------------|
| `model.py` | Core `SchellingAgent` and `SchellingModel` classes |
| `run.py` | CLI runner with matplotlib visualisation |

---

## How to run

```bash
pip install mesa matplotlib
python run.py
```

Options:
```
--homophily INT    Minimum same-type neighbours (default: 3)
--density FLOAT    Grid occupancy (default: 0.8)
--minority_pc FLOAT Fraction of minority agents (default: 0.2)
--steps INT        Max simulation steps (default: 200)
--seed INT         Random seed (default: 42)
--no-plot          Skip matplotlib output
```

---

## What I learned

### Mesa 3.x API differences from older tutorials
The most immediately useful thing was working out how Mesa 3.x differs from older examples online:
- Agents no longer take a `unique_id` parameter — the model assigns one automatically
- `self.schedule.step()` is gone; `self.agents.shuffle_do("step")` replaces it
- `AgentSet` gives you a clean iterable over all agents without needing a separate scheduler object

### Emergent segregation from mild preferences
Running the model with `homophily=3` (only 3 of 8 neighbours need to match) still produces visually obvious segregation within ~30 steps. This matched what Schelling described and is a clean demonstration of the gap between micro-preferences and macro-outcomes — directly relevant to why behaviorally realistic agents matter.

### Data collection pattern
`DataCollector` with lambda model reporters is clean and composable. I used it to track `pct_happy` over time and plot convergence. One thing I noticed: iterating `m.agents` multiple times in the same lambda is fine for small models but would be worth caching for larger ones.

### `model.running` as a halt condition
Setting `self.running = False` when all agents are happy is an elegant pattern — the model self-terminates cleanly without needing an external loop condition.

---

## Experiments run

| homophily | Approx. steps to equilibrium | Final % happy |
|-----------|------------------------------|---------------|
| 2         | ~10                          | 100%          |
| 3         | ~25–35                       | 100%          |
| 4         | ~50–80                       | ~95%          |
| 5         | >100 (often doesn't converge)| ~85%          |

At `homophily=5`, the model often fails to reach full equilibrium — some agents can't find enough similar neighbours regardless of where they move. This is an interesting edge case where individual preferences become collectively infeasible.

---

## Connection to Behavioral Framework

This model's agents have no internal state beyond `agent_type` and `homophily`. Their "decision" is binary and reactive — move if unhappy, stay if happy. There's no memory, no goal representation, no adaptation.

The Behavioral Framework project aims to give agents something like:
- **Beliefs** about their neighbourhood (not just a snapshot count)
- **Desires** that trade off multiple competing goals
- **Intentions** that persist across steps

A BDI-extended Schelling agent might, for example, weight economic factors alongside social ones, or adapt its homophily threshold based on past experience — much closer to how real residential decisions are actually made.
