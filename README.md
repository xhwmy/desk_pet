# 赤焰桌宠

- `animations/idle-six/`：六种待机动作、原生轮播图集、完整动画预览和自检报告，见[制作说明](animations/idle-six/README.md)。
- `designs/idle-2026-10-15/`：三套待机动作设计稿和生成提示词。
- `codex-pet/chiyan/`：Codex 内置宠物的原始素材与制作资料。
- `windows-chiyan/`：使用同一角色精灵图的独立 Windows 桌宠源码。
- `windows-chiyan/release/Chiyan-DesktopPet-Windows-x64.zip`：解压后双击 EXE 即可运行，无需安装 Python 或 Codex。

当前原生版本将六个待机关键姿势自动轮播，约 6.6 秒一轮。完整连续动画为 28.43 秒；原生上传路径会把动画文件转成静态图，因此完整动画目前仅作为素材和预览保存。

![原生六姿势轮播](animations/idle-six/final/native-six-poses.gif)

操作、构建方式和两者的区别见 [独立版说明](windows-chiyan/README.md)。
