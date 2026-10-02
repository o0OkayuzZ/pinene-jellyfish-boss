import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
VERSION = ".".join(str(n) for n in json.loads((ROOT / "behavior_pack/manifest.json").read_text(encoding="utf-8"))["header"]["version"])
OUTPUT = DIST / f"pinene-jellyfish-boss-v{VERSION}.mcaddon"

def zip_tree(source, target):
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source).as_posix())

subprocess.run([sys.executable, str(ROOT / "scripts/validate_pack.py")], check=True)
DIST.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as temp:
    temp_root = Path(temp)
    bp_mcpack = temp_root / "Pinene_Jellyfish_Boss_BP.mcpack"
    rp_mcpack = temp_root / "Pinene_Jellyfish_Boss_RP.mcpack"
    zip_tree(ROOT / "behavior_pack", bp_mcpack)
    zip_tree(ROOT / "resource_pack", rp_mcpack)
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as addon:
        addon.write(bp_mcpack, bp_mcpack.name)
        addon.write(rp_mcpack, rp_mcpack.name)

print(f"BUILT {OUTPUT} ({OUTPUT.stat().st_size} bytes)")