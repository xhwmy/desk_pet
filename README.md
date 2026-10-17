# 赤焰桌宠

- `dragon-codex-boot/duo/`：Bamboo Duo 客户端内部壁纸与自动加载，见[壁纸说明](dragon-codex-boot/duo/README.md)。外部开屏已移除，保留原生启动界面。
- `animations/native-motion-2026-10-17/`：内置赤焰当前挥手和跳跃优化，保留原 ID、轻呼吸待机及十六方向，见[更新说明](animations/native-motion-2026-10-17/README.md)。
- `animations/idle-breath-2026-10-16/`：当前轻呼吸、发梢摆动和眨眼待机，见[制作说明](animations/idle-breath-2026-10-16/README.md)。
- `animations/idle-six/`：此前柔和待机、六种动作素材、完整动画预览和自检报告，见[历史制作说明](animations/idle-six/README.md)。
- `designs/idle-2026-10-15/`：三套待机动作设计稿和生成提示词。
- `codex-pet/chiyan/`：Codex 内置宠物的原始素材与制作资料。
- `windows-chiyan/`：使用同一角色精灵图的独立 Windows 桌宠源码。
- `windows-chiyan/release/Chiyan-DesktopPet-Windows-x64.zip`：解压后双击 EXE 即可运行，无需安装 Python 或 Codex。

当前原生版本保留同一站姿的轻呼吸、发梢摆动和眨眼，约 6.6 秒一轮，并优化挥手衔接与跳跃落地体型。保持官方客户端，未添加“每 30 秒随机动作”的播放功能；当前安装版本的原生播放器不提供该配置。此前待机版本、六套动作和 28.43 秒完整动画仍保留为素材和预览。

![当前原生轻呼吸待机](animations/idle-breath-2026-10-16/previews/idle.gif)

操作、构建方式和两者的区别见 [独立版说明](windows-chiyan/README.md)。
