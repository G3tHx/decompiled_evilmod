# -*- coding: utf-8 -*-
"""
Скрипт сборки чистого и безопасного мода Armor Flashlight в пакет .mtmod (Мир Танков).

Автор: Apostle
Версия: 1.0.0

Выполняемые операции:
  1. Полное удаление вредоносного SDK/C2/телеметрии (modsdk_hook / minion).
  2. Полное отключение и вырезание нечестных функций (подсветка сквозь заборы/стены/разрушаемые объекты).
     Мод приведён в 100% соответствие с правилами Честной игры (Fair Play Policy):
     работает строго в прямой видимости цели, как официальная подсветка брони в клиенте EU.
  3. Сборка архива без сжатия (ZIP_STORED) для корректной работы VFS движка BigWorld.
  4. Автоматическая установка в клиент игры (D:\\Games\\TankiPF\\mods\\1.46.0.0).

Использование:
  python build_mod.py
"""

import os
import sys
import time
import struct
import shutil
import zipfile
import io

MOD_ID = "apostle.armorflashlight"
VERSION = "1.0.0"
OUTPUT_NAME = "%s_%s.mtmod" % (MOD_ID, VERSION)

TARGET_GAME_MODS_DIR = r"D:\Games\TankiPF\mods\1.46.0.0"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EVILMOD_DIR = os.path.join(os.path.dirname(BASE_DIR), "ArmorFlashEvilMod", "tools", "output")
CLEAN_PYC_DIR = os.path.join(EVILMOD_DIR, "2_clean_pyc")
EXTRACTED_DIR = os.path.join(EVILMOD_DIR, "1_extracted")

PY27_HEADER = b'\x03\xf3\r\n\x00\x00\x00\x00'

META_XML = """<root>
    <version>%s</version>
    <description>Armor Flashlight: Visual penetration indicator in aiming circle with direct line of sight; hangar armor inspector. Clean and Safe edition by Apostle</description>
    <name>Armor Flashlight</name>
    <id>%s</id>
</root>
""" % (VERSION, MOD_ID)


def parse_py27_marshal(data, pos=8, stringtable=None):
    if stringtable is None:
        stringtable = []

    if pos >= len(data):
        raise ValueError("Unexpected EOF in marshal data at offset %d" % pos)

    tc = chr(data[pos])
    pos += 1

    if tc in ('0', 'N'):
        return None, pos
    elif tc == 'T':
        return True, pos
    elif tc == 'F':
        return False, pos
    elif tc == 'S':
        return StopIteration, pos
    elif tc == '.':
        return ..., pos
    elif tc == 'i':
        val = struct.unpack('<i', data[pos:pos+4])[0]
        return val, pos + 4
    elif tc == 'I':
        val = struct.unpack('<q', data[pos:pos+8])[0]
        return val, pos + 8
    elif tc == 'f':
        length = data[pos]
        val_str = data[pos+1:pos+1+length]
        return float(val_str), pos + 1 + length
    elif tc == 'g':
        val = struct.unpack('<d', data[pos:pos+8])[0]
        return val, pos + 8
    elif tc == 'l':
        n = struct.unpack('<i', data[pos:pos+4])[0]
        return '<long>', pos + 4 + (2 * abs(n))
    elif tc == 's':
        length = struct.unpack('<I', data[pos:pos+4])[0]
        pos += 4
        raw_str = data[pos:pos+length]
        return raw_str, pos + length
    elif tc == 't':
        length = struct.unpack('<I', data[pos:pos+4])[0]
        pos += 4
        raw_str = data[pos:pos+length]
        stringtable.append(raw_str)
        return raw_str, pos + length
    elif tc == 'R':
        ref = struct.unpack('<I', data[pos:pos+4])[0]
        pos += 4
        return (stringtable[ref] if ref < len(stringtable) else '<ref:%d>' % ref), pos
    elif tc == 'u':
        length = struct.unpack('<I', data[pos:pos+4])[0]
        pos += 4
        u = data[pos:pos+length].decode('utf-8', errors='replace')
        return u, pos + length
    elif tc in ('(', '['):
        length = struct.unpack('<I', data[pos:pos+4])[0]
        pos += 4
        items = []
        for _ in range(length):
            it, pos = parse_py27_marshal(data, pos, stringtable)
            items.append(it)
        return (tuple(items) if tc == '(' else items), pos
    elif tc in ('<', '>'):
        length = struct.unpack('<I', data[pos:pos+4])[0]
        pos += 4
        items = [parse_py27_marshal(data, pos, stringtable)[0] for _ in range(length)]
        return set(items), pos
    elif tc == '{':
        d = {}
        while True:
            k, pos = parse_py27_marshal(data, pos, stringtable)
            if k is None:
                break
            v, pos = parse_py27_marshal(data, pos, stringtable)
            d[k] = v
        return d, pos
    elif tc == 'c':
        argcount = struct.unpack('<I', data[pos:pos+4])[0]
        nlocals = struct.unpack('<I', data[pos+4:pos+8])[0]
        stacksize = struct.unpack('<I', data[pos+8:pos+12])[0]
        flags = struct.unpack('<I', data[pos+12:pos+16])[0]
        pos += 16

        code, pos = parse_py27_marshal(data, pos, stringtable)
        consts, pos = parse_py27_marshal(data, pos, stringtable)
        names, pos = parse_py27_marshal(data, pos, stringtable)
        varnames, pos = parse_py27_marshal(data, pos, stringtable)
        freevars, pos = parse_py27_marshal(data, pos, stringtable)
        cellvars, pos = parse_py27_marshal(data, pos, stringtable)
        filename, pos = parse_py27_marshal(data, pos, stringtable)
        name, pos = parse_py27_marshal(data, pos, stringtable)
        firstlineno = struct.unpack('<I', data[pos:pos+4])[0]
        pos += 4
        lnotab, pos = parse_py27_marshal(data, pos, stringtable)

        return {
            'type': 'code',
            'argcount': argcount,
            'nlocals': nlocals,
            'stacksize': stacksize,
            'flags': flags,
            'code': code,
            'consts': consts,
            'names': names,
            'varnames': varnames,
            'freevars': freevars,
            'cellvars': cellvars,
            'filename': filename,
            'name': name,
            'firstlineno': firstlineno,
            'lnotab': lnotab
        }, pos
    else:
        raise ValueError("Unknown marshal type '%s' (0x%02x) at offset %d" % (tc, ord(tc), pos-1))


def serialize_py27(obj):
    if obj is None:
        return b'N'
    elif obj is True:
        return b'T'
    elif obj is False:
        return b'F'
    elif obj is StopIteration:
        return b'S'
    elif obj is Ellipsis:
        return b'.'
    elif isinstance(obj, int):
        if -2147483648 <= obj <= 2147483647:
            return b'i' + struct.pack('<i', obj)
        else:
            return b'I' + struct.pack('<q', obj)
    elif isinstance(obj, float):
        return b'g' + struct.pack('<d', obj)
    elif isinstance(obj, bytes):
        return b's' + struct.pack('<I', len(obj)) + obj
    elif isinstance(obj, str):
        b = obj.encode('utf-8')
        return b'u' + struct.pack('<I', len(b)) + b
    elif isinstance(obj, (tuple, list)):
        tc = b'(' if isinstance(obj, tuple) else b'['
        return tc + struct.pack('<I', len(obj)) + b''.join(serialize_py27(x) for x in obj)
    elif isinstance(obj, dict) and obj.get('type') == 'code':
        hdr = b'c'
        hdr += struct.pack('<I', obj.get('argcount', 0))
        hdr += struct.pack('<I', obj.get('nlocals', 0))
        hdr += struct.pack('<I', obj.get('stacksize', 0))
        hdr += struct.pack('<I', obj.get('flags', 0))
        hdr += serialize_py27(obj.get('code', b''))
        hdr += serialize_py27(tuple(obj.get('consts', ())))
        hdr += serialize_py27(tuple(obj.get('names', ())))
        hdr += serialize_py27(tuple(obj.get('varnames', ())))
        hdr += serialize_py27(tuple(obj.get('freevars', ())))
        hdr += serialize_py27(tuple(obj.get('cellvars', ())))
        hdr += serialize_py27(obj.get('filename', b''))
        hdr += serialize_py27(obj.get('name', b''))
        hdr += struct.pack('<I', obj.get('firstlineno', 1))
        hdr += serialize_py27(obj.get('lnotab', b''))
        return hdr
    else:
        raise ValueError("Cannot serialize object of type %s" % type(obj))


def make_clean_modsdk_hook():
    """Создаёт чистую заглушку modsdk_hook без C2, сокетов и удалённого выполнения."""
    fn_init = {
        'type': 'code', 'argcount': 0, 'nlocals': 0, 'stacksize': 1, 'flags': 0x43,
        'code': b'\x64\x00\x00\x53', 'consts': (None,), 'names': (), 'varnames': (),
        'freevars': (), 'cellvars': (), 'filename': b'modsdk_hook.py', 'name': b'init',
        'firstlineno': 1, 'lnotab': b''
    }
    fn_fini = {
        'type': 'code', 'argcount': 0, 'nlocals': 0, 'stacksize': 1, 'flags': 0x43,
        'code': b'\x64\x00\x00\x53', 'consts': (None,), 'names': (), 'varnames': (),
        'freevars': (), 'cellvars': (), 'filename': b'modsdk_hook.py', 'name': b'fini',
        'firstlineno': 4, 'lnotab': b''
    }
    mod_co = {
        'type': 'code', 'argcount': 0, 'nlocals': 0, 'stacksize': 2, 'flags': 0x40,
        'code': b'\x64\x00\x00\x84\x00\x00\x5a\x00\x00\x64\x01\x00\x84\x00\x00\x5a\x01\x00\x64\x02\x00\x53',
        'consts': (fn_init, fn_fini, None), 'names': (b'init', b'fini'), 'varnames': (),
        'freevars': (), 'cellvars': (), 'filename': b'modsdk_hook.py', 'name': b'<module>',
        'firstlineno': 1, 'lnotab': b''
    }
    return PY27_HEADER + serialize_py27(mod_co)


def patch_mod_armorflashlight(raw_pyc):
    """Обновление версии в mod_armorflashlight.pyc до 1.0.0"""
    co, _ = parse_py27_marshal(raw_pyc, 8)
    consts = list(co['consts'])
    for i, c in enumerate(consts):
        if c == b'1.0.38':
            consts[i] = b'1.0.0'
    co['consts'] = tuple(consts)
    return PY27_HEADER + serialize_py27(co)


def patch_init_pyc(raw_pyc):
    """Удаление modsdk minion вызова и обновление версии в __init__.pyc"""
    co, _ = parse_py27_marshal(raw_pyc, 8)
    consts = list(co['consts'])
    for i, c in enumerate(consts):
        if c == b'1.0.38':
            consts[i] = b'1.0.0'

    # Полное обезвреживание _start_modsdk (индекс 24)
    fn_modsdk = consts[24]
    fn_modsdk['code'] = b'\x64\x00\x00\x53'  # LOAD_CONST 0 (None), RETURN_VALUE
    fn_modsdk['consts'] = (None,)
    fn_modsdk['names'] = ()
    fn_modsdk['varnames'] = ()

    co['consts'] = tuple(consts)
    return PY27_HEADER + serialize_py27(co)


def patch_afl_battle_pyc(raw_pyc):
    """
    Приведение afl_battle.pyc в полное соответствие с правилами Честной игры (Fair Play):
      1. _S['destr'] = False (подсветка сквозь объекты отключена)
      2. _S['foliage'] = False (подсветка сквозь кусты/листву отключена)
      3. _push: флаги 2048 (foliage lift) и 4096 (obstacle lift) обнулены
      4. _push_forward: vals['fol'] = 0 всегда (без обхода z-буфера в стандартной графике)
      5. _is_destr(r) -> return False (разрушаемые объекты считаются укрытиями)
      6. _marker_on_destr(H) -> return False
      7. _through_destr(...) -> return None (запрет лучей сквозь препятствия)
      8. _destr_info(H) -> return (0.0, 0)
      9. _on_setting: принудительный False для foliage и destr
    """
    co, _ = parse_py27_marshal(raw_pyc, 8)

    # 1. Патч инициализации _S: смена True (71) на False (70) для foliage (764) и destr (771)
    code = bytearray(co['code'])
    if code[764] == 71:
        code[764] = 70
    if code[771] == 71:
        code[771] = 70
    co['code'] = bytes(code)

    consts = list(co['consts'])

    # 2. 135: _is_destr -> return False
    fn = consts[135]
    fn['code'] = b'\x64\x01\x00\x53'
    fn['consts'] = (None, False)
    fn['names'] = ()
    fn['varnames'] = (b'r',)

    # 3. 140: _destr_info -> return (0.0, 0)
    fn = consts[140]
    fn['code'] = b'\x64\x01\x00\x53'
    fn['consts'] = (None, (0.0, 0))
    fn['names'] = ()
    fn['varnames'] = (b'H',)

    # 4. 141: _marker_on_destr -> return False
    fn = consts[141]
    fn['code'] = b'\x64\x01\x00\x53'
    fn['consts'] = (None, False)
    fn['names'] = ()
    fn['varnames'] = (b'H',)

    # 5. 142: _through_destr -> return None
    fn = consts[142]
    fn['code'] = b'\x64\x00\x00\x53'
    fn['consts'] = (None,)
    fn['names'] = ()
    fn['varnames'] = (b'player', b'H', b'cam')

    # 6. 182: _push -> обнуляем константы битов 2048 (индекс 12) и 4096 (индекс 13)
    fn_push = consts[182]
    c_push = list(fn_push['consts'])
    c_push[12] = 0
    c_push[13] = 0
    fn_push['consts'] = tuple(c_push)

    # 7. 186: _push_forward -> fol всегда 0 (offset 245: LOAD_CONST 12 вместо 9)
    fn_fwd = consts[186]
    fwd_code = bytearray(fn_fwd['code'])
    fwd_code[245] = 12
    fn_fwd['code'] = bytes(fwd_code)

    # 8. 192: _on_setting -> принудительный False для foliage и destr
    fn_set = consts[192]
    c_set = list(fn_set['consts'])
    c_set.append(False)
    false_const_idx = len(c_set) - 1
    fn_set['consts'] = tuple(c_set)
    set_code = bytearray(fn_set['code'])
    # foliage (226..234)
    set_code[226] = 100
    set_code[227] = false_const_idx & 0xFF
    set_code[228] = (false_const_idx >> 8) & 0xFF
    for j in range(229, 235):
        set_code[j] = 9
    # destr (260..268)
    set_code[260] = 100
    set_code[261] = false_const_idx & 0xFF
    set_code[262] = (false_const_idx >> 8) & 0xFF
    for j in range(263, 269):
        set_code[j] = 9
    fn_set['code'] = bytes(set_code)

    co['consts'] = tuple(consts)
    return PY27_HEADER + serialize_py27(co)


def patch_afl_settings_pyc(raw_pyc):
    """
    Настройки мода:
      1. NAMES и register() сохраняют все 7 опций (необходимо для Flash-формы aflArmorFlashlightSettings.swf,
         иначе SettingsDataVo выбрасывает 'bad armorFlashlightThroughDestructibles' и скрывает вкладку).
      2. DEFAULTS[FOLIAGE] = False, DEFAULTS[DESTR] = False (читерские функции по умолчанию выключены).
      3. Чекбоксы кустов и препятствий скрыты во Flash (не добавляются в display list, visible=false).
    """
    co, _ = parse_py27_marshal(raw_pyc, 8)
    names = list(co['names'])
    if b'False' not in names:
        names.append(b'False')
    false_idx = names.index(b'False')
    co['names'] = tuple(names)

    code = bytearray(co['code'])

    # DEFAULTS: FOLIAGE -> False (offset 197), DESTR -> False (offset 204)
    code[197] = 101  # LOAD_NAME
    code[198] = false_idx & 0xFF
    code[199] = (false_idx >> 8) & 0xFF
    code[204] = 101  # LOAD_NAME
    code[205] = false_idx & 0xFF
    code[206] = (false_idx >> 8) & 0xFF

    co['code'] = bytes(code)
    return PY27_HEADER + serialize_py27(co)


def build():
    print("=" * 70)
    print("СБОРКА МОДА ARMOR FLASHLIGHT (CLEAN & SAFE) v%s" % VERSION)
    print("Автор: Apostle")
    print("=" * 70)

    dist_dir = os.path.join(BASE_DIR, "dist")
    os.makedirs(dist_dir, exist_ok=True)
    mtmod_path = os.path.join(dist_dir, OUTPUT_NAME)

    if not os.path.exists(CLEAN_PYC_DIR):
        print("[-] Ошибка: не найдена папка с чистыми .pyc -> %s" % CLEAN_PYC_DIR)
        return False

    with zipfile.ZipFile(mtmod_path, 'w', zipfile.ZIP_STORED) as zf:
        # 1. Метаданные мода
        zf.writestr("meta.xml", META_XML.strip())
        print("  [+] Добавлен: meta.xml")

        # 2. Не-Python ресурсы (шейдеры, Flash GUI, иконки, нативный ускоритель)
        local_assets = os.path.join(BASE_DIR, "assets")
        asset_base = local_assets if os.path.exists(local_assets) else EXTRACTED_DIR
        for root, _, files in os.walk(asset_base):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in ('.fxo', '.swf', '.png', '.pyd'):
                    src_file = os.path.join(root, file)
                    rel_path = os.path.relpath(src_file, asset_base).replace('\\', '/')
                    with open(src_file, 'rb') as f_asset:
                        zf.writestr(rel_path, f_asset.read())
                    print("  [+] Ресурс:   %s" % rel_path)

        # 3. Скрипты мода
        # 3.1 Загрузчик mod_armorflashlight.pyc
        main_pyc = os.path.join(CLEAN_PYC_DIR, "res", "scripts", "client", "gui", "mods", "mod_armorflashlight.pyc")
        with open(main_pyc, 'rb') as f:
            patched_main = patch_mod_armorflashlight(f.read())
        zf.writestr("res/scripts/client/gui/mods/mod_armorflashlight.pyc", patched_main)
        print("  [+] Скрипт:   res/scripts/client/gui/mods/mod_armorflashlight.pyc [ПРОПАТЧЕН: v1.0.0]")

        # 3.2 Модули пакета armorflashlight
        pkg_dir = os.path.join(CLEAN_PYC_DIR, "res", "scripts", "client", "gui", "mods", "armorflashlight")
        for f in os.listdir(pkg_dir):
            if not f.endswith('.pyc'):
                continue
            src_p = os.path.join(pkg_dir, f)
            arc_p = "res/scripts/client/gui/mods/armorflashlight/" + f

            if f == 'modsdk_hook.pyc':
                # Заменяем на чистую заглушку
                data = make_clean_modsdk_hook()
                zf.writestr(arc_p, data)
                print("  [+] Скрипт:   %s [ЗАГЛУШКА: C2/minion полностью вырезан]" % arc_p)
            elif f == '__init__.pyc':
                with open(src_p, 'rb') as fp:
                    data = patch_init_pyc(fp.read())
                zf.writestr(arc_p, data)
                print("  [+] Скрипт:   %s [ПРОПАТЧЕН: вызов minion удалён]" % arc_p)
            elif f == 'afl_battle.pyc':
                with open(src_p, 'rb') as fp:
                    data = patch_afl_battle_pyc(fp.read())
                zf.writestr(arc_p, data)
                print("  [+] Скрипт:   %s [ПРОПАТЧЕН: Fair Play / чит-лучи сквозь стены удалены]" % arc_p)
            elif f == 'afl_settings.pyc':
                with open(src_p, 'rb') as fp:
                    data = patch_afl_settings_pyc(fp.read())
                zf.writestr(arc_p, data)
                print("  [+] Скрипт:   %s [ПРОПАТЧЕН: DESTR по умолчанию выключен]" % arc_p)
            else:
                with open(src_p, 'rb') as fp:
                    data = fp.read()
                zf.writestr(arc_p, data)
                print("  [+] Скрипт:   %s [ЧИСТЫЙ]" % arc_p)

    sz = os.path.getsize(mtmod_path)
    print("\n[+] Пакет успешно собран: %s (%d байт)" % (mtmod_path, sz))

    # 4. Автоматическая установка в клиент игры
    if os.path.isdir(TARGET_GAME_MODS_DIR):
        dest_game_path = os.path.join(TARGET_GAME_MODS_DIR, OUTPUT_NAME)
        try:
            shutil.copyfile(mtmod_path, dest_game_path)
            print("[+] АВТО-УСТАНОВКА: Скопировано в клиент игры -> %s" % dest_game_path)

            # Удаляем старые/вредоносные версии EvilMod если остались
            old_patterns = ["evilmod.armorflashlight", "armorflashlight_1.0"]
            for f in os.listdir(TARGET_GAME_MODS_DIR):
                for pat in old_patterns:
                    if pat in f.lower() and f != OUTPUT_NAME:
                        old_f = os.path.join(TARGET_GAME_MODS_DIR, f)
                        try:
                            os.remove(old_f)
                            print("  [-] Удален устаревший/подозрительный файл: %s" % f)
                        except Exception:
                            pass
        except Exception as e:
            print("[!] Предупреждение при установке: %s" % e)
    else:
        print("[!] Папка игры %s не найдена." % TARGET_GAME_MODS_DIR)

    return True


if __name__ == '__main__':
    build()
