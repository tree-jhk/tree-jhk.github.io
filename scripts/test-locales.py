"""Check bilingual content and generated output without third-party packages."""

import importlib.util
import json
import re
import unittest
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_locales", ROOT / "scripts/build-locales.py")
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class Document(HTMLParser):
    def __init__(self, source, base):
        super().__init__()
        self.base = base
        self.links = []
        self.assets = []
        self.images = []
        self.ids = []
        self.current_language = []
        self.lang = None
        self.canonical = None
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html":
            self.lang = attrs["lang"]
        if attrs.get("id"):
            self.ids.append(attrs["id"])
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonical = attrs["href"]
        if tag == "a":
            self.links.append(urljoin(self.base, attrs["href"]))
            if "language-option" in attrs.get("class", "") and attrs.get("aria-current") == "page":
                self.current_language.append(attrs["lang"])
        if tag in {"img", "script"} and attrs.get("src"):
            self.assets.append(urljoin(self.base, attrs["src"]))
        if tag == "img":
            self.images.append(attrs)
        if tag == "link" and attrs.get("rel") in {"stylesheet", "icon"}:
            self.assets.append(urljoin(self.base, attrs["href"]))


class LocaleTests(unittest.TestCase):
    def setUp(self):
        self.en = (ROOT / "index.html").read_text(encoding="utf-8")
        self.ko = (ROOT / "ko/index.html").read_text(encoding="utf-8")
        self.translations = json.loads((ROOT / "assets/i18n/ko.json").read_text(encoding="utf-8"))
        self.en_doc = Document(self.en, BUILDER.SITE)
        self.ko_doc = Document(self.ko, BUILDER.SITE + "ko/")

    def test_translation_coverage(self):
        localizer = BUILDER.Localizer(self.en, self.translations)
        localizer.render()
        self.assertGreater(sum(localizer.seen.values()), 30)

    def test_generation_is_reproducible(self):
        BUILDER.build()
        self.assertEqual(self.ko, (ROOT / "ko/index.html").read_text(encoding="utf-8"))

    def test_language_and_canonical(self):
        for document, language, path in [(self.en_doc, "en", ""), (self.ko_doc, "ko", "ko/")]:
            self.assertEqual(document.lang, language)
            self.assertEqual(document.current_language, [language])
            self.assertEqual(document.canonical, BUILDER.SITE + path)

    def test_links_are_preserved(self):
        # The ordering of POSTECH and its graduate school changes naturally in Korean.
        en = Counter(link for link in self.en_doc.links if "#" not in link)
        ko = Counter(link for link in self.ko_doc.links if "#" not in link)
        self.assertEqual(en, ko)

    def test_assets_are_shared(self):
        self.assertEqual(self.en_doc.assets, self.ko_doc.assets)
        for asset in self.ko_doc.assets:
            if asset.startswith(BUILDER.SITE):
                self.assertTrue((ROOT / asset.removeprefix(BUILDER.SITE)).is_file(), asset)

    def test_anchor_ids_are_preserved_and_unique(self):
        self.assertEqual(self.en_doc.ids, self.ko_doc.ids)
        self.assertEqual(len(self.ko_doc.ids), len(set(self.ko_doc.ids)))

    def test_all_five_papers_have_original_figures_and_previews(self):
        manifest = json.loads((ROOT / "assets/img/papers/sources.json").read_text(encoding="utf-8"))
        self.assertEqual(set(manifest), {"procompnav", "viro", "reckg", "mmtb", "segmentweave"})
        for document in [self.en_doc, self.ko_doc]:
            images = [image for image in document.images if "/papers/" in image["src"]]
            self.assertEqual(len(images), 5)
            for image in images:
                name = Path(image["src"]).name.split("-figure1")[0]
                self.assertEqual([int(image["width"]), int(image["height"])], manifest[name]["preview_size"])
                self.assertEqual(image["loading"], "lazy")
                self.assertTrue(image["alt"].strip())
                self.assertLessEqual(max(manifest[name]["preview_size"]), 800)
                original = ROOT / "assets/img/papers" / manifest[name]["original"]
                self.assertTrue(original.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
                self.assertIn(BUILDER.SITE + "assets/img/papers/" + original.name, document.links)

    def test_bio_expresses_personal_choice(self):
        self.assertIn("AI that people can actually use and interact with", self.en)
        self.assertIn("chose to move into Applied AI", self.en)
        self.assertIn("사람들의 손길이 직접 닿는 AI", self.ko)
        self.assertIn("확신", self.translations["bio.journey"])

    def test_paper_titles_authors_and_venues_stay_in_english(self):
        for css_class in ["paper-title", "authors", "venue"]:
            pattern = rf'<div class="{css_class}"[^>]*>(.*?)</div>'
            en = re.findall(pattern, self.en, re.DOTALL)
            ko = re.findall(pattern, self.ko, re.DOTALL)
            self.assertEqual(len(en), len(ko))
            for original, translated in zip(en, ko):
                if "second author" not in original and "Under review" not in original:
                    self.assertEqual(original, translated)
        self.assertNotRegex(self.ko, r"Submitted to|ICLR 2027|ISM 2027")

    def test_missing_translation_fails(self):
        with self.assertRaisesRegex(ValueError, "Missing Korean translation"):
            BUILDER.Localizer('<p data-i18n="missing">English</p>', {}).render()

    def test_unused_translation_fails(self):
        with self.assertRaisesRegex(ValueError, "Unused Korean translations"):
            BUILDER.Localizer("<p>English</p>", {"unused": "한국어"}).render()


if __name__ == "__main__":
    unittest.main()
