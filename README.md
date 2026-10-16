# 赤焰桌宠

- `animations/idle-six/`：当前柔和待机、六种动作素材、完整动画预览和自检报告，见[制作说明](animations/idle-six/README.md)。
- `designs/idle-2026-10-15/`：三套待机动作设计稿和生成提示词。
- `codex-pet/chiyan/`：Codex 内置宠物的原始素材与制作资料。
- `windows-chiyan/`：使用同一角色精灵图的独立 Windows 桌宠源码。
- `windows-chiyan/release/Chiyan-DesktopPet-Windows-x64.zip`：解压后双击 EXE 即可运行，无需安装 Python 或 Codex。

当前原生版本恢复为同一站姿的柔和待机和眨眼，约 6.6 秒一轮，避免六种大动作关键姿势连续跳切。保持官方客户端，未添加“每 30 秒随机动作”的播放功能；当前安装版本的原生播放器不提供该配置。六套动作和 28.43 秒完整动画仍保留为素材和预览。

![当前原生柔和待机](animations/idle-six/calm/previews/idle.gif)

操作、构建方式和两者的区别见 [独立版说明](windows-chiyan/README.md)。
