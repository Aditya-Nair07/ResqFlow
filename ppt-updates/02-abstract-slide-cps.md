# Abstract Slide — New Content (8 Lines, CPS-Updated)

**Official project title:** **ResQFlow: Closed-Loop Cyber-Physical Orchestration for Disaster Resource Dispatch**

**Slide title:** `ABSTRACT`  
**Format:** Exactly **8 lines** per examiner guidance.  
**Placement:** After title slide (Slide 2) or before Problem Statement — confirm with guide.

---

## Slide layout suggestion

- Title: **ABSTRACT**
- Body: 8 bullet lines (one sentence each, no sub-bullets)
- Optional footer: *Keywords: cyber-physical systems, digital twin, closed-loop control, multi-agent orchestration, disaster response*

---

## Abstract text (copy to slide)

1. **ResQFlow: Closed-Loop Cyber-Physical Orchestration for Disaster Resource Dispatch** is a browser–backend system that coordinates simulated field assets through a **physical plant** (operations map) and a NetworkX **digital twin**.

2. The methodology follows **sense–decide–verify–actuate–feedback**: sensed map state is serialized to a snapshot, resources are ranked, an **agent council** advises on twin-grounded context, and **physical constraint verification** gates every dispatch.

3. A **client-side auction engine** ranks candidates using a weighted multi-factor score **S = Σ w·factor** over urgency, distance, capability, fuel margin, and route risk under user-selected strategies.

4. A **graph-grounded agent council** (Medical, Logistics, Route) applies capped score deltas from k-hop subgraph evidence; a **verify-then-actuate controller** runs eight checks—including predictive **fuel-at-arrival** and **ETA-vs-urgency** feasibility—before issuing an actuation command.

5. **Results:** The live demo achieves transparent allocation with auditable traces (trace ID, scores, verification outcomes, rejected alternatives) and twin-grounded evidence paths with ripple analysis on every decision cycle.

6. **Results:** Closed-loop mode blocks unsafe actuation when checks fail (pending allocation / transactional repair); an open-loop demo toggle contrasts score-only dispatch without verification feedback, validating CPS safety interlocks.

7. The system integrates FastAPI, NetworkX, optional LLM narrative (briefing/report/council), and session-continuous operations map plus digital twin explorer—without replacing deterministic safety checks.

8. **Conclusion:** The framework demonstrates that disaster dispatch can be modeled as **feedback-based cyber-physical control**—where digital intelligence proposes actions but actuators fire only when twin-grounded verification confirms physical feasibility.

---

## Speaker note (optional, not on slide)

Ma'am's mapping: Line 1 = title; Line 2 = methodology; Lines 3–4 = algorithm; Lines 5–6 = results; Lines 7–8 = integration + conclusion (fits 8-line cap).

If she wants **strictly** lines 7–8 also as results, merge lines 5–6 into one line and split integration/conclusion across 7–8 — current version balances CPS framing with her rubric.

---

## Title slide (Slide 1)

**Main title (use on deck):**

> **ResQFlow: Closed-Loop Cyber-Physical Orchestration for Disaster Resource Dispatch**

**Optional tagline (one line under title):**

> *Transparent, constraint-safe, and auditable decision support for post-disaster resource allocation.*

*(Keep student names / IDs unchanged.)*
