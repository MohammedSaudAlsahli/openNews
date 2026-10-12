"""Isolated interpreter entry point inside the app; never import from the working directory."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eis_engine.__main__ import main
main()
