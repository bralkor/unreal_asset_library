
import typing
import unreal

from simple_asset_library.unreal_systems import (
    asset_registry_helper,
    asset_registry,
    EditorAssetSubsystem,
    log
)


# The supported metadata names used by the system
META_MANAGED_ASSET = "ALIB_managed_asset"
META_ASSET_TYPE = "ALIB_asset_type"
META_ASSET_CATEGORY = "ALIB_asset_category"
META_DISPLAY_NAME = "ALIB_display_name"
META_ADDED_BY = "ALIB_added_by"


ALL_ALL_METADATA_NAMES = [
    META_MANAGED_ASSET,
    META_ASSET_TYPE,
    META_ASSET_CATEGORY,
    META_DISPLAY_NAME,
    META_ADDED_BY
]


def register_metadata_names():
    """Register the metadata names to the Unreal Asset Registry"""
    unreal.SimpleAssetLibraryBPLibrary.register_metadata_tags(ALL_ALL_METADATA_NAMES)

    log(
        f"The following tags have been registered to the Asset Registry: {ALL_ALL_METADATA_NAMES}"
    )


def set_asset_metadata(asset: typing.Union[unreal.Object, str], data: dict):
    """
    Set the desired metadata on the given asset & save it
    
    Args:
        asset (unreal.Object or str): the loaded asset or string asset path to add the metadata to
        data (dict): A dictionary of key:value pairs
    """
    if isinstance(asset, str):
        asset = unreal.load_asset(asset)

    for tag, value in data.items():
        EditorAssetSubsystem.set_metadata_tag(asset, str(tag), str(value))
    EditorAssetSubsystem.save_loaded_asset(asset, False)


def get_asset_metadata(
        asset: typing.Union[unreal.Object, str], tag: str, default: typing.Any = None
) -> typing.Optional[str]:
    """
    Get the metadata tag from the given asset or asset path

    Args:
        asset (unreal.Object or str): the loaded asset or string asset path to get the metadata from
        tag (str or None): the metadata tag if found
        default: the default value to return if None
    """
    if isinstance(asset, str):
        data = EditorAssetSubsystem.get_tag_values(asset).get(tag)
    elif isinstance(asset, unreal.AssetData):
        data = asset.get_tag_value(tag)
    else:
        data = EditorAssetSubsystem.get_metadata_tag(asset, tag)
    if data == "None":
        data = None
    if tag == META_MANAGED_ASSET:
        data = data.lower() == "true"
    return data or default


def remove_asset_metadata(asset: typing.Union[unreal.Object, str]):
    """
    Remove the Asset Library metadata tags from the given asset

    Args:
        asset (unreal.Object or str): the loaded asset or string asset path to remove the metadata from
    """
    if isinstance(asset, str):
        asset = unreal.load_asset(asset)

    for tag in ALL_ALL_METADATA_NAMES:
        if get_asset_metadata(asset, tag) is not None:
            set_asset_metadata(asset, {tag: ""})
            EditorAssetSubsystem.remove_metadata_tag(asset, str(tag))

    EditorAssetSubsystem.save_loaded_asset(asset, True)
    asset_registry.scan_paths_synchronous([asset.get_outer().get_path_name()], True)


def find_assets(
        metadata: typing.Dict[str, str],
) -> typing.List[unreal.AssetData]:
    """Find Unreal Assets based on a given name, class, or metadata {name:value} pairs

    parameters:
        metadata (dict): a dictionary of metadata name:value pairs

    returns:
        list(unreal.AssetData):
    """

    # Create a basic filter and perform an initial search
    base_filter = unreal.ARFilter(class_names=["object"], recursive_classes=True)
    results = asset_registry.get_assets(base_filter) or []

    # Remove any Temp asset paths
    results = [r for r in results if not str(r.package_path).startswith("/Temp/")]

    # Filter the results by each metadata key:value pair
    for key, value in metadata.items():
        query = unreal.TagAndValue(str(key), str(value))
        meta_filter = asset_registry_helper.set_filter_tags_and_values(base_filter, [query])
        results = asset_registry.run_assets_through_filter(results, meta_filter) or []
        if not results:
            break

    # Sort results by asset path, list local assets before any plugin assets
    if len(results) > 1:
        results = sorted(
            results,
            key=lambda p: (
                not str(p.package_path).startswith("/Game/"),  # False is 0 True is 1,
                get_asset_metadata(p, META_DISPLAY_NAME).lower(),
                str(p.get_full_name()).lower()
            )
        )
    #log(f"Found {len(results)} results for {metadata}")

    return results
