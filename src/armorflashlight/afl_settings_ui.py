# uncompyle6 version 3.9.3
# Python bytecode version base 2.7 (62211)
# Decompiled from: Python 3.10.0 (tags/v3.10.0:b494f59, Oct  4 2021, 19:00:18) [MSC v.1929 64 bit (AMD64)]
# Embedded file name: scripts/client/gui/mods/armorflashlight/afl_settings_ui.py
# Compiled at: 2026-01-01 03:00:00
import ResMgr, afl_settings as S, log as L
SWF = 'aflArmorFlashlightSettings.swf'
PULL = 'afl:armorFlashlightData'
GROUP = 'armorFlashlight'
TAB_LABEL = u'\u0x4340x4410x4320x4350x4420x43a0x430 0x4310x4400x43e0x43d0x438'
BUILD_CLIENT = '1.46.0.0'
_state = {'hooked': False, 'listening': False}

def _dotted(text):
    import re
    m = re.search('(\\d+(?:\\.\\d+){3})', text or '')
    if m:
        return m.group(1)
    else:
        return


def client_matches():
    """(ok, client, build): the running client is the one the settings tab was built for (the dotted version; a hotfix build
    number after '#' is ignored)"""
    build = _dotted(BUILD_CLIENT)
    try:
        import helpers
        client = _dotted(helpers.getClientVersion())
    except Exception:
        client = None

    return (
     build is None or client is None or build == client, client, build)


def pack():
    core = S.register()
    return {'settings': (core.packSettings(S.NAMES)), 'tabLabel': TAB_LABEL}


def _load(app):
    try:
        if app is not None and app.initialized:
            app.as_loadLibrariesS([SWF])
    except Exception:
        import traceback
        traceback.print_exc()

    return


def _on_app_initialized(event):
    from gui.app_loader.settings import APP_NAME_SPACE
    from helpers import dependency
    from skeletons.gui.app_loader import IAppLoader
    if event.ns in APP_NAME_SPACE.RANGE:
        _load(dependency.instance(IAppLoader).getApp(event.ns))
    return


def _hook():
    from gui.Scaleform.daapi.view.common.settings.SettingsParams import SettingsParams
    from gui.Scaleform.daapi.view.common.settings.SettingsWindow import SettingsWindow
    if _state['hooked']:
        return
    import weakref
    init, on_change = SettingsWindow.__init__, SettingsWindow.onSettingsChange
    preview, apply_ = SettingsParams.preview, SettingsParams.apply

    def _pull():
        try:
            return pack()
        except Exception:
            import traceback
            traceback.print_exc()
            return

        return

    def __init__(self, *args, **kwargs):
        init(self, *args, **kwargs)
        ref = weakref.ref(self)

        def onSettingsChange(settingName, settingValue):
            if settingName == PULL:
                return _pull()
            else:
                w = ref()
                if w is not None:
                    return type(w).onSettingsChange(w, settingName, settingValue)
                return

        self.onSettingsChange = onSettingsChange
        return

    def onSettingsChange(self, settingName, settingValue):
        if settingName == PULL:
            return _pull()
        return on_change(self, settingName, settingValue)

    def previewSetting(self, settingName, value):
        if settingName == GROUP and isinstance(value, dict):
            for name, v in value.items():
                if name in S.NAMES:
                    preview(self, name, v)

            return None
        return preview(self, settingName, value)

    def applySettings(self, diff, restartApproved):
        sub = diff.get(GROUP) if isinstance(diff, dict) else None
        if isinstance(sub, dict):
            diff = dict(diff)
            del diff[GROUP]
            diff.update((k, v) for k, v in sub.iteritems() if k in S.NAMES)
        return apply_(self, diff, restartApproved)

    dispose = SettingsWindow._dispose

    def _dispose(self):
        try:
            from helpers import dependency
            from skeletons.account_helpers.settings_core import ISettingsCore
            cont = dependency.instance(ISettingsCore).options
            for name in S.NAMES:
                if cont is not None and name in cont.indices:
                    opt = cont.getSetting(name)
                    if getattr(opt, 'valueReal', None) is not None:
                        opt.revert()

        except Exception:
            import traceback
            traceback.print_exc()

        return dispose(self)

    SettingsWindow.__init__ = __init__
    SettingsWindow._dispose = _dispose
    SettingsWindow.onSettingsChange = onSettingsChange
    SettingsParams.preview = previewSetting
    SettingsParams.apply = applySettings
    _state['hooked'] = True
    return


def install():
    S.load()
    if not ResMgr.isFile('gui/flash/' + SWF):
        L.note('afl', 'settings tab: gui/flash/%s missing, no Подсветка брони tab in the settings' % SWF)
        return
    ok, client, build = client_matches()
    if not ok:
        L.note('afl', 'settings tab OFF: built for client %s, this is %s (the stock settings window is left alone)' % (build, client))
        import runtime
        runtime.notify(u'\u0x4340x4410x4320x4350x4420x43a0x430 0x4310x4400x43e0x43d0x438: 0x43c0x43e0x434 0x4410x43e0x4310x4400x4300x43d 0x4340x43b0x44f 0x43a0x43b0x4380x4350x43d0x4420x430 %s, 0x443 0x4320x4300x441 %s. 0x4120x43a0x43b0x4300x4340x43a0x430 0x43d0x4300x4410x4420x4400x43e0x4350x43a 0x43e0x4420x43a0x43b0x44e0x4470x4350x43d0x430, 0x4470x4420x43e0x4310x44b 0x43d0x435 0x43b0x43e0x43c0x4300x4420x44c 0x43e0x43a0x43d0x43e 0x43d0x4300x4410x4420x4400x43e0x4350x43a 0x4380x4330x4400x44b; 0x43e0x4310x43d0x43e0x4320x4380x4420x435 0x43c0x43e0x434.' % (
         build, client))
        return
    L.note('afl', 'settings tab: client %s, build %s -> on' % (client, build or 'dev copy'))
    _hook()
    from gui.app_loader.settings import APP_NAME_SPACE
    from gui.shared import EVENT_BUS_SCOPE, g_eventBus
    from gui.shared.events import AppLifeCycleEvent
    from helpers import dependency
    from skeletons.gui.app_loader import IAppLoader
    if not _state['listening']:
        g_eventBus.addListener(AppLifeCycleEvent.INITIALIZED, _on_app_initialized, scope=EVENT_BUS_SCOPE.GLOBAL)
        _state['listening'] = True
    loader = dependency.instance(IAppLoader)
    for ns in APP_NAME_SPACE.RANGE:
        _load(loader.getApp(ns))

    return


return
