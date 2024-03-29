# GD-EOS

[点击查中文说明](README.zh.md)

**Epic Online Services** for Godot. Use as **C++ SDK** or compile as **GDScript SDK**.

## Feature

1. OOP and Godot Style, all APIs have been typed as far as possible.
2. Almost APIs are generated from EOS C SDK, you can refer Epic Online Services document directly.
3. `EOSMultiplayerPeer` for godot multiplayer.

## Support Me

This project is cost a lot of time and effort, if it can help you, please [by me a coffee](https://afdian.net/a/Daylily-Zeleen).

## How to start

1. Get `GD-EOS` plugin:
   - Download pre-compiled plugin from release page.
   - Compile by yourself.
2. Install it like regular Godot plugin.

## How to compile

1. Clone this repo with submodule (godot-cpp).
2. Download EOS C SDK from Epic Developer Portal, and place is at "thirdparty/eos-sdk". (Because I have not right to redistribute it).
3. [Setup your enviroment](https://docs.godotengine.org/en/latest/contributing/development/compiling/index.html#building-for-target-platforms). In orther words, you need `python3`, `scons`, and an appropriate c++ compiler. Additionally, you need ndk to compile for android.
4. Navigate to this project root, and run commands below:
    - For debug build:

        ``` shell
            scons platform=windows target=template_debug dev_build=yes
        ```

    - For release build:

        ``` shell
            scons platform=windows target=template_release
        ```

    More detail of compile commands, please refer to godot-cpp's compile system.
5. Last, you can get the compiled addon which is localed at "test_project/addons/gd-eos/".

## **Cautious**

This repo is lack of testing. Don't use this for your release project.
Expacially andriod build, it may not work at all.

## TODO

1. Detect constants and generate their binding to godot.
2. Detect deprecated menbers instead of heard codeing.
3. Generate typed callback apis for c++ user.
4. Add ios build.

## Others

Thanks to Delano Lourenco.The Godot multiplayer mechanism is base on [epic-online-servies-godot](https://github.com/3ddelano/epic-online-services-godot).
