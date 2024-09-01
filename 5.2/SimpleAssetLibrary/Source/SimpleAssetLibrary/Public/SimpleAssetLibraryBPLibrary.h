// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "Kismet/BlueprintFunctionLibrary.h"
#include "SimpleAssetLibraryBPLibrary.generated.h"

/* 
*	Function library class.
*	Each function in it is expected to be static and represents blueprint node that can be called in any blueprint.
*
*	When declaring function you can define metadata for the node. Key function specifiers will be BlueprintPure and BlueprintCallable.
*	BlueprintPure - means the function does not affect the owning object in any way and thus creates a node without Exec pins.
*	BlueprintCallable - makes a function which can be executed in Blueprints - Thus it has Exec pins.
*	DisplayName - full name of the node, shown when you mouse over the node and in the blueprint drop down menu.
*				Its lets you name the node using characters not allowed in C++ function names.
*	CompactNodeTitle - the word(s) that appear on the node.
*	Keywords -	the list of keywords that helps you to find node when you search for it using Blueprint drop-down menu. 
*				Good example is "Print String" node which you can find also by using keyword "log".
*	Category -	the category your node will be under in the Blueprint drop-down menu.
*
*	For more info on custom blueprint nodes visit documentation:
*	https://wiki.unrealengine.com/Custom_Blueprint_Node_Creation
*/

DECLARE_LOG_CATEGORY_EXTERN(AssetLibrary, Log, All);

UCLASS()
class USimpleAssetLibraryBPLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_UCLASS_BODY()

	/**  Get the Mouse Position in the Editor Viewport,
	 * this will check whether the mouse is over an Editor Viewport and, if so,
	 * return the mouse's World Space position over that viewport
	 */
	UFUNCTION(BlueprintCallable, Category = "Asset Library | Viewport")
	static UPARAM(DisplayName = "Is Over Viewport") bool GetEditorViewportMousePositionWS(FVector& WorldOrigin, FVector& WorldDirection);

	/**  Register the given list of metadata key names to the Asset Registry
	 * @param  Tags  the list of metadtaa names
	 */
	UFUNCTION(BlueprintCallable, Category = "Asset Library | Utils")
	static void RegisterMetadataTags(const TArray<FName>& Tags);

	/**  Get the existing asset thumbnail and apply to the `texture` Texture2D param of the dynamic material
	 * @param  DynamicMaterial  the dynamic material to apply the thumbnail image to (requires a `texture` Texture2D param)
	 * @param  AssetData  the asset to load the thumbnail from
	 * @param  DefaultTexture the default texture to use if a thumbnail isn't available
	 */
	UFUNCTION(BlueprintCallable, Category = "Asset Library | Utils")
	static void AddExistingAssetThumbnailToDynamicMaterial(UMaterialInstanceDynamic* DynamicMaterial, int32& ImageWidth, int32& ImageHeight, bool& IsValid, const FAssetData& AssetData, UTexture2D* DefaultTexture);

	/**  Generate or Get an Asset Thumbnail and apply to the `texture` Texture2D param of the dynamic material
	 * @param  DynamicMaterial  the dynamic material to apply the thumbnail image to (requires a `texture` Texture2D param)
	 * @param  AssetData  the asset to load the thumbnail from
	 * @param  DefaultTexture the default texture to use if a thumbnail isn't available
	 */
	UFUNCTION(BlueprintCallable, Category = "Asset Library | Utils")
	static void RenderAssetThumbnailToDynamicMaterial(UMaterialInstanceDynamic* DynamicMaterial, int32& ImageWidth, int32& ImageHeight, bool& IsValid, const FAssetData& AssetData, UTexture2D* DefaultTexture);

	/**  log a message to the AssetLibrary category
	 * @param  Message  the message to log
	 */
	UFUNCTION(BlueprintCallable, Category = "Asset Library | Utils")
	static void Log(FString message);

	/**  log a warning to the AssetLibrary category
	 * @param  Message  the message to log
	 */
	UFUNCTION(BlueprintCallable, Category = "Asset Library | Utils")
	static void Warning(FString message);

	/**  log an error to the AssetLibrary category
	 * @param  Message  the message to log
	 */
	UFUNCTION(BlueprintCallable, Category = "Asset Library | Utils")
	static void Error(FString message);
};

