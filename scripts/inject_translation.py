#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MTool 翻译字典清洗 + 覆盖率模拟 + 离线注入 RPG Maker MV/MZ 游戏数据

用法:
  python3 inject_translation.py <游戏目录> <翻译.json> --dry-run   # 只出报告
  python3 inject_translation.py <游戏目录> <翻译.json>             # 注入(自动备份 data/)

流程:
  1. 清洗字典: 剔除占位条目(值=原文/空), 从多行合并条目拆出单行译文
  2. 覆盖率模拟: 对 data/ 全部文本串跑三级匹配(精确/去控制码/切段重组)
  3. 注入: 替换命中串, 保护规则跳过资源名、插件命令标识符、脚本、标签
保护规则(勿绕过):
  - 资源文件名: 原文等于 audio/img/effects/fonts 下真实文件名(不含扩展名), 或含 '/', 或带媒体扩展名
  - code 357: parameters[0](插件名)/[1](命令名) 不译;  code 356: 全部参数不译
  - code 355/655(脚本): 不译;  code 118/119(标签): 不译
"""
import argparse, json, os, re, shutil, sys, time, glob

RE_CODE = re.compile(r'\\[A-Za-z0-9]+(\[[^\]]*\])?|\{([^{}|]*)\|[^{}|]*\}')
JP = re.compile(r'[ぁ-んァ-ヶ]')
CN = re.compile(r'[一-鿿]')

def load_dict(path):
    raw = json.load(open(path, encoding='utf-8'))
    real = {k: str(v) for k, v in raw.items() if str(v).strip() and k != v}
    added = {}
    for k, v in real.items():
        kl, vl = k.split('\n'), v.split('\n')
        if len(kl) != len(vl) or len(kl) < 2:
            continue
        for ki, vi in zip(kl, vl):
            ki, vi = ki.strip(), vi.strip()
            if ki and JP.search(ki) and ki not in real and ki not in added:
                added[ki] = vi
    real.update(added)
    return real

def make_smart(d):
    keys = set(d.keys())
    def smart(text):
        if text in keys: return d[text]
        tt = text.strip()
        if tt != text and tt in keys: return d[tt]
        segs, codes, masked, last = [], [], '', 0
        for m in RE_CODE.finditer(text):
            if m.start() > last:
                segs.append(text[last:m.start()]); masked += text[last:m.start()]
            masked += m.group(2) or ''
            codes.append(m.group(0)); last = m.end()
        if last < len(text): segs.append(text[last:]); masked += text[last:]
        if masked == text: return None
        if masked in keys and not codes: return d[masked]
        out, allHit, anyT = '', True, False
        for i, seg in enumerate(segs):
            t = seg
            if JP.search(seg):
                if seg in keys: t = d[seg]; anyT = True
                else:
                    st = seg.strip()
                    if st != seg and st in keys: t = d[st]; anyT = True
                    else: allHit = False; break
            out += t
            if i < len(codes): out += codes[i]
        if allHit and anyT: return out
        if masked in keys: return d[masked]
        mt = masked.strip()
        if mt != masked and mt in keys: return d[mt]
        return None
    return smart

def collect_stems(game_dir):
    stems = set()
    for root in ('audio', 'img', 'effects', 'fonts', 'www/audio', 'www/img', 'www/effects'):
        p = os.path.join(game_dir, root)
        if os.path.isdir(p):
            for dp, _, fns in os.walk(p):
                for fn in fns: stems.add(os.path.splitext(fn)[0])
    return stems

def data_files(game_dir):
    base = 'data' if os.path.isdir(os.path.join(game_dir, 'data')) else 'www/data'
    return sorted(glob.glob(os.path.join(game_dir, base, '*.json')))

MEDIA_EXT = re.compile(r'\.(ogg|m4a|png|wav|mp3|rpgmvp|rpgmvo)$', re.I)

def walk_event(o, ctx, visit):
    """带事件代码上下文遍历; ctx=(code, list索引) 供保护规则判断"""
    if isinstance(o, dict):
        code = o.get('code', ctx[0])
        if 'parameters' in o and isinstance(o['parameters'], list):
            for i, v in enumerate(o['parameters']):
                walk_event(v, (code, i), visit)
            for k, v in o.items():
                if k != 'parameters': walk_event(v, (code, None), visit)
        else:
            for v in o.values(): walk_event(v, (code, None), visit)
    elif isinstance(o, list):
        for v in o: walk_event(v, ctx, visit)
    elif isinstance(o, str):
        visit(o, ctx)

def protected(text, ctx, stems):
    o = text.strip()
    if o in stems or '/' in o or MEDIA_EXT.search(o):
        return True
    code, idx = ctx
    if code == 357 and idx in (0, 1): return True
    if code == 356: return True
    if code in (355, 655, 118, 119): return True
    return False

def main():
    ap = argparse.ArgumentParser(description='MTool 字典清洗+注入')
    ap.add_argument('game_dir')
    ap.add_argument('translation_json')
    ap.add_argument('--dry-run', action='store_true', help='只出覆盖率报告, 不写文件')
    a = ap.parse_args()

    d = load_dict(a.translation_json)
    print(f'字典: {len(d)} 条有效译文')
    smart = make_smart(d)
    stems = collect_stems(a.game_dir)
    print(f'资源文件名: {len(stems)} 个')

    files = data_files(a.game_dir)
    if not files:
        raise SystemExit('找不到 data/*.json')

    # 覆盖率模拟
    total = hit = 0
    sample_miss = []
    for f in files:
        try: obj = json.load(open(f, encoding='utf-8'))
        except Exception: continue
        strs = []
        def collect(o):
            if isinstance(o, dict):
                for v in o.values(): collect(v)
            elif isinstance(o, list):
                for v in o: collect(v)
            elif isinstance(o, str) and JP.search(o): strs.append(o)
        collect(obj)
        for s in set(strs):
            total += 1
            if smart(s): hit += 1
            elif len(sample_miss) < 10: sample_miss.append(s)
    print(f'\n覆盖率: {hit}/{total} = {hit/max(total,1)*100:.1f}%')
    for s in sample_miss: print('  漏翻:', repr(s[:60]))
    if a.dry_run:
        return
    if hit / max(total, 1) < 0.9:
        print('覆盖率低于90%, 仍要注入请加 --force'); sys.exit(1)

    # 备份
    bak = os.path.join(a.game_dir, 'data_backup_' + time.strftime('%Y%m%d'))
    src_base = 'data' if os.path.isdir(os.path.join(a.game_dir, 'data')) else 'www/data'
    if not os.path.exists(bak):
        shutil.copytree(os.path.join(a.game_dir, src_base), bak)
        print(f'\n已备份: {bak}')

    # 注入
    for f in files:
        try:
            raw = open(f, encoding='utf-8').read()
            obj = json.loads(raw)
        except Exception as e:
            print(f'{f}: 解析失败跳过 ({e})'); continue
        cache = {}
        def xlate(s, ctx):
            if s in cache: return cache[s]
            r = s
            if JP.search(s) and not protected(s, ctx, stems):
                t = smart(s)
                if t: r = t
            cache[s] = r
            return r
        def walk(o, ctx=(None, None)):
            if isinstance(o, dict):
                code = o.get('code', ctx[0])
                if 'parameters' in o and isinstance(o['parameters'], list):
                    o['parameters'] = [walk(v, (code, i)) for i, v in enumerate(o['parameters'])]
                    return {k: (walk(v, (code, None)) if k != 'parameters' else o['parameters']) for k, v in o.items()}
                return {k: walk(v, (code, None)) for k, v in o.items()}
            if isinstance(o, list):
                return [walk(v, ctx) for v in o]
            if isinstance(o, str):
                return xlate(o, ctx)
            return o
        new = walk(obj)
        s_new = json.dumps(new, ensure_ascii=False, separators=(',', ':'))
        if s_new != raw:
            open(f, 'w', encoding='utf-8').write(s_new)
            print(f'注入: {os.path.basename(f)}')

    # 终验: JSON 可解析
    for f in files:
        json.load(open(f, encoding='utf-8'))
    print('\n全部 JSON 校验通过 ✓')

if __name__ == '__main__':
    main()
