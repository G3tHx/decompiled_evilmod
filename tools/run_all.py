# -*- coding: utf-8 -*-
"""
=============================================================================
             ВСЁ-В-ОДНОМ (RUN ALL): ПОЛНЫЙ ЦИКЛ РАЗБОРА МОДА
=============================================================================
Этот скрипт объединяет все 4 шага в единый автоматический процесс:
  [1] Распаковка .mtmod / .wotmod архива.
  [2] Снятие защитных слоёв OWG-SEAL и PjOrion.
  [3] Извлечение и расшифровка скрытого SDK ядра (12 модулей).
  [4] Расшифровка XOR-строк и декомпиляция байткода Python 2.7 в .py.

Использование:
  python run_all.py
  или
  python run_all.py evilmod.armorflashlight_1.0.38.mtmod
"""

import os
import sys
import time

# Импорт шагов
from step1_unpack import unpack_archive, find_default_mod
from step2_deobfuscate import deobfuscate_all
from step3_unpack_sdk import extract_and_unpack_sdk, find_modsdk_hook
from step4_decompile import decompile_all


def run_pipeline(mod_path=None, base_out="output"):
    start_time = time.time()

    if not mod_path:
        mod_path = find_default_mod()

    if not os.path.exists(mod_path):
        print(f"[-] Файл мода не найден: {mod_path}")
        print("    Пожалуйста, укажите путь к файлу .mtmod или .wotmod")
        return False

    print("=" * 80)
    print("      АВТОМАТИЧЕСКИЙ РАЗБОР И ДЕКОМПИЛЯЦИЯ ИГРОВОГО МОДА (МИР ТАНКОВ)")
    print("=" * 80)
    print(f"[*] Целевой файл мода : {os.path.abspath(mod_path)}")
    print(f"[*] Папка результатов : {os.path.abspath(base_out)}\n")

    dir_extracted = os.path.join(base_out, "1_extracted")
    dir_clean_pyc = os.path.join(base_out, "2_clean_pyc")
    dir_clean_sdk = os.path.join(base_out, "3_clean_sdk")
    dir_decompiled = os.path.join(base_out, "4_decompiled_src")

    # ШАГ 1
    print("\n" + "=" * 80)
    print(">>> ШАГ 1: РАСПАКОВКА АРХИВА")
    print("=" * 80)
    if not unpack_archive(mod_path, dir_extracted):
        print("[-] Ошибка на шаге 1. Прерывание.")
        return False

    # ШАГ 2
    print("\n" + "=" * 80)
    print(">>> ШАГ 2: ДЕОБФУСКАЦИЯ БАЙТКОДА (СНЯТИЕ OWG-SEAL И PjOrion)")
    print("=" * 80)
    if not deobfuscate_all(dir_extracted, dir_clean_pyc):
        print("[-] Ошибка на шаге 2. Прерывание.")
        return False

    # ШАГ 3
    print("\n" + "=" * 80)
    print(">>> ШАГ 3: ИЗВЛЕЧЕНИЕ И РАСПАКОВКА СКРЫТОГО МОДУЛЯ SDK")
    print("=" * 80)
    hook_pyc = find_modsdk_hook(dir_clean_pyc)
    if not hook_pyc:
        print("[-] Предупреждение: modsdk_hook.pyc не обнаружен, пропускаем извлечение SDK.")
    else:
        extract_and_unpack_sdk(hook_pyc, dir_clean_sdk)

    # ШАГ 4
    print("\n" + "=" * 80)
    print(">>> ШАГ 4: ДЕКОМПИЛЯЦИЯ В ЧИТАЕМЫЙ PYTHON (.py)")
    print("=" * 80)
    decompile_all(dir_clean_pyc, dir_clean_sdk, dir_decompiled)

    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"[+] ВСЕ ОПЕРАЦИИ УСПЕШНО ВЫПОЛНЕНЫ ЗА {elapsed:.2f} сек.!")
    print("=" * 80)
    print(f"  [1] Распакованные ресурсы : {os.path.abspath(dir_extracted)}")
    print(f"  [2] Чистый байткод (.pyc) : {os.path.abspath(dir_clean_pyc)}")
    print(f"  [3] Чистые модули SDK     : {os.path.abspath(dir_clean_sdk)}")
    print(f"  [4] ИСХОДНЫЙ КОД (.py)    : {os.path.abspath(dir_decompiled)}")
    print("=" * 80)
    return True


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else None
    out = sys.argv[2] if len(sys.argv) > 2 else 'output'
    run_pipeline(target, out)
