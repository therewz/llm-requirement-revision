Revise the existing Python implementation to satisfy the current requirements below. Treat these requirements as authoritative. Remove restrictions they do not require, preserve all specified functionality, and avoid unrelated changes. If no changes are needed, leave the implementation unchanged.

**Current requirements**

### Task description

You are asked to implement a Python function that determines whether a set of resource requests can be satisfied given limited capacity. The function takes as input a list of requests and available resources and returns whether a valid allocation exists. The goal is to determine feasibility of allocation based on the provided information. You may assume inputs are provided in a reasonable and consistent format. You may use ChatGPT to assist with reasoning about the problem, generating code, or writing tests.

### Specification

```json
{
  "v1_human_g2_ac": [
    {
      "ac_1": "Given user provides cpu:10, ram:32, and request for 4, ram:8, when is_alloc_feasible called v2_human time return true.",
      "ac_2": "given cpu:16, ram:16 and it cpu:3, cpu:10 is provided when is_alloc_feasible called v2_human time return false.",
      "ac_3": "when is_infeasible called v2_human time return false. called given cpu:10 and request cpu:4, cpu:2, when is_feasible called v2_human time return true.",
      "ac_4": "given cpu:-3, requested when func called, it returns false.",
      "ac_5": "given wrong format is used, when is_feasible called return false.",
      "ac_6": "given resource cpu:-5, when should called return false."
    }
  ],
  "v1_human_g2_constraints": [
    {
      "c_1": "Resources must be non-negative.",
      "c_2": "Resources are independent & each other",
      "c_3": "No ordering of requests.",
      "c_4": "the allocation is all or nothing.",
      "c_5": "No time dimension.",
      "c_6": "Unit of measure ment are consistent."
    }
  ],
  "v1_human_g2_goal": "To find resources are enough to give it to a request to run. the request requires CPUs and some memory to run & we need to make sure we have enough.",
  "v1_human_g2_input": "resources are a dictionary mapping each resource str to its available capacity. requests maps resource name str to amount required number int. Valid -> str, int",
  "v1_human_g2_output": "A boolean -> True or false.",
  "id": "S0027"
}
```

**Requirement withdrawal**

The following requirement has been withdrawn. Remove the restriction it introduced; it is not part of the current requirements:

At least one resource must remain unallocated after assignment. This requirement applies in addition to all previously described behavior. An allocation that satisfies all other conditions but consumes all available resources is no longer valid.

Briefly summarize any changes.
