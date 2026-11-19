# -*- coding: utf-8 -*-
"""
=============================================================================
ШАГ 2: Снятие многослойной защиты байткода Python 2.7 (OWG-SEAL + PjOrion)
=============================================================================
Скрипт рекурсивно обходит распакованные файлы .pyc и снимает протекторы:
  1. Внешний слой: OWG-SEAL (native_shim).
     Декодирование Base64 -> Расшифровка потоковым шифром SHA-256 -> zlib.
  2. Внутренний слой: PjOrion Protector.
     zlib -> Инверсия бит (bit-reversal) по таблице LUT -> Дешифрование XOR ключом.

Результат: чистый байткод Python 2.7 (Magic 03f30d0a), сохраняемый в папку `clean_pyc/`.
"""

import os
import sys
import glob

# Подключение локального модуля утилит
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from deobf_utils import full_unwrap, parse_py27_marshal


def deobfuscate_all(input_dir, output_dir):
    if not os.path.exists(input_dir):
        print(f"[-] Ошибка: папка не найдена -> {input_dir}")
        print("    Сначала запустите шаг 1 (step1_unpack.py)")
        return False

    print(f"[*] Сканирование защищённых файлов в: {input_dir}")
    print(f"[*] Целевая папка для чистых .pyc: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)

    pyc_files = glob.glob(os.path.join(input_dir, '**', '*.pyc'), recursive=True)
    if not pyc_files:
        print(f"[-] Не найдено ни одного файла .pyc в {input_dir}")
        return False

    print(f"[*] Найдено скомпилированных скриптов: {len(pyc_files)}\n")

    success_count = 0
    err_count = 0

    for pyc_path in pyc_files:
        rel_path = os.path.relpath(pyc_path, input_dir)
        # Убираем возможный длинный путь res/scripts/... для удобства, либо сохраняем структуру
        out_path = os.path.join(output_dir, rel_path)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        try:
            with open(pyc_path, 'rb') as f:
                raw_bytes = f.read()

            clean_bytes = full_unwrap(raw_bytes)

            with open(out_path, 'wb') as f:
                f.write(clean_bytes)

            # Проверка читаемости заголовка и имени модуля
            info = ""
            try:
                res, _ = parse_py27_marshal(clean_bytes, 8)
                mod_name = res.get('name', b'').decode('ascii', errors='ignore')
                fn = res.get('filename', b'').decode('ascii', errors='ignore')
                info = f" [модуль: {mod_name or fn}]"
            except Exception:
                pass

            print(f"  [+] {rel_path} ({len(raw_bytes)} -> {len(clean_bytes)} байт){info}")
            success_count += 1
        except Exception as e:
            print(f"  [-] Ошибка обработки {rel_path}: {e}")
            err_count += 1

    print("\n" + "=" * 70)
    print(f"[+] Деобфускация завершена! Успешно: {success_count}, Ошибок: {err_count}")
    print(f"[i] Чистые .pyc сохранены в: {os.path.abspath(output_dir)}")
    return success_count > 0


if __name__ == '__main__':
    in_dir = sys.argv[1] if len(sys.argv) > 1 else 'extracted'
    out_dir = sys.argv[2] if len(sys.argv) > 2 else 'clean_pyc'

    print("=" * 70)
    print("ШАГ 2: ДЕОБФУСКАЦИЯ БАЙТКОДА (СНЯТИЕ ЗАЩИТЫ)")
    print("=" * 70)
    ok = deobfuscate_all(in_dir, out_dir)
    if not ok:
        sys.exit(1)
