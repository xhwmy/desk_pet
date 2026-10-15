# 赤焰：六种待机动作

使用内置 ImageGen 生成了理头发、整理衣领、抱膝打盹、伸懒腰、敲小键盘、左右探头，每套六个源姿势。提示词及原图保存在各动作目录。理头发复用正确的同手姿势，跳过换手的源帧；衣领素材依据透明像素低谷分隔相邻发梢后，再由插件脚本提取。

## 已安装的原生版本

- `final/chiyan-native-six-poses.webp`：六个关键姿势占用原生待机的六个帧位，约 6.6 秒一轮。
- `final/native-six-poses.gif`：实际原生轮播预览。
- `final/native-stored-readback.png`：更新后从服务器重新下载的文件。
- `final/native-stored-verification.json`：确认回读像素完全相同、六个待机姿势各不相同。
- 原有赤焰 ID `pet_6abb898c7228819191b6e896f2538d5d` 已更新并选为激活宠物，没有创建副本。

原生上传路径将动画 WebP 转为静态 PNG。因此，当前实际安装的是六个关键姿势轮播，**不是六套完整连续动画**。没有修改应用程序或添加后台播放器。

## 完整连续动画素材

- `final/chiyan-six-idles.webp`：48 个时间帧，约 28.43 秒，无限循环的完整 v2 图集。
- `final/six-idles.gif`：完整待机动画预览。
- `final/six-idles-contact.png`：六套动作逐帧检查图。
- `qa/previews/all-states.gif` / `.mp4`：全部状态预览。
- `final/stored-readback.webp` 与 `stored-verification.json`：首次动画上传后被转为单帧的验证记录；已被上面的原生六姿势版本替换。

沿用原来的任务、移动及十六个看向动作。整包校验发现旧跳跃帧被分别缩放、落在同一高度，已根据原始 jumping.png 的共享几何位置恢复腾空轨迹；使用原来已清理的像素，没有重画。其余任务和看向帧保留。

## 验证和复现

`build_loops.py` 调用 work-pets 插件自带的拆帧、检查、去溢色、合成和质量验证脚本。动画编码采用精确保留透明像素的 WebP 帧封装。`build_native.py` 从已验收素材生成当前原生六姿势版本。

`qa/native/atlas-validation.json` 与 `qa/native/pet-quality.json` 均通过；Pets 官方预检也通过。Library 保存工具在本次会话不可用，所有原图、提示、QA 和预览均保存在本目录。

重建需要 Python 3.10+ 和已安装的 work-pets 插件。安装依赖后依次运行：

```powershell
python -m pip install -r animations/idle-six/requirements.txt
python animations/idle-six/build_loops.py
python animations/idle-six/build_native.py
python animations/idle-six/self_check.py
```

脚本会从当前用户的 Codex 插件缓存寻找工具目录，也可通过 `WORK_PETS_SCRIPTS` 指定插件的 `skills/create-pet/scripts` 路径。依赖未提交到仓库；所有生成素材已经保存，重建不需要重新调用图片生成服务，也不会自动修改云端桌宠。

`self_check.py` 使用 `final/native-stored-readback.png` 核对已下载的云端版本，检查六个动作的对应关系、预览节奏、48 帧时间线及任务状态是否保持稳定，并生成 `qa/self-check.json`。要验证后续云端更新，应先用 Pets 工具重新下载该文件。
