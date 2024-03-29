# GD-EOS

[Click here to refer English Readme](README.md).

适用于Godot的**Epic Online Services**。可作为**C++ SDK**或者编译后作为**GDScript SDK**。

## 特性

1. Godot风格的面向对象,所有的接口均尽可能的类型化。
2. 几乎所有的接口都是从 EOS 的 C SDK 生成，你可以直接查看 Epic Online Services 的文档。
3. 用于Godot多人网络的`EOSMultiplayerPeer`。

## 赞助

这个项目花费了我大量时间和经历，如果该项目对你有用的话，请考虑为我[充电](https://afdian.net/a/Daylily-Zeleen)。

## 如何开始

1. 获取`GD-EOS`插件:
   - 在Release页面下载预编译的插件。
   - 克隆该仓库自行编译。
2. 像通常的Godot插件一样安装即可。

## 如何编译

1. 将该仓库克隆到本地（包含子模块 godot-cpp）。
2. 从Epic开发者门户下载EOS的C SDK，并将其置于目录"thirdparty/eos-sdk"下（因为我没有重新分发的权利）.
3. [配置你的开发环境](https://docs.godotengine.org/en/latest/contributing/development/compiling/index.html#building-for-target-platforms). 换句话说，你需要`python3`, `scons`, 以及一个合适的c++编译器。如果你需要为Android编译，你还需要NDK。
4. 在命令中导航到该项目根目录下，并允许下方命令:
    - For debug build:

        ``` shell
            scons platform=windows target=template_debug dev_build=yes
        ```

    - For release build:

        ``` shell
            scons platform=windows target=template_release
        ```

    关于更多编译命令的细节，请参考 godot-cpp 的编译系统。
5. 在编译完成后，你将在 "test_project/addons/gd-eos/"获得该插件。

## **注意**

该仓库缺乏测试，请不要用于你的发布项目中。
尤其是安卓构建，它可能完全不起作用。

## TODO

1. 检测常量并为他们生成Godot绑定。
2. 检测废弃成员代替目前生成器中的硬编码。
3. 为c++开发者生成类型化的回调接口（代替直接使用Callable）。
4. 添加IOS构建

## 其他

1. 感谢Delano Lourenco。目前的Godot多人网络机制是基于该仓库[epic-online-servies-godot](https://github.com/3ddelano/epic-online-services-godot)实现。
2. 欢迎提交任何bug修复或功能优化的pr。
