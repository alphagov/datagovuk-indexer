# OpenSearch pre-populated with a snapshot of datagovuk datasets/collections.
# The build context is a directory containing the `data/` dir copied from the
# `opensearch-seed` compose service (see `just seed-build`).
FROM opensearchproject/opensearch:3.7.0

LABEL org.opencontainers.image.source=https://github.com/alphagov/datagovuk-indexer
LABEL org.opencontainers.image.description="OpenSearch pre-populated with datagovuk datasets and collections"

# cluster.name must match the node that wrote the data dir.
ENV cluster.name=opensearch-cluster \
    node.name=opensearch-node1 \
    discovery.type=single-node \
    DISABLE_INSTALL_DEMO_CONFIGS=true \
    DISABLE_SECURITY_PLUGIN=true \
    OPENSEARCH_JAVA_OPTS="-Xms512m -Xmx512m"

COPY --chown=1000:1000 data/ /usr/share/opensearch/data/

# Lock files copied in an image layer get replaced on first write (overlayfs copy-up),
# which Lucene treats as tampering and refuses to start. Let OpenSearch recreate them.
RUN rm -f /usr/share/opensearch/data/nodes/0/node.lock \
    /usr/share/opensearch/data/nodes/0/_state/write.lock \
    /usr/share/opensearch/data/nodes/0/indices/*/*/index/write.lock
