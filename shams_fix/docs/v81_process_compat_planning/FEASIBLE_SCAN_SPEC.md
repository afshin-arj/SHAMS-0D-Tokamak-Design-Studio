# Feasible Scan Specification

A Feasible Scan is a parametric sweep evaluated strictly under
frozen SHAMS constraints.

Each scan point records:
- Feasibility flag
- Active constraint set
- Signed constraint margins
- Failure mode (if infeasible)

Infeasible points are retained as diagnostic data.
