# PPT Slide-by-Slide CPS Update Guide

**Source deck:** ResQFlow: Closed-Loop Cyber-Physical Orchestration for Disaster Resource Dispatch (16 slides + new Abstract)
**Scope:** Content-only updates for CPS implementation. **No design changes** unless noted. Slides not listed = **keep as-is**.

---

## Summary

| Action | Slides |
|--------|--------|
| **New slide** | ABSTRACT (insert — see `02-abstract-slide-cps.md`) |
| **Significant edit** | 1, 2, 5, 6, 7, 8, 9, 10, 16 |
| **Minor / optional** | 3, 4, 14 |
| **Keep unchanged** | 11, 12, 13, 15 |
| **Consider deleting** | 10 (duplicate of 9) |

---

## NEW — Insert after Slide 1

### ABSTRACT
See **`02-abstract-slide-cps.md`** for full 8-line text.

---

## Slide 1 — Title

**Change level:** Replace title text

**Main title (copy to slide):**

> **ResQFlow: Closed-Loop Cyber-Physical Orchestration for Disaster Resource Dispatch**

**Optional tagline (one line below):**

> *A final-year capstone project — transparent, constraint-safe, and auditable decision support for post-disaster resource allocation.*

*(Keep student names / IDs unchanged.)*

---

## Slide 2 — PROJECT OBJECTIVE

**Change level:** Significant

**Revised bullets (replace 5 items — keep concise):**

1. **Cyber-Physical Control** — Model dispatch as sense–decide–verify–actuate–feedback across a simulated physical plant and digital twin.

2. **Explainable Decisions** — Every actuation justified with scores, **8 physical constraint checks**, and twin-grounded evidence.

3. **Multi-Agent Council** — Medical, Logistics, Route specialists review **top-N ranked candidates** on graph context **before** verification.

4. **Closed-Loop Safety** — Verify-then-actuate with predictive CPS (fuel-at-arrival, ETA); transactional repair; optional open-loop contrast demo.

5. **Working Demo** — Physical plant map, digital twin explorer, closed/open-loop toggle, session continuity.

---

## Slide 3 — PROBLEM STATEMENT

**Change level:** Optional minor

**Add one bullet under “Core Gap” (single line):**
> Current tools lack a **closed-loop cyber-physical control layer** that feeds verification feedback back before actuation.

*(Rest unchanged.)*

---

## Slide 4 — LITERATURE REVIEW (intro)

**Change level:** Optional minor

**Add half-line to closing sentence:**
> …including **real-time cyber-physical control loops** with graph-grounded feedback.

*(Or keep unchanged if tight on space.)*

---

## Slide 5 — SYSTEM ARCHITECTURE (text overview)

**Change level:** Significant

**Revised content (replace three columns):**

**Outer: CPS control loop**  
Sensors (plant state) → Decide (auction + council) → **Verify (8 checks)** → Actuate (dispatch) → Feedback (traces + twin sync)

**Middle: Backend**  
FastAPI — digital twin build, agent council, graph evidence, optional LLM briefing/report

**Core: Frontend**  
Physical plant (simulated map) + Digital twin explorer; **client-side auction**; closed/open-loop toggle

**Footer line (one sentence):**  
Snapshot flows to API for council and twin evidence; **verification and actuation gating run in the browser control loop** before plant state updates.

---

## Slide 6 — CORE ENGINE / Allocation Methodology

**Change level:** Significant

**Deterministic Scoring** *(keep, 2 lines)*  
Weighted **S = Σ w·factor**: urgency, distance, capability, fuel, route risk. Strategy presets: balanced, urgency-first, nearest, risk-aware, saving.

**Verify-Then-Actuate** *(replace)*  
**8 checks** before actuation: availability, fuel margin, capability, route risk, double-booking, priority gate, **fuel-at-arrival**, **ETA vs urgency**. Fail → repair (next safe candidate) or **pending** (closed-loop).

**Outputs** *(replace one line)*  
Latest allocation: actuation command, physical verification, twin-grounded evidence, open vs closed-loop mode badge.

---

## Slide 7 — KNOWLEDGE GRAPH & AGENTS

**Change level:** Significant (terminology + flow order)

**Left column title:** **Digital Twin (ResQFlow)** — was “Knowledge Graph”

**Key flow line (add at bottom, replace old closing line):**  
`Rank → Council (top-N) → Verify (8 checks) → Actuate → Twin feedback`

**“Shown in the product” bullets — update labels:**
- Latest allocation — **twin-grounded evidence**, physical constraint verification
- Digital twin explorer — Focus / Reachability / Full map

**Agent Council — one line fix:**  
*Planner re-ranks after council → then **physical constraint verification** (council does not bypass safety).*

---

## Slide 8 — KEY NOVELTIES

**Change level:** Significant (add 2, tweak 2)

**Replace “Graph Evidence” bullet:**
> **Digital Twin Evidence** — k-hop paths and ripple checks ground every actuation in the twin.

**Add new bullet (replace “What-If Planning” OR “End-to-End Demo” if space tight — else add as 9th and trim elsewhere):**
> **Closed-Loop CPS Control** — Predictive feasibility + verification feedback; open-loop toggle for contrast.

**Tweak “Verify-Then-Commit” bullet:**
> **Verify-Then-Actuate** — Eight physical checks including predictive CPS; blocks unsafe actuation.

*(Keep Simulation-Grounded, Explainable Scoring, Transactional Repair, Auditable Traces, Agent Council, End-to-End Demo if space allows.)*

---

## Slide 9 — IMPLEMENTATION / Overview

**Change level:** Significant

**Technology Stack — add/update bullets:**
- Frontend: Tailwind UI, **physical plant** + **digital twin explorer**, Lucide icons
- **Control loop:** Client-side auction + **closed/open-loop toggle**
- CPS checks: fuel-at-arrival, ETA window (client-side)

**Delivered Modules — replace verify bullet:**
- **Closed-loop verify-then-actuate** — 8 physical constraint checks + transactional repair + pending when unsafe

**Phased build — append final phase:**
> …→ CPS labeling + predictive verification + open/closed-loop demo toggle

---

## Slide 10 — IMPLEMENTATION / Delivered Modules

**Change level:** Redundant

**Recommendation:** **Delete this slide** — duplicates Slide 9. If kept, merge into Slide 9 only.

---

## Slides 11–15 — Literature Review sections

| Slide | Title | Action |
|-------|--------|--------|
| 11 | Section I intro | **Keep** |
| 12 | A. Optimization Models | **Keep** |
| 13 | B. Multi-Agent Systems | **Keep** |
| 14 | C. Knowledge Graphs / GraphRAG | **Optional:** Gap line already mentions “cyber-physical control loops” — no change needed |
| 15 | D. Explainable AI | **Keep** (already mentions verification + repair cycles) |

---

## Slide 16 — SYSTEM ARCHITECTURE (diagram)

**Change level:** Significant (diagram only — not slide text)

**Slide text:** Minimal or title-only — diagram carries content.

**Action:** Regenerate diagram using **`01-architecture-diagram-prompt-cps.md`**.

**Optional caption under diagram (one line):**  
*Processing order: Auction → Council → Verify (8 checks) → Actuation → Feedback*

---

## Suggested final deck order (17 slides if abstract added)

1. **Title** — ResQFlow: Closed-Loop Cyber-Physical Orchestration for Disaster Resource Dispatch  
2. **Abstract** *(new)*  
3. Project Objective  
4. Problem Statement  
5. Literature Review intro  
6. System Architecture (text)  
7. Core Engine  
8. Knowledge Graph & Agents / Digital Twin  
9. Key Novelties  
10. Implementation Overview *(merge old 10 into this)*  
11–15. Literature A–D  
16. Architecture diagram  

---

## Slides safe to leave unchanged

- Literature deep-dives (12, 13, 15) — already support CPS/gap narrative  
- Problem statement core (slide 3) — still valid with optional one-line add  

---

## Demo talking points tied to slides (for presenter)

| Slide | Live demo beat |
|-------|----------------|
| Objective / Core Engine | Show **Closed loop** badge + **8/8 Physical verify** |
| Novelties | Show **Pending allocation** (feedback blocked actuation) |
| Implementation | Toggle **open-loop** → actuation despite failed checks |
| Architecture | Point to verify gate before OUTPUT actuation |
