try:
    from ._version import version as __version__
except ImportError:
    __version__ = 'unknown'

from ._sample_data import make_cells_3d_sample_data, make_nuclei_md_sample_data
from ._widget import MetadataWidget

__all__ = (
    'make_cells_3d_sample_data',
    'make_nuclei_md_sample_data',
    'MetadataWidget',
)
