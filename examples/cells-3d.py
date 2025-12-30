import napari

viewer = napari.Viewer()

viewer.open_sample(plugin='napari-metadata', sample='cells-3d')
viewer.window.add_plugin_dock_widget(plugin_name='napari-metadata')

napari.run()
