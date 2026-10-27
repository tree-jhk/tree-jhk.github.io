"""Generate static Korean pages from their English sources and translations."""

import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = "https://tree-jhk.github.io/"
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class Localizer(HTMLParser):
    def __init__(self, source, translations):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.translations = translations
        self.lines = [0]
        for match in re.finditer("\n", source):
            self.lines.append(match.end())
        self.stack = []
        self.replacements = []
        self.seen = Counter()

    def source_offset(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attrs):
        if tag in VOID_TAGS:
            return
        key = dict(attrs).get("data-i18n")
        if key:
            if key not in self.translations:
                raise ValueError(f"Missing Korean translation: {key}")
            if any(item[1] for item in self.stack):
                raise ValueError(f"Nested translation markers are not supported: {key}")
            self.seen[key] += 1
        self.stack.append((tag, key, self.source_offset() + len(self.get_starttag_text())))

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1][0] != tag:
            raise ValueError(f"Unbalanced HTML end tag: {tag}")
        _, key, start = self.stack.pop()
        if key:
            self.replacements.append((start, self.source_offset(), self.translations[key]))

    def render(self):
        self.feed(self.source)
        self.close()
        if self.stack:
            raise ValueError("Unclosed HTML elements")
        unused = self.translations.keys() - self.seen.keys()
        if unused:
            raise ValueError(f"Unused Korean translations: {sorted(unused)}")
        result = self.source
        for start, end, value in sorted(self.replacements, reverse=True):
            result = result[:start] + value + result[end:]
        return result


def build_page(source_path, destination_path, translation_path, description, og_description):
    source = (ROOT / source_path).read_text(encoding="utf-8")
    translations = json.loads((ROOT / translation_path).read_text(encoding="utf-8"))
    localizer = Localizer(source, translations)
    result = localizer.render()
    english_path = source_path.removesuffix("index.html")
    korean_path = destination_path.removesuffix("index.html")
    english_description = re.search(r'<meta name="description" content="([^"]*)">', source).group(1)
    english_og_description = re.search(r'<meta property="og:description" content="([^"]*)">', source).group(1)
    replacements = {
        '<html lang="en">': '<html lang="ko">',
        f'<meta name="description" content="{english_description}">': f'<meta name="description" content="{description}">',
        f'<meta property="og:description" content="{english_og_description}">': f'<meta property="og:description" content="{og_description}">',
        f'<meta property="og:url" content="{SITE}{english_path}">': f'<meta property="og:url" content="{SITE}{korean_path}">',
        '<meta property="og:locale" content="en_US">': '<meta property="og:locale" content="ko_KR">',
        '<meta property="og:locale:alternate" content="ko_KR">': '<meta property="og:locale:alternate" content="en_US">',
        f'<link rel="canonical" href="{SITE}{english_path}">': f'<link rel="canonical" href="{SITE}{korean_path}">',
        'aria-label="English" aria-current="page"': 'aria-label="English"',
        'aria-label="한국어">KR': 'aria-label="한국어" aria-current="page">KR',
        'aria-label="Main navigation"': 'aria-label="주요 메뉴"',
        'aria-label="Junhyuk Kwon home"': 'aria-label="Junhyuk Kwon 홈"',
        'aria-label="Language"': 'aria-label="언어 선택"',
        'aria-label="Toggle dark mode" title="Toggle dark mode"': 'aria-label="다크 모드 전환" title="다크 모드 전환"',
    }
    for original, replacement in replacements.items():
        if result.count(original) != 1:
            raise ValueError(f"Expected exactly one document marker: {original}")
        result = result.replace(original, replacement)
    for original, replacement in {
        'aria-label="Social links"': 'aria-label="연락처 및 프로필"',
        'alt="Portrait of Junhyuk Kwon"': 'alt="Junhyuk Kwon 프로필 사진"',
    }.items():
        result = result.replace(original, replacement)
    result = re.sub(
        r'(<a\b[^>]*\bhref=")[^"]*("[^>]*\bdata-nav=")(about|beyond)("[^>]*>)',
        lambda match: match[1] + "/ko/" + ("beyond/" if match[3] == "beyond" else "") + match[2] + match[3] + match[4],
        result,
    )
    asset_prefix = "../" * len(Path(destination_path).parent.parts)
    result = re.sub(r'((?:src|href)=")(?:\.\./)*assets/', lambda match: match[1] + asset_prefix + "assets/", result)
    result = f'<!-- Generated by scripts/build-locales.py. Edit {source_path} and {translation_path} instead. -->\n' + result
    destination = ROOT / destination_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(result, encoding="utf-8")
    print(f"Generated {destination_path} ({sum(localizer.seen.values())} translated elements)")


def build():
    build_page(
        "index.html", "ko/index.html", "assets/i18n/ko.json",
        "사람들의 손길이 직접 닿는 AI를 좋아하는 Junhyuk Kwon의 홈페이지입니다. Recommender systems와 multimodal agents를 다룹니다.",
        "사람들이 직접 사용하고 상호작용하는 AI에 관심이 있습니다. Recommender systems부터 multimodal agents까지 다룹니다.",
    )
    build_page(
        "beyond/index.html", "ko/beyond/index.html", "assets/i18n/beyond.ko.json",
        "논문과 프로젝트 밖의 Junhyuk Kwon 이야기입니다.",
        "논문과 프로젝트 밖의 Junhyuk Kwon 이야기입니다.",
    )


if __name__ == "__main__":
    build()
