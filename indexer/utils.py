import asyncio

import mistune
from selectolax.lexbor import LexborHTMLParser as HTMLParser


def strip_markdown_html(text: str) -> str:
    # Convert Markdown to HTML using mistune
    html = mistune.html(text)
    # Parse HTML instantly via Lexbor C engine
    tree = HTMLParser(html)
    return (tree.body.text(deep=True) if tree.body else tree.text()).strip()


async def strip_markdown_and_html(text: str) -> str:
    return await asyncio.to_thread(strip_markdown_html, text)
