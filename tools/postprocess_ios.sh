#!/bin/sh

build_target=debug
if [ "$1" = "target=release" ] || [ "$1" = "target=template_release" ]; then
    build_target=release
fi

gdeos_ios_bin_dir=./demo/addons/gd-eos/bin/ios
godotcpp_bin_dir=./thirdparty/godot-cpp/bin

# Delete existing target-independent xcframeworks if any
rm -rf "${gdeos_ios_bin_dir}/libgodot-cpp.ios.xcframework"
rm -rf "${gdeos_ios_bin_dir}/libgdeos.ios.xcframework"

# Create libgodot-cpp xcframework
xcodebuild -create-xcframework \
-library "${godotcpp_bin_dir}/libgodot-cpp.ios.template_${build_target}.arm64.a" \
-output "${gdeos_ios_bin_dir}/libgodot-cpp.ios.xcframework"

# Create libgdeos xcframework
xcodebuild -create-xcframework \
-library "${gdeos_ios_bin_dir}/libgdeos.ios.arm64.dylib" \
-output "${gdeos_ios_bin_dir}/libgdeos.ios.xcframework"

# Delete the intermediate dylib from the plugin directory
rm -f "${gdeos_ios_bin_dir}/libgdeos.ios.arm64.dylib"
