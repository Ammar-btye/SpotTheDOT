import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # spot_mcp, client_example
sys.path.insert(0, str(HERE))         # fakes
