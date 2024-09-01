
import json
from pathlib import Path
import typing
import unreal


BASE_CONFIG = {
  "asset_types": [
    "char",
    "envir",
    "FX",
    "prop"
  ],
  "default_category_options": [
    "default"
  ],
  "placed_actor_folder": "placed"
}


def get_plugin_directory() -> Path:
    """Get the root directory for this plugin as a Path object

    Returns:
        (Path) the plugin's root directory
    """
    return Path(unreal.PluginBlueprintLibrary.get_plugin_base_dir("SimpleAssetLibrary")).resolve()


def get_config_data() -> typing.Dict[str, str]:
    """Get the config settings for this plugin

    1) if available, get the settings for the current uproject:
        <project_dir>/Config/simple_asset_library_settings.json
    2) otherwise, use the default settings from the uplugin:
        <plugin_dir>/Config/simple_asset_library_settings.json
    3) lastly, use the BASE_CONFIG in the python module
        if the default settings file is missing

    Returns:
        (dict) a dictionary of the config data
    """

    # Check if the settings json is set in the project
    settings_json = Path(unreal.Paths.project_config_dir()) / "simple_asset_library_settings.json"
    if settings_json.exists():
        return json.loads(settings_json.read_text())

    # Check for the default settings json in the plugin's directory
    settings_json = get_plugin_directory() / "Config/simple_asset_library_settings.json"
    if settings_json.exists():
        return json.loads(settings_json.read_text())

    # Otherwise, return the base config defined in this module
    return BASE_CONFIG


def get_config_asset_types() -> typing.List[str]:
    """Get the list of asset types defined in the settings json

    Returns:
        (list(str)) the list of asset types
    """
    settings = get_config_data()
    return settings.get("asset_types", ["default"])


def get_config_default_categories() -> typing.List[str]:
    """Get the list of default asset categories defined in the settings json

    Note: Users can add their own categories when adding new assets to the asset library,
          these are just the baseline options

    Returns:
        (list(str)) the list of default categories
    """
    settings = get_config_data()
    return settings.get("default_category_options", ["default"])


def get_config_actor_folder_path() -> typing.List[str]:
    """Get the actor folder path setting defined in the settings json

    Returns:
        (str) the default actor folder path to assign actors placed from the Asset Library UI
    """
    settings = get_config_data()
    return settings.get("placed_actor_folder", "")
