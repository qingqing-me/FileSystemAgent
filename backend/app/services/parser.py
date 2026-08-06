"""HTML parser — extract clean text from raw HTML using trafilatura + BeautifulSoup fallback."""

import re

import trafilatura
from bs4 import BeautifulSoup


def extract_text(html: str) -> str:
    """
    Extract clean, readable text from HTML.

    Uses trafilatura as primary extractor (state-of-the-art boilerplate removal,
    handles Chinese pages well). Falls back to BeautifulSoup if trafilatura
    produces too little content.
    """
    # Try trafilatura first
    text = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=True,
        include_images=False,
        output_format="txt",
    )

    if text and len(text.strip()) > 100:
        return clean_text(text)

    # Fallback: BeautifulSoup targeting common content containers
    soup = BeautifulSoup(html, "lxml")

    # Remove obvious boilerplate
    for tag in soup.select("script, style, nav, footer, header, .sidebar, .menu, .nav"):
        tag.decompose()

    # Try common content selectors
    content = soup.select_one(
        "article, main, .content, #content, .article, #article, "
        ".post, .entry, .main-content, #main-content, "
        ".text-content, .body, #body"
    )

    if content:
        text = content.get_text(separator="\n")
    else:
        text = soup.body.get_text(separator="\n") if soup.body else ""

    return clean_text(text)


def clean_text(text: str) -> str:
    """Clean up extracted text: normalize whitespace, remove garbage lines."""
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)  # collapse multiple blank lines
    text = re.sub(r"[ \t]{2,}", " ", text)          # collapse multiple spaces
    text = re.sub(r"[\r\f\v]", "", text)            # remove weird whitespace

    lines = text.split("\n")
    lines = [line.strip() for line in lines]
    lines = [line for line in lines if line]  # remove empty lines

    return "\n".join(lines)


def extract_title(html: str) -> str:
    """Extract page title from HTML."""
    soup = BeautifulSoup(html, "lxml")
    if soup.title:
        return soup.title.get_text(strip=True)

    h1 = soup.select_one("h1")
    if h1:
        return h1.get_text(strip=True)

    return "无标题"
