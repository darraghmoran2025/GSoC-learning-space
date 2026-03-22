# Review: 1khaled-ctrl (Khaled Saber)

**Repo:** https://github.com/1khaled-ctrl/mesa-behavior-framework-prototype
**Discussion:** https://github.com/mesa/mesa/discussions/3559
**Date reviewed:** 2026-03-22

---

## What they built

A modular behavioural system prototype with three core components:

1. **`BehaviorModule`** — base class for reusable, composable behaviour units attachable to any agent
2. **`StateMachine`** — finite-state controller using lambda-based conditions to trigger transitions
3. **`BehaviorMixin`** — mixin providing `add_behavior()`, `remove_behavior()`, `run_behaviors()` to any Mesa agent

Two example models: a forager (energy-based state cycling between search and rest) and a predator-prey model reusing the same movement and energy modules for both wolves and sheep.

---

## What I found interesting

### The compositional approach is different from mine

Khaled went with **FSM + composition** (behaviours are modules that plug into agents) whereas I went with **BDI + deliberation** (agents have an internal cognitive cycle). These are genuinely different architectures, not just implementation differences:

- FSM is better for agents with well-defined, enumerable states and deterministic transitions
- BDI is better for agents with open-ended goals, partial information, and the need to replan

For Mesa's Behavioral Framework, both probably belong in the toolbox — FSM for simpler agents (traffic lights, disease states), BDI for cognitively richer agents (economic actors, strategic decision-makers).

### Behaviour reuse across agent types is a real Mesa gap
The predator-prey example is a good demonstration of the compositional advantage: wolves and sheep share energy depletion and random movement modules. In standard Mesa, you'd copy-paste or build an inheritance hierarchy. The mixin approach is leaner.

### Lambda-based FSM transitions are clean but limited
Using lambdas for conditions (`lambda agent: agent.energy < 5`) is elegant for simple cases but will get unwieldy for conditions that depend on multiple belief states, time history, or other agents. No explicit reference to how this would scale.

---

## What I learned from reading their work

The FSM approach made me reconsider one thing: **not all agents need full BDI deliberation**. For a grass patch that cycles between grown/ungrown, a simple FSM is the right tool. The Behavioral Framework proposal is stronger if it offers a spectrum — FSM for simple state cycling, BDI for goal-directed agents, RL for adaptive agents — rather than mandating one architecture for everything.

This also suggests a shared abstraction: both FSM and BDI share the concept of a "current behavioural mode" (state / current desire) and "transition triggers" (FSM conditions / desire re-evaluation). A common `BehavioralAgent` base that both FSM and BDI extend would allow interoperability.

---

## Feedback I'd offer

### Strengths
- The modular composition idea solves a real Mesa pain point (behaviour reuse) that my proposal doesn't address directly
- The predator-prey reuse example is a concrete, compelling demo
- Clean separation of concerns: FSM handles state, modules handle execution

### Questions / gaps
1. **How does the FSM handle competing priorities?** If an agent is in SEARCH state but encounters a predator, how does it override to FLEE? Priority-based interruption isn't evident in the current design — this is where BDI's desire ordering handles things more naturally.

2. **No belief representation.** The FSM conditions read agent attributes directly (e.g. `agent.energy`). For agents with partial observability or beliefs that can be wrong, you'd want a layer between perception and decision. Without it, FSM agents are still implicitly omniscient.

3. **How does this relate to `mesa.experimental.actions`?** Mesa already has an experimental Actions system with duration and interruption semantics (discussion #3304). It would strengthen the proposal to explicitly address how BehaviorModule relates to (or supersedes) the existing experimental work.

4. **No DataCollector integration.** There's no mention of how to collect behavioural state data over time — which state are agents in, how often do they transition, what's the distribution of module execution? This is important for any serious modelling use case.

### Overall
A solid FSM-based approach with a clear compositional advantage. The discussion post deserves mentor feedback — the design is coherent enough to warrant engagement. Worth following to see if the FSM and BDI approaches can be reconciled into a unified Behavioral Framework that offers both.
