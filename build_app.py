import os
import sys
import shutil
import platform
import subprocess
import PyInstaller.__main__

def build():
    app_name = "NoBG"
    main_script = "flet_app.py"
    
    # Clean dist/build
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    if os.path.exists("build"):
        shutil.rmtree("build")

    # Raw PyInstaller arguments
    # We replicate flet pack's important flags but skip its signing/wrapping logic
    pyi_args = [
        main_script,
        "--noconfirm",
        "--clean",
        "--name", app_name,
        "--onedir", # Use onedir to avoid onefile signing issues and improve startup time
        "--windowed", # Start as GUI app (suppresses console)
        "--icon", "assets/icon.icns",
        
        # Data and Imports
        "--add-data", "app:app",
        # "--add-data", "models:models", # Skip huge model copy to save space/time, we do it manually
        
        "--hidden-import", "transformers",
        "--hidden-import", "torch",
        "--hidden-import", "torchvision",
        "--hidden-import", "PIL",
        "--hidden-import", "numpy",
        "--hidden-import", "huggingface_hub",
        "--hidden-import", "flet",
        "--hidden-import", "kornia",
        "--hidden-import", "kornia.geometry",
        "--hidden-import", "kornia.filters",
        "--hidden-import", "timm",
        "--hidden-import", "timm.models",
        "--hidden-import", "timm.models.layers",
        "--hidden-import", "timm.models.registry",
        "--hidden-import", "timm.layers",
        "--hidden-import", "timm.models.vision_transformer",
        "--hidden-import", "timm.models.resnet",
        "--hidden-import", "timm.models.efficientnet",
        "--hidden-import", "timm.data",
        "--hidden-import", "timm.optim",
        "--hidden-import", "timm.scheduler",
        "--hidden-import", "kornia.enhance",
        "--hidden-import", "flet.platform",
    ]

    print(f"Building {app_name} using raw PyInstaller (onedir)...")
    PyInstaller.__main__.run(pyi_args)
    
    # Post-build: Patch the bundle that PyInstaller created
    if platform.system() == "Darwin":
        print("Patching macOS App Bundle...")
        app_bundle = f"dist/{app_name}.app"
        contents = os.path.join(app_bundle, "Contents")
        macos_dir = os.path.join(contents, "MacOS")
        resources = os.path.join(contents, "Resources")
        
        if not os.path.exists(app_bundle):
            print(f"Error: {app_bundle} not found. PyInstaller failed to create bundle.")
            return

        # Manually copy 'models' to Contents/Resources/models
        # This saves disk space during build (1.3GB) and satisfies codesign
        print("Copying models manually to bundle Resources...")
        if os.path.exists("models"):
            dest_models = os.path.join(resources, "models")
            if os.path.exists(dest_models):
                shutil.rmtree(dest_models)
            shutil.copytree("models", dest_models)
            
        # Patch Info.plist
        print("Patching Info.plist...")
        import plistlib
        plist_path = os.path.join(contents, "Info.plist")
        
        if os.path.exists(plist_path):
            with open(plist_path, "rb") as f:
                plist = plistlib.load(f)
            
            # Update key identifiers and versions
            plist["CFBundleIdentifier"] = "com.winter.nobg"
            plist["LSMinimumSystemVersion"] = "12.0"
            plist["LSUIElement"] = False # Revert to False so window appears on double-click
            
            with open(plist_path, "wb") as f:
                plistlib.dump(plist, f)

    # Post-build: Re-sign the app (ad-hoc)
    print("Re-signing application...")
    try:
        subprocess.check_call(["xattr", "-rc", f"dist/{app_name}.app"])
        subprocess.check_call(["codesign", "--force", "--deep", "--sign", "-", f"dist/{app_name}.app"])
    except subprocess.CalledProcessError as e:
        print(f"Warning: Signing failed: {e}")

    # Final cleanup: Remove the redundant onedir directory if the .app bundle exists
    raw_dist_dir = f"dist/{app_name}"
    if os.path.exists(raw_dist_dir) and os.path.isdir(raw_dist_dir) and os.path.exists(f"dist/{app_name}.app"):
        print(f"Cleaning up redundant directory {raw_dist_dir}...")
        shutil.rmtree(raw_dist_dir)

    print("Build complete!")
    print(f"App Bundle is at dist/{app_name}.app")

if __name__ == "__main__":
    build()
