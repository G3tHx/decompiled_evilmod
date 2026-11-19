# -*- coding: utf-8 -*-
"""
Утилиты для анализа, деобфускации и сериализации байткода Python 2.7 (BigWorld / Mir Tankov).
Используется скриптами step2, step3, step4 и run_all.
"""

import struct
import zlib
import base64
import hashlib

# Магический заголовок Python 2.7 (Magic 03f30d0a + 4 байта timestamp/padding)
PY27_HEADER = b'\x03\xf3\r\n\x00\x00\x00\x00'

# Таблица зеркального переворота бит (Look-Up Table) для алгоритма PjOrion
LUT = bytes([int(bin(b)[2:].rjust(8, '0')[::-1], 2) for b in range(256)])

# Стандартный ключ шифрования строк EvilMod (__owg_d)
DEFAULT_OWG_KEY = b'b37bc73c3138d88ce559dde8ba89c257'


def ensure_pyc_header(data):
    """Гарантирует наличие валидного заголовка Python 2.7."""
    if data.startswith(b'\x03\xf3\r\n'):
        return data
    elif data.startswith(b'c'):
        return PY27_HEADER + data
    return PY27_HEADER + data


def parse_py27_marshal(data, pos=8, stringtable=None):
    """
    Парсер формата маршаллинга Python 2.7.
    Преобразует бинарный marshal в структуры Python (словари, кортежи, списки, байты).
    """
    if stringtable is None:
        stringtable = []

    if pos >= len(data):
        raise ValueError(f"Неожиданный конец данных в смещении {pos}")

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
        return (stringtable[ref] if ref < len(stringtable) else f'<ref:{ref}>'), pos
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
        raise ValueError(f"Неизвестный тип marshal: {tc} (0x{ord(tc):02x}) в позиции {pos-1}")


def serialize_py27(obj):
    """Сериализует AST/структуры Python обратно в бинарный marshal Python 2.7."""
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
        raise ValueError(f"Невозможно сериализовать объект типа {type(obj)}")


def unwrap_native_shim(data):
    """Снятие защиты первого уровня OWG-SEAL (native_shim)"""
    data = ensure_pyc_header(data)
    res, _ = parse_py27_marshal(data, 8)
    boot_co = res['consts'][0]

    seal_key = boot_co['consts'][2]
    seal_data = boot_co['consts'][3]
    seal_salt = boot_co['consts'][4]

    ct = base64.b64decode(seal_data)
    n = len(ct)

    ks = b''
    counter = 0
    while len(ks) < n:
        ks += hashlib.sha256(seal_key + seal_salt + str(counter).encode('ascii')).digest()
        counter += 1

    pt = bytes([ct[i] ^ ks[i] for i in range(n)])
    raw = zlib.decompress(pt)
    return ensure_pyc_header(raw)


def unwrap_pjorion(data):
    """Снятие защиты второго уровня PjOrion Protector"""
    data = ensure_pyc_header(data)
    res, _ = parse_py27_marshal(data, 8)

    data_c = None
    key_c = None
    slice_data = 50
    slice_key = 49

    for c in res['consts']:
        if isinstance(c, bytes):
            if b'__OWG_PYCOMPILE_PROTECT_DATA' in c:
                data_c = c
            elif b'__OWG_PYCOMPILE_PROTECT_KEY' in c:
                key_c = c

    if not data_c or not key_c:
        for c in res['consts']:
            if isinstance(c, bytes) and len(c) > 100:
                data_c = c
            elif isinstance(c, bytes) and 50 < len(c) < 100:
                key_c = c

    pjo_data = data_c[slice_data:]
    pjo_key = key_c[slice_key:]

    pjo_raw = zlib.decompress(pjo_data)
    pjo_bit_rev = bytes([LUT[b] for b in pjo_raw])
    pjo_decrypted = bytes([pjo_bit_rev[i] ^ pjo_key[i % len(pjo_key)] for i in range(len(pjo_bit_rev))])
    return ensure_pyc_header(pjo_decrypted)


def full_unwrap(data):
    """Рекурсивная распаковка всех слоёв защиты до чистого байткода Python 2.7"""
    curr = ensure_pyc_header(data)
    for _ in range(5):
        try:
            res, _ = parse_py27_marshal(curr, 8)
        except Exception:
            break
        fn = res.get('filename', b'')
        if isinstance(fn, bytes):
            fn = fn.decode('ascii', errors='ignore')
        names = [n.decode('ascii', errors='ignore') if isinstance(n, bytes) else str(n) for n in res.get('names', [])]

        if fn == 'native_shim':
            curr = unwrap_native_shim(curr)
        elif '<pjorion' in fn or any('PJO_' in n for n in names):
            curr = unwrap_pjorion(curr)
        else:
            break
    return ensure_pyc_header(curr)


def patch_owg_strings(co):
    """
    Рекурсивно находит вызовы функции расшифровки строк __owg_d(encrypted_bytes)
    и заменяет их на константу с уже расшифрованной строкой (LOAD_CONST + NOP).
    Это позволяет uncompyle6 генерировать читаемый и валидный исходный код.
    """
    consts = list(co.get('consts', []))
    owg_indices = {}

    for i, c in enumerate(consts):
        if isinstance(c, dict) and c.get('type') == 'code':
            if c.get('name') == b'__owg_d':
                k = None
                for sub_c in c.get('consts', []):
                    if isinstance(sub_c, bytes) and len(sub_c) == 32:
                        k = sub_c
                        break
                owg_indices[i] = k or DEFAULT_OWG_KEY
            else:
                consts[i] = patch_owg_strings(c)

    co['consts'] = consts

    if not owg_indices:
        return co

    code = bytearray(co['code'])
    i = 0
    n = len(code)
    while i <= n - 12:
        # Паттерн вызова: LOAD_CONST (owg_d), MAKE_FUNCTION, LOAD_CONST (arg), CALL_FUNCTION 1
        if (code[i] == 100 and
            code[i+3] == 132 and code[i+4] == 0 and code[i+5] == 0 and
            code[i+6] == 100 and
            code[i+9] == 131 and code[i+10] == 1 and code[i+11] == 0):

            owg_arg = code[i+1] | (code[i+2] << 8)
            enc_arg = code[i+7] | (code[i+8] << 8)

            if owg_arg in owg_indices and enc_arg < len(consts):
                k = owg_indices[owg_arg]
                enc_bytes = consts[enc_arg]
                if isinstance(enc_bytes, bytes):
                    m = len(k)
                    dec_bytes = bytes([enc_bytes[j] ^ k[j % m] for j in range(len(enc_bytes))])
                    consts[enc_arg] = dec_bytes

                    # Превращаем в LOAD_CONST <dec_arg> + NOPs
                    code[i] = 100
                    code[i+1] = enc_arg & 0xFF
                    code[i+2] = (enc_arg >> 8) & 0xFF
                    for nop_idx in range(i+3, i+12):
                        code[nop_idx] = 9  # NOP
                    i += 12
                    continue
        i += 1

    co['code'] = bytes(code)
    co['consts'] = consts
    return co
