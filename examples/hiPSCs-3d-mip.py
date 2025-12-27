import napari

viewer = napari.Viewer()

viewer.open_sample(plugin='napari-metadata', sample='hipsc-3d-mip')
viewer.window.add_plugin_dock_widget(plugin_name='napari-metadata')

napari.run()
