"""Run rotclimate.calibrate from the project root with an isolated interpreter:
    python -I scripts/calibrate_cli.py --physics world --start ... (same arguments)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rotclimate.calibrate import main  # noqa: E402

if __name__ == "__main__":
    main()
