//=============================================================================
// VoiceSystem.js
// 角色配音系统 - 战斗/H场景自动语音
//=============================================================================

/*:
 * @target MZ
 * @plugindesc 角色配音: 战斗喊声 + 剧情关键词反应音 (语音文件: audio/se/voice/)
 * @author Kimi
 *
 * @param volume
 * @text 语音音量
 * @desc 配音播放音量
 * @type number
 * @min 0
 * @max 100
 * @default 90
 *
 * @param cooldown
 * @text 最短间隔(毫秒)
 * @desc 同一类语音的最短播放间隔, 防止刷屏
 * @type number
 * @min 200
 * @max 10000
 * @default 1200
 *
 * @param battleVoice
 * @text 战斗语音
 * @desc 战斗中是否播放攻击/受创/开始/胜利语音
 * @type boolean
 * @default true
 *
 * @param eventVoice
 * @text 剧情语音
 * @desc 对话中是否按关键词播放反应音
 * @type boolean
 * @default true
 *
 * @help
 * 语音文件放在 audio/se/voice/ 下(已加密, 后缀 .ogg_ 由引擎自动处理)
 * 战斗: 角色攻击/受创/战斗开始/胜利时随机播放对应语音
 * 剧情: 对话文本命中关键词时播放对应语音(中文字匹配)
 */

(function() {
    'use strict';
    const pluginName = 'VoiceSystem';
    const params = PluginManager.parameters(pluginName);
    const cfg = {
        volume: parseInt(params.volume) || 90,
        cooldown: parseInt(params.cooldown) || 1200,
        battleVoice: params.battleVoice !== 'false',
        eventVoice: params.eventVoice !== 'false'
    };

    const lastPlay = {};   // 类别 -> 时间戳

    function canPlay(cat) {
        const now = Date.now();
        if (lastPlay[cat] && now - lastPlay[cat] < cfg.cooldown) return false;
        lastPlay[cat] = now;
        return true;
    }

    function playVoice(name, cat, pitchVar) {
        if (!canPlay(cat || name)) return;
        const pitch = 100 + Math.floor(Math.random() * (pitchVar || 20)) - (pitchVar || 20) / 2;
        AudioManager.playSe({ name: 'voice/' + name, volume: cfg.volume, pitch: Math.round(pitch), pan: 0 });
    }

    function playRandom(names, cat) {
        playVoice(names[Math.floor(Math.random() * names.length)], cat);
    }

    //========================================================================
    // 战斗语音
    //========================================================================
    if (cfg.battleVoice) {
        // 角色受创
        const _Game_Actor_performDamage = Game_Actor.prototype.performDamage;
        Game_Actor.prototype.performDamage = function() {
            _Game_Actor_performDamage.call(this);
            playRandom(['A_damagevoice1', 'A_damagevoice2', 'A_damagevoice3'], 'damage');
        };
        // 角色攻击
        const _Game_Actor_performAttack = Game_Actor.prototype.performAttack;
        Game_Actor.prototype.performAttack = function() {
            _Game_Actor_performAttack.call(this);
            playRandom(['A_kougekivoice1', 'A_kougekivoice2'], 'attack');
        };
        // 战斗开始(我方行动回合开始)
        const _BattleManager_startTurn = BattleManager.startTurn;
        BattleManager.startTurn = function() {
            _BattleManager_startTurn.call(this);
            if (this._turnCount === 1) playRandom(['A_sentouzivoice1', 'A_sentouzivoice2'], 'battlestart');
        };
        // 战斗胜利
        const _BattleManager_processVictory = BattleManager.processVictory;
        BattleManager.processVictory = function() {
            playRandom(['A_sentouendvoice1', 'A_sentouendvoice2'], 'victory');
            _BattleManager_processVictory.call(this);
        };
    }

    //========================================================================
    // 剧情关键词语音 (匹配注入后的中文文本)
    //========================================================================
    if (cfg.eventVoice) {
        // 关键词 -> [语音文件列表, 类别]
        const KEYWORDS = [
            [['欢迎光临', '欢迎'], ['A_irassyai'], 'irassyai'],
            [['谢谢', '感谢'], ['A_arigatou'], 'arigatou'],
            [['请'], ['A_matadouzo'], 'matadouzo']
        ];

        function checkText(text) {
            if (!text || typeof text !== 'string') return;
            for (const [words, voices, cat] of KEYWORDS) {
                for (const w of words) {
                    if (text.indexOf(w) !== -1) {
                        playRandom(voices, cat);
                        return; // 一句只触发一类
                    }
                }
            }
        }

        // 对话文本(MZ的101命令内部消费401行)与滚动文本(105消费405行)
        // MZ把command.parameters作为参数传入, 不能用MV式的this._params
        const _Game_Interpreter_command101 = Game_Interpreter.prototype.command101;
        Game_Interpreter.prototype.command101 = function(params) {
            const r = _Game_Interpreter_command101.call(this, params);
            if (r !== false) checkText($gameMessage.allText());
            return r;
        };
        const _Game_Interpreter_command105 = Game_Interpreter.prototype.command105;
        Game_Interpreter.prototype.command105 = function(params) {
            const r = _Game_Interpreter_command105.call(this, params);
            if (r !== false) checkText($gameMessage.allText());
            return r;
        };

        // CG语音: 显示CG图片(cs/event/event_s目录)时播放反应音
        const CG_PREFIX = ['cs/', 'event/', 'event_s/'];
        const CG_VOICES = ['A_zettyoumae1', 'A_zettyoumae2', 'A_zettyoumae3',
                           'A_nakadasimae1', 'A_nakadasimae2',
                           'A_oppaidamage', 'A_osiridamage', 'A_kousokuvoice'];
        const _Game_Interpreter_command231 = Game_Interpreter.prototype.command231;
        Game_Interpreter.prototype.command231 = function(params) {
            const r = _Game_Interpreter_command231.call(this, params);
            const name = params && params[1];
            if (typeof name === 'string') {
                for (const p of CG_PREFIX) {
                    if (name.indexOf(p) === 0) { playRandom(CG_VOICES, 'cg'); break; }
                }
            }
            return r;
        };
    }
})();
