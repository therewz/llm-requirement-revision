# Data dictionary

`metadata/programs.csv` maps each pseudonymous program ID to its task, original specification group (G1–G3), Phase I source, original Phase II source and prepared `Repo_V2`. `prepared_changed` identifies the 13 adapted starts; `change` states the adjustment. Hashes identify the exact original and prepared source bytes. `metadata/sessions.csv` locates all 432 sessions and selects each main-analysis grade.

## Conditions and oracles

- **RR:** Requirement Retained; the added Phase II restriction remains active.
- **SA:** Specification Alignment; original requirements with the common instruction to remove unsupported restrictions, without an explicit withdrawal notice.
- **EW:** Explicit Withdrawal; the same context with the withdrawn requirement identified.
- **O1:** Expected behavior after withdrawal. In Task A keys, `expected.withdrawn`; in Task B, `withdrawn_expectation`.
- **O2:** Restriction-present criterion (`expected.retained` or `retained_expectation`), supported by linked control observations.

`evaluation/oracle_index.csv` locates every target/control record. Scheduling includes seven canonical targets; allocation includes four. Native-weekday and additional diagnostic profiles are preserved. Historical case IDs `B-O1` and `B-O2` name overload controls; they are not the paper's oracle symbols O1/O2.

## Outcomes and rates

Saved labels are `RESTORED`, `RETAINED`, `PARTIAL`, `OTHER_FAILURE` and `INDETERMINATE`. In SA/EW, retained/partial indicate full/partial residue. In RR, they indicate retention of an active requirement. Other failures cover invalid results or errors; indeterminate means the controls do not support attribution. Missing grades are separate.

`target_n` is the number of eligible targets; category counts divide by it. Core transitions are PP (pass–pass), PF (pass–nonpass), FP (nonpass–pass) and FF (nonpass–nonpass). `core_opportunities` is PP+PF; `core_loss_rate` is PF/(PP+PF), undefined when no baseline test passed. Transition fractions divide by all 28 core tests. Task/model summaries average program-level rates equally. Counts of tests are not independent sample sizes. Raw statuses distinguish failures, execution errors and skips.

## Analysis views and statistics

`primary69__main` is the paper's common 69-program population. `alternative62__main` additionally requires the original Phase I target-behavior predicate. Other views identify original-limit missingness, specification conflicts, prepared sources, duplicate-date target coverage, stricter attribution controls, Phase I format and their intersections. `all72_preservation` views retain all candidates for core preservation. The six `expanded_` views separately add the S0069 specification conflict to the original registry. View-level membership and selected case IDs are explicit in the descriptive tables.

Statistical reporting tables retain `planned_raw_p`/`planned_holm_p` (original exact/Monte Carlo calibration) and `exact_raw_p`/`exact_holm_p` (uniform exact recalculation). Blank p-values mean unavailable or uninformative, never zero. Mean-effect intervals are nominal 95% bootstrap intervals; Holm-adjusted tests and these intervals answer different uncertainty questions. Differences are right minus left; `_pp` means percentage points. Group comparisons are exploratory. Analysis policies were refined after preliminary results; this is not a preregistered analysis.
