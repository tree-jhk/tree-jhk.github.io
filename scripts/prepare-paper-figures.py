"""Download published Figure 1 assets and prepare lightweight, faithful previews.

The optional author-provided SegmentWeave PDF is used only to render Figure 1.
The manuscript itself is never copied into the public website.
Requires Pillow; the optional PDF export also requires PyMuPDF.
"""

import argparse
import json
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets/img/papers"
SOURCES = {
    "procompnav": "https://arxiv.org/html/2605.06223v4/figures/Teaserfigure.png",
    "viro": "https://arxiv.org/html/2601.12781v2/VIRO_main.png",
    "reckg": "https://arxiv.org/html/2501.03598v2/RecKG.png",
    "mmtb": "https://arxiv.org/html/2605.10966v1/mmtb-figure1-v6.png",
}


def preview(name, original, source):
    with Image.open(BytesIO(original)) as image:
        full_size = image.size
        image = image.convert("RGB")
        image.thumbnail((800, 800), Image.Resampling.LANCZOS)
        image.save(OUTPUT / f"{name}-figure1.webp", quality=92, method=6)
        return {
            "figure": 1,
            "source": source,
            "full_size": list(full_size),
            "preview_size": list(image.size),
            "original": f"{name}-figure1.png",
            "preview": f"{name}-figure1.webp",
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--segmentweave-pdf", type=Path)
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUTPUT / "sources.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    for name, source in SOURCES.items():
        request = Request(source, headers={"User-Agent": "Academic-homepage-figure-import/1.0"})
        with urlopen(request, timeout=30) as response:
            original = response.read()
        # Keep the full-resolution original available only when the visitor opens it.
        (OUTPUT / f"{name}-figure1.png").write_bytes(original)
        manifest[name] = preview(name, original, source)
        print(name, manifest[name]["full_size"], "preview", manifest[name]["preview_size"])

    if args.segmentweave_pdf:
        import pymupdf

        with pymupdf.open(args.segmentweave_pdf) as document:
            page = document[1]
            if "Figure 1: Illustration of our goal" not in page.get_text():
                raise ValueError("SegmentWeave PDF layout has changed; inspect Figure 1 before exporting")
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(3, 3), clip=pymupdf.Rect(106, 70, 507, 341), alpha=False)
            original = pixmap.tobytes("png")
        (OUTPUT / "segmentweave-figure1.png").write_bytes(original)
        manifest["segmentweave"] = preview("segmentweave", original, "Author-provided Figure 1, shared with permission")
        print("segmentweave", manifest["segmentweave"]["full_size"], "preview", manifest["segmentweave"]["preview_size"])
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
