#!/bin/sh

target=debug
if [ "$1" = "target=release"] || [ "$1" = "target=template_release" ] ; then
    target=release
fi

gdeos_ios_bin_dir=./demo/addons/gd-eos/bin/ios
godotcpp_bin_dir=./godot-cpp/bin

# Delete existing libgodot-cpp xcframework if any
rm -rf ${gdeos_ios_bin_dir}/libgodot-cpp.ios.template*

# Create libgodot-cpp xcframework
xcodebuild -create-xcframework \
-library ${godotcpp_bin_dir}/libgodot-cpp.ios.template_${target}.arm64.a \
-output ${gdeos_ios_bin_dir}/libgodot-cpp.ios.template_${target}.xcframework
# -library ${godotcpp_bin_dir}/libgodot-cpp.ios.template_${target}.arm64.simulator.a \

# Create libgdeos xcframework
xcodebuild -create-xcframework \
-library ${gdeos_ios_bin_dir}/libgdeos.ios.template_${target}.arm64.dylib \
-output ${gdeos_ios_bin_dir}/libgdeos.ios.template_${target}.xcframework
# -library ${gdeos_ios_bin_dir}/libgdeos.ios.template_${target}.arm64.simulator.dylib \

# Delete all .dylib from gdeos ios bin dir
rm -rf ${gdeos_ios_bin_dir}/*.dylib