# Requirement withdrawal by coding agents

Replication materials for **Can Coding Agents Let Go? Understanding Behavioral Residue After Requirement Withdrawal**, by Reza Rezazadeh Tehrani, Elmira Onagh, Maleknaz Nayebi and Zhen Ming (Jack) Jiang.

The experiment contains 72 programs and 432 independent revision sessions: three conditions (RR, SA, EW) and two models. The paper's main analyses use 69 programs; the Phase-I-restricted alternative uses 62. All original observations are retained.

| Folder | Contents |
|---|---|
| `programs/Task_A`, `programs/Task_B` | Unchanged Phase I and Phase II sources, plus the exact prepared `Repo_V2` used by the agents. `programs/cleanup/` contains the 13 preparation patches. |
| `model_inputs/` | Exact RR/SA/EW prompts, shared instructions and provider tool definitions. `requirements/` retains the original 48 Phase I specifications and common task-description/Phase II requirement text used to build those prompts. |
| `model_runs/Task_A`, `model_runs/Task_B` | Requests, responses, tool activity, final programs and grades for every session; settings and accounting are in `records/`. |
| `evaluation/Task_A`, `evaluation/Task_B` | Joint `O1_O2.json` answer keys, linked controls, original `T_core` (28 tests), `T_new` (five diagnostic tests) and saved baselines. |
| `analysis/` | Saved descriptive tables, planned and exact statistical results, sensitivity analyses, paper tables, figures and plotted data. |
| `workflow/` | Original preparation, editing, grading and numerical producer code. Use the portable entry point below for saved-data reproduction. |
| `metadata/` | Program/session registries, scientific policies and original-to-package path mapping. |

Task A is scheduling; Task B is resource allocation. O1 describes the behavior expected after withdrawal; O2 identifies the added restriction with supporting checks. They are not names for the two historical code phases. See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for outcome labels, table columns and sensitivity views.

## Reproduce the results

Use Python 3.12. Install the pinned numerical/plotting dependencies:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python reproduce.py --part check
python reproduce.py --part all --output outputs/run1
```

The integrity check validates files, cohort counts and all 432 grade/final-code links. The full command rebuilds descriptive, statistical, expanded-conflict and figure outputs from saved evidence. Each numerical CSV must match its saved reference byte for byte. It writes `outputs/run1/REPRODUCTION.json` and never overwrites an existing output directory. Use `--part descriptive`, `statistics`, `exact`, `conflicts` or `figures` for individual stages. PDF creation timestamps may differ; plotted data must match exactly.

These commands make no model calls and do not execute participant programs. Re-running model sessions requires separately configured provider credentials and incurs API charges. Fresh code grading additionally requires the recorded isolated macOS runtime and date policy; its source and environment are retained, but it is not part of the portable saved-data command.

The one ninth-turn continuation is next to its original session, `S0033_SA_openai_r1/extra_turn/`. Its final source is unchanged. The main analysis uses that grade once; original-eight-turn missingness is retained as a sensitivity view. Historical path strings in raw records and tables are preserved; `metadata/source_map.json` resolves them within this package.

## Provenance and reuse

Original participant sources and hidden suites come from the preceding specification study. Their recovered input commit and archive are identified in `metadata/source_provenance.json`; these are distinct from the earlier [public supporting snapshot](https://github.com/SecretActionDev/ICSE2027-How-Specification-Explicitness-Shapes-Failure-in-LLM-Generated-Code). The current paper hash and analysis policies are in `metadata/analysis_policy.json`. See [NOTICE.md](NOTICE.md) for reuse status. The package is self-contained and does not depend on pre-existing GitHub files.
