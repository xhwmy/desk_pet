# 赤焰：轻呼吸、发梢摆动与眨眼待机

在现有站姿上新增的一套连贯待机，已更新原有赤焰 `pet_6abb898c7228819191b6e896f2538d5d`，保持激活。使用内置 ImageGen，按下载的当前图集及待机行保持角色身份，生成一个六帧横条；没有修改 Codex 客户端。

六帧顺序：放松站立 → 浅吸气、发梢轻轻展开 → 眼睑半闭 → 轻呼气、闭眼 → 睁眼回落 → 放松站立。原生按 `[1680,660,660,840,840,1920]` 毫秒播放，总计约 6.6 秒，循环。动作幅度刻意控制很小。原生只支持一行六帧待机，本次增强当前待机，不表示多套动作随机切换；此前所有版本仍保留。

![实际原生节奏预览](previews/idle.gif)

- `decoded/idle.png`：生成的原始横条。
- `prompt.txt`：实际使用的完整提示词；工具为内置 `image_gen`。
- `before.png`、`current-idle-reference.png`：更新前下载图集与角色参考。
- `generation/`：work-pets 生成计划及布局参考。仅执行 idle 行生成，已有基础角色、任务行及看向行直接复用。
- `chiyan-native-breath.webp`：最终上传的静态 v2 图集。
- `stored-readback.png`：更新后重新下载的云端图集，与最终图集逐像素一致。
- `previews/`：九种状态 GIF、看向循环、待机到跳跃循环及全状态 MP4。
- `qa/self-check.json`：17 项检查全部通过。六帧脚底基线相同，首尾轮廓交并比约 97.9%；所有任务和看向行与更新前完全相同。
- `qa/official-preflight.json`、`qa/pet-quality.json`：官方预检与插件质量门禁通过。

拆帧、去底、去溢色、合成和门禁使用 work-pets 插件自带工具。整行采用共享缩放，额外仅平移 1–2 像素校正脚底取整误差，避免逐帧缩放导致身体忽大忽小。Library 工具当前不可用，素材、预览、QA 均保存在项目中。

重建需要 Python 3.10+、`../idle-six/requirements.txt` 的依赖和已安装的 work-pets 插件（或设置 `WORK_PETS_SCRIPTS`），运行 `python animations/idle-breath-2026-10-16/build.py`。验证云端更新后，先通过 Pets 工具重新下载为 `stored-readback.png`，再运行 `python animations/idle-breath-2026-10-16/self_check.py`。脚本不会自动上传或切换宠物。
