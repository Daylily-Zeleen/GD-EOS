#!/bin/sh

build_target=debug
if [ "$1" = "target=release" ] || [ "$1" = "target=template_release" ]; then
    build_target=release
fi

gdeos_ios_bin_dir=./demo/addons/gd-eos/bin/ios

# Delete existing target-independent xcframeworks if any
rm -rf "${gdeos_ios_bin_dir}/libgdeos.ios.xcframework"

# NOTE: libgodot-cpp is statically linked into libgdeos.ios.arm64.dylib
# (godot-cpp is built as a static library and linked via the SConscript env),
# so we do NOT distribute a separate libgodot-cpp xcframework anymore.
# CI verifies the dylib has no undefined godot-cpp symbols before this step.

# Create libgdeos xcframework
xcodebuild -create-xcframework \
-library "${gdeos_ios_bin_dir}/libgdeos.ios.arm64.dylib" \
-output "${gdeos_ios_bin_dir}/libgdeos.ios.xcframework"

# Delete the intermediate dylib from the plugin directory
rm -f "${gdeos_ios_bin_dir}/libgdeos.ios.arm64.dylib"
