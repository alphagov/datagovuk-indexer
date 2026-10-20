import pytest

from indexer.utils import get_all_collections, strip_markdown_and_html


@pytest.mark.asyncio
async def test_strip_markdown_and_html_no_markdown_no_html():
    """Plain text with no markdown or HTML should pass through unchanged."""
    result = await strip_markdown_and_html("Hello, world!")
    assert result == "Hello, world!"


@pytest.mark.asyncio
async def test_strip_markdown_and_html_markdown_only():
    """Markdown formatting should be stripped to plain text."""
    md = "# Heading\n\nThis is **bold** and *italic*.\n\n- List item"
    result = await strip_markdown_and_html(md)
    assert result == "Heading\nThis is bold and italic.\n\nList item"


@pytest.mark.asyncio
async def test_strip_markdown_and_html_html_only():
    """HTML tags should be stripped, leaving only text content."""
    html = "<p>Hello <b>world</b>!</p>"
    result = await strip_markdown_and_html(html)
    assert result == "Hello world!"


@pytest.mark.asyncio
async def test_strip_markdown_and_html_both_markdown_and_html():
    """Mixed Markdown and HTML should have both stripped."""
    mixed = "# <b>Title</b>\n\nParagraph with **bold** and <i>italic</i>."
    result = await strip_markdown_and_html(mixed)
    assert "Title" in result
    assert "bold" in result
    assert "italic" in result
    # No HTML tags or markdown syntax should remain
    assert "<b>" not in result
    assert "**" not in result


@pytest.mark.asyncio
async def test_strip_markdown_and_html_empty_string():
    """An empty string should return an empty string."""
    result = await strip_markdown_and_html("")
    assert result == ""


@pytest.mark.asyncio
async def test_strip_markdown_and_html_whitespace_only():
    """Whitespace-only input should return stripped whitespace."""
    result = await strip_markdown_and_html("   \n\n  ")
    assert result == ""


@pytest.mark.asyncio
async def test_strip_markdown_and_html_nested_markdown():
    """Nested Markdown formatting (e.g. bold + italic, headers) should be fully stripped."""
    md = "## Nested **formatting**\n\nThis has *italic* and ***bold italic***.\n\nA [link](http://example.com)."
    result = await strip_markdown_and_html(md)
    assert "Nested formatting" in result
    assert "italic" in result
    assert "bold italic" in result
    assert "A link" in result
    assert "**" not in result
    assert "*" not in result
    assert "#" not in result
    assert "[" not in result
    assert "(" not in result
    assert "]" not in result


@pytest.mark.asyncio
async def test_strip_markdown_and_html_nested_html():
    """Nested HTML tags should be fully stripped."""
    html = "<div><p>This is <strong>very <em>emphasized</em></strong> content.</p></div>"
    result = await strip_markdown_and_html(html)
    assert result == "This is very emphasized content."


@pytest.mark.asyncio
async def test_strip_markdown_and_html_unicode():
    """Unicode characters should be preserved."""
    text = "Café résumé naïve 🌍 日本語"
    result = await strip_markdown_and_html(text)
    assert result == "Café résumé naïve 🌍 日本語"


@pytest.mark.asyncio
async def test_strip_markdown_and_html_with_special_characters():
    """Special characters and symbols should be preserved."""
    text = "Price: $100 | Stock: 5 < 10 | Special: @#%^&*"
    result = await strip_markdown_and_html(text)
    assert "$100" in result
    assert "<" in result or "10" in result
    assert "@" in result


@pytest.mark.asyncio
async def test_strip_markdown_and_html_multi_paragraph():
    """Multiple paragraphs separated by blank lines should be preserved."""
    md = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    result = await strip_markdown_and_html(md)
    assert "First paragraph." in result
    assert "Second paragraph." in result
    assert "Third paragraph." in result


@pytest.mark.asyncio
async def test_strip_markdown_and_html_code_blocks():
    """Inline code and code blocks should have their formatting stripped."""
    md = "Use `print()` to output.\n\n```\ndef hello():\n    pass\n```"
    result = await strip_markdown_and_html(md)
    assert "print()" in result
    assert "def hello():" in result
    assert "    pass" in result
    assert "`" not in result


@pytest.mark.asyncio
async def test_strip_markdown_and_html_table():
    """Markdown tables should have table syntax stripped, leaving row content."""
    md = "| Header 1 | Header 2 |\n|----------|----------|\n| Cell 1   | Cell 2   |"
    result = await strip_markdown_and_html(md)
    assert "Header 1" in result
    assert "Cell 1" in result
    assert "Header 2" in result
    assert "Cell 2" in result
    assert "|" not in result
    assert "---" not in result


def test_get_all_collections_parses_markdown(collection_factory):
    collections = get_all_collections()
    assert len(collections) == 1
    assert collections[0]["uuid"] == collection_factory["uuid"]
    assert collections[0]["title"] == collection_factory["title"]
    assert collections[0].content == collection_factory.content
    assert collections[0]["created_at"] == collection_factory["created_at"]
    assert collections[0]["updated_at"] == collection_factory["updated_at"]


def test_get_all_collections_with_no_markdown_files():
    collections = get_all_collections()
    assert len(collections) == 0
