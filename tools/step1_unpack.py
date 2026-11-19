# -*- coding: utf-8 -*-
"""
=============================================================================
ШАГ 1: Распаковка игрового контейнера .mtmod / .wotmod (Мир Танков / WoT)
=============================================================================
Модификации для Мира Танков (.mtmod) и World of Tanks (.wotmod) представляют
собой обычные ZIP-архивы без сжатия или с Deflate-сжатием.

Скрипт:
  1. Автоматически находит файл .mtmod/.wotmod в текущей или родительской папке.
  2. Распаковывает архив в директорию `extracted/`.
  3. Собирает статистику по типам ресурсов (Python .pyc, шейдеры .fxo, UI .swf/.png, нативные .pyd).
"""

import os
import sys
import glob
import zipfile


def find_default_mod():
    """Поиск мода в текущей и родительской директориях"""
    candidates = []
    for pattern in ('*.mtmod', '*.wotmod'):
        candidates.extend(glob.glob(pattern))
        candidates.extend(glob.glob(os.path.join('..', pattern)))
    if candidates:
        return candidates[0]
    return 'evilmod.armorflashlight_1.0.38.mtmod'


def unpack_archive(mod_path, output_dir):
    if not os.path.exists(mod_path):
        print(f"[-] Ошибка: файл не найден -> {mod_path}")
        return False

    print(f"[*] Открытие архива: {mod_path}")
    print(f"[*] Папка назначения: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)

    with zipfile.ZipFile(mod_path, 'r') as zf:
        infolist = zf.infolist()
        total_size = sum(info.file_size for info in infolist)
        print(f"[*] Файлов в архиве: {len(infolist)} (общий объём: {total_size / (1024*1024):.2f} МБ)")

        pyc_count = 0
        shader_count = 0
        ui_count = 0
        native_count = 0
        other_count = 0

        for info in infolist:
            zf.extract(info, output_dir)
            name = info.filename.lower()
            if name.endswith('.pyc'):
                pyc_count += 1
            elif name.endswith('.fxo'):
                shader_count += 1
            elif name.endswith('.swf') or name.endswith('.png'):
                ui_count += 1
            elif name.endswith('.pyd') or name.endswith('.dll'):
                native_count += 1
            else:
                other_count += 1

    print("\n[+] Распаковка завершена успешно!")
    print(f"    - Скрипты Python (.pyc)         : {pyc_count}")
    print(f"    - Шейдеры DirectX (.fxo)        : {shader_count}")
    print(f"    - Элементы UI (.swf, .png)      : {ui_count}")
    print(f"    - Нативные библиотеки (.pyd)    : {native_count}")
    print(f"    - Прочие файлы                  : {other_count}")
    print(f"\n[i] Все файлы сохранены в: {os.path.abspath(output_dir)}")
    return True


if __name__ == '__main__':
    target_mod = sys.argv[1] if len(sys.argv) > 1 else find_default_mod()
    target_out = sys.argv[2] if len(sys.argv) > 2 else 'extracted'

    print("=" * 70)
    print("ШАГ 1: РАСПАКОВКА АРХИВА МОДА")
    print("=" * 70)
    success = unpack_archive(target_mod, target_out)
    if not success:
        sys.exit(1)
