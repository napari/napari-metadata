"""The file size portion of the metadata widget is not part of the
metadata stored with the image (e.g. name, scale). Instead, it is
a property which is populated on the fly at runtime.
"""

from __future__ import annotations

import logging
import math
import urllib.parse
from pathlib import Path
from typing import Union

from napari.layers import Layer

logger = logging.getLogger(__name__)

# URL schemes that indicate a remote (non-local) data source.
_REMOTE_SCHEMES = frozenset(
    {'http', 'https', 's3', 'gs', 'gcs', 'az', 'abfs', 'ftp', 'ftps'}
)


def _generate_text_for_size(size: Union[int, float], suffix: str = '') -> str:
    """Generate the text for the file size widget. Consumes size in bytes,
    reduces the order of magnitude and appends the units. Optionally adds
    an additional suffix to the end of the string.

    >>> _generate_text_for_size(13)
    '13.00 bytes'
    >>> _generate_text_for_size(1303131, suffix=' (in memory)')
    '1.30 MB (in memory)'

    Parameters
    ---------
    size: (int | float)
        The size in bytes
    suffix: (str, optional)
        Additional text suffix to add to the display. Defaults to ''.

    Returns
    -------
    str
        formatted text string for the file size
    """
    order = 0 if size == 0 else int(math.log10(size))

    logger.debug('order: %s', order)
    if order <= 2:
        text = f'{size:.2f} bytes'
    elif order >= 3 and order < 6:
        text = f'{size / (10**3):.2f} KB'
    elif order >= 6 and order < 9:
        text = f'{size / 10**6:.2f} MB'
    else:
        text = f'{size / 10**9:.2f} GB'
    return f'{text}{suffix}'


def _is_remote_path(path: str | None) -> bool:
    """Return True if *path* is a remote URL.

    Recognises common cloud and web schemes (http, https, s3, gs, az, …).
    Single-character schemes are treated as Windows drive letters and are
    therefore considered local.

    Parameters
    ----------
    path : str | None
        The source path from ``layer.source.path``.
    """
    if not path:
        return False
    scheme = urllib.parse.urlparse(str(path)).scheme.lower()
    # Windows drive letters (e.g. 'C' in 'C:\\...') are single characters.
    if len(scheme) <= 1:
        return False
    return scheme in _REMOTE_SCHEMES


def _is_lazy_data(data: object) -> bool:
    """Return True if *data* is a lazy/deferred array (e.g. dask.array.Array).

    Avoids importing dask at module level; returns False if dask is not installed.
    """
    try:
        import dask.array as da

        return isinstance(data, da.Array)
    except ImportError:  # pragma: no cover
        return False


def _has_lazy_data(layer: Layer) -> bool:
    """Return True if any data component of *layer* is a lazy/dask array."""
    if type(layer).__name__ in ('Shapes', 'Surface') or getattr(
        layer, 'multiscale', False
    ):
        return any(_is_lazy_data(d) for d in layer.data)
    return _is_lazy_data(layer.data)


def _get_napari_size(layer: Layer) -> int:
    """Return the uncompressed in-napari size of *layer* in bytes.

    For lazy (dask) arrays this is the *theoretical* fully-loaded size, not
    the currently-resident memory footprint.  For multiscale, Shapes and
    Surface layers the per-component sizes are summed.
    """
    if type(layer).__name__ in ('Shapes', 'Surface') or getattr(
        layer, 'multiscale', False
    ):
        return sum(getattr(d, 'nbytes', 0) for d in layer.data)
    return layer.data.nbytes


def _get_stored_size(path: str) -> int | None:
    """Return the on-disk size of a local file or directory in bytes.

    Returns ``None`` if *path* does not exist or cannot be read.
    """
    try:
        p = Path(path)
        if p.is_dir():
            return sum(f.stat().st_size for f in p.rglob('*') if f.is_file())
        if p.is_file():
            return p.stat().st_size
    except OSError:
        logger.debug('Could not read stored size for %s', path)
    return None


def generate_display_size(layer: Layer) -> str:
    """Generate a display string describing the size of *layer*.

    Two size values are reported when possible:

    * **Stored size** — compressed size of the data on local disk (file or
      directory, e.g. a zarr store).  Omitted for remote sources and
      purely in-memory layers.
    * **Napari size** — uncompressed, dtype-based size of the layer data.
      For lazy (dask) arrays this is the theoretical fully-loaded footprint,
      marked ``(uncompressed, lazy)``.  For in-memory numpy arrays it is the
      actual allocation, marked ``(in memory)``.

    Parameters
    ----------
    layer : napari.layers.Layer
        The layer to describe.

    Returns
    -------
    str
        A formatted string, for example:

        ``"18.00 MB (on disk) / 3.00 GB (uncompressed)"``   — local .tif
        ``"4.20 MB (on disk) / 17.00 GB (uncompressed, lazy)"``  — local zarr
        ``"17.00 GB (uncompressed, lazy)"``                  — remote zarr
        ``"100.00 MB (in memory)"``                          — pure in-memory
    """
    path = layer.source.path
    is_remote = _is_remote_path(path)
    has_local_source = bool(path) and not is_remote
    is_lazy = _has_lazy_data(layer)

    napari_size = _get_napari_size(layer)

    if is_lazy:
        napari_suffix = ' (uncompressed, lazy)'
    elif has_local_source or is_remote:
        napari_suffix = ' (uncompressed)'
    else:
        napari_suffix = ' (in memory)'

    napari_text = _generate_text_for_size(napari_size, suffix=napari_suffix)

    if has_local_source:
        stored_size = _get_stored_size(path)
        if stored_size is not None:
            stored_text = _generate_text_for_size(
                stored_size, suffix=' (on disk)'
            )
            return f'{stored_text} / {napari_text}'

    return napari_text
