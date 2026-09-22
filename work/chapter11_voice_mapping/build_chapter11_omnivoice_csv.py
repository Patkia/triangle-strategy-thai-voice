from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from chapter11_13_common_builder import build

if __name__ == '__main__':
    build(11)
