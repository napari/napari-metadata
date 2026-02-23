"""The file size portion of the metadata widget is not part of the
metadata stored with the image (e.g. name, scale). Instead, it is
a property which is populated on the fly at runtime.
"""

import logging
import math
import os
import urllib
from pathlib import Path
from typing import Union

from napari.layers import Layer

logger = logging.getLogger()


def generate_text_for_size(size: Union[int, float], suffix: str = '') -> str:
    """Generate the text for the file size widget. Consumes size in bytes,
    reduces the order of magnitude and appends the units. Optionally adds
    an addition suffix to the end of the string.

    >>> generate_text_for_size(13)
    '13.00 bytes'
    >>> generate_text_for_size(1303131, suffix=' (in memory)')
    '1.30 MB (in memory)'

    Parameters
    ---------
    size: (int | float)
        The size in bytes
    suffix: (str, optional)
        Addition text suffix to add to the display. Defaults to ''.

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


def generate_display_size(layer: Layer) -> str:
    """High level generator for the displayed file size text on the widget.
    If the provided layer has a source path, it will read the memory size on
    disk. If there is no source path on the layer, it will use the size of
    the data array.

    Parameters
    ----------
    layer: napari.Layer
        Napari Layer for which to generate file size text

    Returns
    -------
    str
        Formatted string for the file size or size in memory of the data.
    """
    is_url = urllib.parse.urlparse(layer.source.path).scheme in (
        'http',
        'https',
    )
    # data exists in file on disk
    if layer.source.path and not is_url:
        size = os.path.getsize(str(layer.source.path))
        suffix = ''
    # data exists only in memory
    else:
        if (
            type(layer).__name__ == 'Shapes'
            or type(layer).__name__ == 'Surface'
            or layer.multiscale is True
        ):
            size = sum(d.nbytes for d in layer.data)
        else:
            size = layer.data.nbytes
        suffix = ' (in memory)'
    text = generate_text_for_size(size, suffix=suffix)

    return text


def directory_size(path: Union[str, Path]) -> int:
    """Recursively walk a directory and add up total size on disk in bytes.
    Note that the napari-ome-zarr plugin doesn't store the path to a local
    zarr file. Until this is resolved, this will be unused.

    Parameters
    ----------
    path: str
        Path to directory

    Returns
    -------
    str
        Number of bytes in directory

    Raises
    ------
    RuntimeError
        If the path provided is not a directory
    """
    p = Path(path)
    if not p.is_dir():
        raise RuntimeError(
            'Path provided is not a directory. Unable to get directory size.'
        )
    return sum(file.stat().st_size for file in p.rglob('*'))
