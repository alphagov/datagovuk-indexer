import pytest

from indexer.utils import (
    CANONICAL_FORMATS,
    FORMAT_MAPPINGS,
    strip_markdown_and_html,
    transform_resource_format,
)


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


@pytest.mark.parametrize("resource_format", [None, ""])
def test_transform_resource_format_empty(resource_format):
    """Missing or empty formats should return an empty string."""
    assert transform_resource_format(resource_format) == ""


@pytest.mark.parametrize("resource_format", CANONICAL_FORMATS)
def test_transform_resource_format_canonical_formats(resource_format):
    """Canonical formats should be returned uppercased, whatever case they arrive in."""
    assert transform_resource_format(resource_format) == resource_format.upper()
    assert transform_resource_format(resource_format.upper()) == resource_format.upper()


@pytest.mark.parametrize(
    ("resource_format", "expected"),
    [
        ("xlsx", "XLS"),
        ("Excel Spreadsheet", "XLS"),
        ("csv / zip", "ZIP"),
        ("TSV", "CSV"),
        ("kmz", "KML"),
        ("Web Page", "HTML"),
        ("ArcGIS Online", "ESRIREST"),
        ("Shapefile", "SHP"),
        ("wmts", "WMS"),
        ("OGC WFS", "WFS"),
        ("rdf", "XML"),
        ("json2.0", "JSON"),
        ("pdf document", "PDF"),
        ("https://www.iana.org/assignments/media-types/text/csv", "CSV"),
    ],
)
def test_transform_resource_format_maps_aliases(resource_format, expected):
    """Known aliases should map to their canonical format, case-insensitively."""
    assert transform_resource_format(resource_format) == expected


@pytest.mark.parametrize(
    "resource_format",
    [" CSV ", ".csv", "csv.", ".csv.", "\tcsv\n", " .Csv. "],
)
def test_transform_resource_format_strips_whitespace_and_dots(resource_format):
    """Surrounding whitespace and a single leading/trailing dot should be removed."""
    assert transform_resource_format(resource_format) == "CSV"


def test_transform_resource_format_strips_dots_before_mapping():
    """Dot stripping should happen before the alias lookup."""
    assert transform_resource_format(".xlsx") == "XLS"


@pytest.mark.parametrize("resource_format", ["docx", "parquet", "something unknown", "c s v"])
def test_transform_resource_format_unknown_formats_are_other(resource_format):
    """Unrecognised formats should fall back to OTHER."""
    assert transform_resource_format(resource_format) == "OTHER"


def test_format_mappings_only_map_to_canonical_formats():
    """Every alias must map to a known canonical format."""
    assert set(FORMAT_MAPPINGS.values()) <= set(CANONICAL_FORMATS)


def test_format_mappings_keys_are_normalised():
    """Mapping keys must already be lowercased and stripped, otherwise they can never match."""
    for key in FORMAT_MAPPINGS:
        assert key == key.strip().removeprefix(".").removesuffix(".").lower()
