# Junhyuk Kwon — Academic Homepage

Static academic homepage for `https://tree-jhk.github.io/`, inspired by the clean information hierarchy of the al-folio theme.

## Preview

Open `index.html` directly or serve the directory with any static HTTP server.

## Languages

- English (default): `https://tree-jhk.github.io/`
- Korean: `https://tree-jhk.github.io/ko/`
- Beyond Research: `/beyond/` (English) and `/ko/beyond/` (Korean).
- The header's EN / KR links switch languages without JavaScript. School, company,
  laboratory, conference, author, and paper names stay in English in both versions.
- The CV is shared and remains in English.

Edit `index.html` for English content and `assets/i18n/ko.json` for Korean text.
The separate Beyond page uses `beyond/index.html` and `assets/i18n/beyond.ko.json`.
Elements marked with `data-i18n` are translated when generating the Korean page:

```bash
python3 scripts/build-locales.py
python3 scripts/test-locales.py
```

Commit the generated `ko/index.html` and `ko/beyond/index.html` along with the source changes. The generator
checks for missing/unused translations and preserves shared publication details,
links, dates, assets, and layout. Unmarked English content is reused verbatim.

## Paper figures

Each paper has a lazy-loaded WebP preview of Figure 1; clicking it opens the
full-resolution PNG. Images are original paper figures, not generated artwork.
Sources and image dimensions are recorded in `assets/img/papers/sources.json`.

To refresh the four public arXiv figures (requires Pillow):

```bash
python3 scripts/prepare-paper-figures.py
```

SegmentWeave Figure 1 was exported with the author's permission. Its manuscript
is not published here. To re-export from an author-provided local PDF (also
requires PyMuPDF), use `--segmentweave-pdf /path/to/manuscript.pdf` after checking
that the figure still occupies the documented page and crop region.

## Rebuild the CV

Run the following from PowerShell:

```powershell
.\scripts\build-cv.ps1
```

The editable source is `cv.html`; the generated file is `assets/pdf/CV.pdf`.

## Deployment status

Published with GitHub Pages from the `main` branch of `tree-jhk/tree-jhk.github.io`.
