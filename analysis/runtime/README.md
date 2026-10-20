# 原 ROM 的完整 NES 核心回放

`scripts/nes_runtime.py` 通过 libretro C API 使用 Nestopia，提供实际 PPU/IRQ/framebuffer 渲染、手柄输入、RAM/SRAM快照和 save state。它不是第一轮的简化 py65 CPU 模型。

来源：[libretro Nestopia](https://github.com/libretro/nestopia)，核心包下载自 [libretro 官方 arm64 构建目录](https://buildbot.libretro.com/nightly/apple/osx/arm64/latest/)。本次下载文件名为 `nestopia_libretro.dylib.zip`，仅解压到本项目 `.toolchain/nestopia/`，没有安装到系统或使用其他游戏资源。

核心身份：Nestopia 2.0.0 `135dfa6`；dylib SHA-256 `924191ebb41b863993a96cf461321058b391c507a6fed2f1203df44eaa5a539a`。本目录每张截图旁的 JSON 记录 ROM/core 摘要、options、输入帧序列、内存长度和限制。save state 依赖此核心版本；下载站的当前构建可能更新，因此重新获取时应核对身份，不把不同 core 的 state 默认为兼容。

复现从冷启动开始的完整输入计划：

```sh
python3 scripts/nes_runtime.py '/Users/paulasmith/Downloads/三国志2超级版.nes' \
  --plan analysis/runtime/replay-original-ui.json --out analysis/runtime/replayed --label officer-list
```

计划通过原游戏界面进入一人游戏、LEVEL1、曹操、兗州菜单与武器店；`game-start.png` 为选择曹操之前的刘备详情，`military-selection.png` 为实际属性列表。输入步骤仅操作虚拟控制器，没有写入模拟 RAM/ROM 以伪造界面。

关闭 composite filter 和 overscan 后保存256×240原生像素；palette 是固定的 Nestopia Royaltea 设置，不能当作物理电视颜色测量。音频 callback 接收但不保存输出，因此本报告没有声音内容验证。

`*.ram.bin` / `*-ram.bin` 是实际 CPU RAM，`*-sram.bin` 是实际 external RAM，`.state` 是模拟器原生序列化状态。后续从已有状态运行时，JSON中的帧数是这次导入后的运行帧数，父状态路径/摘要保留在事件里；完整冷启动回放计划用来补足全部前置输入。`validation.json` 对照了冷启动回放和逐状态继续运行的像素与 RAM/SRAM。

冷启动串接回放与分段导入状态回放在三个检查点的像素、SRAM 相同；CPU RAM 在刘备详情/属性列表分别有9/20字节不同，主要集中在栈区，另包含 RNG 游标。完整差异保存在 `validation.json`，原因尚未全部隔离，所以不能声称两条回放路径全部内部状态相同。

这些证据建立了原 ROM 在指定模拟器中的显示/输入行为，不宣称物理卡带、整套战斗动画、音频或全部游戏流程已验证。
