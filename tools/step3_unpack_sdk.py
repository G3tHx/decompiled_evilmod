# -*- coding: utf-8 -*-
"""
=============================================================================
ШАГ 3: Извлечение скрытого сетевого ядра EvilMod SDK из modsdk_hook
=============================================================================
Файл `modsdk_hook.pyc` содержит замаскированный словарь `_SDK_B64`, в котором
в виде Base64-строк спрятаны 12 независимых модулей SDK:
  - agent     : Сетевой координатор ("миньон") в ботнете мода
  - anti      : Сканер античитов, отладчиков и хуков (Frida, Cheat Engine, PyDev)
  - attest    : Криптографическая аттестация клиента
  - crypto    : AES, HMAC и сессионные шифры
  - hwid      : Сбор аппаратного отпечатка железа (SMBIOS, серийные номера дисков)
  - importer  : RCE-загрузчик с удалённого C2 сервера в рантайме (sys.meta_path hook)
  - io        : Сетевой транспорт (WebSocket / TCP)
  - keywrap   : Защита и упаковка сессионных ключей
  - pin       : SSL Pinning и валидация сертификатов
  - protocol  : Бинарный протокол взаимодействия с сервером EvilMod
  - session   : Менеджер игровых сессий и аккаунтов
  - __init__  : Инициализатор SDK ядра

Скрипт:
  1. Извлекает все Base64-модули из констант `modsdk_hook.pyc`.
  2. Снимает внутреннюю обфускацию PjOrion с каждого модуля SDK.
  3. Сохраняет чистые .pyc в папку `clean_sdk/`.
"""

import os
import sys
import glob
import base64

# Подключение локального модуля утилит
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from deobf_utils import parse_py27_marshal, full_unwrap, ensure_pyc_header


# Описания модулей для информирования пользователя
SDK_DESCRIPTIONS = {
    'importer': 'КРИТИЧЕСКИЙ РИСК: Загрузка и выполнение внешнего байткода (RCE) с C2 сервера',
    'hwid':     'ВЫСОКИЙ РИСК: Снятие серийников дисков, SMBIOS и железа компьютера',
    'anti':     'ВЫСОКИЙ РИСК: Сканирование запущенных процессов и DLL на наличие отладчиков',
    'agent':    'СРЕДНИЙ РИСК: Передача данных арены/боя и координация миньонов EvilMod',
    'session':  'СРЕДНИЙ РИСК: Управление сетевой сессией и токенами игрока',
    'io':       'Транспортный уровень: WebSocket и TCP клиент для связи с evilmod.me',
    'protocol': 'Бинарный протокол сериализации пакетов',
    'crypto':   'Криптография: шифрование сетевого трафика',
    'keywrap':  'Управление сессионными ключами шифрования',
    'pin':      'SSL Pinning (защита от перехвата трафика через Charles/Fiddler)',
    'attest':   'Проверка целостности клиента и отправка отчётов на сервер',
    '__init__': 'Точка входа и инициализация внутренних сервисов SDK'
}


def find_modsdk_hook(clean_dir):
    """Поиск файла modsdk_hook.pyc в директории чистых .pyc"""
    if os.path.isfile(clean_dir) and 'modsdk_hook' in clean_dir:
        return clean_dir
    candidates = glob.glob(os.path.join(clean_dir, '**', '*modsdk_hook*.pyc'), recursive=True)
    if candidates:
        return candidates[0]
    return None


def extract_and_unpack_sdk(hook_pyc_path, output_sdk_dir):
    if not hook_pyc_path or not os.path.exists(hook_pyc_path):
        print(f"[-] Ошибка: modsdk_hook.pyc не найден по пути: {hook_pyc_path}")
        print("    Убедитесь, что шаг 2 (step2_deobfuscate.py) был выполнен.")
        return False

    print(f"[*] Анализ файла: {hook_pyc_path}")
    print(f"[*] Папка для чистых модулей SDK: {output_sdk_dir}")
    os.makedirs(output_sdk_dir, exist_ok=True)

    with open(hook_pyc_path, 'rb') as f:
        data = f.read()

    res, _ = parse_py27_marshal(data, 8)
    consts = res.get('consts', [])

    extracted = {}

    # Поиск пар (base64_data, module_name) в константах маршалла
    for i, c in enumerate(consts):
        if isinstance(c, bytes) and len(c) > 50:
            try:
                decoded = base64.b64decode(c)
                # Проверяем, является ли decoded байткодом Python (маршаллинг 'c' или pyc header)
                if decoded.startswith(b'c') or decoded.startswith(b'\x03\xf3\r\n'):
                    # Имя модуля обычно находится в следующей или предыдущей константе
                    mod_name = None
                    for adj in (i + 1, i - 1):
                        if 0 <= adj < len(consts):
                            val = consts[adj]
                            if isinstance(val, bytes):
                                val_str = val.decode('ascii', errors='ignore')
                            elif isinstance(val, str):
                                val_str = val
                            else:
                                val_str = ''
                            if val_str and val_str not in ('evilmod.armorflashlight', 'hooked') and len(val_str) < 40:
                                mod_name = val_str
                                break
                    if not mod_name:
                        mod_name = f"unknown_mod_{i}"

                    extracted[mod_name] = decoded
            except Exception:
                pass

    if not extracted:
        print("[-] Не удалось найти встроенные модули SDK в modsdk_hook.pyc.")
        return False

    print(f"[+] Обнаружено {len(extracted)} скрытых модулей SDK! Снятие защиты PjOrion...\n")

    success_count = 0
    for name, raw_pyc in extracted.items():
        try:
            # Снимаем защиту PjOrion со скрытого модуля
            clean_pyc = full_unwrap(raw_pyc)
            out_file = os.path.join(output_sdk_dir, f"{name}.pyc")
            with open(out_file, 'wb') as f_out:
                f_out.write(clean_pyc)

            desc = SDK_DESCRIPTIONS.get(name, 'Внутренний вспомогательный модуль')
            print(f"  [+] {name:<12s} ({len(clean_pyc):6d} байт) -> {desc}")
            success_count += 1
        except Exception as e:
            print(f"  [-] Ошибка деобфускации модуля {name}: {e}")

    print("\n" + "=" * 70)
    print(f"[+] Извлечение SDK завершено: {success_count} из {len(extracted)} модулей успешно распакованы.")
    print(f"[i] Модули SDK сохранены в: {os.path.abspath(output_sdk_dir)}")
    return True


if __name__ == '__main__':
    clean_base = sys.argv[1] if len(sys.argv) > 1 else 'clean_pyc'
    out_sdk = sys.argv[2] if len(sys.argv) > 2 else 'clean_sdk'

    print("=" * 70)
    print("ШАГ 3: ИЗВЛЕЧЕНИЕ И ДЕОБФУСКАЦИЯ СЕТЕВОГО SDK")
    print("=" * 70)

    target_hook = find_modsdk_hook(clean_base)
    if not target_hook:
        # Проверяем fallback путь
        fallback = os.path.join(clean_base, 'armorflashlight', 'modsdk_hook.pyc')
        if os.path.exists(fallback):
            target_hook = fallback
        else:
            print(f"[-] Файл modsdk_hook.pyc не найден в {clean_base}")
            sys.exit(1)

    ok = extract_and_unpack_sdk(target_hook, out_sdk)
    if not ok:
        sys.exit(1)
