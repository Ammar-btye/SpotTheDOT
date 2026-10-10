# SPOT dataset: insights we found (our evidence base)

_Computed 2026-10-09 with pandas over `SPOTDATA/…/02_DATA/`. The data is synthetic: 27 missions, 270 actions, 220 readings, 40 anomalies, 15 waypoints, 20 assets, 500 replay events (23 missions, no readings or anomalies in the stream)._
These are the "surface relationships that would otherwise require manual investigation" the brief asks for. Each is a candidate dashboard panel and a pitch line. Recompute in Databricks (notebook 02) so the numbers come from the pipeline, not this file.

## Headline insights (ranked by pitch value)
1. **"Green but broken": mission status hides failures.** 26 of 27 missions say COMPLETED, yet **21 of those 26 contain FAILED actions**, and **14 of the 15 HIGH/CRITICAL anomalies occurred inside COMPLETED missions.** This mirrors Orbit's wall of green dots. → Hero metric: *True Mission Health* vs reported status.
2. **There's a battery cliff.** Action success is **33% at ≤25% battery** vs 80–90% above it (24 V1 actions in that band). The only FAILED mission (M017) ended at 16%. → An actionable rule: recommend return-to-dock below ~30%.
3. **About 60% of V2's "improvement" is battery management, not configuration.** Headline: V1 77.2% → V2 91.1% action success (+13.9 pts). **At matched battery (>40%): 85.8% → 91.1% (+5.3 pts).** V2 starts higher (89.9% vs 75.9%), drains about half as fast per action (2.8 vs 5.6 %/action), and never enters the ≤25% band. V2 does genuinely improve gauge (64→92%) and thermal (77→100%) reliability. *Small sample; say so.*
4. **Location and environment drive failures.** Worst waypoints: WP09 Turbine Hall South (64%, HIGH_NOISE), WP02 Electrical Room (69%, DUSTY), WP15 Inspection Dock (69%, LOW_LIGHT). **All 6 LOCALIZATION_FAILUREs happen in HIGH_NOISE areas.** Navigation fails 50% at WP02, WP03 and WP12, and 28% at WP05 (matches NextEra's own `wp05_navigation_failure_pct`).
5. **Acoustic is the least reliable inspection** (70% success), then gauge (74%). Visual is the most reliable (91%).
6. **Severity ≠ priority.** Anomaly severity and asset criticality disagree often (e.g., HIGH anomalies on LOW-criticality assets, MEDIUM ones on HIGH assets). → Priority = severity × asset criticality. Repeat offenders: PANEL-212 (5 anomalies, HIGH criticality), HX-204 and HX-208 (4 each).
7. **"Questionable" readings = failed actions.** All 42 QUESTIONABLE readings come from FAILED actions, and all 178 GOOD readings from successful ones. Don't trust a value from a failed action, even if one was recorded.

## Things that are deterministic (don't overclaim)
- `operator_review_required` is exactly `severity ∈ {HIGH, CRITICAL}`, so it's not an independent label to evaluate a model against.
- `operator_mode` is always AUTOWALK; `scenario` and `configuration_version` are perfectly paired (BASELINE=V1, IMPROVED=V2).
- Locations' `x_coord`/`y_coord` don't match the floor-plan PNG pixel positions; we calibrate pins to the image separately.

## Assumptions we introduce (state these to judges)
- Sample inspection images (gauge, thermal, valve, acoustic, pipe, motor) are attached to actions *by action type* for the demo. The dataset doesn't link images to actions.
- Replay events are enriched with readings and anomalies by `action_id` at replay time, since the stream lacks them.
