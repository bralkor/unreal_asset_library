
import typing
import unreal

# Registries and Libraries
asset_registry_helper = unreal.AssetRegistryHelpers()
asset_registry        = asset_registry_helper.get_asset_registry()
EditorAssetLibrary    = unreal.EditorAssetLibrary()
ToolMenus             = unreal.ToolMenus.get()
AssetTools            = unreal.AssetToolsHelpers.get_asset_tools()

# Subsystems
AssetEditorSubsystem   = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
EditorActorSubsystem   = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
EditorAssetSubsystem   = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
EditorUtilitySubsystem = unreal.get_editor_subsystem(unreal.EditorUtilitySubsystem)
LevelEditorSubsystem   = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
UnrealEditorSubsystem  = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)


# Asset Library logger
def log(message: typing.Any):
    """
    print the given message using the AssetLibrary log category in Unreal

    Args:
        message (str): the message to print, this will convert the input to a string
    """
    unreal.SimpleAssetLibraryBPLibrary.log(str(message))
