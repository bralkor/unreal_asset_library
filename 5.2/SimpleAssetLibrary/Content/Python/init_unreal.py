
import unreal

from simple_asset_library import (
    menus,
    metadata
)


metadata.register_metadata_names()

# Add the Asset Library button to the Content Browser
content_browser_menu = unreal.ToolMenus.get().find_menu("ContentBrowser.ToolBar")
menus.AssetLibraryLauncher(content_browser_menu, "")
unreal.ToolMenus.get().refresh_all_widgets()
