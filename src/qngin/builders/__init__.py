"""Build QueryModel from Flow metadata + request payload."""

from __future__ import annotations

from qngin.builders.metadata import MetadataQueryModelBuilder
from qngin.builders.view import ViewQueryModelBuilder
from qngin.metadata.flow import Flow, FlowType


def get_builder(flow: Flow) -> MetadataQueryModelBuilder | ViewQueryModelBuilder:
    """Return the appropriate builder for a flow type."""
    if flow.flow_type in (FlowType.VIEW, FlowType.MATERIALIZED_VIEW):
        return ViewQueryModelBuilder(flow)
    return MetadataQueryModelBuilder(flow)


__all__ = [
    "MetadataQueryModelBuilder",
    "ViewQueryModelBuilder",
    "get_builder",
]
