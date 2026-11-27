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


ZIP = "zip"
XML = "xml"
XLS = "xls"
WMS = "wms"
WFS = "wfs"
SHP = "shp"
PDF = "pdf"
KML = "kml"
JSON = "json"
HTML = "html"
GEOJSON = "geojson"
ESRIREST = "esrirest"
CSV = "csv"
OTHER = "other"


CANONICAL_FORMATS = [
    ZIP,
    XML,
    XLS,
    WMS,
    WFS,
    SHP,
    PDF,
    KML,
    JSON,
    HTML,
    GEOJSON,
    ESRIREST,
    CSV,
    OTHER,
]


FORMAT_MAPPINGS = {
    # zip
    "7z": ZIP,
    "application/zip, application/octet-stream, application/x-zip-compressed, multipart/x-zip": ZIP,
    "csv / zip": ZIP,
    "csv/zip": ZIP,
    "gz": ZIP,
    "https://www.iana.org/assignments/media-types/application/zip": ZIP,
    "shp / zip": ZIP,
    "txt / gz": ZIP,
    "xls / zip": ZIP,
    "xlsx / zip": ZIP,
    "xml (tgz file)": ZIP,
    "xml / zip": ZIP,
    "xml/zip": ZIP,
    ZIP: ZIP,
    "zip / zip": ZIP,
    "zipped shapefile": ZIP,
    # xml
    "application/gml+xml": XML,
    "atom feed": XML,
    "citygml": XML,
    "csw": XML,
    "georss": XML,
    "getcapabilities": XML,
    "gml": XML,
    "https://www.iana.org/assignments/media-types/application/gpx+xml": XML,
    "https://www.iana.org/assignments/media-types/application/rdf+xml": XML,
    "metadata": XML,
    "rdf": XML,
    "rss": XML,
    XML: XML,
    "xsd": XML,
    "xsl": XML,
    "xslt": XML,
    # xls
    "1 / xls": XLS,
    "els": XLS,
    "excel": XLS,
    "excel spreadsheet": XLS,
    "excell": XLS,
    "exel": XLS,
    "https://www.iana.org/assignments/media-types/application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": XLS,  # noqa: E501
    "microsoft excel": XLS,
    "xlam": XLS,
    "xlb": XLS,
    XLS: XLS,
    "xls / xlsx": XLS,
    "xlsb": XLS,
    "xlsm": XLS,
    "xlsx": XLS,
    "xlw": XLS,
    "xlx": XLS,
    "xlxs": XLS,
    "xslx": XLS,
    # wms
    "ogc wms": WMS,
    WMS: WMS,
    "wmts": WMS,
    # wfs
    "ogc api - features": WFS,
    "ogc wfs": WFS,
    "wfs": WFS,
    # shp
    "cpg": SHP,
    "esri shapefile mapinfo tab": SHP,
    "esri shapefile mapinfo tab geojson": SHP,
    "prj": SHP,
    "sbn": SHP,
    "sbx": SHP,
    "shape": SHP,
    "shapefile": SHP,
    SHP: SHP,
    "shx": SHP,
    # pdf
    "0_v2 / pdf": PDF,
    "1 / pdf": PDF,
    "pd": PDF,
    PDF: PDF,
    "pdf / pdf": PDF,
    "pdf document": PDF,
    "web-optimised pdf": PDF,
    # kml
    "https://www.iana.org/assignments/media-types/application/vnd.google-earth.kml+xml": KML,
    KML: KML,
    "kmx": KML,
    "kmz": KML,
    # json
    "https://www.iana.org/assignments/media-types/application/json": JSON,
    "https://www.iana.org/assignments/media-types/application/ld+json": JSON,
    JSON: JSON,
    "json1.0": JSON,
    "json2.0": JSON,
    # html
    "application/xhtml+xml": HTML,
    "ashx": HTML,
    "asp": HTML,
    "aspx": HTML,
    "dashboard": HTML,
    "gis online map": HTML,
    "hml": HTML,
    "htm": HTML,
    HTML: HTML,
    "html+rdfa": HTML,
    "html5": HTML,
    "htmlhtml": HTML,
    "hmtl": HTML,
    "http": HTML,
    "https": HTML,
    "information and download": HTML,
    "open data hub webpage": HTML,
    "open data site": HTML,
    "open data website": HTML,
    "open date site": HTML,
    "php": HTML,
    "rdfa": HTML,
    "rshiny": HTML,
    "school localities on open data site": HTML,
    "sharepoint": HTML,
    "shtml": HTML,
    "sparql web form": HTML,
    "text/html; charset=utf-8": HTML,
    "url": HTML,
    "web": HTML,
    "web map": HTML,
    "web page": HTML,
    "weblink": HTML,
    "webmap": HTML,
    "webpage": HTML,
    "website": HTML,
    "website containing data files": HTML,
    "wep page": HTML,
    # geojson
    "geojson": GEOJSON,
    # esri rest
    "arcgis experience": ESRIREST,
    "arcgis geoservices rest api": ESRIREST,
    "arcgis online": ESRIREST,
    "arcgis online item": ESRIREST,
    "arcgis online map": ESRIREST,
    "arcgis storymap": ESRIREST,
    "arcgis storymap collection": ESRIREST,
    "esri geoservice": ESRIREST,
    "esri map": ESRIREST,
    "esri open data site": ESRIREST,
    ESRIREST: ESRIREST,
    "esri rest api": ESRIREST,
    "esri rest service": ESRIREST,
    "feature server": ESRIREST,
    "feature service": ESRIREST,
    "map service": ESRIREST,
    # csv
    "cav": CSV,
    CSV: CSV,
    "csv / csv": CSV,
    "csv file": CSV,
    "cvc": CSV,
    "cvs": CSV,
    "dsv": CSV,
    "https://www.iana.org/assignments/media-types/text/csv": CSV,
    "tsv": CSV,
    "vsv": CSV,
}


def transform_resource_format(resource_format):
    if not resource_format:
        return ""
    stripped_format = resource_format.strip().removeprefix(".").removesuffix(".").lower()
    if stripped_format in CANONICAL_FORMATS:
        return stripped_format.upper()
    return FORMAT_MAPPINGS.get(stripped_format, OTHER).upper()
