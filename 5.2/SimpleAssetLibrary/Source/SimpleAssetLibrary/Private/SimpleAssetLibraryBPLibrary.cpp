// Copyright Epic Games, Inc. All Rights Reserved.

#include "SimpleAssetLibraryBPLibrary.h"
#include "SimpleAssetLibrary.h"


#include "AssetRegistry/AssetRegistryModule.h"
#include "Widgets/SWidget.h"
#include "Widgets/SViewport.h"
#include "SEditorViewport.h"
#include "LevelEditorViewport.h"
#include "EditorViewportClient.h"
#include "SceneView.h"
#include "Slate/SceneViewport.h"
#include "Engine/Texture2D.h"
#include "Engine/Texture2DDynamic.h"
#include "ImageUtils.h"
#include "IImageWrapper.h"
#include "IImageWrapperModule.h"
#include "TextureResource.h"
#include "ObjectTools.h"
#include "UObject/SoftObjectPath.h"
#include "Materials/MaterialInstanceDynamic.h"


DEFINE_LOG_CATEGORY(AssetLibrary);

USimpleAssetLibraryBPLibrary::USimpleAssetLibraryBPLibrary(const FObjectInitializer& ObjectInitializer)
: Super(ObjectInitializer)
{}


bool
USimpleAssetLibraryBPLibrary::GetEditorViewportMousePositionWS(FVector& WorldOrigin, FVector& WorldDirection)
{
    FVector2D ScreenPos;
    FIntPoint MousePosition;

    // confirm mouse is over a viewport
    const FVector2D GlobalMousePosition = FSlateApplication::Get().GetPlatformCursor()->GetPosition();
    FWidgetPath WidgetUnderMouse = FSlateApplication::Get().LocateWindowUnderMouse(GlobalMousePosition, FSlateApplication::Get().GetInteractiveTopLevelWindows(), true);
    if (WidgetUnderMouse.GetLastWidget().Get().GetTypeAsString() != FString("SViewport")) {
        UE_LOG(LogTemp, Warning, TEXT("Mouse is not over a viewport -- Detected UI element under mouse: %s"), *FString(WidgetUnderMouse.GetLastWidget().Get().GetTypeAsString()));
        return false;
    }

    // check all level editor viewports
    FLevelEditorViewportClient* VPClient;
    for (int32 i = 0; i < GEditor->GetLevelViewportClients().Num(); i++)
    {
        // confirm it's the viewport under the mouse
        VPClient = GEditor->GetLevelViewportClients()[i];
        if (WidgetUnderMouse.GetLastWidget() == VPClient->GetEditorViewportWidget()->GetSceneViewport()->GetViewportWidget()) {

            // process the viewport
            FSceneViewFamilyContext ViewFamily(FSceneViewFamilyContext::ConstructionValues(
                VPClient->Viewport,
                VPClient->GetScene(),
                VPClient->EngineShowFlags)
                .SetRealtimeUpdate(VPClient->IsRealtime())
            );

            // get the return data
            if (FSceneView* SceneView = VPClient->CalcSceneView(&ViewFamily))
            {
                VPClient->Viewport->GetMousePos(MousePosition, true);
                ScreenPos.X = MousePosition.X;
                ScreenPos.Y = MousePosition.Y;
                SceneView->DeprojectFVector2D(ScreenPos, WorldOrigin, WorldDirection);
                return true;
            }
        }
    }

    UE_LOG(LogTemp, Warning, TEXT("Could not find a valid viewport under the mouse"));
    return false;
}

void
USimpleAssetLibraryBPLibrary::RegisterMetadataTags(const TArray<FName>& Tags)
{
    TSet<FName>& GlobalTagsForAssetRegistry = UObject::GetMetaDataTagsForAssetRegistry();
    for (FName Tag : Tags)
    {
        if (!Tag.IsNone())
        {
            if (!GlobalTagsForAssetRegistry.Contains(Tag))
            {
                GlobalTagsForAssetRegistry.Add(Tag);
            }
        }
    }
}

void
USimpleAssetLibraryBPLibrary::AddExistingAssetThumbnailToDynamicMaterial(
    UMaterialInstanceDynamic* DynamicMaterial,
    int32& ImageWidth,
    int32& ImageHeight,
    bool& IsValid,
    const FAssetData& AssetData,
    UTexture2D* DefaultTexture
)
{
    /* thanks to 3dRaven on this method
     * https://forums.unrealengine.com/t/getting-asset-thumbnails-as-a-texture2d/1180079/2
     */

    FString PackageFilename;
    const FName ObjectFullName = FName(*AssetData.GetFullName());
    TSet<FName> ObjectFullNames;
    ObjectFullNames.Add(ObjectFullName);

    if (AssetData.PackageName.ToString() != "None" && FPackageName::DoesPackageExist(AssetData.PackageName.ToString(), &PackageFilename))
    {
        FThumbnailMap ThumbnailMap;
        ThumbnailTools::LoadThumbnailsFromPackage(PackageFilename, ObjectFullNames, ThumbnailMap);
        FObjectThumbnail* Thumbnail = ThumbnailMap.Find(ObjectFullName);

        IImageWrapperModule& ImageWrapperModule = FModuleManager::Get().LoadModuleChecked<IImageWrapperModule>(TEXT("ImageWrapper"));
        TSharedPtr<IImageWrapper> ImageWrapper = ImageWrapperModule.CreateImageWrapper(EImageFormat::PNG);

        ImageWidth = Thumbnail->GetImageWidth();
        ImageHeight = Thumbnail->GetImageHeight();

        ImageWrapper->SetRaw(
            Thumbnail->GetUncompressedImageData().GetData(),
            Thumbnail->GetUncompressedImageData().Num(),
            ImageWidth,
            ImageHeight,
            ERGBFormat::BGRA, 8
        );

        const TArray64<uint8>& CompressedByteArray = ImageWrapper->GetCompressed();
        UTexture2D* ThumbnailTexture = FImageUtils::ImportBufferAsTexture2D(CompressedByteArray);
        DynamicMaterial->SetTextureParameterValue("texture", ThumbnailTexture);
    }
    else{
        DynamicMaterial->SetTextureParameterValue("texture", DefaultTexture);
    }
}

void
USimpleAssetLibraryBPLibrary::RenderAssetThumbnailToDynamicMaterial(
    UMaterialInstanceDynamic* DynamicMaterial,
    int32& ImageWidth,
    int32& ImageHeight,
    bool& IsValid,
    const FAssetData& AssetData,
    UTexture2D* DefaultTexture
)
{
    /* thanks to 3dRaven and NanceDevDiaries for all the important stuff in here (links below)
     * this function will populate the Dynamic Material in the following priority:
     *     1) Generate a new thumbnail if possible (helps to show animated materials)
     *     2) Fallback to the asset's existing thumbnail if the asset is valid
     *     3) Default to the provided Default Texture if the asset isn't valid
     * https://forums.unrealengine.com/t/getting-asset-thumbnails-as-a-texture2d/1180079/2
     * https://github.com/NanceDevDiaries/Tutorials/blob/main/ThumbnailToTextureToolTutorial/LyraEditor.cpp
     */
    IsValid = false;

    // validate the asset exists
    FString PackageFilename;
    FObjectThumbnail* thumb;
    if (AssetData.PackageName.ToString() != "None") {
        if (FPackageName::DoesPackageExist(AssetData.PackageName.ToString(), &PackageFilename)){
            IsValid = true;
        }
    }

    // If the asset is valid, attempt to generate the thumbnail and make sure it's usable
    if (IsValid) {
        thumb = ThumbnailTools::GenerateThumbnailForObjectToSaveToDisk(AssetData.GetAsset());
        ImageWidth = 0;
        ImageHeight = 0;
        if (thumb){
            ImageWidth = thumb->GetImageWidth();
            ImageHeight = thumb->GetImageHeight();
        }
        if (ImageWidth < 1 || ImageHeight < 1) {
            ImageWidth = 1;
            ImageHeight = 1;
            IsValid = false;
        }

        // Prepare the transient texture
        UTexture2D* ThumbnailTexture = UTexture2D::CreateTransient(ImageWidth, ImageHeight, PF_B8G8R8A8);
        if (ThumbnailTexture == nullptr) {
            IsValid = false;
        }

        // If everything is valid, Populate the thumbnail into the transient texture
        if (IsValid) {
            uint8* MipData = (uint8*)ThumbnailTexture->GetPlatformData()->Mips[0].BulkData.Lock(LOCK_READ_WRITE);
            TArray<uint8> RawData = thumb->GetUncompressedImageData();
            FMemory::Memcpy(MipData, RawData.GetData(), RawData.Num());

            ThumbnailTexture->bNotOfflineProcessed = true;
            ThumbnailTexture->GetPlatformData()->Mips[0].BulkData.Unlock();
            ThumbnailTexture->UpdateResource();
            ThumbnailTexture->AddToRoot();

            // apply the texture to dynamic material
            DynamicMaterial->SetTextureParameterValue("texture", ThumbnailTexture);
            return;
        }

    }

    // If any issues were encountered, try to get the existing default thumbnail for the asset instead
    const FName ObjectFullName = FName(*AssetData.GetFullName());
    TSet<FName> ObjectFullNames;
    ObjectFullNames.Add(ObjectFullName);

    // If the asset exists, get its existing static thumbnail
    if (AssetData.PackageName.ToString() != "None" && FPackageName::DoesPackageExist(AssetData.PackageName.ToString(), &PackageFilename))
    {
        FThumbnailMap ThumbnailMap;
        ThumbnailTools::LoadThumbnailsFromPackage(PackageFilename, ObjectFullNames, ThumbnailMap);
        FObjectThumbnail* DefaultThumb = ThumbnailMap.Find(ObjectFullName);

        IImageWrapperModule& ImageWrapperModule = FModuleManager::Get().LoadModuleChecked<IImageWrapperModule>(TEXT("ImageWrapper"));
        TSharedPtr<IImageWrapper> ImageWrapper = ImageWrapperModule.CreateImageWrapper(EImageFormat::PNG);

        ImageWidth = DefaultThumb->GetImageWidth();
        ImageHeight = DefaultThumb->GetImageHeight();

        ImageWrapper->SetRaw(
            DefaultThumb->GetUncompressedImageData().GetData(),
            DefaultThumb->GetUncompressedImageData().Num(),
            ImageWidth,
            ImageHeight,
            ERGBFormat::BGRA, 8
        );

        const TArray64<uint8>& CompressedByteArray = ImageWrapper->GetCompressed();
        UTexture2D* ThumbnailTexture = FImageUtils::ImportBufferAsTexture2D(CompressedByteArray);
        DynamicMaterial->SetTextureParameterValue("texture", ThumbnailTexture);
        IsValid = true;
        return;
    }

    // Final fallback, use the provided default texture if the asset appears invalid
    DynamicMaterial->SetTextureParameterValue("texture", DefaultTexture);
}

void
USimpleAssetLibraryBPLibrary::Log(FString message)
{
    UE_LOG(AssetLibrary, Log, TEXT("%s"), *message);
}


void
USimpleAssetLibraryBPLibrary::Warning(FString message)
{
    UE_LOG(AssetLibrary, Warning, TEXT("%s"), *message);
}


void
USimpleAssetLibraryBPLibrary::Error(FString message)
{
    UE_LOG(AssetLibrary, Error, TEXT("%s"), *message);
}
