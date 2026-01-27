# napari-metadata

[![License BSD-3](https://img.shields.io/pypi/l/napari-metadata.svg?color=green)](https://github.com/napari/napari-metadata/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/napari-metadata.svg?color=green)](https://pypi.org/project/napari-metadata/)
[![Python Version](https://img.shields.io/pypi/pyversions/napari-metadata.svg?color=green)](https://python.org)
[![tests](https://github.com/napari/napari-metadata/workflows/tests/badge.svg)](https://github.com/napari/napari-metadata/actions)
[![codecov](https://codecov.io/gh/napari/napari-metadata/branch/main/graph/badge.svg)](https://codecov.io/gh/napari/napari-metadata)
[![napari hub](https://img.shields.io/endpoint?url=https://api.napari-hub.org/shields/napari-metadata)](https://napari-hub.org/plugins/napari-metadata)

This is a [napari] plugin that expands the functionality of napari's handling of layer metadata by using the `Layer.metadata` dictionary to store some extra metadata attributes.

https://user-images.githubusercontent.com/2608297/229252866-68117b59-c574-44f5-9420-c59028007d37.mp4

It provides a few contributions.

- A reader to read some metadata from OME-Zarr images.
- A writer to write some metadata to a multiscale OME-Zarr image.
- A widget to control the extra attributes and view some other important read-only attributes.
- Some sample data to demonstrate basic usage.

This plugin is still an experimental work in progress. As such, it is not widely distributed and you should not expect support or future maintenance.

This plugin lacks a public API by design. In particular, you should not rely on any of the extra keys or values in `Layer.metadata` in your own software of napari plugins. They are purely implementation details of this plugin.

You can of course feel free to use the plugin or any of its code, but by doing so accept ownership of any issues that arise. If you have ideas or comments about this work, feel free to [file an issue].

## Installation

You can install the latest development version of `napari-metadata` via [pip]:

    pip install git+https://github.com/andy-sweet/napari-metadata.git

Alternatively, fork or clone this repository directly and install in editable mode for development:

    pip install -e . --group dev

## Findings

Since this plugin is an experiment, we performed some [initial testing](https://github.com/andy-sweet/napari-metadata/blob/main/docs/testing-2023-05.md) to assess its value.
Overall sentiment was positive, though there were some suggestions and points of discussion that could be useful for related and future work.

We also received some feedback on [the zulip topic where this plugin was announced](https://napari.zulipchat.com/#narrow/stream/309872-plugins/topic/WIP.20metadata.20plugin), which may be useful to reference.

## Contributing

Since this is still experimental, I don't encourage contributions and likely won't review PRs with much urgency.

## License

Distributed under the terms of the [BSD-3] license,
"napari-metadata" is free and open source software

[napari]: https://github.com/napari/napari
[BSD-3]: http://opensource.org/licenses/BSD-3-Clause
[file an issue]: https://github.com/andy-sweet/napari-metadata/issues
[pip]: https://pypi.org/project/pip
