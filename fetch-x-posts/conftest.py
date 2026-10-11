"""Put the skill root on sys.path so tests/ can import the flat script module."""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))
