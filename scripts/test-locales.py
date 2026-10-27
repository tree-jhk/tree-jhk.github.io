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
        self.nav_routes = []
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
            if attrs.get("data-nav"):
                self.nav_routes.append((attrs["data-nav"], urljoin(self.base, attrs["href"])))
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
        # Internal navigation is localized; publications and shared assets are not.
        en = Counter(link.replace(BUILDER.SITE + "ko/", BUILDER.SITE) for link in self.en_doc.links if "#" not in link)
        ko = Counter(link.replace(BUILDER.SITE + "ko/", BUILDER.SITE) for link in self.ko_doc.links if "#" not in link)
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

    def test_school_details_stay_in_education_not_bio(self):
        for source in [self.en, self.ko]:
            bio = re.search(r'<div class="bio">(.*?)</div>', source, re.DOTALL).group(1)
            self.assertNotRegex(bio, r"POSTECH|Inha|Graduate School|M\.S\.")
            education = re.search(r'<section id="education".*?</section>', source, re.DOTALL).group(0)
            self.assertIn("POSTECH", education)
            self.assertIn("Inha University", education)
        self.assertIn("real user behavior", self.en)

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


class BeyondTests(unittest.TestCase):
    def setUp(self):
        self.en = (ROOT / "beyond/index.html").read_text(encoding="utf-8")
        self.ko = (ROOT / "ko/beyond/index.html").read_text(encoding="utf-8")
        self.translations = json.loads((ROOT / "assets/i18n/beyond.ko.json").read_text(encoding="utf-8"))
        self.en_doc = Document(self.en, BUILDER.SITE + "beyond/")
        self.ko_doc = Document(self.ko, BUILDER.SITE + "ko/beyond/")

    def test_translation_coverage_and_reproducibility(self):
        BUILDER.Localizer(self.en, self.translations).render()
        BUILDER.build()
        self.assertEqual(self.ko, (ROOT / "ko/beyond/index.html").read_text(encoding="utf-8"))

    def test_language_and_page_local_switch_links(self):
        for document, language, path in [(self.en_doc, "en", "beyond/"), (self.ko_doc, "ko", "ko/beyond/")]:
            self.assertEqual(document.lang, language)
            self.assertEqual(document.current_language, [language])
            self.assertEqual(document.canonical, BUILDER.SITE + path)
            self.assertIn(BUILDER.SITE + "beyond/", document.links)
            self.assertIn(BUILDER.SITE + "ko/beyond/", document.links)

    def test_navigation_and_assets_remain_in_correct_locale(self):
        for document, prefix in [(self.en_doc, ""), (self.ko_doc, "ko/")]:
            for name, link in document.nav_routes:
                self.assertEqual(link, BUILDER.SITE + prefix + ("beyond/" if name == "beyond" else ""))
            for asset in document.assets:
                if asset.startswith(BUILDER.SITE):
                    self.assertTrue((ROOT / asset.removeprefix(BUILDER.SITE)).is_file(), asset)
            self.assertIn(BUILDER.SITE + "assets/pdf/CV.pdf", document.links)

    def test_four_concise_items(self):
        entries = [re.sub(r'<[^>]+>', '', text) for text in re.findall(r'<dd[^>]*>(.*?)</dd>', self.en, re.DOTALL)]
        self.assertEqual(len(entries), 4)
        self.assertLess(sum(len(text.split()) for text in entries), 110)
        self.assertTrue(all(len(text.split()) < 40 for text in entries))
        self.assertNotIn('data-i18n="questions.', self.en)
        self.assertNotIn('data-i18n="questions.', self.ko)
        self.assertNotIn("questions.title", self.translations)
        for name in ["USD", "QLD", "KATUSA", "United States Army"]:
            self.assertIn(name, self.en)
            self.assertIn(name, self.ko)

    def test_everyday_ai_and_katusa_official_link(self):
        link = "https://8tharmy.korea.army.mil/site/about/katusa-soldier-program.asp"
        for source, document in [(self.en, self.en_doc), (self.ko, self.ko_doc)]:
            self.assertIn("Korean Augmentation to the United States Army", source)
            self.assertIn(link, document.links)
        for text in ["waking up", "just before bed", "planning my day", "untangling thoughts", "practicing English", "set the direction", "delegate the legwork"]:
            self.assertIn(text, self.en)
        self.assertIn("큰 방향", self.translations["everyday.text"])
        self.assertIn("매 거래일", self.translations["investing.text"])

    def test_four_shared_decorative_icons(self):
        names = ["everyday-ai", "investing", "military-service", "running"]
        for document in [self.en_doc, self.ko_doc]:
            icons = [image for image in document.images if image.get("class") == "beyond-icon"]
            self.assertEqual(len(icons), 4)
            self.assertEqual([Path(image["src"]).stem for image in icons], names)
            for image in icons:
                self.assertEqual(image["alt"], "")
                self.assertEqual(image["aria-hidden"], "true")
                self.assertEqual(image["width"], "44")
                self.assertEqual(image["height"], "44")
                self.assertEqual(image["loading"], "lazy")
        self.assertEqual(self.en_doc.assets, self.ko_doc.assets)

    def test_military_heading_and_professional_experience(self):
        self.assertIn("Serving with the U.S. Army", self.en)
        self.assertIn("미군과 함께한 군 복무", self.ko)
        military = re.search(r'<dd data-i18n="military.text">(.*?)</dd>', self.en, re.DOTALL).group(1)
        self.assertIn("American workplace culture", military)
        self.assertIn("cross-cultural collaboration", military)
        self.assertIn('title="Korean Augmentation to the United States Army"', military)
        self.assertNotRegex(military, r"interpreting|transportation operations")
        self.assertIn("미국식 업무 문화와 협업 방식", self.translations["military.text"])

    def test_main_navigation_links_to_matching_beyond_page(self):
        for path, expected in [("index.html", "beyond/"), ("ko/index.html", "ko/beyond/")]:
            source = (ROOT / path).read_text(encoding="utf-8")
            document = Document(source, BUILDER.SITE + ("ko/" if path.startswith("ko/") else ""))
            self.assertIn(("beyond", BUILDER.SITE + expected), document.nav_routes)


if __name__ == "__main__":
    unittest.main()
