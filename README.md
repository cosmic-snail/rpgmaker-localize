# rpgmaker-localize

RPG Maker MV/MZ 游戏汉化与音频改造 skill（Kimi / Kimi Work 技能包）。

一条命令完成：MTool 翻译字典清洗 → 覆盖率模拟 → 安全注入 `data/*.json`（自动保护资源名、插件命令、脚本）→ 加密音频解封/替换 → 自动配音插件安装。

## 内容

| 路径 | 说明 |
|---|---|
| `SKILL.md` | 主流程与触发条件（技能入口） |
| `scripts/inject_translation.py` | 翻译清洗 + 覆盖率报告 + 离线注入（`--dry-run` 只报告） |
| `scripts/rpgm_audio.py` | RPG Maker 加密音频（`.ogg_` / `.rpgmvo`）解密/加密 |
| `assets/VoiceSystem.js` | 自动配音插件模板（战斗喊声 / CG 触发 / 剧情关键词） |
| `references/engine-gotchas.md` | MV/MZ 引擎差异、事件命令代码表、加密格式、踩坑记录 |

## 独立使用（不装 skill 也能跑）

```bash
# 干跑: 清洗字典 + 覆盖率报告
python3 scripts/inject_translation.py <游戏目录> <翻译.json> --dry-run

# 注入汉化(自动备份 data/)
python3 scripts/inject_translation.py <游戏目录> <翻译.json>

# 解密/加密音频(密钥自动从游戏 System.json 读取)
python3 scripts/rpgm_audio.py decrypt <游戏目录> <文件.ogg_>
python3 scripts/rpgm_audio.py encrypt <游戏目录> <文件.ogg>
```

## 安装为 Kimi Work skill

把整个 `rpgmaker-localize/` 目录复制到 Kimi Work 技能目录即可：

```bash
cp -R rpgmaker-localize "/Users/simon/Library/Application Support/kimi-desktop/daimon-share/daimon/skills/"
```

## 注意事项

- 仅用于你拥有正版授权的游戏之个人本地化研究；翻译文本与语音的版权归原作者及发行方所有，请勿分发修改后的游戏文件。
- 注入前一定先 `--dry-run` 看覆盖率；已注入过的游戏重复执行是安全的（无日文即无改动）。
