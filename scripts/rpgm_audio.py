#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RPG Maker MV/MZ 加密音频解密/加密
加密格式: 16字节 "RPGMV" 头 + 音频前16字节与System.json的encryptionKey异或, 其余明文。
用法:
  python3 rpgm_audio.py decrypt <游戏目录> <.ogg_/.rpgmvo 文件...>   # 解密出 .ogg
  python3 rpgm_audio.py encrypt <游戏目录> <.ogg 文件...>            # 加密回 .ogg_ (自动备份旧文件)
密钥从 <游戏目录>/data/System.json (MZ) 或 <游戏目录>/www/data/System.json (MV) 读取。
跨游戏迁移语音: 先对源游戏 decrypt, 再对目标游戏 encrypt。
"""
import argparse, json, os, shutil, time

HEADER = bytes([0x52, 0x50, 0x47, 0x4D, 0x56, 0x00, 0x00, 0x00,
                0x00, 0x03, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00])

def get_key(game_dir):
    for p in ('data/System.json', 'www/data/System.json'):
        f = os.path.join(game_dir, p)
        if os.path.exists(f):
            key = json.load(open(f, encoding='utf-8')).get('encryptionKey')
            if key:
                return bytes.fromhex(key)
    raise SystemExit(f'在 {game_dir} 找不到 data/System.json 或 encryptionKey')

def decrypt_file(path, key):
    if path.endswith('.rpgmvo'):
        dst = path[:-7] + '.ogg'
    elif path.endswith('.rpgmvm'):
        dst = path[:-7] + '.m4a'
    elif path.endswith('_'):
        dst = path[:-1]
    else:
        dst = path + '.ogg'
    data = open(path, 'rb').read()
    if data[:5] != b'RPGMV':
        raise SystemExit(f'{path}: 不是 RPG Maker 加密音频(无 RPGMV 头)')
    body = bytearray(data[16:])
    for i in range(16):
        body[i] ^= key[i]
    if body[:4] != b'OggS':
        raise SystemExit(f'{path}: 解密失败, 前16字节异或后不是 OggS(密钥不对?)')
    open(dst, 'wb').write(body)
    print(f'解密: {path} → {dst}')

def encrypt_file(path, key):
    data = open(path, 'rb').read()
    if data[:4] != b'OggS':
        raise SystemExit(f'{path}: 不是合法 ogg 文件')
    dst = path[:-4] + '.ogg_' if path.endswith('.ogg') else path + '.ogg_'
    body = bytearray(data)
    for i in range(16):
        body[i] ^= key[i]
    if os.path.exists(dst):
        bak = dst + '.bak_' + time.strftime('%m%d_%H%M%S')
        shutil.copy2(dst, bak)
        print(f'原文件已备份: {bak}')
    open(dst, 'wb').write(HEADER + body)
    print(f'加密: {path} → {dst}')

def main():
    ap = argparse.ArgumentParser(description='RPG Maker MV/MZ 加密音频工具')
    ap.add_argument('mode', choices=['decrypt', 'encrypt'])
    ap.add_argument('game_dir', help='游戏目录(读取加密密钥)')
    ap.add_argument('files', nargs='+')
    a = ap.parse_args()
    key = get_key(a.game_dir)
    for f in a.files:
        decrypt_file(f, key) if a.mode == 'decrypt' else encrypt_file(f, key)

if __name__ == '__main__':
    main()
