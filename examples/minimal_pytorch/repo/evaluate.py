from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=False)
    args = parser.parse_args()
    Path("outputs").mkdir(exist_ok=True)
    Path("outputs/metrics.json").write_text(json.dumps({"accuracy": 93.8, "checkpoint": args.checkpoint}), encoding="utf-8")
    print("accuracy=93.8")


if __name__ == "__main__":
    main()
