
import json
import os
from pathlib import Path
import typing
import unreal

from simple_asset_library import (
    config,
    metadata,
)
from simple_asset_library.unreal_systems import (
    EditorActorSubsystem,
    EditorAssetSubsystem,
    EditorUtilitySubsystem,
    log,
    UnrealEditorSubsystem
)


ENTRY_DATA_CLASS = unreal.load_asset('/SimpleAssetLibrary/tool/widgets/asset_library_entry_data').generated_class()
SPAWNED_ACTOR_TAG = "Asset Library Spawned"
ALL = "all"

cached_asset_types = dict()


def get_available_asset_types(include_all_option: bool = True) -> typing.List[str]:
    """
    Get the list of asset types from the asset library config

    Args:
        include_all_option (bool): whether to include an 'all' option in the return

    Returns:
        list(str) the list of asset types from the config file
    """
    global cached_asset_types
    if not cached_asset_types.get(include_all_option):
        base_list = [ALL] if include_all_option else []
        cached_asset_types[include_all_option] = base_list + config.get_config_asset_types()
        log(f"Found the following asset types: {cached_asset_types}")
    return cached_asset_types[include_all_option]


def get_available_asset_categories(asset_type: str = ALL, include_all_option: bool = True) -> typing.List[str]:
    """
    Get the list of categories for the given asset type
    This includes the default categories as well as any categories added by the user

    NOTE: if the provided Asset Type is 'all' this will return all categories

    Args:
        asset_type (str): the asset type to get the categories for
        include_all_option (bool): whether to include an 'all' option in the return

    Returns:
        list(str) the list of asset types from the config file
    """
    categories = config.get_config_default_categories() if asset_type != ALL else []

    meta_query = {metadata.META_MANAGED_ASSET: True}
    if asset_type.lower() != ALL:
        meta_query = meta_query | {metadata.META_ASSET_TYPE: asset_type}

    # Get the user added categories from Unreal
    user_added_categories = [
        metadata.get_asset_metadata(item, metadata.META_ASSET_CATEGORY)
        for item in metadata.find_assets(meta_query)
        if metadata.get_asset_metadata(item, metadata.META_ASSET_CATEGORY)
    ]

    # Remove any duplicates and organize the list
    base_list = [ALL] if include_all_option else []
    categories = base_list + sorted(set(categories + user_added_categories))
    return categories


def get_asset_list(asset_type: str = ALL, category: str = ALL) -> typing.List[unreal.AssetData]:
    """
    get the list of assets registered to the Asset Library for the given asset type + category

    Args:
        asset_type: if provided, only get the assets of this type
        category: if provided, only get the assets of this category

    Returns:

    """
    meta_query = {metadata.META_MANAGED_ASSET: True}
    if asset_type.lower() != ALL:
        meta_query = meta_query | {metadata.META_ASSET_TYPE: asset_type}
    if category.lower() != ALL:
        meta_query = meta_query | {metadata.META_ASSET_CATEGORY: category}

    return metadata.find_assets(meta_query)


def get_asset_list_for_gui(asset_type: str) -> typing.List[unreal.EditorUtilityObject]:
    """
    get the list of assets to use for the Asset Library GUI

    Args:
        asset_type (str): the asset type to get the assets for

    Returns:
        list(unreal.EditorUtilityObject) the list of assets as asset library entry data objects
    """

    # Get the managed assets as a list of entry data objects
    entries = []
    for asset_data in get_asset_list(asset_type):
        new_entry = unreal.new_object(ENTRY_DATA_CLASS)
        new_entry.set_editor_properties({
            "asset_data": asset_data,
            "asset_path": str(asset_data.package_name),
            "asset_metadata": EditorAssetSubsystem.get_metadata_tag_values(asset_data.get_asset()),
            "asset_display_name": metadata.get_asset_metadata(asset_data, metadata.META_DISPLAY_NAME, ""),
            "asset_type": metadata.get_asset_metadata(asset_data, metadata.META_ASSET_TYPE, ""),
            "asset_category": metadata.get_asset_metadata(asset_data, metadata.META_ASSET_CATEGORY, "default"),
            "added_by": metadata.get_asset_metadata(asset_data, metadata.META_ADDED_BY, "unknown"),
            "unreal_class": str(asset_data.asset_class_path.asset_name)
        })
        entries.append(new_entry)

    # Show the 'Add Entry' button if enabled
    asset_library_instance = get_asset_libary_instance()
    if asset_library_instance and asset_library_instance.get_editor_property("show_add_entry_button"):
        new_entry_button = unreal.new_object(ENTRY_DATA_CLASS)
        new_entry_button.set_editor_property("is_new_entry_button", True)
        entries.append(new_entry_button)

    log(f"found {len(entries)} registered assets of type {asset_type}")
    return entries


def filter_asset_list_for_gui(
        entries: typing.List[unreal.EditorUtilityObject],
        category: typing.Optional[str] = None,
        string_in_name: typing.Optional[str] = None
) -> typing.List[unreal.EditorUtilityObject]:
    """
    Filter the asset list to only those matching the provided category and/or string

    Args:
        entries (list(unreal.EditorUtilityObject)): the list of asset library entry data objects
        category (str): if provided, filter for the assets matching the given category
        string_in_name (str): if provided, filter for the assets matching the given name (Display name or Asset name)

    Returns:
        list(unreal.EditorUtilityObject) the list of assets matching the category + name filter
    """
    string_in_name = str(string_in_name) if string_in_name else None
    filtered_entries = entries.copy()

    # Filter for category matches if provided
    # Category should be a 1:1 match as it's managed entirely by the Asset Library
    if category and category.lower() != ALL:
        filtered_entries = [
            item
            for item in filtered_entries
            if item.get_editor_property("asset_metadata").get(metadata.META_ASSET_CATEGORY) == category
            or item.get_editor_property("is_new_entry_button")
        ]

    # Filter for str in name if provided
    # Will check if the given string is in the display name or unreal asset name
    if string_in_name:
        filtered_entries = [
            item
            for item in filtered_entries
            if string_in_name.lower() in str(item.get_editor_property("asset_display_name") or "").lower()
            or string_in_name.lower() in str(item.get_editor_property("asset_path") or "").split("/")[-1].lower()
            or item.get_editor_property("is_new_entry_button")
        ]
    log(f"{len(filtered_entries)}/{len(entries)} entries match the current display filter")
    return filtered_entries


def register_asset(asset: typing.Union[unreal.Object, str], asset_type: str, category: str, display_name: str):
    """
    Register the given asset or asset path to the asset library

    Args:
        asset (str or unreal.Object): the asset or asset path to register
        asset_type (str): the asset library asset type for this asset
        category (str): the asset library category for this asset
        display_name (str): the asset library display name for this asset
    """
    if isinstance(asset, str):
        asset = unreal.load_asset(asset)

    data = {
        metadata.META_MANAGED_ASSET: True,
        metadata.META_ASSET_TYPE: asset_type,
        metadata.META_ASSET_CATEGORY: category,
        metadata.META_DISPLAY_NAME: display_name,
        metadata.META_ADDED_BY: os.getlogin()
    }
    metadata.set_asset_metadata(asset, data)
    log(
        f"{asset.get_outer().get_path_name()} has been added to the Asset Library"
        f"\ndetails:\n\tasset: {asset.get_outer().get_path_name()}"
        f"\n\tdisplay name: {display_name}\n\tasset type: {asset_type}\n\tcategory: {category}"
    )


def unregister_asset(asset: typing.Union[unreal.Object, str]):
    """
    Unregister the given asset or asset path from the asset library

    Args:
        asset (str or unreal.Object): the asset or asset path to remove
    """
    if isinstance(asset, str):
        asset = unreal.load_asset(asset)

    metadata.remove_asset_metadata(asset)
    log(
        f"{asset.get_outer().get_path_name()} has been removed from the Asset Library"
    )

    # Refresh the UI
    asset_library_instance = get_asset_libary_instance()
    if asset_library_instance:
        load_settings()


def get_asset_library_data_for_asset(asset: typing.Union[unreal.Object, str]) -> typing.Tuple[bool, str, str, str]:
    """
    Get the Asset Library data for the given asset

    Args:
        asset (str or unreal.Object): the asset or asset path to register

    Returns:
        (bool, str, str, str): Whether the asset is managed, its asset type, its category, its display name
    """
    if isinstance(asset, str):
        asset = unreal.load_asset(asset)
    if not asset:
        return False, "", "", ""

    default_name = str(asset.get_name()).replace("_", " ").title()
    return (
        bool(metadata.get_asset_metadata(asset, metadata.META_MANAGED_ASSET, False)),
        metadata.get_asset_metadata(asset, metadata.META_ASSET_TYPE, ""),
        metadata.get_asset_metadata(asset, metadata.META_ASSET_CATEGORY, ""),
        metadata.get_asset_metadata(asset, metadata.META_DISPLAY_NAME) or default_name
    )


def spawn_asset_in_viewport(asset_to_spawn: unreal.Object, display_name: str) -> typing.Optional[unreal.Actor]:
    """
    Attempt to spawn the given actor asset in the current viewport under the mouse

    Args:
        asset_to_spawn (unreal.Object): the asset to spawn
        display_name (str): the display name to use on the new asset

    Returns:
        unreal.Actor: the newly spawned actor
    """

    # Get Mouse position if it's over a viewport
    origin, direction = unreal.SimpleAssetLibraryBPLibrary.get_editor_viewport_mouse_position_ws() or (None, None)
    if not origin:
        unreal.SimpleAssetLibraryBPLibrary.warning(
            f"Mouse is not currently over a viewport, cannot spawn {asset_to_spawn.get_path_name()}"
        )
        return None

    # Default settings
    align_to_surface = True
    ignore_placed_assets = True
    select_after_spawning = True
    max_distance = 10000

    # Get the settings from Asset Library instance
    asset_library_instance = get_asset_libary_instance()
    if asset_library_instance:
        align_to_surface = asset_library_instance.get_editor_property("align_to_surface")
        ignore_placed_assets = asset_library_instance.get_editor_property("ignore_placed_assets")
        select_after_spawning = asset_library_instance.get_editor_property("select_after_spawning")
        max_distance = asset_library_instance.get_editor_property("max_distance") or max_distance

    # [OPTIONAL] ignore actors spawned from the Asset Library
    actors_to_ignore = unreal.GameplayStatics.get_all_actors_with_tag(
        UnrealEditorSubsystem.get_editor_world(),
        SPAWNED_ACTOR_TAG
    ) if ignore_placed_assets else []

    # Perform a hit test to find any surfaces under the mouse
    destination = direction * max_distance + origin
    hit_test_results = unreal.SystemLibrary.sphere_trace_single(
        UnrealEditorSubsystem.get_editor_world(),
        start=origin,
        end=destination,
        radius=1.0,
        trace_channel=unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
        trace_complex=True,
        actors_to_ignore=actors_to_ignore,
        draw_debug_type=unreal.DrawDebugTrace.NONE
    )

    # Get Location + Normal of impact or use default if too far away from camera
    if hit_test_results:  # and hit_test_results.to_tuple()[3] < max_distance:
        spawn_location, impact_location, spawn_normal, impact_normal = hit_test_results.to_tuple()[4:8]
    else:
        unreal.SimpleAssetLibraryBPLibrary.warning(
            f"No hit test results, will spawn 10 units in front of camera"
        )
        spawn_location = direction * 1000 + origin
        spawn_normal = unreal.Vector(0, 0, 1)

    # Spawn rotation
    spawn_rotation = unreal.Rotator(0, 0, 0)
    if align_to_surface:
        # Convert the hit test normal to a rotator
        normal_to_vector = unreal.MathLibrary.conv_vector_to_rotator(spawn_normal)
        spawn_rotation = unreal.Rotator(0, -90, 0).combine(normal_to_vector)

    # Spawn the actor & set its properties
    new_actor = EditorActorSubsystem.spawn_actor_from_object(
        asset_to_spawn,
        spawn_location,
        spawn_rotation
    )
    if not new_actor:
        log(f"Failed to spawn {asset_to_spawn.get_outer().get_path_name()}, it may not be a valid actor-compatible asset!")
        return None

    new_actor.set_actor_label(display_name)
    new_actor.tags.append(SPAWNED_ACTOR_TAG)

    actor_folder_path = config.get_config_actor_folder_path()
    if actor_folder_path:
        new_actor.set_folder_path(actor_folder_path)

    if select_after_spawning:
        EditorActorSubsystem.set_selected_level_actors([new_actor])

    log(
        f"Spawned asset {asset_to_spawn.get_outer().get_path_name()} from the Asset Library"
    )

    return new_actor


def get_color_for_asset_type(asset_type) -> unreal.LinearColor:
    """
    Get a unique color for the given asset type, used for visual context in the UI

    Args:
        asset_type (str): the asset type to get the unique color for

    Returns:
        unreal.LinearColor: a Linear Color object of the unique color for that asset type
    """
    if asset_type.lower() == ALL:
        return unreal.LinearColor(1, 1, 1, 1)

    # Determine the Hue (0-359)
    available_asset_types = get_available_asset_types(False)
    hue = 0
    if asset_type in available_asset_types:
        hue = available_asset_types.index(asset_type) / len(available_asset_types) * 359

    asset_type_color = unreal.LinearColor()
    asset_type_color.set_from_hsv(hue, 0.8, 0.8, 0.5)
    return asset_type_color


def save_settings():
    """
    Save the user settings to disk for the Asset Library instance
    """
    asset_library_instance = get_asset_libary_instance()
    if not asset_library_instance or not asset_library_instance.get_editor_property("can_save_settings"):
        return

    prefs_file = Path(unreal.Paths.project_saved_dir(), f"Config/asset_library_prefs.json")
    if not prefs_file.exists():
        prefs_file.parent.mkdir(parents=True, exist_ok=True)

    with prefs_file.open("w", encoding="utf-8") as f:
        asset_type, asset_category, name_filter = asset_library_instance.call_method("get_menu_state")
        prefs_data = {
            "align_to_surface": asset_library_instance.get_editor_property("align_to_surface"),
            "ignore_placed_assets": asset_library_instance.get_editor_property("ignore_placed_assets"),
            "select_after_spawning": asset_library_instance.get_editor_property("select_after_spawning"),
            "max_distance": asset_library_instance.get_editor_property("max_distance"),
            "show_add_entry_button": asset_library_instance.get_editor_property("show_add_entry_button"),
            "show_delete_button": asset_library_instance.get_editor_property("show_delete_button"),
            "entry_size": asset_library_instance.get_editor_property("entry_size"),
            "ui_state_type": asset_type,
            "ui_state_category": asset_category,
            "ui_state_filter": name_filter,
        }
        json.dump(prefs_data, f, indent=2)


def load_settings():
    """
    Load the settings from disk for the Asset Library instance
    """
    asset_library_instance = get_asset_libary_instance()
    if not asset_library_instance:
        return

    prefs_file = Path(unreal.Paths.project_saved_dir(), f"Config/asset_library_prefs.json")
    prefs_data = None

    # Apply Asset Library settings
    if prefs_file.exists():
        prefs_data = json.loads(prefs_file.read_text())
        asset_library_instance.set_editor_properties({
            "align_to_surface": prefs_data.get("align_to_surface", True),
            "ignore_placed_assets": prefs_data.get("ignore_placed_assets", True),
            "select_after_spawning": prefs_data.get("select_after_spawning", True),
            "show_add_entry_button": prefs_data.get("show_add_entry_button", True),
            "show_delete_button": prefs_data.get("show_delete_button", False),
            "max_distance": prefs_data.get("max_distance", 10000),
            "entry_size": prefs_data.get("entry_size", 1.0),
        })
    asset_library_instance.call_method("update_entry_size")

    # Populate the asset type dropdown
    asset_library_instance.call_method("populate_asset_type_dropdown")
    if prefs_data and prefs_data.get("ui_state_type"):
        asset_library_instance.call_method("set_type_selection", (prefs_data.get("ui_state_type"),))

    # Populate the asset category dropdown
    asset_library_instance.call_method("populate_category_query_dropdown")
    if prefs_data and prefs_data.get("ui_state_category"):
        asset_library_instance.call_method("set_category_selection", (prefs_data.get("ui_state_category"),))

    # Populate the filter input field
    if prefs_data and prefs_data.get("ui_state_filter"):
        asset_library_instance.call_method("set_filter", (prefs_data.get("ui_state_filter"),))

    # Populate the UI
    asset_library_instance.call_method("get_asset_list")
    asset_library_instance.call_method("filter_asset_list")
    asset_library_instance.set_editor_property("can_save_settings", True)


def get_asset_libary_instance():
    """Get the currently open instance of the Asset Library"""
    asset = unreal.load_asset('/SimpleAssetLibrary/tool/AssetLibrary')
    return EditorUtilitySubsystem.find_utility_widget_from_blueprint(asset)
