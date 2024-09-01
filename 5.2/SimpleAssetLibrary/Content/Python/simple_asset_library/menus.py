
import unreal

from simple_asset_library.unreal_systems import (
    log,
    EditorUtilitySubsystem
)


@unreal.uclass()
class AssetLibraryLauncher(unreal.ToolMenuEntryScript):
    """
    menu tool class to launch the Asset Library
    """
    name = "simple_asset_library"
    display_name = "Asset Lib"
    tool_tip = "Open the Simple Asset Library"

    def __init__(self, menu, section):
        """
        initialize the menu entry and add it to the given menu's section

        parameters:
            menu: the menu object to add this tool to
            section: the section to group this tool under
        """
        super().__init__()
        menu.add_section(section, section)

        self.init_entry(
            owner_name="simple_asset_library",
            menu=menu.menu_name,
            section=section,
            name=self.name,
            label=self.display_name,
            tool_tip=self.tool_tip
        )

        # set the entry data as a toolbar button with the object browser icon
        self.data.advanced.entry_type = unreal.MultiBlockType.TOOL_BAR_BUTTON
        self.data.icon = unreal.ScriptSlateIcon("EditorStyle", "ObjectBrowser.TabIcon")

        menu.add_menu_entry_object(self)

    @unreal.ufunction(override=True)
    def execute(self, context):
        """Open the Asset Library"""
        log(f"Launching the Simple Asset Library")
        asset = unreal.load_asset('/SimpleAssetLibrary/tool/AssetLibrary')
        EditorUtilitySubsystem.spawn_and_register_tab(asset)
