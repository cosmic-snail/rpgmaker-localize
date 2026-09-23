---
name: rpgmaker-localize
description: RPG Maker MV/MZ 游戏汉化与音频改造全流程。用于: (1) 加载/清洗 MTool 格式翻译 JSON(含占位条目清理、多行条目拆行补充), (2) 离线注入式汉化(直接改写 data/*.json, 带资源名/插件命令/脚本保护规则), (3) RPG Maker 加密音频(.ogg_/.rpgmvo)解密提取与重新加密替换, (4) 给游戏安装自动配音插件(战斗喊声/CG触发/剧情关键词), (5) MV 与 MZ 引擎差异排错。触发词: RPG Maker 汉化、MTool 翻译文件、游戏配音、.ogg_ 解密、指名/热带追逐类游戏改造。
---

# RPG Maker MV/MZ 游戏汉化与音频改造

## 第一步:判断引擎与结构

- 目录有 `www/` 子目录 + `www/data/System.json` → **MV**;直接 `data/System.json` → **MZ**
- 两者加密格式相同,只是密钥不同(都存在 `System.json` 的 `encryptionKey`,32 位十六进制)
- 翻译文件通常是 MTool 格式 `{"原文": "译文"}`,可能在游戏根目录(`.json`)或由 MTool 工具目录管理

## 第二步:清洗翻译字典(必做)

MTool 导出的 JSON 常有**值=原文的占位条目**(占比可达 70%+),必须清洗,否则命中占位条目原样显示日文。

```bash
python3 scripts/inject_translation.py <游戏目录> <翻译.json> --dry-run
```

`--dry-run` 先出覆盖率报告不写入。脚本自动完成:
1. 剔除占位条目(值=原文或空)
2. 从多行合并条目(键含 `\n` 且行数与译文对齐)拆出单行译文补充
3. 用三级匹配模拟覆盖率: 精确 → 去控制码/红宝石注音整段 → 切段重组(保留 `\F1[...]` 等立绘代码和 `{汉字|假名}` 注音)

覆盖率达到 95%+ 即可注入;控制码正则: `\\[A-Za-z0-9]+(\[[^\]]*\])?|\{([^{}|]*)\|[^{}|]*\}`,红宝石注音取汉字部分(`m.group(2)`)。

## 第三步:注入式汉化(推荐)或运行时插件

**注入式(首选,确定性最高)**:同一脚本去掉 `--dry-run` 执行,自动备份 `data/` 到 `data_backup_<时间戳>/`。
**保护规则**(已内置,勿绕过):资源文件名(对照 audio/img/effects/fonts 目录真实文件名)、含 `/` 的串、代码 357 插件命令的 parameters[0]/[1]、356 全部参数、355/655 脚本串、118/119 标签,一律不译。

**运行时插件(免改数据,备选)**:用 LLM_AutoTranslator(支持 MTOOL 格式)并打两个补丁: ①`isEnabled()` 允许无 API 密钥时用 MTOOL ②`translate()` 缓存未命中且无密钥时直接返回原文。再升级 `_smartTranslate` 三级匹配(见 scripts/inject_translation.py 里的 `smart()` 函数,逻辑可直接移植到 JS)。

## 第四步:音频解封与替换

```bash
# 解密(游戏目录用于读密钥, 支持 .ogg_ 和 .rpgmvo)
python3 scripts/rpgm_audio.py decrypt <游戏目录> audio/se/xxx.ogg_
# 加密放回(自动备份同名旧文件)
python3 scripts/rpgm_audio.py encrypt <游戏目录> xxx.ogg
```

加密算法: 16 字节 `RPGMV` 头 + 音频前 16 字节与密钥异或,其余明文。替换时**文件名必须与原文件一致**。

## 第五步:自动配音

1. 语音放 `audio/se/voice/*.ogg_`(用第四步的脚本加密;可从其他 RPG Maker 游戏迁移——先 decrypt 源游戏再 encrypt 目标游戏,密钥各自独立)
2. 复制 `assets/VoiceSystem.js` 到 `js/plugins/`,在 `js/plugins.js` 的数组末尾注册(参考已有条目格式,`status:true`)
3. 触发逻辑: 战斗受创/攻击/开局/胜利、CG(显示 event/ 等目录图片)、剧情关键词(默认匹配中文,改 KEYWORDS 表适配其他语言)

## 排错速查

- **MZ 命令方法签名是 `commandXXX(params)`,参数是传进来的,`this._params` 是 undefined!** 钩子必须 `function(params)` 且转发 `orig.call(this, params)`。MV 才是 `this._params` 风格
- MZ 没有独立的 command401/command405:消息文本由 `command101` 统一消费(循环吃后续 401 行),滚动文本是 `command105` 吃 405。挂消息钩子用 101/105,通过 `$gameMessage.allText()` 取文本
- 显示图片是 `command231`,CG 判定看 `params[1]` 图片名前缀
- 报错 `Failed to load audio/se/...`:注入时翻译了音效文件名,用备份回退该字段
- 改完游戏必须完全退出(Cmd+Q)再启动;nwjs 缓存可疑时删 `~/Library/Application Support/<游戏名>`(存档一般在游戏目录 `save/`)
- 文本显示为日文但数据已中文:CG 文字可能画在加密图片 `.png_` 里,翻译文件救不了,需改图

详细引擎差异与命令代码表见 [references/engine-gotchas.md](references/engine-gotchas.md)。
