import argparse
import json
from pathlib import Path

from models.inputs import PointInputs
from frontier.nudges import directional_nudges

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--point", required=True, help="Path to PointInputs JSON dict")
    ap.add_argument("--out", default="", help="Optional path to write suggestions JSON")
    args = ap.parse_args()

    d = json.loads(Path(args.point).read_text(encoding="utf-8"))
    p = PointInputs(**d)
    sug = directional_nudges(p)

    if args.out:
        Path(args.out).write_text(json.dumps(sug, indent=2), encoding="utf-8")
    else:
        print(json.dumps(sug, indent=2))

if __name__ == "__main__":
    main()
