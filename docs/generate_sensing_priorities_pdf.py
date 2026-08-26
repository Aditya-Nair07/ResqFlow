#!/usr/bin/env python3
"""Generate sensing/feedback priorities PDF (information base)."""

from pathlib import Path

from fpdf import FPDF

OUT = Path(__file__).resolve().parents[1] / "docs" / "ResQFlow-Flood-Sensing-Feedback-Priorities.pdf"


def T(s: str) -> str:
    return (
        s.replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2192", "->")
    )


class Doc(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(100, 100, 100)
        self.set_x(self.l_margin)
        self.cell(0, 8, T("ResQFlow-Flood - Sensing & Feedback Priorities"), align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.set_x(self.l_margin)
        self.cell(0, 10, T(f"Page {self.page_no()}/{{nb}} | Internal notes - not a field claim"), align="C")

    def h1(self, text):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(15, 60, 100)
        self.multi_cell(0, 9, T(text))
        self.ln(2)

    def h2(self, text):
        self.ln(2)
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(20, 80, 120)
        self.multi_cell(0, 7, T(text))
        self.ln(1)

    def h3(self, text):
        self.ln(1)
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 6, T(text))
        self.ln(0.5)

    def body(self, text):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5.5, T(text))
        self.ln(1)

    def bullet(self, text):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5.5, T(f"- {text}"))

    def priority_line(self, rank, title, do_it, why):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(20, 20, 20)
        self.multi_cell(0, 5.5, T(f"{rank}. {title}"))
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 5.5, T(f"   Do it? {do_it}"))
        self.set_x(self.l_margin)
        self.multi_cell(0, 5.5, T(f"   Why: {why}"))
        self.ln(1)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf = Doc(format="A4")
    pdf.set_margins(16, 16, 16)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.alias_nb_pages()
    pdf.add_page()

    pdf.h1("ResQFlow-Flood")
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(0, 7, T("Sensing & Continuous Feedback - Suggestions and Priorities"))
    pdf.ln(1)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(80, 80, 80)
    pdf.multi_cell(0, 5.5, T("Information storage base for the revised urban flood evacuation project."))
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 5.5, T("Purpose: decision-support demo with software-only sensing (no IoT hardware budget)."))
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 5.5, T("Status: planning notes - implement in priority order after team agreement."))
    pdf.ln(3)

    pdf.h2("1. Project framing (keep this honest)")
    pdf.body(
        "ResQFlow-Flood is closed-loop decision support for urban flood evacuation: "
        "move at-risk groups to capacity-limited shelters using buses, high-clearance vehicles, and boats. "
        "Feedback is generated in software (simulator + human report forms + optional public weather APIs). "
        "This is not a live city flood-control system and not autonomous emergency command."
    )
    pdf.body(
        "Strong mentor line: Public weather gives regional context; citizens give early street reports; "
        "operators give high-trust fast feedback. Actuation and 8-check verification stay in the closed-loop dispatcher. "
        "Hardware sensors would later plug into the same report API."
    )

    pdf.h2("2. The two bottlenecks")
    pdf.h3("Bottleneck A - Initial sensing (input)")
    pdf.body(
        "Problem: Where does the system get the disaster? Mentors need a believable Sense step before dispatch runs."
    )
    pdf.body(
        "Need: Something enters the plant - citizen report, weather context, or operator report - "
        "so the map and priorities are not only hard-coded scenario JSON."
    )
    pdf.h3("Bottleneck B - Continuous / fast feedback")
    pdf.body(
        "Problem: The loop must stay closed as the flood changes - plans invalidate mid-mission."
    )
    pdf.body(
        "Need: Frequent updates that can invalidate or repair a plan. "
        "'Instantaneous' for this project means: operator submits in 1-2 seconds -> state updates -> "
        "re-rank / repair on the next decision cycle (or immediately on high-priority reports). "
        "It does NOT require satellite GPS or Google Maps as the core mechanism."
    )

    pdf.add_page()
    pdf.h2("3. Initial sensing options")
    pdf.h3("3.1 Citizen report form (already started on flood)")
    pdf.bullet("Feasible: YES - best first move. Free, live-demoable, maps to real crowdsourced disaster apps.")
    pdf.bullet("Use for: street waterlogging started; people need help at a location.")
    pdf.bullet("Limit: noisy (duplicates, wrong location). Can later become a feature (stale/duplicate handling).")
    pdf.bullet("Verdict: Keep and polish. Primary Sense story for review.")
    pdf.bullet("Current artifact: report.html + POST /flood/report (Part A).")

    pdf.h3("3.2 Public weather / flood APIs")
    pdf.bullet("Feasible: YES for context - NOT for street-level rescue claims.")
    pdf.bullet("Examples: Open-Meteo, OpenWeather (rain/alerts); optional gov river gauges if published.")
    pdf.bullet("Good for: why flooding is likely; nudge simulator rainfall; dashboard banner.")
    pdf.bullet("Bad for: exact street depth; which underpass is closed.")
    pdf.bullet("Verdict: Second Sense channel. Do not claim weather API replaces street reports.")

    pdf.h2("4. Continuous feedback options")
    pdf.h3("4.1 Operator high-priority form (strongly recommended next)")
    pdf.bullet("Feasible: YES - demo gold.")
    pdf.bullet("Citizen = lower/medium trust; Operator/field unit = high trust, higher priority for reinforcements.")
    pdf.bullet("One-tap actions: road closed; need reinforcements; shelter full; vehicle cannot proceed; urgency 1-5.")
    pdf.bullet("Maps to real incident command: official reports outrank public tips.")
    pdf.bullet("Verdict: Highest value next build after citizen form.")

    pdf.h3("4.2 Click-on-map feedback (ops dashboard)")
    pdf.bullet("Feasible: YES. Faster than a separate form.")
    pdf.bullet("Operator clicks cell/road -> mark flooded / request unit.")
    pdf.bullet("Verdict: Nice follow-on after operator form.")

    pdf.h3("4.3 Browser GPS / phone geolocation")
    pdf.bullet("Feasible as a toy; WEAK as a core claim.")
    pdf.bullet("Problems: map is a simulated grid, not real lat/lng; classroom Wi-Fi/permissions flaky.")
    pdf.bullet("Verdict: Optional later only - not the feedback backbone.")

    pdf.h3("4.4 Google Maps integration")
    pdf.bullet("Technically possible; mostly NOT worth it for next review.")
    pdf.bullet("Costs: API keys, billing, time; still no water depth; pulls focus from CPS loop to map product.")
    pdf.bullet("Verdict: Skip unless faculty explicitly asks for GIS.")

    pdf.h3("4.5 Photos of flooding")
    pdf.bullet("Feasible as evidence attachment + manual severity by operator.")
    pdf.bullet("NOT feasible (without money/time): reliable CV that measures depth from a phone photo.")
    pdf.bullet("Honest framing: photo supports an operator report; severity is selected by the human.")
    pdf.bullet("Verdict: Optional later. Do not make vision the feedback path for the next review.")

    pdf.add_page()
    pdf.h2("5. Priority ladder (do in this order)")
    pdf.priority_line("P0 (now)", "Citizen form on flood demo", "YES - already started", "Solves initial Sense; live mentor demo.")
    pdf.priority_line("P1 (next)", "Operator high-priority form + trust / priority weighting", "YES - build next", "Solves fast continuous feedback; high-trust reinforcements outrank citizen noise.")
    pdf.priority_line("P2 (if one evening free)", "Public weather API banner / rainfall nudge", "YES - low cost", "Shows public-data sensing without claiming street accuracy.")
    pdf.priority_line("P3 (follow-on)", "Click-map operator actions + report log (citizen vs operator)", "Nice to have", "Makes feedback feel more instantaneous on the ops UI.")
    pdf.priority_line("P4 (immediate replan)", "High-priority operator report triggers replan without waiting many ticks", "Do after P1", "Strengthens closed-loop story.")
    pdf.priority_line("Defer / skip for next review", "Google Maps, GPS-as-core, photo -> automatic depth AI, real IoT sensors", "NO for now", "Cost, scope creep, and honesty risk with mentors.")

    pdf.h2("6. Feasibility summary")
    pdf.body("Citizen form - Feasible now - Primary initial Sense.")
    pdf.body("Operator priority form - Feasible next - Primary fast feedback.")
    pdf.body("Weather API (context only) - Feasible soon - Secondary Sense.")
    pdf.body("Map click feedback - Feasible after P1 - UX speed.")
    pdf.body("Browser GPS - Weak core - Optional toy later.")
    pdf.body("Google Maps - Skip now - Time/billing/focus cost.")
    pdf.body("Photo AI depth - Not for review - Optional evidence attachment only.")
    pdf.body("Real IoT sensors - Out of budget - Same API later if funded.")

    pdf.h2("7. What to avoid claiming in review")
    pdf.bullet("Public weather equals street-level rescue sensing.")
    pdf.bullet("Photos measure water depth without a real validated model.")
    pdf.bullet("Building Google Maps before the operator priority lane.")
    pdf.bullet("Mixing simulated grid plant with real city streets without saying which is which.")
    pdf.bullet("Implying autonomous emergency command or live municipal deployment.")

    pdf.h2("8. Suggested mentor narrative (30 seconds)")
    pdf.body(
        "We have three Sense channels: public weather for regional context, "
        "citizens for early street reports, and operators for high-trust fast feedback. "
        "The dispatcher still prioritizes with Flood-GAPD, ranks vehicle-route-shelter options, "
        "verifies eight flood checks, then actuates. If roads close or shelters fill, "
        "feedback invalidates the plan and we repair or fail safely. "
        "Hardware sensors are out of budget; they would use the same report API later."
    )

    pdf.h2("9. Relation to general demo vs flood demo")
    pdf.body(
        "Same CPS pattern, different nouns. Citizen/operator/weather Sense can feed flood "
        "(waterlogging, groups, shelters) or the general demo (incidents/resources). "
        "Prefer prototyping Sense+feedback on the flood specialization first; "
        "general demo index.html remains on GitHub (origin/main) as a safe rollback."
    )
    pdf.body(
        "GitHub fallback: https://github.com/abhinav429/ResQFlow - restore general demo with: "
        "git checkout origin/main -- index.html"
    )

    pdf.h2("10. Document control")
    pdf.body("Created as an internal information base for the revised ResQFlow-Flood project.")
    pdf.body("Complements ARCHITECTURE-FLOOD.md and the implementation plan with Sense/Feedback priorities.")
    pdf.body("Next build recommendation when the team is ready: P1 Operator high-priority form.")

    pdf.output(str(OUT))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
