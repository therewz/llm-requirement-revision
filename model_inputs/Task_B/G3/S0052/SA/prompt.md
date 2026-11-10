Revise the existing Python implementation to satisfy the current requirements below. Treat these requirements as authoritative. Remove restrictions they do not require, preserve all specified functionality, and avoid unrelated changes. If no changes are needed, leave the implementation unchanged.

**Current requirements**

### Task description

You are asked to implement a Python function that determines whether a set of resource requests can be satisfied given limited capacity. The function takes as input a list of requests and available resources and returns whether a valid allocation exists. The goal is to determine feasibility of allocation based on the provided information. You may assume inputs are provided in a reasonable and consistent format. You may use ChatGPT to assist with reasoning about the problem, generating code, or writing tests.

### Specification

```json
{
  "id": "S0052",
  "v1_human_g3_constraints": [
    {
      "c_1": "Non-negative value constraint",
      "c_2": "Equal length constraint independent resource assumption",
      "c_3": "Type constraint No resource borrowing",
      "c_4": "One-to-one correspondence assumption deterministic behavior",
      "c_5": "Independent resource assumption resources must be finite",
      "c_6": "Static allocation assumption"
    }
  ],
  "v1_human_g3_exception": "Immediate Failure Rule. Empty input Rule. length constraint. Non-negativity constraint",
  "v1_human_g3_frs": [
    {
      "fr_1": "Accept available resources as input (dictionary)",
      "fr_10": "",
      "fr_2": "Accept required demands as input (list)",
      "fr_3": "Both input parameters are lists no mediation to inputs",
      "fr_4": "Elements are integers Aggregate total usage per resource",
      "fr_5": "Lists have same length",
      "fr_6": "Return True if satisfied",
      "fr_7": "Return False if demand exceeds",
      "fr_8": "Both lists are non-negative",
      "fr_9": "Handle empty list as valid inputs"
    }
  ],
  "v1_human_g3_goal": "The objective is to determine whether a given allocation of resources satisfies all specified constraints and demands. It evaluates inputs to ensure resources are distributed in a way that is feasible without exceeding available limits",
  "v1_human_g3_input": "Resources: Type → Dictionary, Number, ] format → list each element represents available quantity of a specific resource. Valid values → non-negative. Demands: Type → list of integers List [Dict [str, Number, ] ] format → each element is required quantity of category resource. Valid values → non-negative",
  "v1_human_g3_invariants": [
    {
      "inv_1": "Usage per resource never exceeds capacity",
      "inv_2": "All referenced required must exist in resource",
      "inv_3": "Resource totals are computed internally per resource key"
    }
  ],
  "v1_human_g3_neg_req": [
    {
      "neg_req_1": "Cannot accept negative resource or demand values",
      "neg_req_2": "Shall not return True if any demand exceeds its corresponding resource"
    }
  ],
  "v1_human_g3_output": "Return Boolean value → True or False. True if feasible → all demands are satisfied. False if any demand exceeds corresponding available resource",
  "v1_human_g3_tie_breaking": "Minimal storage Resource Usage priority → choose the one that leaves the least unused resources. Fair Distribution Priority → balances resources evenly. First Valid Priority → Accept first feasible scenario"
}
```

Briefly summarize any changes.
