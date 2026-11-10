ADDITIONAL_INFO_RELEVANT_KEYS = {
    "licence",
    "metadata-date",
    "access_constraints",
    "guid",
    "bbox-east-long",
    "bbox-west-long",
    "bbox-north-lat",
    "bbox-south-lat",
    "spatial-reference-system",
    "dataset-reference-date",
    "frequency-of-update",
    "responsible-party",
    "resource-type",
    "metadata-language",
    "harvest_object_id",
}

ADDITIONAL_INFO_JSON_VALUE_KEYS = {"access_constraints", "dataset-reference-date"}


TOPIC_SLUGS = [
    "business-and-economy",
    "crime-and-justice",
    "defence",
    "digital-services-performance",
    "education",
    "environment",
    "government",
    "government-reference-data",
    "government-spending",
    "health",
    "mapping",
    "society",
    "towns-and-cities",
    "transport",
]


LICENCES = {
    "odc-pddl": {
        "title": "Open Data Commons Public Domain Dedication and License (PDDL)",
        "url": "http://www.opendefinition.org/licenses/odc-pddl",
    },
    "odc-odbl": {
        "title": "Open Data Commons Open Database License (ODbL)",
        "url": "http://www.opendefinition.org/licenses/odc-odbl",
    },
    "odc-by": {
        "title": "Open Data Commons Attribution License",
        "url": "http://www.opendefinition.org/licenses/odc-by",
    },
    "cc-zero": {
        "title": "Creative Commons CCZero",
        "url": "http://www.opendefinition.org/licenses/cc-zero",
    },
    "cc-by": {
        "title": "Creative Commons Attribution",
        "url": "http://www.opendefinition.org/licenses/cc-by",
    },
    "cc-by-sa": {
        "title": "Creative Commons Attribution Share-Alike",
        "url": "http://www.opendefinition.org/licenses/cc-by-sa",
    },
    "gfdl": {
        "title": "GNU Free Documentation License",
        "url": "http://www.opendefinition.org/licenses/gfdl",
    },
    "other-open": {
        "title": "Other (Open)",
        "url": None,
    },
    "other-pd": {
        "title": "Other (Public Domain)",
        "url": None,
    },
    "other-at": {
        "title": "Other (Attribution)",
        "url": None,
    },
    "uk-ogl": {
        "title": "UK Open Government Licence (OGL)",
        "url": "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
    },
    "cc-nc": {
        "title": "Creative Commons Non-Commercial (Any)",
        "url": "http://creativecommons.org/licenses/by-nc/2.0/",
    },
    "other-nc": {
        "title": "Other (Non-Commercial)",
        "url": None,
    },
    "other-closed": {
        "title": "Other (Not Open)",
        "url": None,
    },
}
