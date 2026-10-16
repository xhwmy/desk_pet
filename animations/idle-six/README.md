# 赤焰：六种待机动作

使用内置 ImageGen 生成了理头发、整理衣领、抱膝打盹、伸懒腰、敲小键盘、左右探头，每套六个源姿势。提示词及原图保存在各动作目录。理头发复用正确的同手姿势，跳过换手的源帧；衣领素材依据透明像素低谷分隔相邻发梢后，再由插件脚本提取。

## 已安装的原生版本

- `calm/chiyan-native-calm.webp`：恢复已批准的六帧连贯站姿待机及眨眼，约 6.6 秒一轮。
- `calm/previews/idle.gif`：按已安装客户端的实际帧时长生成的预览。
- `calm/stored-readback.png`：本次更新后从服务器重新下载的文件。
- `calm/self-check.json`：核对云端回读、连贯待机来源、脚底高度、原有任务及看向帧均保持不变。
- 原有赤焰 ID `pet_6abb898c7228819191b6e896f2538d5d` 已更新并选为激活宠物，没有创建副本。

上一版把六套动作各抽一帧放进待机循环，导致站立、坐下、伸懒腰等姿势直接跳切，已按用户选择撤回这种轮播。旧版文件 `final/chiyan-native-six-poses.webp` 和对应报告保留作历史记录，不再代表当前安装版本。

只读检查当前安装客户端的 `Ccc`、`kcc`、`Rcc` 播放逻辑，待机六帧固定循环，时长为 `[1680,660,660,840,840,1920]` 毫秒；没有发现可配置的 30 秒随机动作调度。原生上传路径还会将动画 WebP 转为静态 PNG。用户选择保留官方客户端，先恢复柔和待机，因此本次没有修改应用程序或添加后台播放器。六套完整动作仍作为素材保留。

## 完整连续动画素材

- `final/chiyan-six-idles.webp`：48 个时间帧，约 28.43 秒，无限循环的完整 v2 图集。
- `final/six-idles.gif`：完整待机动画预览。
- `final/six-idles-contact.png`：六套动作逐帧检查图。
- `qa/previews/all-states.gif` / `.mp4`：全部状态预览。
- `final/stored-readback.webp` 与 `stored-verification.json`：首次动画上传后被转为单帧的验证记录；已被上面的原生六姿势版本替换。

沿用原来的任务、移动及十六个看向动作。整包校验发现旧跳跃帧被分别缩放、落在同一高度，已根据原始 jumping.png 的共享几何位置恢复腾空轨迹；使用原来已清理的像素，没有重画。其余任务和看向帧保留。

## 验证和复现

`build_loops.py` 调用 work-pets 插件自带的拆帧、检查、去溢色、合成和质量验证脚本。动画编码采用精确保留透明像素的 WebP 帧封装。`build_native.py` 重建已撤回的六姿势版本；`build_calm_idle.py` 重建当前柔和待机。

当前版本的 `calm/atlas-validation.json`、`calm/pet-quality.json` 和 `calm/official-preflight.json` 均通过。Library 保存工具在本次会话不可用，所有原图、提示、QA 和预览均保存在本目录。

重建需要 Python 3.10+ 和已安装的 work-pets 插件。安装依赖后依次运行：

```powershell
python -m pip install -r animations/idle-six/requirements.txt
python animations/idle-six/build_loops.py
python animations/idle-six/build_native.py
python animations/idle-six/self_check.py
```

以上命令重建历史六动作预览及旧版六姿势图集。重建当前柔和待机：先通过 Pets 工具获取当前精灵图，将下载内容保存为 `animations/idle-timing-review/before-update.png`，再运行 `python animations/idle-six/build_calm_idle.py`。仅替换首行前六格，其余像素保留。上传并重新下载为 `calm/stored-readback.png` 后，运行 `python animations/idle-six/self_check_calm.py` 验证。

脚本会从当前用户的 Codex 插件缓存寻找工具目录，也可通过 `WORK_PETS_SCRIPTS` 指定插件的 `skills/create-pet/scripts` 路径。依赖未提交到仓库；所有生成素材已经保存，重建不需要重新调用图片生成服务，也不会自动修改云端桌宠。

`self_check.py` 和 `qa/self-check.json` 验证历史六姿势与完整动画素材。当前安装版本以 `self_check_calm.py` 和 `calm/self-check.json` 为准；后续云端更新应先重新下载对应回读文件。
