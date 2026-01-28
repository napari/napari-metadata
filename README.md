# napari-metadata

[![License BSD-3](https://img.shields.io/pypi/l/napari-metadata.svg?color=green)](https://github.com/napari/napari-metadata/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/napari-metadata.svg?color=green)](https://pypi.org/project/napari-metadata/)
[![Python Version](https://img.shields.io/pypi/pyversions/napari-metadata.svg?color=green)](https://python.org)
[![tests](https://github.com/napari/napari-metadata/workflows/tests/badge.svg)](https://github.com/napari/napari-metadata/actions)
[![codecov](https://codecov.io/gh/napari/napari-metadata/branch/main/graph/badge.svg)](https://codecov.io/gh/napari/napari-metadata)
[![napari hub](https://img.shields.io/endpoint?url=https://api.napari-hub.org/shields/napari-metadata)](https://napari-hub.org/plugins/napari-metadata)

napari-metadata is a [napari] plugin that visually exposes the functionality of napari's handling of layer metadata by directly connecting with the public API of napari layers.

> [!NOTE]
> This plugin is in active development. *You should not depend on any API, as it is likely to change*. Instead, understand that this plugin intends to serve as a GUI to manage already available public API of napari layers.
> If you find a feature of this plugin useful, but it is not available in napari's core API, please consider opening an issue here or in the [napari repository](https://github.com/napari/napari/issues/new/choose). 

## Usage

This plugin adds a dock widget to napari that allows you to view and edit metadata for each layer in your napari viewer. The widget is intended to be used in the typical vertical widget layout and additionally is designed to work great in a horizontal layout.

![horizontal layout of metadata widget](https://raw.githubusercontent.com/napari/napari-metadata/main/resources/horizontal-widget.png)

## Installation

You can install `napari-metadata` via pip:

```bash
pip install napari-metadata
```

Alternatively, fork or clone this repository directly and install in editable mode for development:

```bash
pip install -e . --group dev
```

## Contributing

Contributions are very welcome. Tests can be run with [tox], please ensure
the coverage at least stays the same before you submit a pull request.

## License

Distributed under the terms of the [BSD-3] license,
"napari-metadata" is free and open source software
