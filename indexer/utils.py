import asyncio
from pathlib import Path

import frontmatter
import mistune
from selectolax.lexbor import LexborHTMLParser as HTMLParser


def _strip_markdown_html(text: str) -> str:
    # Convert Markdown to HTML using mistune
    html = mistune.html(text)
    # Parse HTML instantly via Lexbor C engine
    tree = HTMLParser(html)
    return (tree.body.text(deep=True) if tree.body else tree.text()).strip()


async def strip_markdown_and_html(text: str) -> str:
    return await asyncio.to_thread(_strip_markdown_html, text)


def _markdown_files(directory: Path) -> list[Path]:
    return directory.rglob("*.md")


def get_all_collections():
    results = []
    collections_path = Path(__file__).parent.parent / "collections"
    for collection_markdown in _markdown_files(collections_path):
        with collection_markdown.open() as f:
            parsed_frontmatter = frontmatter.load(f)
        context = {}
        context["title"] = parsed_frontmatter.get("title", "")
        context["uuid"] = parsed_frontmatter.get("uuid", "")
        context["description"] = _strip_markdown_html(parsed_frontmatter.content)
        context["organisations"] = parsed_frontmatter.get("organisations", [])
        context["created_at"] = parsed_frontmatter.get("created_at", "")
        context["updated_at"] = parsed_frontmatter.get("updated_at", "")
        results.append(_transform_context(context))
    return results


def _transform_context(context):
    """
    Recursively transform keys frontmatter kebab-case to pythonic underscores, e.g.
    my-key becomes my_key
    """
    if isinstance(context, dict):
        return {key.lower().replace("-", "_"): _transform_context(value) for key, value in context.items()}
    if isinstance(context, list):
        return [_transform_context(item) for item in context]
    return context
