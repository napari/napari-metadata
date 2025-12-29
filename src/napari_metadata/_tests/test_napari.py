from napari_metadata._widget import MetadataWidget


def test_add_widget_to_napari(make_napari_viewer):
    viewer = make_napari_viewer()
    _, widget = viewer.window.add_plugin_dock_widget('napari-metadata')
    assert isinstance(widget, MetadataWidget)
