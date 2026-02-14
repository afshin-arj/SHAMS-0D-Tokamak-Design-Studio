# Global Run Lock + Status Strip

SHAMS enforces a global **Running Sequence** lock: when any solver action begins (Evaluate / Solve / Run / Build / Compute / Scan / Pareto / Search / Atlas), all other solver actions are disabled until completion.

## Expert notifications
- Start: **Coils Charging** toast
- Completion: **Sequence Complete** toast (suppressed in Silence Mode)

## Top-of-page status strip
A professional status strip appears at the top during runs and shows a small tail of the **Black-Box Chronicle**.
