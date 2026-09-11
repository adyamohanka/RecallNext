# Safety and limitations

RecallNext supports an internal recall investigation. It does not certify food safety, determine legal compliance, issue public alerts or release inventory.

The committed model covers intact cases, one product, one location and a closed synthetic inventory window. It does not support transformations, biological cross-contamination, returns, losses, opening inventory, arbitrary unit conversion or warehouse-scale optimization. Unsupported inputs must be marked unresolved.

Current limits:

- The web runtime reads the synthetic fixture. Live Exasol schema validation and the API repository adapter remain pending.
- Evidence examples are synthetic structured facts. No live document model is connected.
- The enumerator is intended for small components and is capped at 250,000 combinations and 10,000 feasible scenarios.
- Retrieval times are fixture assumptions, not measured operational times.
- One-step action ranking does not claim a globally optimal investigation policy.
- A retained-case scan establishes only that case unless independent evidence establishes a broader homogeneous group.
- In-memory evidence versions reset when the API process restarts.

Unknown coverage, invalid scenarios, computation limits, contradictory evidence and missing results preserve or broaden uncertainty. They never imply exclusion.
