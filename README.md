# Junhyuk Kwon — Academic Homepage

Static academic homepage for `https://tree-jhk.github.io/`, inspired by the clean information hierarchy of the al-folio theme.

## Preview

Open `index.html` directly or serve the directory with any static HTTP server.

## Languages

- English (default): `https://tree-jhk.github.io/`
- Korean: `https://tree-jhk.github.io/ko/`
- The header's EN / KR links switch languages without JavaScript. School, company,
  laboratory, conference, author, and paper names stay in English in both versions.
- The CV is shared and remains in English.

Edit `index.html` for English content and `assets/i18n/ko.json` for Korean text.
Elements marked with `data-i18n` are translated when generating the Korean page:

```bash
python3 scripts/build-locales.py
python3 scripts/test-locales.py
```

Commit the generated `ko/index.html` along with the source changes. The generator
checks for missing/unused translations and preserves shared publication details,
links, dates, assets, and layout. Unmarked English content is reused verbatim.

## Rebuild the CV

Run the following from PowerShell:

```powershell
.\scripts\build-cv.ps1
```

The editable source is `cv.html`; the generated file is `assets/pdf/CV.pdf`.

## Deployment status

Published with GitHub Pages from the `main` branch of `tree-jhk/tree-jhk.github.io`.
