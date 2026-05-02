from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=False)
    parser.add_argument("--epochs", type=int, default=1)
    args = parser.parse_args()
    Path("outputs").mkdir(exist_ok=True)
    Path("outputs/best.pt").write_text("placeholder checkpoint\n", encoding="utf-8")
    print(f"trained with config={args.config} epochs={args.epochs}")


if __name__ == "__main__":
    main()
