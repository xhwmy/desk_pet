# 赤焰 Windows 独立桌宠

这是 Codex 内置桌宠“赤焰”的独立 Windows 版本。角色素材直接取自 `../codex-pet/chiyan/package/spritesheet.webp`；`assets/spritesheet.webp` 是原样复制，`assets/spritesheet.png` 是其解码后的像素等价 PNG，供独立程序加载。Codex 内置宠物和旧版 `windows-standalone/` 均不受影响。

## 使用

将 `Chiyan-DesktopPet.exe` 拷贝到任意位置，双击运行。适用 64 位 Windows 10/11；无需安装 Python、PyQt、Codex 或联网。首次启动单文件程序需要临时解包，可能稍慢。

- 左键拖动；双击跳跃。
- 右键可挥手、跳跃、朝鼠标走、等待、认真思考、暂停自动活动、调整大小、重置位置或退出。
- 靠近宠物时，它会朝鼠标方向看；空闲时会随机活动。
- 托盘图标可操作，双击托盘图标可找回宠物。
- 位置、大小和暂停状态会记住。

截图底部的按钮属于 Codex 应用界面，不是宠物素材；此程序提供自己的右键和托盘菜单。

## 开发构建

开发电脑安装 Python 后，在本目录运行：

```powershell
python -m pip install -r requirements-build.txt
.\build.bat
```

输出为 `dist/Chiyan-DesktopPet.exe`。构建工具只在开发电脑上需要。
