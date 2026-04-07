"""Widget subpackage for napari-metadata.

All Qt-dependent code lives here.
"""

from napari_metadata.widgets._main import MetadataWidget
from napari_metadata.widgets._viewer_metadata import ViewerMetadataWidget

__all__ = ['MetadataWidget', 'ViewerMetadataWidget']
