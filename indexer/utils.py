import asyncio

import frontmatter
import mistune
from selectolax.lexbor import LexborHTMLParser as HTMLParser

from config import config


def strip_markdown_html(text: str) -> str:
    # Convert Markdown to HTML using mistune
    html = mistune.html(text)
    # Parse HTML instantly via Lexbor C engine
    tree = HTMLParser(html)
    return (tree.body.text(deep=True) if tree.body else tree.text()).strip()


async def strip_markdown_and_html(text: str) -> str:
    return await asyncio.to_thread(strip_markdown_html, text)


def get_all_collections():
    results = []
    for collection_markdown_file in config.COLLECTIONS_PATH.rglob("*.md"):
        with collection_markdown_file.open() as f:
            collection = frontmatter.load(f)
            collection["slug"] = str(collection_markdown_file.name).replace(".md", "")
            collection["collection"] = str(collection_markdown_file.parent.name)
            results.append(collection)
    return results
