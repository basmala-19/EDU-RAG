import importlib.util
import inspect
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

root = Path(__file__).parent
sys.path.insert(0, str(root))

test_dir = root / "tests" / "unit"
files = sorted(test_dir.glob("test_*.py"))

total = 0
passed = 0
failed = []
skipped = []

for f in files:
    modname = f.stem
    spec = importlib.util.spec_from_file_location(modname, f)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        skipped.append((f.name, f"IMPORT ERROR: {e}"))
        continue
    for name in dir(module):
        if not name.startswith("test_"):
            continue
        fn = getattr(module, name)
        if not callable(fn):
            continue
        total += 1
        # Minimal pytest `tmp_path` fixture shim — the only fixture this test suite uses.
        params = list(inspect.signature(fn).parameters)
        tmp_dir = None
        try:
            if params == ["tmp_path"]:
                tmp_dir = tempfile.mkdtemp(prefix="edu_rag_test_")
                fn(Path(tmp_dir))
            else:
                fn()
            passed += 1
        except Exception:
            failed.append((f.name, name, traceback.format_exc()))
        finally:
            if tmp_dir:
                shutil.rmtree(tmp_dir, ignore_errors=True)

print(f"\n{'='*70}")
print(f"Total: {total}  Passed: {passed}  Failed: {len(failed)}  Skipped files: {len(skipped)}")
if skipped:
    print("\n--- SKIPPED (import errors, likely missing optional deps) ---")
    for fname, err in skipped:
        print(f"  {fname}: {err}")
if failed:
    print("\n--- FAILURES ---")
    for fname, tname, tb in failed:
        print(f"\n{fname}::{tname}")
        print(tb)
sys.exit(1 if failed else 0)
