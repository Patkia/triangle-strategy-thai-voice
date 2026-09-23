from pathlib import Path
import importlib.util

COMMON = Path(__file__).resolve().parents[1] / 'chapter17_20_common_builder.py'
spec = importlib.util.spec_from_file_location('chapter17_20_common_builder', COMMON)
if spec is None or spec.loader is None:
    raise RuntimeError('Could not load chapter17_20_common_builder.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.build(21)
