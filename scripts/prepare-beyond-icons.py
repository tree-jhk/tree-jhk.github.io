"""Export generated transparent icons at a consistent UI size (requires Pillow).

Pass each input as --source NAME=/path/to/generated.png. Original PNGs are kept
unchanged; WebP exports only resize and add transparent padding, preserving alpha.
"""

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets/img/beyond"
NAMES = {"everyday-ai", "investing", "asking-questions", "military-service", "running"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="append", required=True, metavar="NAME=PNG_PATH")
    args = parser.parse_args()
    sources = dict(item.split("=", 1) for item in args.source)
    if set(sources) != NAMES:
        raise ValueError(f"Exactly these five icons are required: {sorted(NAMES)}")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    metadata = {}
    for name, filename in sources.items():
        source = Path(filename)
        with Image.open(source) as original:
            image = original.convert("RGBA")
        if image.getchannel("A").getextrema() != (0, 255):
            raise ValueError(f"{name} needs genuine transparent and opaque pixels")
        destination = OUTPUT / f"{name}.png"
        if destination.exists() and destination.read_bytes() != source.read_bytes():
            raise FileExistsError(f"Do not replace an existing original without selecting a new version: {destination}")
        if not destination.exists():
            shutil.copy2(source, destination)
        source_size = image.size
        image.thumbnail((96, 96), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        position = ((128 - image.width) // 2, (128 - image.height) // 2)
        canvas.alpha_composite(image, position)
        target = OUTPUT / f"{name}.webp"
        canvas.save(target, "WEBP", lossless=True, method=6)
        with Image.open(target) as exported:
            alpha = exported.convert("RGBA").getchannel("A")
            left, top, right, bottom = alpha.getbbox()
            margin = min(left, top, 128 - right, 128 - bottom)
            if margin < 13:
                raise ValueError(f"{name} must keep at least 10% clear margin")
            metadata[name] = {"source": destination.name, "display": target.name, "source_size": list(source_size), "display_size": [128, 128], "alpha_extrema": list(alpha.getextrema()), "clear_margin_px": margin}
        print(name, "transparent WebP", target.stat().st_size, "bytes; clear margin", margin)
    (OUTPUT / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
