import os
import sys

# Make the Simulator directory importable so gui submodules can do
# "from simulator import Simulator", "from clock import ClockMode", etc.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
