# RPG Maker MV/MZ 引擎差异与命令代码备忘

## MV 与 MZ 的核心差异(排错重点)

| | MV | MZ |
|---|---|---|
| 目录结构 | `www/data`, `www/audio`, `www/img` | 根目录直接 `data`, `audio`, `img` |
| 命令方法签名 | `command231()`, 读 `this._params` | `command231(params)`, **参数传进来, `this._params` 是 undefined** |
| 消息命令 | 101 后开始, 401 每行独立执行 | **没有独立 command401**, `command101` 内部 `while(nextEventCode()===401)` 统一消费, 取文本用 `$gameMessage.allText()` |
| 滚动文本 | 405 独立 | `command105` 内部消费 405, 同样用 `$gameMessage.allText()` |
| 加密音频后缀 | `.rpgmvo` / `.rpgmvm` | `.ogg_` / `.m4a_` |
| 加密图片后缀 | `.rpgmvp` | `.png_` |
| 数据文件 | 都是明文 JSON, 可直接读写 | 同左 |

写任何 `Game_Interpreter.prototype.commandXXX` 的补丁:
```js
// 错误(MV思维): function() { orig.call(this); this._params[0] }   // this._params undefined
// 正确(MZ):      function(params) { orig.call(this, params); params[0] }
```
不确定时直接读目标游戏的 `js/rmmz_objects.js`(明文)确认签名。

## 常用事件命令代码

| code | 含义 | 备注 |
|---|---|---|
| 101 | 显示消息 | MZ 里消费后续所有 401 行 |
| 102/103/104 | 选项/输数字/选物品 | 跟在 101 后 |
| 105 | 滚动文本 | 消费后续 405 行 |
| 108/408 | 注释 | 翻译无害 |
| 111 | 条件分支 | 串比较罕见, 一般可译 |
| 118/119 | 标签 | **不译**(跳转按标签名) |
| 121/122 | 开关/变量操作 | 数值 |
| 231 | 显示图片 | `params[1]`=图片名(可含子目录如 `event/xxx`), CG 判定挂这里 |
| 232 | 移动图片 | |
| 355/655 | 脚本 | **绝不翻译** |
| 356 | 旧式插件命令(字符串) | **全部参数不译** |
| 357 | 新式插件命令 | `parameters[0]`=插件名, `[1]`=命令名, **这两个不译**; `[2]` 多为编辑器显示标签, 可译 |

## 加密格式(音频/图片)

- 音频: 16 字节头 `52 50 47 4D 56 00 00 00 00 03 01 00 00 00 00 00`(`"RPGMV"` + 固定字节), 其后音频数据**前 16 字节**与密钥逐字节异或, 其余明文 ogg
- 密钥: `data/System.json`(MV 在 `www/data/`)的 `encryptionKey`, 32 位 hex = 16 字节; 默认密钥是空字符串的 MD5(`d41d8cd98f00b204e9800998ecf8427e`)
- 解密验证: 异或后前 4 字节必须是 `OggS`(4F 6767 53)
- 图片: 整文件 XOR(更复杂, 一般不用处理; CG 上的文字要汉化只能改图)
- 引擎通过 `Decrypter.hasEncryptedAudio` 标志自动切换 `.ogg`/`.ogg_`, 放入正确命名的加密文件即可被游戏直接加载, 播子目录用 `AudioManager.playSe({name:'voice/xxx', ...})`

## MTool 翻译文件的坑

- MTool 导出 JSON 含大量**占位条目**(值=原文), 比例可达 70%+, 不过滤会导致「部分句子显示日文」且难以排查
- 键里**不含任何控制码**(`\c[1]`、`\F1[s_01]`、`\AA[2]`、`{汉字|假名}` 都被剥掉了), 游戏里实际文本带码, 需要三级匹配
- 多行文本常合并成一个键(含 `\n`), 单行出现的句子要拆行补充
- 红宝石注音 `{膣内|なか}` 字典里取**汉字部分**(`膣内`)做键

## 运行时翻译插件(LLM_AutoTranslator)补丁要点

1. `isEnabled()`: 改为 `return this._translationEnabled && (hasKey || this._useMtool);`(否则无 API 密钥时 MTOOL 也不生效)
2. `translate()`: 缓存未命中处加 `if (!hasKey) return text;`(否则每个新句子都发失败请求)
3. `_smartTranslate()`: 加三级匹配; **不要用 `String.split(带捕获组的正则)`**, 捕获组会混进结果, 用 `exec`/`finditer` 手工切分重组
4. 该插件 hook 的是 `Window_Base.prototype.drawText/drawTextEx`; 直接画到 Bitmap 的文字(如 TextPicture 插件)绕过 hook, 需注入式兜底

## nwjs 运行时

- 改文件后必须完全退出(Cmd+Q)再启动, 热重载不存在
- nwjs 用户数据目录: `~/Library/Application Support/<package.json的name>`; 存档通常在**游戏目录** `save/`(MZ nwjs 部署), 删缓存目录不丢档
- 报错排查: `Failed to load audio/se/xxx` = 资源引用被改名; `TypeError ... reading 'N'` = 多半是 MZ 参数没转发
