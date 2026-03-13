"""
Claude Agent Desktop v8
• Стриминг ответов, кнопка остановки
• Сайдбар с поиском, toggle, Ctrl+N
• Браузерные инструменты (Selenium, опционально)
• Автообновление через GitHub Releases
• Temperature, DeepSeek think-фильтр
"""

import os, sys, json, shutil, threading, uuid, subprocess, platform, re
import urllib.request
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from tkinter import filedialog
import tkinter as tk

# Keyring — безопасное хранение API-ключей (опционально)
try:
    import keyring
    _KEYRING_SERVICE = "claude-agent-desktop"
    _KEYRING_USER = "api_key"
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

import customtkinter as ctk

# Drag & Drop (опционально)
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

# ============ CONSTANTS ============

APP_NAME = "Claude Agent"
APP_VERSION = "9.0"
GITHUB_REPO = "OlegBOSS11/claude-agent-desktop"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
WINDOW_SIZE = "1040x760"
MIN_SIZE = (820, 580)

# ============ LOCALIZATION ============

LANGS = {
    "Русский": {
        "new_chat": "Новый чат", "search": "🔍 Поиск...", "files": "📂 Файлы",
        "settings": "Настройки", "save": "Сохранить", "cancel": "Отмена",
        "api_key": "API ключ", "api_hint": "Ключ от ProxyAPI, OpenAI или другого провайдера",
        "model": "Модель", "model_hint": "Выберите или введите название",
        "base_url": "Base URL", "url_hint": "Выберите или введите URL",
        "output_dir": "Папка для файлов", "temperature": "Temperature",
        "temp_hint": "0 = точный, 1 = креативный. Авто для reasoning-моделей",
        "appearance": "Оформление", "theme": "Тема", "font_size": "Размер шрифта",
        "bubble_color": "Цвет ваших сообщений", "language": "Язык интерфейса",
        "you": "Вы", "assistant": "Ассистент", "thinking": "✦ Думаю...",
        "connected": "Подключен", "disconnected": "Не подключен", "reconnecting": "Переподключение",
        "no_chats": "Нет чатов", "not_found": "Ничего не найдено",
        "show": "Показать", "hide": "Скрыть",
        "hint_bar": "Enter — отправить  •  Shift+Enter — перенос  •  📎 — файл  •  /help",
        "attach_tip": "📎 Загрузить файлы:\nExcel, CSV, PDF, Word,\nизображения, текст, код",
        "agent_ready": "✓ Агент готов", "no_api_key": "⚠️ Настройки → API-ключ",
        "welcome_sub": "AI-ассистент: поиск, Excel, PDF, Word, изображения, код",
        "update_available": "🔄 Доступна версия", "download": "Скачать",
        "copy": "📋", "retry": "🔄",
        "copy_selected": "Копировать выделенное", "copy_all": "Копировать всё",
        "paste": "Вставить", "cut": "Вырезать", "select_all": "Выделить всё",
        "theme_restart": "Тема изменена",
        "settings_updated": "Настройки обновлены",
        "excel": "Excel", "pdf_word": "PDF/Word", "images": "Картинки", "code": "Код",
    },
    "English": {
        "new_chat": "New chat", "search": "🔍 Search...", "files": "📂 Files",
        "settings": "Settings", "save": "Save", "cancel": "Cancel",
        "api_key": "API key", "api_hint": "Key from ProxyAPI, OpenAI or other provider",
        "model": "Model", "model_hint": "Select or type model name",
        "base_url": "Base URL", "url_hint": "Select or type URL",
        "output_dir": "Output folder", "temperature": "Temperature",
        "temp_hint": "0 = precise, 1 = creative. Auto for reasoning models",
        "appearance": "Appearance", "theme": "Theme", "font_size": "Font size",
        "bubble_color": "Your message color", "language": "Interface language",
        "you": "You", "assistant": "Assistant", "thinking": "✦ Thinking...",
        "connected": "Connected", "disconnected": "Disconnected", "reconnecting": "Reconnecting",
        "no_chats": "No chats", "not_found": "Nothing found",
        "show": "Show", "hide": "Hide",
        "hint_bar": "Enter — send  •  Shift+Enter — new line  •  📎 — file  •  /help",
        "attach_tip": "📎 Upload files:\nExcel, CSV, PDF, Word,\nimages, text, code",
        "agent_ready": "✓ Agent ready", "no_api_key": "⚠️ Settings → API key",
        "welcome_sub": "AI assistant: search, Excel, PDF, Word, images, code",
        "update_available": "🔄 Update available", "download": "Download",
        "copy": "📋", "retry": "🔄",
        "copy_selected": "Copy selected", "copy_all": "Copy all",
        "paste": "Paste", "cut": "Cut", "select_all": "Select all",
        "theme_restart": "Theme changed",
        "settings_updated": "Settings updated",
        "excel": "Excel", "pdf_word": "PDF/Word", "images": "Images", "code": "Code",
    },
}

def T(key):
    """Получить перевод по ключу."""
    lang = _current_lang
    return LANGS.get(lang, LANGS["Русский"]).get(key, key)

_current_lang = "Русский"

if getattr(sys, 'frozen', False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent

SETTINGS_FILE = APP_DIR / "settings.json"
HISTORY_DIR = APP_DIR / "chat_history"

PRESET_MODELS = [
    "claude-opus-4-6", "claude-opus-4-5", "claude-sonnet-4-5",
    "claude-sonnet-4-20250514", "claude-3-7-sonnet-20250219",
    "claude-haiku-4-5", "claude-3-5-haiku-20241022",
]
PRESET_URLS = [
    "https://openai.api.proxyapi.ru/v1",
    "https://api.openai.com/v1",
    "https://api.anthropic.com/v1",
]

BUBBLE_COLORS = {
    "Синий": "#2563EB", "Фиолетовый": "#7C5CFC", "Зелёный": "#059669",
    "Красный": "#DC2626", "Оранжевый": "#EA580C", "Розовый": "#DB2777",
    "Бирюзовый": "#0891B2", "Серый": "#4B5563",
}

# ============ THEME ============

def _dark():
    return {
        "bg": "#0D0D0F", "bg2": "#16161A", "bg3": "#1E1E24",
        "bg_input": "#1A1A20", "border": "#2A2A32", "border_lt": "#35353F",
        "text": "#E8E8ED", "text2": "#9898A4", "text3": "#65656F",
        "bot_bg": "#1E1E24", "bot_text": "#E8E8ED",
        "accent": "#7C5CFC", "accent_h": "#6B4FE0",
        "ok": "#22C55E", "err": "#EF4444", "warn": "#F59E0B",
        "file_bg": "#1C2333", "file_bd": "#2D3A50", "link": "#60A5FA",
        "sidebar": "#111114", "sidebar_hover": "#1C1C22", "sidebar_active": "#252530",
        "user_bubble": "",  # пустой = использовать цвет из BUBBLE_COLORS
    }

def _light():
    return {
        "bg": "#FFFFFF", "bg2": "#F5F5F7", "bg3": "#EAEAEF",
        "bg_input": "#FFFFFF", "border": "#D4D4DC", "border_lt": "#C8C8D0",
        "text": "#1A1A1F", "text2": "#5A5A68", "text3": "#8A8A98",
        "bot_bg": "#F5F5F8", "bot_text": "#1A1A1F",
        "accent": "#7C5CFC", "accent_h": "#6B4FE0",
        "ok": "#16A34A", "err": "#DC2626", "warn": "#D97706",
        "file_bg": "#EFF6FF", "file_bd": "#BFDBFE", "link": "#2563EB",
        "sidebar": "#F0F0F3", "sidebar_hover": "#E5E5EA", "sidebar_active": "#D8D8E0",
        "user_bubble": "#E8E8ED",  # бледно-серый пузырь для светлой темы
    }

C = _dark()

def apply_theme(name):
    global C
    if name == "Light": C = _light(); ctk.set_appearance_mode("Light")
    elif name == "Dark": C = _dark(); ctk.set_appearance_mode("Dark")
    else:
        ctk.set_appearance_mode("System")
        C = _light() if ctk.get_appearance_mode() == "Light" else _dark()


# ============ SETTINGS ============

def _defaults():
    return {
        "api_key": "", "model": "claude-3-5-haiku-20241022",
        "base_url": PRESET_URLS[0], "output_dir": "",
        "custom_models": [], "custom_urls": [],
        "theme": "Dark", "bubble_color": "Синий",
        "font_size": 14, "sidebar_width": 210,
        "bg_image": "", "language": "Русский",
    }

def load_settings():
    d = _defaults()
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                d.update(json.load(f))
    except Exception:
        pass
    # Загружаем API-ключ из системного хранилища (keyring)
    if KEYRING_AVAILABLE:
        try:
            stored_key = keyring.get_password(_KEYRING_SERVICE, _KEYRING_USER)
            if stored_key:
                d["api_key"] = stored_key
        except Exception:
            pass
    return d

def save_settings(s):
    # Сохраняем API-ключ в системное хранилище, из файла убираем
    s_to_file = s.copy()
    if KEYRING_AVAILABLE:
        try:
            keyring.set_password(_KEYRING_SERVICE, _KEYRING_USER, s.get("api_key", ""))
            s_to_file["api_key"] = ""  # не хранить в plaintext
        except Exception:
            pass  # если keyring недоступен — fallback в файл
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(s_to_file, f, ensure_ascii=False, indent=2)
        # Ограничиваем права файла только владельцем (Unix)
        if platform.system() != "Windows":
            os.chmod(SETTINGS_FILE, 0o600)
    except Exception:
        pass

def all_models(s): return list(dict.fromkeys(PRESET_MODELS + s.get("custom_models", [])))
def all_urls(s): return list(dict.fromkeys(PRESET_URLS + s.get("custom_urls", [])))
def user_bubble(s): return BUBBLE_COLORS.get(s.get("bubble_color", "Синий"), "#2563EB")


# ============ CHAT HISTORY ============

class ChatHistory:
    def __init__(self): HISTORY_DIR.mkdir(exist_ok=True)
    def save_chat(self, cid, title, msgs):
        with open(HISTORY_DIR / f"{cid}.json", "w", encoding="utf-8") as f:
            json.dump({"id": cid, "title": title, "updated": datetime.now().isoformat(), "messages": msgs}, f, ensure_ascii=False, indent=2)
    def load_chat(self, cid):
        p = HISTORY_DIR / f"{cid}.json"
        if not p.exists(): return None
        with open(p, "r", encoding="utf-8") as f: return json.load(f)
    def list_chats(self):
        chats = []
        for f in HISTORY_DIR.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fh: d = json.load(fh)
                chats.append({"id": d.get("id", f.stem), "title": d.get("title", ""), "updated": d.get("updated", "")})
            except Exception: pass
        chats.sort(key=lambda x: x.get("updated", ""), reverse=True); return chats
    def delete_chat(self, cid):
        p = HISTORY_DIR / f"{cid}.json"
        if p.exists(): p.unlink()
    def export_chat(self, cid, fmt="md"):
        data = self.load_chat(cid)
        if not data: return None
        lines = [f"# {data.get('title','Чат')}\n", f"*{data.get('updated','')}*\n\n---\n"]
        for m in data.get("messages", []):
            s, t = m.get("sender",""), m.get("text","")
            if s == "user": lines.append(f"**Вы:**\n{t}\n")
            elif s == "bot": lines.append(f"**Ассистент:**\n{t}\n")
            else: lines.append(f"*{t}*\n")
            lines.append("---\n")
        safe = re.sub(r'[^\w\s-]', '', data.get('title','chat'))[:40].strip()
        exp = APP_DIR / "exports"; exp.mkdir(exist_ok=True)
        out = exp / f"{safe}_{cid[:8]}.{fmt}"
        with open(out, "w", encoding="utf-8") as f: f.write("\n".join(lines))
        return str(out)

hist = ChatHistory()

def open_file(fp):
    try:
        p = Path(fp)
        if not p.exists(): return
        if platform.system() == "Darwin": subprocess.Popen(["open", str(p)])
        elif platform.system() == "Windows": os.startfile(str(p))
        else: subprocess.Popen(["xdg-open", str(p)])
    except Exception: pass

def open_folder(fp):
    try:
        p = Path(fp)
        if not p.exists(): return
        if platform.system() == "Darwin": subprocess.Popen(["open", str(p)])
        elif platform.system() == "Windows": subprocess.Popen(["explorer", str(p)])
        else: subprocess.Popen(["xdg-open", str(p)])
    except Exception: pass


# ============ UPDATE SYSTEM ============

GITHUB_RAW = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main"

def check_for_updates(callback=None):
    """Проверить наличие обновлений на GitHub Releases."""
    try:
        req = urllib.request.Request(GITHUB_API, headers={
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": f"ClaudeAgent/{APP_VERSION}"
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        latest = data.get("tag_name", "").lstrip("v")
        current = APP_VERSION

        if latest and latest != current:
            if callback:
                callback({
                    "available": True,
                    "latest": latest,
                    "current": current,
                    "notes": data.get("body", "")[:200]
                })
        else:
            if callback:
                callback({"available": False, "current": current, "latest": latest})

    except Exception:
        if callback:
            callback({"available": False, "current": APP_VERSION, "error": True})


def auto_update(on_done=None):
    """Скачать обновлённые .py файлы из GitHub и перезапустить."""
    files_to_update = ["claude_agent_gui.py", "claude_agent_v3.py", "requirements.txt"]
    updated = []
    try:
        for fname in files_to_update:
            url = f"{GITHUB_RAW}/{fname}"
            req = urllib.request.Request(url, headers={
                "User-Agent": f"ClaudeAgent/{APP_VERSION}",
                "Cache-Control": "no-cache"
            })
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    new_content = resp.read()

                target = APP_DIR / fname
                # Бэкап
                if target.exists():
                    backup = APP_DIR / f"{fname}.bak"
                    shutil.copy2(target, backup)

                target.write_bytes(new_content)
                updated.append(fname)
            except Exception as e:
                print(f"Ошибка обновления {fname}: {e}")

        if on_done:
            on_done(updated)

    except Exception as e:
        if on_done:
            on_done([])


# ============ SETTINGS WINDOW ============

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, settings, on_save):
        super().__init__(parent)
        self.settings = settings.copy(); self.on_save = on_save
        self.title(T("settings")); self.geometry("540x660"); self.resizable(False, False)
        self.transient(parent); self.grab_set(); self.configure(fg_color=C["bg"])
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 540) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 620) // 2
        self.geometry(f"+{x}+{y}")
        # Scrollable content area
        scroll = ctk.CTkScrollableFrame(self, fg_color=C["bg"])
        scroll.pack(fill="both", expand=True, padx=0, pady=(0, 0))
        self._f = scroll
        # Fixed buttons at bottom (outside scroll)
        bf = ctk.CTkFrame(self, fg_color=C["bg"], height=60)
        bf.pack(fill="x", side="bottom"); bf.pack_propagate(False)
        ctk.CTkFrame(bf, height=1, fg_color=C["border"]).pack(fill="x")
        btn_inner = ctk.CTkFrame(bf, fg_color="transparent")
        btn_inner.pack(fill="x", padx=24, pady=10)
        ctk.CTkButton(btn_inner, text=T("cancel"), width=120, height=38, corner_radius=10,
            fg_color="transparent", border_width=1, border_color=C["border"],
            text_color=C["text2"], command=self.destroy).pack(side="left")
        ctk.CTkButton(btn_inner, text=T("save"), width=120, height=38, corner_radius=10,
            fg_color=C["accent"], hover_color=C["accent_h"], text_color="#FFF",
            font=ctk.CTkFont(weight="bold"), command=self._save).pack(side="right")
        self._build()

    def _build(self):
        f, P = self._f, 24
        ctk.CTkLabel(f, text=T("settings"), font=ctk.CTkFont(size=20, weight="bold"),
                      text_color=C["text"]).pack(pady=(20, 14), padx=P, anchor="w")

        # API
        self._lbl(T("api_key")); self._hint(T("api_hint"))
        self.api_entry = ctk.CTkEntry(f, placeholder_text="sk-...", show="•", height=38,
            corner_radius=10, fg_color=C["bg_input"], border_color=C["border"], text_color=C["text"])
        self.api_entry.pack(fill="x", padx=P, pady=(0, 2))
        if self.settings.get("api_key"): self.api_entry.insert(0, self.settings["api_key"])
        self._show_key = False
        self._tbtn = ctk.CTkButton(f, text=T("show"), width=80, height=22, corner_radius=6,
            fg_color="transparent", border_width=1, border_color=C["border"],
            text_color=C["text2"], font=ctk.CTkFont(size=10), command=self._toggle)
        self._tbtn.pack(anchor="e", padx=P, pady=(2, 6))

        # Model
        self._lbl(T("model")); self._hint(T("model_hint"))
        self.model_var = ctk.StringVar(value=self.settings.get("model", PRESET_MODELS[-1]))
        ctk.CTkComboBox(f, variable=self.model_var, values=all_models(self.settings),
            height=38, corner_radius=10, fg_color=C["bg_input"], border_color=C["border"],
            button_color=C["accent"], button_hover_color=C["accent_h"]).pack(fill="x", padx=P, pady=(0, 8))

        # URL
        self._lbl(T("base_url")); self._hint(T("url_hint"))
        self.url_var = ctk.StringVar(value=self.settings.get("base_url", PRESET_URLS[0]))
        ctk.CTkComboBox(f, variable=self.url_var, values=all_urls(self.settings),
            height=38, corner_radius=10, fg_color=C["bg_input"], border_color=C["border"],
            button_color=C["accent"], button_hover_color=C["accent_h"]).pack(fill="x", padx=P, pady=(0, 8))

        # Output dir
        self._lbl(T("output_dir"))
        df = ctk.CTkFrame(f, fg_color="transparent"); df.pack(fill="x", padx=P, pady=(0, 4))
        cur = self.settings.get("output_dir", "") or "./outputs"
        self.dir_label = ctk.CTkLabel(df, text=cur, font=ctk.CTkFont(size=11),
            text_color=C["text2"], fg_color=C["bg_input"], corner_radius=8, height=34, anchor="w")
        self.dir_label.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(df, text="📁", width=38, height=34, corner_radius=8,
            fg_color=C["bg3"], hover_color=C["border"], command=self._pick_dir).pack(side="right")

        # Temperature
        self._lbl(T("temperature"))
        self._hint(T("temp_hint"))
        tf = ctk.CTkFrame(f, fg_color="transparent"); tf.pack(fill="x", padx=P, pady=(0, 8))
        self.temp_val = ctk.DoubleVar(value=self.settings.get("temperature", 0))
        self.temp_label = ctk.CTkLabel(tf, text=f"{self.temp_val.get():.1f}",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=C["accent"], width=40)
        self.temp_label.pack(side="right")
        ctk.CTkSlider(tf, from_=0, to=1, number_of_steps=10,
            variable=self.temp_val, command=self._on_temp_slide,
            fg_color=C["bg3"], progress_color=C["accent"],
            button_color=C["accent"], button_hover_color=C["accent_h"]).pack(side="left", fill="x", expand=True, padx=(0, 8))

        # ---- Оформление ----
        ctk.CTkFrame(f, height=1, fg_color=C["border"]).pack(fill="x", padx=P, pady=(10, 8))
        ctk.CTkLabel(f, text=T("appearance"), font=ctk.CTkFont(size=16, weight="bold"),
                      text_color=C["text"]).pack(anchor="w", padx=P, pady=(0, 8))

        # Language
        self._lbl(T("language"))
        self.lang_var = ctk.StringVar(value=self.settings.get("language", "Русский"))
        ctk.CTkSegmentedButton(f, values=list(LANGS.keys()),
            variable=self.lang_var).pack(fill="x", padx=P, pady=(0, 10))

        # Theme
        self._lbl(T("theme"))
        self.theme_var = ctk.StringVar(value=self.settings.get("theme", "Dark"))
        ctk.CTkSegmentedButton(f, values=["Light", "System", "Dark"],
            variable=self.theme_var).pack(fill="x", padx=P, pady=(0, 10))

        # Font size
        self._lbl(T("font_size"))
        fs_frame = ctk.CTkFrame(f, fg_color="transparent"); fs_frame.pack(fill="x", padx=P, pady=(0, 8))
        self.font_val = ctk.IntVar(value=self.settings.get("font_size", 14))
        self.font_label = ctk.CTkLabel(fs_frame, text=f"{self.font_val.get()} px",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=C["accent"], width=50)
        self.font_label.pack(side="right")
        ctk.CTkSlider(fs_frame, from_=12, to=22, number_of_steps=10,
            variable=self.font_val, command=self._on_font_slide,
            fg_color=C["bg3"], progress_color=C["accent"],
            button_color=C["accent"], button_hover_color=C["accent_h"]).pack(side="left", fill="x", expand=True, padx=(0, 8))

        # Bubble color
        self._lbl(T("bubble_color"))
        cf = ctk.CTkFrame(f, fg_color="transparent"); cf.pack(fill="x", padx=P, pady=(0, 4))
        self.bubble_var = ctk.StringVar(value=self.settings.get("bubble_color", "Синий"))
        self._color_btns = {}
        for name, hx in BUBBLE_COLORS.items():
            sel = name == self.bubble_var.get()
            b = ctk.CTkButton(cf, text="", width=34, height=34, corner_radius=17,
                fg_color=hx, hover_color=hx, border_width=3 if sel else 0,
                border_color="#FFFFFF", command=lambda n=name: self._pick_bubble(n))
            b.pack(side="left", padx=2); self._color_btns[name] = b
        self.bbl_lbl = ctk.CTkLabel(f, text=self.bubble_var.get(), font=ctk.CTkFont(size=10),
            text_color=C["text3"])
        self.bbl_lbl.pack(anchor="w", padx=P, pady=(0, 12))

        # Версия
        ctk.CTkFrame(f, height=1, fg_color=C["border"]).pack(fill="x", padx=P, pady=(4, 8))
        ctk.CTkLabel(f, text=f"{APP_NAME} v{APP_VERSION}  •  github.com/{GITHUB_REPO}",
            font=ctk.CTkFont(size=10), text_color=C["text3"]).pack(anchor="w", padx=P, pady=(0, 8))

    def _lbl(self, t):
        ctk.CTkLabel(self._f, text=t, font=ctk.CTkFont(size=12, weight="bold"),
                      text_color=C["text2"]).pack(anchor="w", padx=24, pady=(0, 2))
    def _hint(self, t):
        ctk.CTkLabel(self._f, text=t, font=ctk.CTkFont(size=10),
                      text_color=C["text3"]).pack(anchor="w", padx=24, pady=(0, 3))
    def _toggle(self):
        self._show_key = not self._show_key
        self.api_entry.configure(show="" if self._show_key else "•")
        self._tbtn.configure(text=T("hide") if self._show_key else T("show"))
    def _pick_dir(self):
        d = filedialog.askdirectory(title="Папка для файлов")
        if d: self.settings["output_dir"] = d; self.dir_label.configure(text=d)
    def _on_font_slide(self, val):
        self.font_label.configure(text=f"{int(float(val))} px")
    def _on_temp_slide(self, val):
        self.temp_label.configure(text=f"{float(val):.1f}")
    def _pick_bubble(self, name):
        self.bubble_var.set(name); self.bbl_lbl.configure(text=name)
        for n, b in self._color_btns.items(): b.configure(border_width=3 if n == name else 0)
    def _save(self):
        key = self.api_entry.get().strip()
        if not key:
            self.api_entry.configure(border_color=C["err"])
            return
        model, url = self.model_var.get().strip(), self.url_var.get().strip()
        # Валидация URL
        if url and not url.startswith(("http://", "https://")):
            url = "https://" + url
            self.url_var.set(url)
        if not url:
            url = PRESET_URLS[0]
            self.url_var.set(url)
        cm = list(self.settings.get("custom_models", []))
        if model and model not in PRESET_MODELS and model not in cm: cm.append(model)
        cu = list(self.settings.get("custom_urls", []))
        if url and url not in PRESET_URLS and url not in cu: cu.append(url)
        self.settings.update({
            "api_key": key, "model": model, "base_url": url,
            "custom_models": cm, "custom_urls": cu,
            "theme": self.theme_var.get(), "bubble_color": self.bubble_var.get(),
            "font_size": int(self.font_val.get()),
            "temperature": round(float(self.temp_val.get()), 1),
            "language": self.lang_var.get(),
        })
        save_settings(self.settings); self.on_save(self.settings); self.destroy()


# ============ MAIN APP ============

# Base class: TkinterDnD if available for drag & drop support
if DND_AVAILABLE:
    class _DnDBase(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)
else:
    _DnDBase = ctk.CTk


class ChatApp(_DnDBase):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        global _current_lang
        _current_lang = self.settings.get("language", "Русский")
        apply_theme(self.settings.get("theme", "Dark"))
        self.title(APP_NAME); self.geometry(WINDOW_SIZE); self.minsize(*MIN_SIZE)
        self.configure(fg_color=C["bg"])

        self.agent = None; self.session_config = None
        self.is_processing = False
        self.attached_files: List[Path] = []
        self._thinking_frame = None
        self.chat_id = uuid.uuid4().hex[:12]
        self.chat_messages: List[Dict] = []
        self.chat_title = T("new_chat")
        self._bg_image = None; self._bg_label = None

        self._build_ui()
        if self.settings.get("api_key"):
            self.model_pill.configure(text=f"  {self.settings.get('model','?')}  ")

    def _rebuild_ui(self):
        """Пересобрать весь интерфейс (для смены темы/языка на лету)."""
        global _current_lang
        _current_lang = self.settings.get("language", "Русский")
        apply_theme(self.settings.get("theme", "Dark"))
        self.configure(fg_color=C["bg"])
        # Сохраняем сообщения
        saved_msgs = list(self.chat_messages)
        saved_id = self.chat_id
        saved_title = self.chat_title
        # Удаляем всё
        for w in self.winfo_children(): w.destroy()
        # Пересобираем
        self._build_ui()
        # Восстанавливаем чат
        self.chat_id = saved_id
        self.chat_title = saved_title
        self.chat_messages = saved_msgs
        if saved_msgs:
            for w in self.chat_scroll.winfo_children(): w.destroy()
            for m in saved_msgs:
                self._add_msg_w(m.get("text",""), m.get("sender","user"), m.get("files"))
        if self.settings.get("api_key"):
            self.model_pill.configure(text=f"  {self.settings.get('model','?')}  ")
        if self.agent:
            self.status_dot.configure(text_color=C["ok"])
            self.status_text.configure(text=T("connected"), text_color=C["ok"])

    def _fs(self): return self.settings.get("font_size", 14)
    def _f(self, delta=0): return ctk.CTkFont(size=max(self._fs() + delta, 8))
    def _fb(self, delta=0): return ctk.CTkFont(size=max(self._fs() + delta, 8), weight="bold")
    def _uc(self): return user_bubble(self.settings)
    def _get_output_dir(self):
        c = self.settings.get("output_dir", "")
        if c and Path(c).exists(): return Path(c)
        d = APP_DIR / "outputs"; d.mkdir(exist_ok=True); return d

    # ==================== BUILD ====================

    def _build_ui(self):
        self._main = ctk.CTkFrame(self, fg_color=C["bg"])
        self._main.pack(fill="both", expand=True)
        self._sidebar_visible = True

        # Sidebar
        sw = 300
        self.sidebar = ctk.CTkFrame(self._main, width=sw, fg_color=C["sidebar"], corner_radius=0)
        self.sidebar.pack(side="left", fill="y"); self.sidebar.pack_propagate(False)

        # Sidebar header: + New chat with hotkey hint
        sh = ctk.CTkFrame(self.sidebar, fg_color="transparent", height=46)
        sh.pack(fill="x"); sh.pack_propagate(False)
        hotkey = "⌘N" if platform.system() == "Darwin" else "Ctrl+N"
        nc_frame = ctk.CTkFrame(sh, fg_color=C["sidebar_hover"], corner_radius=8,
            cursor="hand2")
        nc_frame.pack(fill="x", padx=8, pady=8)
        ctk.CTkLabel(nc_frame, text=f"＋  {T('new_chat')}", font=self._fb(-2),
            text_color=C["text"], cursor="hand2").pack(side="left", padx=(10, 0), pady=4)
        ctk.CTkLabel(nc_frame, text=hotkey, font=self._f(-5),
            text_color=C["text3"], cursor="hand2").pack(side="right", padx=(0, 10), pady=4)
        nc_frame.bind("<Button-1>", lambda e: self._new_chat())
        for child in nc_frame.winfo_children():
            child.bind("<Button-1>", lambda e: self._new_chat())

        # Поиск по чатам
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._refresh_sidebar())
        self.search_entry = ctk.CTkEntry(self.sidebar, placeholder_text=T("search"),
            textvariable=self.search_var, height=30, corner_radius=8,
            fg_color=C["sidebar_hover"], border_color=C["border"], border_width=1,
            text_color=C["text"], font=self._f(-3))
        self.search_entry.pack(fill="x", padx=8, pady=(0, 6))

        ctk.CTkFrame(self.sidebar, height=1, fg_color=C["border"]).pack(fill="x")

        # Chats list
        self.chats_list = ctk.CTkScrollableFrame(self.sidebar, fg_color=C["sidebar"],
            scrollbar_button_color=C["border"], scrollbar_button_hover_color=C["border_lt"])
        self.chats_list.pack(fill="both", expand=True)

        # Sidebar bottom
        sb_bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        sb_bottom.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(sb_bottom, text=T("files"), height=28, corner_radius=8,
            fg_color=C["sidebar_hover"], hover_color=C["sidebar_active"],
            text_color=C["text2"], font=self._f(-4),
            command=lambda: open_folder(str(self._get_output_dir()))).pack(fill="x")

        # Separator line
        ctk.CTkFrame(self._main, width=1, fg_color=C["border"], corner_radius=0).pack(side="left", fill="y")

        # Right panel
        self.right = ctk.CTkFrame(self._main, fg_color=C["bg"], corner_radius=0)
        self.right.pack(side="right", fill="both", expand=True)

        # Topbar
        top = ctk.CTkFrame(self.right, height=46, fg_color=C["bg2"], corner_radius=0)
        top.pack(fill="x"); top.pack_propagate(False)

        # Toggle sidebar button (☰)
        ctk.CTkButton(top, text="☰", width=34, height=30, corner_radius=8,
            fg_color="transparent", hover_color=C["bg3"], text_color=C["text2"],
            font=self._fb(2), command=self._toggle_sidebar).pack(side="left", padx=(8, 4))

        ctk.CTkLabel(top, text="Claude Agent", font=self._fb(0),
                      text_color=C["text"]).pack(side="left", padx=(4, 0))

        self.model_pill = ctk.CTkLabel(top, text="—", font=self._f(-4),
            text_color=C["text3"], fg_color=C["bg3"], corner_radius=10, width=160, height=22)
        self.model_pill.pack(side="left", padx=8)

        # Right side of topbar
        self.status_dot = ctk.CTkLabel(top, text="●", font=self._f(-5),
            text_color=C["err"], width=14)
        self.status_dot.pack(side="right", padx=(0, 10))
        self.status_text = ctk.CTkLabel(top, text=T("disconnected"),
            font=self._f(-4), text_color=C["text3"])
        self.status_text.pack(side="right", padx=(0, 3))

        for txt, cmd in [("⚙", self._open_settings), ("💾", self._export_chat)]:
            ctk.CTkButton(top, text=txt, width=30, height=26, corner_radius=8,
                fg_color="transparent", hover_color=C["bg3"], text_color=C["text2"],
                font=self._f(-1), command=cmd).pack(side="right", padx=1)

        ctk.CTkFrame(self.right, height=1, fg_color=C["border"]).pack(fill="x")

        # Chat scroll
        self.chat_scroll = ctk.CTkScrollableFrame(self.right, fg_color=C["bg"], corner_radius=0,
            scrollbar_button_color=C["border"], scrollbar_button_hover_color=C["border_lt"])
        self.chat_scroll.pack(fill="both", expand=True)
        self._apply_bg_image()
        self._show_welcome()

        # Files bar
        self.files_bar = ctk.CTkFrame(self.right, fg_color=C["bg2"], corner_radius=0)
        self.files_inner = ctk.CTkFrame(self.files_bar, fg_color="transparent")
        self.files_inner.pack(fill="x", padx=12, pady=4)

        ctk.CTkFrame(self.right, height=1, fg_color=C["border"]).pack(fill="x")

        # Input bar
        self.ibar = ctk.CTkFrame(self.right, fg_color=C["bg2"], corner_radius=0)
        self.ibar.pack(fill="x")
        inner = ctk.CTkFrame(self.ibar, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=8)

        self.attach_btn = ctk.CTkButton(inner, text="📎", width=38, height=38, corner_radius=10,
            fg_color=C["accent"], hover_color=C["accent_h"], font=self._f(1),
            text_color="#FFF", command=self._attach)
        self.attach_btn.pack(side="left", padx=(0, 6))

        # Тултип при наведении на скрепку
        self._tooltip = None
        def _show_tip(event):
            if self._tooltip: return
            x = self.attach_btn.winfo_rootx()
            y = self.attach_btn.winfo_rooty() - 50
            self._tooltip = tk.Toplevel(self)
            self._tooltip.wm_overrideredirect(True)
            self._tooltip.wm_geometry(f"+{x}+{y}")
            tip_text = T("attach_tip")
            lbl = tk.Label(self._tooltip, text=tip_text, justify="left",
                bg="#333340", fg="#E8E8ED", font=("Segoe UI", 9),
                padx=8, pady=5, relief="solid", borderwidth=1)
            lbl.pack()
        def _hide_tip(event):
            if self._tooltip:
                self._tooltip.destroy()
                self._tooltip = None
        self.attach_btn.bind("<Enter>", _show_tip)
        self.attach_btn.bind("<Leave>", _hide_tip)

        self.input_box = ctk.CTkTextbox(inner, height=44, corner_radius=12,
            fg_color=C["bg_input"], border_color=C["border"], border_width=1,
            text_color=C["text"], font=self._f(0), wrap="word",
            activate_scrollbars=False)
        self.input_box.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.input_box.bind("<Return>", self._on_enter)
        self.input_box.bind("<Shift-Return>", lambda e: None)
        self.input_box.bind("<KeyRelease>", self._auto_grow_input)

        # ПКМ для поля ввода — вставить, копировать, вырезать
        def _input_menu(event):
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label=T("paste"), command=lambda: self._paste_to_input())
            try:
                self.input_box._textbox.get("sel.first", "sel.last")
                menu.add_command(label=T("copy_selected"), command=lambda: self._copy_from_input())
                menu.add_command(label=T("cut"), command=lambda: self._cut_from_input())
            except Exception:
                pass
            menu.add_separator()
            menu.add_command(label=T("select_all"), command=lambda: self._select_all_input())
            menu.tk_popup(event.x_root, event.y_root)

        inner_input = self.input_box._textbox if hasattr(self.input_box, '_textbox') else self.input_box
        inner_input.bind("<Button-3>", _input_menu)

        # Горячие клавиши для поля ввода (Windows: Ctrl, macOS: Cmd)
        inner_input.bind("<Control-v>", lambda e: self._paste_to_input() or "break")
        inner_input.bind("<Control-V>", lambda e: self._paste_to_input() or "break")
        inner_input.bind("<Control-c>", lambda e: self._copy_from_input() or "break")
        inner_input.bind("<Control-C>", lambda e: self._copy_from_input() or "break")
        inner_input.bind("<Control-x>", lambda e: self._cut_from_input() or "break")
        inner_input.bind("<Control-X>", lambda e: self._cut_from_input() or "break")
        inner_input.bind("<Control-a>", lambda e: self._select_all_input() or "break")
        inner_input.bind("<Control-A>", lambda e: self._select_all_input() or "break")
        # macOS Cmd
        if platform.system() == "Darwin":
            inner_input.bind("<Meta-v>", lambda e: self._paste_to_input() or "break")
            inner_input.bind("<Meta-c>", lambda e: self._copy_from_input() or "break")
            inner_input.bind("<Meta-x>", lambda e: self._cut_from_input() or "break")
            inner_input.bind("<Meta-a>", lambda e: self._select_all_input() or "break")

        self.send_btn = ctk.CTkButton(inner, text="↑", width=38, height=38, corner_radius=19,
            fg_color=C["accent"], hover_color=C["accent_h"],
            font=self._fb(3), text_color="#FFF", command=self._send)
        self.send_btn.pack(side="right")

        ctk.CTkLabel(self.ibar,
            text=T("hint_bar"),
            font=self._f(-5), text_color=C["text3"]).pack(pady=(0, 5))

        self._refresh_sidebar()

        # Глобальные горячие клавиши
        self.bind("<Control-n>", lambda e: self._new_chat())
        self.bind("<Control-N>", lambda e: self._new_chat())
        if platform.system() == "Darwin":
            self.bind("<Meta-n>", lambda e: self._new_chat())

        # Drag & Drop
        if DND_AVAILABLE:
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self._on_drop)

        # Проверка обновлений при запуске (фоновый поток)
        threading.Thread(target=check_for_updates,
            args=(lambda info: self.after(0, self._on_update_check, info),),
            daemon=True).start()

    def _on_update_check(self, info):
        """Показать уведомление об обновлении."""
        if not info.get("available"):
            return

        latest = info.get("latest", "?")

        # Баннер обновления
        self._update_banner = ctk.CTkFrame(self.right, fg_color=C["accent"], corner_radius=0, height=32)
        self._update_banner.pack(fill="x", after=list(self.right.winfo_children())[0])
        self._update_banner.pack_propagate(False)

        self._update_label = ctk.CTkLabel(self._update_banner, text=f"{T('update_available')} {latest}",
            font=self._fb(-3), text_color="#FFF")
        self._update_label.pack(side="left", padx=12)

        self._update_btn = ctk.CTkButton(self._update_banner, text="⬇ "+T("download"), width=100, height=24, corner_radius=6,
            fg_color="#FFFFFF", hover_color="#E0E0E0", text_color=C["accent"],
            font=self._fb(-4), command=lambda: self._do_update(latest))
        self._update_btn.pack(side="right", padx=(0, 6), pady=4)

        ctk.CTkButton(self._update_banner, text="✕", width=24, height=24, corner_radius=4,
            fg_color="transparent", hover_color="#FFFFFF33", text_color="#FFF",
            font=self._f(-4), command=self._update_banner.destroy).pack(side="right", padx=2, pady=4)

    def _do_update(self, version):
        """Скачать обновление и перезапустить."""
        self._update_btn.configure(state="disabled", text="⏳...")
        self._update_label.configure(text="⏳ Обновление...")

        def _run():
            auto_update(on_done=lambda files: self.after(0, self._on_update_done, files, version))

        threading.Thread(target=_run, daemon=True).start()

    def _on_update_done(self, updated_files, version):
        """Обновление завершено — перезапустить приложение."""
        if updated_files:
            self._update_label.configure(text=f"✓ Обновлено: {', '.join(updated_files)}")
            self._update_btn.configure(text="🔄 Перезапуск", state="normal",
                command=self._restart_app)
            # Автоперезапуск через 2 сек
            self.after(2000, self._restart_app)
        else:
            self._update_label.configure(text="⚠️ Ошибка обновления")
            self._update_btn.configure(text="✕", state="normal",
                command=self._update_banner.destroy)

    def _restart_app(self):
        """Перезапустить приложение."""
        python = sys.executable
        script = str(APP_DIR / "claude_agent_gui.py")
        self.destroy()
        os.execl(python, python, script)

    def _auto_grow_input(self, event=None):
        """Автоувеличение поля ввода (до 8 строк), без скроллбара."""
        text = self.input_box.get("1.0", "end-1c")
        lines = text.count("\n") + 1
        for line in text.split("\n"):
            lines += len(line) // 65
        lines = min(max(lines, 1), 8)
        fs = self._fs()
        line_h = fs + 8
        new_h = max(line_h + 14, 8 + lines * line_h)
        if not hasattr(self, '_last_input_h'):
            self._last_input_h = 0
        if new_h != self._last_input_h:
            self._last_input_h = new_h
            self.input_box.configure(height=new_h)

    def _paste_to_input(self):
        try:
            clip = self.clipboard_get()
            self.input_box.insert("insert", clip)
            self._auto_grow_input()
        except Exception: pass

    def _copy_from_input(self):
        try:
            sel = self.input_box._textbox.get("sel.first", "sel.last")
            if sel: self.clipboard_clear(); self.clipboard_append(sel)
        except Exception: pass

    def _cut_from_input(self):
        try:
            sel = self.input_box._textbox.get("sel.first", "sel.last")
            if sel:
                self.clipboard_clear(); self.clipboard_append(sel)
                self.input_box._textbox.delete("sel.first", "sel.last")
        except Exception: pass

    def _select_all_input(self):
        try:
            self.input_box._textbox.tag_add("sel", "1.0", "end-1c")
        except Exception: pass

    def _apply_bg_image(self):
        """Фон отключён — используется цвет темы."""
        pass

    def _toggle_sidebar(self):
        """Показать/скрыть сайдбар."""
        if self._sidebar_visible:
            self.sidebar.pack_forget()
            # Hide separator too
            for w in self._main.winfo_children():
                if isinstance(w, ctk.CTkFrame) and w.cget("width") == 1 and w != self.right:
                    w.pack_forget(); self._sep = w; break
        else:
            self.right.pack_forget()
            self.sidebar.pack(side="left", fill="y")
            if hasattr(self, '_sep'):
                self._sep.pack(side="left", fill="y")
            self.right.pack(side="right", fill="both", expand=True)
        self._sidebar_visible = not self._sidebar_visible

    # ==================== SIDEBAR ====================

    def _refresh_sidebar(self):
        for w in self.chats_list.winfo_children(): w.destroy()
        chats = hist.list_chats()

        # Фильтр поиска
        query = self.search_var.get().strip().lower() if hasattr(self, 'search_var') else ""
        if query:
            chats = [c for c in chats if query in c.get("title", "").lower()]

        if not chats:
            txt = T("not_found") if query else T("no_chats")
            ctk.CTkLabel(self.chats_list, text=txt, font=self._f(-3),
                          text_color=C["text3"]).pack(pady=20)
            return
        for ch in chats[:30]:
            cid = ch["id"]; active = cid == self.chat_id
            bf = ctk.CTkFrame(self.chats_list,
                fg_color=C["sidebar_active"] if active else "transparent", corner_radius=6,
                cursor="hand2")
            bf.pack(fill="x", padx=6, pady=1)

            # Крестик удаления — pack FIRST (side=right) чтобы гарантированно был виден
            ctk.CTkButton(bf, text="✕", width=22, height=22, corner_radius=4,
                fg_color="transparent", hover_color=C["err"],
                text_color=C["text3"], font=self._f(-5),
                command=lambda c=cid: self._delete_chat(c)).pack(side="right", padx=(0, 4))

            # Обрезаем по пробелу чтобы не на полуслове
            raw = ch["title"].strip()
            max_len = 28
            if len(raw) > max_len:
                cut = raw[:max_len].rsplit(" ", 1)[0]
                if len(cut) < 12: cut = raw[:max_len]
                title = cut.rstrip() + "..."
            else:
                title = raw

            lbl = ctk.CTkLabel(bf, text=title, anchor="w", height=32,
                text_color=C["text"] if active else C["text2"],
                font=self._f(-2), cursor="hand2")
            lbl.pack(side="left", fill="x", expand=True, padx=(10, 0))

            lbl.bind("<Button-1>", lambda e, c=cid: self._load_chat(c))
            bf.bind("<Button-1>", lambda e, c=cid: self._load_chat(c))

    def _load_chat(self, cid):
        data = hist.load_chat(cid)
        if not data: return
        self.chat_id = cid; self.chat_title = data.get("title","Чат")
        self.chat_messages = data.get("messages", [])
        for w in self.chat_scroll.winfo_children(): w.destroy()
        for m in self.chat_messages:
            s, t = m.get("sender","user"), m.get("text","")
            fl = [Path(f) for f in m.get("files",[])] if m.get("files") else None
            if s in ("user","bot"): self._add_msg_w(t, s, files=fl)
            else: self._sys_msg(t)
        if self.agent:
            try:
                from claude_agent_v3 import make_session_config
                self.session_config = make_session_config(f"gui_{cid[:8]}")
            except ImportError: pass
        self._refresh_sidebar()

    def _delete_chat(self, cid):
        hist.delete_chat(cid)
        if cid == self.chat_id: self._new_chat()
        else: self._refresh_sidebar()

    def _save_current(self):
        if not self.chat_messages: return
        if self.chat_title in ("Новый чат", "New chat") and self.chat_messages:
            first = self.chat_messages[0].get("text","")
            self.chat_title = first[:50] + ("..." if len(first) > 50 else "")
        hist.save_chat(self.chat_id, self.chat_title, self.chat_messages)
        self._refresh_sidebar()

    def _export_chat(self):
        if not self.chat_messages: self._sys_msg("Чат пуст"); return
        self._save_current()
        p = hist.export_chat(self.chat_id, "md")
        if p: self._sys_msg(f"✓ {Path(p).name}"); self._add_file_link(p)

    # ==================== WELCOME ====================

    def _show_welcome(self):
        w = ctk.CTkFrame(self.chat_scroll, fg_color="transparent")
        w.pack(fill="x", pady=(36, 14))
        ctk.CTkLabel(w, text="✦", font=self._f(16), text_color=C["accent"]).pack(pady=(0, 4))
        ctk.CTkLabel(w, text="Claude Agent", font=self._fb(6),
                      text_color=C["text"]).pack(pady=(0, 3))
        ctk.CTkLabel(w, text=T("welcome_sub"),
                      font=self._f(-2), text_color=C["text3"]).pack(pady=(0, 18))
        cards = ctk.CTkFrame(w, fg_color="transparent"); cards.pack()
        for emoji, key in [("📊","excel"), ("📄","pdf_word"), ("🖼","images"), ("🐍","code")]:
            c = ctk.CTkFrame(cards, fg_color=C["bg3"], corner_radius=10, width=110, height=56,
                             border_width=1, border_color=C["border"])
            c.pack(side="left", padx=3); c.pack_propagate(False)
            ctk.CTkLabel(c, text=emoji, font=self._f(0)).pack(pady=(7, 1))
            ctk.CTkLabel(c, text=T(key), font=self._f(-5), text_color=C["text2"]).pack()

    # ==================== MESSAGES ====================

    def _add_msg(self, text, sender="user", files=None):
        msg = {"sender": sender, "text": text}
        if files: msg["files"] = [str(f) for f in files]
        self.chat_messages.append(msg)
        self._add_msg_w(text, sender, files)
        self._save_current()

    def _add_msg_w(self, text, sender="user", files=None):
        is_user = sender == "user"
        fs = self._fs()

        # Цвет пузыря: на светлой теме — бледно-серый для пользователя
        if is_user:
            uc = C.get("user_bubble", "") or self._uc()
            txt_color = "#FFF" if not C.get("user_bubble") else C["text"]
        else:
            uc = C["bot_bg"]
            txt_color = C["bot_text"]

        outer = ctk.CTkFrame(self.chat_scroll, fg_color="transparent")
        outer.pack(fill="x", padx=10, pady=2)

        bubble = ctk.CTkFrame(outer,
            fg_color=uc, corner_radius=14,
            border_width=0 if is_user else 1,
            border_color=C["border"] if not is_user else uc)
        bubble.pack(fill="x", padx=(40 if is_user else 0, 0 if is_user else 40))

        # Иконка + текст в одной строке (компактно как DeepSeek)
        header = ctk.CTkFrame(bubble, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(5, 0))
        icon = "👤" if is_user else "✦"
        icon_color = txt_color if is_user else C["accent"]
        ctk.CTkLabel(header, text=icon, font=self._f(-4),
            text_color=icon_color, width=16).pack(side="left")
        name = T("you") if is_user else T("assistant")
        ctk.CTkLabel(header, text=name, font=self._fb(-4),
            text_color=icon_color).pack(side="left", padx=(3, 0))

        if files:
            for fp in files: self._file_chip(bubble, fp)

        # URL cleanup for bot
        display_text = text
        if sender == "bot":
            # Убрать блок рассуждений <think>...</think>
            display_text = re.sub(r'<think>.*?</think>', '', display_text, flags=re.DOTALL).strip()

            url_pattern = r'https?://[^\s\)\]\},<>\"\']+' 
            urls_in_text = list(dict.fromkeys(re.findall(url_pattern, display_text)))
            for i, url in enumerate(urls_in_text[:10], 1):
                display_text = display_text.replace(url, f"[{i}]")
            display_text = re.sub(r'\[([^\]]+)\]\(\[(\d+)\]\)', r'\1 [\2]', display_text)

        lines = display_text.count("\n") + 1
        for line in display_text.split("\n"): lines += len(line) // 75
        height = min(max(lines * (fs + 5) + 6, 24), 600)

        # Разбиваем на текст и блоки кода
        code_pattern = r'```(\w*)\n(.*?)```'
        parts = re.split(code_pattern, display_text, flags=re.DOTALL)

        if sender == "bot" and len(parts) > 1:
            # Есть блоки кода — рендерим по частям
            i = 0
            while i < len(parts):
                if i + 2 < len(parts) and (i % 3 == 1):
                    # parts[i] = язык, parts[i+1] = код
                    lang = parts[i] or "code"
                    code = parts[i + 1].strip()

                    # Рамка для блока кода
                    code_frame = ctk.CTkFrame(bubble, fg_color=C.get("bg3", "#1E1E2E"),
                        corner_radius=8, border_width=1, border_color=C["border"])
                    code_frame.pack(fill="x", padx=8, pady=3)

                    # Заголовок с языком и кнопкой копирования
                    code_header = ctk.CTkFrame(code_frame, fg_color="transparent", height=24)
                    code_header.pack(fill="x", padx=6, pady=(4, 0))
                    code_header.pack_propagate(False)
                    ctk.CTkLabel(code_header, text=lang, font=self._f(-5),
                        text_color=C["text3"]).pack(side="left")
                    _code = code  # capture
                    ctk.CTkButton(code_header, text="📋 Copy", width=60, height=20,
                        corner_radius=4, fg_color="transparent", hover_color=C["border"],
                        text_color=C["text3"], font=self._f(-5),
                        command=lambda c=_code: [self.clipboard_clear(), self.clipboard_append(c)]
                    ).pack(side="right")

                    # Текст кода
                    c_lines = code.count("\n") + 1
                    c_h = min(max(c_lines * (fs + 3) + 8, 28), 400)
                    code_tb = ctk.CTkTextbox(code_frame, height=c_h, corner_radius=0,
                        fg_color=C.get("bg3", "#1E1E2E"),
                        text_color=C.get("ok", "#48BB78"),
                        font=ctk.CTkFont(family="Courier", size=max(fs - 1, 10)),
                        border_width=0, wrap="none", activate_scrollbars=False)
                    code_tb.pack(fill="x", padx=6, pady=(0, 6))
                    code_tb.insert("1.0", code)
                    code_tb.configure(state="disabled")
                    i += 2
                else:
                    # Обычный текст
                    txt_part = parts[i].strip()
                    if txt_part:
                        t_lines = txt_part.count("\n") + 1
                        for ln in txt_part.split("\n"): t_lines += len(ln) // 75
                        t_h = min(max(t_lines * (fs + 5) + 6, 24), 600)
                        tb_part = ctk.CTkTextbox(bubble, height=t_h, corner_radius=4,
                            fg_color=uc, text_color=txt_color,
                            font=ctk.CTkFont(size=fs), border_width=0, wrap="word",
                            activate_scrollbars=False)
                        tb_part.pack(fill="x", padx=8, pady=(1, 1))
                        tb_part.insert("1.0", txt_part)
                        tb_part.configure(state="disabled")
                    i += 1
            tb = None  # no single textbox
        else:
            # Обычное сообщение без блоков кода
            tb = ctk.CTkTextbox(bubble, height=height, corner_radius=4,
                fg_color=uc, text_color=txt_color,
                font=ctk.CTkFont(size=fs), border_width=0, wrap="word",
                activate_scrollbars=False)
            tb.pack(fill="x", padx=8, pady=(1, 3))
            tb.insert("1.0", display_text); tb.configure(state="disabled")

        # Keyboard & mouse copy bindings
        def _copy_all():
            self.clipboard_clear(); self.clipboard_append(text)

        if tb:
            def _copy_sel(event=None):
                try:
                    tb.configure(state="normal")
                    sel = tb.get("sel.first", "sel.last")
                    tb.configure(state="disabled")
                    if sel: self.clipboard_clear(); self.clipboard_append(sel)
                except Exception: pass

            def _ctx_menu(event):
                menu = tk.Menu(self, tearoff=0)
                try:
                    tb.configure(state="normal")
                    sel = tb.get("sel.first", "sel.last")
                    tb.configure(state="disabled")
                    if sel: menu.add_command(label=T("copy_selected"), command=_copy_sel)
                except Exception: pass
                menu.add_command(label=T("copy_all"), command=_copy_all)
                menu.tk_popup(event.x_root, event.y_root)

            itb = tb._textbox if hasattr(tb, '_textbox') else tb
            itb.bind("<Control-c>", _copy_sel); itb.bind("<Control-C>", _copy_sel)
            def _sel_all(e=None):
                tb.configure(state="normal"); itb.tag_add("sel", "1.0", "end-1c")
                tb.configure(state="disabled"); return "break"
            itb.bind("<Control-a>", _sel_all); itb.bind("<Control-A>", _sel_all)
            if platform.system() == "Darwin":
                itb.bind("<Meta-c>", _copy_sel); itb.bind("<Meta-a>", _sel_all)
            itb.bind("<Button-3>", _ctx_menu)
            if platform.system() == "Darwin": itb.bind("<Button-2>", _ctx_menu)

        # --- Кнопки действий под пузырём (как DeepSeek) ---
        actions = ctk.CTkFrame(outer, fg_color="transparent")
        actions.pack(anchor="e" if is_user else "w", padx=(12 if not is_user else 0, 12 if is_user else 0), pady=(0, 2))

        def _make_action(parent, icon, tooltip, cmd):
            b = ctk.CTkButton(parent, text=icon, width=28, height=22, corner_radius=6,
                fg_color="transparent", hover_color=C["bg3"],
                text_color=C["text3"], font=self._f(-4), command=cmd)
            b.pack(side="left", padx=1)
            return b

        _make_action(actions, "📋", "Копировать", _copy_all)

        if sender == "bot":
            def _retry():
                if len(self.chat_messages) >= 2:
                    last_user = None
                    for m in reversed(self.chat_messages):
                        if m.get("sender") == "user":
                            last_user = m.get("text", ""); break
                    if last_user and not self.is_processing:
                        self.is_processing = True
                        self._stop_event = threading.Event()
                        self.send_btn.configure(text="■", fg_color=C["err"],
                            hover_color="#B91C1C", command=self._stop_gen)
                        self._show_streaming_bubble()
                        threading.Thread(target=self._process_stream, args=(last_user,), daemon=True).start()

            _make_action(actions, "🔄", "Повторить", _retry)
            self._detect_files(bubble, text)
            self._detect_links(bubble, text)

        self._scroll_down()

    def _detect_links(self, bubble, text):
        """Найти URL в тексте и показать как кликабельные номерки."""
        import webbrowser
        url_pattern = r'https?://[^\s\)\]\},<>\"\']+' 
        urls = list(dict.fromkeys(re.findall(url_pattern, text)))  # unique, keep order
        if not urls: return

        links_frame = ctk.CTkFrame(bubble, fg_color="transparent")
        links_frame.pack(anchor="w", padx=12, pady=(2, 4))

        ctk.CTkLabel(links_frame, text="🔗", font=self._f(-3),
                      text_color=C["text3"]).pack(side="left", padx=(0, 4))

        for i, url in enumerate(urls[:10], 1):
            # Короткое имя для тултипа
            domain = url.split("//")[-1].split("/")[0].replace("www.", "")

            btn = ctk.CTkButton(links_frame, text=str(i), width=26, height=26,
                corner_radius=13, fg_color=C["accent"], hover_color=C["accent_h"],
                text_color="#FFF", font=self._fb(-3),
                command=lambda u=url: webbrowser.open(u))
            btn.pack(side="left", padx=2)

            # Тултип при наведении
            def _enter(e, b=btn, d=domain):
                b.configure(text=d[:12])
            def _leave(e, b=btn, n=str(i)):
                b.configure(text=n)
            btn.bind("<Enter>", _enter)
            btn.bind("<Leave>", _leave)

    def _file_chip(self, parent, fp):
        fc = ctk.CTkFrame(parent, fg_color=C["file_bg"], corner_radius=8,
                          border_width=1, border_color=C["file_bd"])
        fc.pack(anchor="w", padx=12, pady=(3, 0))
        ctk.CTkButton(fc, text=f"📄 {Path(fp).name}", height=24, corner_radius=6,
            fg_color="transparent", hover_color=C["border_lt"],
            text_color=C["link"], font=self._f(-3), anchor="w",
            command=lambda: open_file(str(fp))).pack(padx=5, pady=2)

    def _detect_files(self, bubble, text):
        out = self._get_output_dir()
        pats = [r'(?:outputs[/\\])(\S+\.\w{2,5})', r'(?:файл[:\s]+)(\S+\.\w{2,5})',
                r'(?:создан[:\s]+)(\S+\.\w{2,5})', r'(?:сохранён[:\s]+)(\S+\.\w{2,5})']
        found = set()
        for p in pats:
            for m in re.finditer(p, text, re.IGNORECASE): found.add(m.group(1).strip('",;:)'))
        for fn in found:
            fp = out / fn
            if fp.exists(): self._file_chip(bubble, fp)

    def _add_file_link(self, fp):
        outer = ctk.CTkFrame(self.chat_scroll, fg_color="transparent")
        outer.pack(fill="x", padx=10, pady=2)
        ctk.CTkButton(outer, text=f"📄 {Path(fp).name}", height=26, corner_radius=8,
            fg_color=C["file_bg"], hover_color=C["border_lt"],
            text_color=C["link"], font=self._f(-3), anchor="w",
            border_width=1, border_color=C["file_bd"],
            command=lambda: open_file(str(fp))).pack(anchor="w")
        self._scroll_down()

    def _sys_msg(self, text):
        f = ctk.CTkFrame(self.chat_scroll, fg_color="transparent")
        f.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(f, text=text, font=self._f(-4),
            text_color=C["text3"], wraplength=550, justify="center").pack()
        self._scroll_down()

    def _scroll_down(self):
        self.chat_scroll._parent_canvas.yview_moveto(1.0)

    # ==================== FILES ====================

    def _attach(self):
        fps = filedialog.askopenfilenames(title="Прикрепить файлы", filetypes=[
            ("Все файлы", "*.*"), ("Excel", "*.xlsx *.xls *.csv"),
            ("PDF", "*.pdf"), ("Word", "*.docx"), ("Изображения", "*.png *.jpg *.jpeg *.webp"),
            ("Текст", "*.txt *.md *.json *.py")])
        if not fps: return
        for fp in fps:
            p = Path(fp)
            if p not in self.attached_files: self.attached_files.append(p)
        self._refresh_files_bar()

    def _on_drop(self, event):
        """Обработка drag & drop файлов."""
        data = event.data
        # tkinterdnd2 может передать пути в фигурных скобках или через пробел
        files = []
        if '{' in data:
            # Формат: {/path/to file.pdf} {/another/file.txt}
            files = re.findall(r'\{([^}]+)\}', data)
        else:
            files = data.strip().split()
        for fp in files:
            p = Path(fp.strip())
            if p.exists() and p.is_file() and p not in self.attached_files:
                self.attached_files.append(p)
        if self.attached_files:
            self._refresh_files_bar()
            self._sys_msg(f"📎 {len(files)} файл(ов) добавлено")

    def _refresh_files_bar(self):
        for w in self.files_inner.winfo_children(): w.destroy()
        if not self.attached_files: self.files_bar.pack_forget(); return
        self.files_bar.pack(fill="x", before=self.input_box.master.master)
        for i, fp in enumerate(self.attached_files):
            ch = ctk.CTkFrame(self.files_inner, fg_color=C["file_bg"], corner_radius=8,
                              border_width=1, border_color=C["file_bd"])
            ch.pack(side="left", padx=(0, 4))
            ctk.CTkLabel(ch, text=f"📄 {fp.name}", font=self._f(-4),
                         text_color=C["text2"]).pack(side="left", padx=(5, 2), pady=3)
            ctk.CTkButton(ch, text="✕", width=18, height=18, corner_radius=4,
                fg_color="transparent", hover_color=C["border"], text_color=C["text3"],
                font=self._f(-4),
                command=lambda idx=i: self._rm_file(idx)).pack(side="right", padx=(0, 3), pady=3)

    def _rm_file(self, idx):
        if 0 <= idx < len(self.attached_files): self.attached_files.pop(idx)
        self._refresh_files_bar()

    def _copy_files(self):
        copied = []; out = self._get_output_dir(); out.mkdir(parents=True, exist_ok=True)
        for fp in self.attached_files:
            try: shutil.copy2(fp, out / fp.name); copied.append(fp)
            except Exception: pass
        return copied

    # ==================== INPUT ====================

    def _on_enter(self, e):
        if not (e.state & 0x1): self._send(); return "break"

    def _send(self):
        text = self.input_box.get("1.0", "end-1c").strip()
        if not text or self.is_processing: return
        self.input_box.delete("1.0", "end")
        self._last_input_h = 0; self._auto_grow_input()
        if text.startswith("/") and self._cmd(text): return
        files_show = list(self.attached_files); copied = []
        if self.attached_files:
            copied = self._copy_files(); self.attached_files.clear(); self._refresh_files_bar()
        self._add_msg(text, "user", files=files_show or None)
        if copied: text += f"\n\n[Файлы: {', '.join(f.name for f in copied)}]"
        if not self.agent and not self._init_agent(): return
        self.is_processing = True
        self._stop_event = threading.Event()
        self.send_btn.configure(text="■", fg_color=C["err"], hover_color="#B91C1C",
            command=self._stop_gen)
        self._show_streaming_bubble()
        threading.Thread(target=self._process_stream, args=(text,), daemon=True).start()

    def _stop_gen(self):
        """Остановить генерацию."""
        if hasattr(self, '_stop_event'):
            self._stop_event.set()

    def _show_streaming_bubble(self):
        """Создать пузырь для стриминга."""
        outer = ctk.CTkFrame(self.chat_scroll, fg_color="transparent")
        outer.pack(fill="x", padx=10, pady=2)
        self._stream_outer = outer

        bubble = ctk.CTkFrame(outer,
            fg_color=C["bot_bg"], corner_radius=14,
            border_width=1, border_color=C["border"])
        bubble.pack(fill="x", padx=(0, 40))
        self._stream_bubble = bubble

        header = ctk.CTkFrame(bubble, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(5, 0))
        ctk.CTkLabel(header, text="✦", font=self._f(-4),
            text_color=C["accent"], width=16).pack(side="left")
        ctk.CTkLabel(header, text=T("assistant"), font=self._fb(-4),
            text_color=C["accent"]).pack(side="left", padx=(3, 0))

        fs = self._fs()
        self._stream_tb = ctk.CTkTextbox(bubble, height=30, corner_radius=4,
            fg_color=C["bot_bg"], text_color=C["bot_text"],
            font=ctk.CTkFont(size=fs), border_width=0, wrap="word",
            activate_scrollbars=False)
        self._stream_tb.pack(fill="x", padx=8, pady=(1, 3))
        self._stream_tb.insert("1.0", T("thinking"))
        self._stream_tb.configure(state="disabled")
        self._stream_text = ""
        self._scroll_down()

    def _append_stream(self, chunk):
        """Добавить текст в стриминг-пузырь. Скрывает <think> блоки."""
        if not hasattr(self, '_stream_tb') or not self._stream_tb.winfo_exists():
            return
        self._stream_text += chunk
        # Защита от утечки памяти при очень длинных ответах
        if len(self._stream_text) > 200_000:
            self._stream_text = self._stream_text[-150_000:]

        # Убрать завершённые <think>...</think>
        display = re.sub(r'<think>.*?</think>', '', self._stream_text, flags=re.DOTALL).strip()
        # Если ещё внутри <think> — не показывать
        if '<think>' in self._stream_text and '</think>' not in self._stream_text:
            display = T("thinking")

        self._stream_tb.configure(state="normal")
        self._stream_tb.delete("1.0", "end")
        self._stream_tb.insert("1.0", display or T("thinking"))
        self._stream_tb.configure(state="disabled")

        fs = self._fs()
        lines = display.count("\n") + 1
        for line in display.split("\n"):
            lines += len(line) // 75
        height = min(max(lines * (fs + 5) + 6, 24), 600)
        self._stream_tb.configure(height=height)
        self._scroll_down()

    def _process_stream(self, text):
        # Автоматический таймаут 5 минут — предотвращает вечное зависание UI
        _timeout_timer = threading.Timer(300, self._stop_event.set)
        _timeout_timer.daemon = True
        _timeout_timer.start()
        try:
            from claude_agent_v3 import run_agent_stream
            r = run_agent_stream(
                self.agent, text,
                session_config=self.session_config,
                on_token=lambda chunk: self.after(0, self._append_stream, chunk),
                stop_event=self._stop_event,
            )
            self.after(0, self._on_stream_done, r.get("output", "Нет ответа"))
        except Exception as e:
            self.after(0, self._on_err, str(e))
        finally:
            _timeout_timer.cancel()

    def _on_stream_done(self, answer):
        """Стриминг завершён — заменить стриминг-пузырь на нормальный."""
        # Удаляем стриминг-пузырь
        if hasattr(self, '_stream_outer') and self._stream_outer.winfo_exists():
            self._stream_outer.destroy()
        # Добавляем нормальное сообщение
        self.is_processing = False
        self.send_btn.configure(text="↑", fg_color=C["accent"],
            hover_color=C["accent_h"], command=self._send)
        self._add_msg(answer, "bot")

    # ==================== COMMANDS ====================

    def _cmd(self, text):
        c = text.lower().strip()
        cmds = {
            "/help": lambda: self._sys_msg("/help • /files • /clear • /settings • /model • /dir • /export"),
            "/clear": lambda: [w.destroy() for w in self.chat_scroll.winfo_children()] or self._show_welcome(),
            "/settings": self._open_settings,
            "/model": lambda: self._sys_msg(f"Модель: {self.settings.get('model','?')}"),
            "/dir": lambda: self._sys_msg(f"📂 {self._get_output_dir()}"),
            "/export": self._export_chat,
        }
        if c in cmds: cmds[c](); return True
        if c == "/files":
            try:
                out = self._get_output_dir()
                items = [f for f in sorted(out.iterdir()) if not f.name.startswith(".")]
                if not items: self._sys_msg("📂 Пусто")
                else:
                    for f in items[:20]: self._add_file_link(str(f))
            except Exception as e: self._sys_msg(f"Ошибка: {e}")
            return True
        return False

    # ==================== AGENT ====================

    def _init_agent(self):
        key = self.settings.get("api_key", "")
        if not key: self._sys_msg(T("no_api_key")); return False
        model_id = self.settings.get("model", "claude-3-5-haiku-20241022")
        url = self.settings.get("base_url", PRESET_URLS[0])
        cd = self.settings.get("output_dir", "")
        if cd:
            try:
                import claude_agent_v3; p = Path(cd); p.mkdir(parents=True, exist_ok=True)
                claude_agent_v3.OUTPUT_DIR = p
            except Exception: pass
        try:
            from claude_agent_v3 import create_claude_agent, make_session_config
            temp = self.settings.get("temperature", 0)
            self.agent = create_claude_agent(api_key=key, base_url=url, model=model_id,
                use_memory=True, temperature=float(temp))
            self.session_config = make_session_config(f"gui_{self.chat_id[:8]}")
            self.status_dot.configure(text_color=C["ok"])
            self.status_text.configure(text=T("connected"), text_color=C["ok"])
            self.model_pill.configure(text=f"  {model_id}  ")
            self._sys_msg(f"{T('agent_ready')}  •  {model_id}"); return True
        except ImportError: self._sys_msg("⚠️ Не найден claude_agent_v3.py"); return False
        except Exception as e:
            self._sys_msg(f"⚠️ {e}"); self.status_dot.configure(text_color=C["err"]); return False

    def _on_err(self, err):
        # Удаляем стриминг-пузырь если есть
        if hasattr(self, '_stream_outer') and self._stream_outer.winfo_exists():
            self._stream_outer.destroy()
        self.is_processing = False
        self.send_btn.configure(text="↑", fg_color=C["accent"],
            hover_color=C["accent_h"], command=self._send)
        self._sys_msg(f"⚠️ {err}")

    # ==================== NAV ====================

    def _open_settings(self): SettingsWindow(self, self.settings, self._on_saved)

    def _on_saved(self, s):
        old = self.settings; self.settings = s
        need_rebuild = False

        if (s.get("model") != old.get("model") or s.get("base_url") != old.get("base_url") or
            s.get("api_key") != old.get("api_key") or s.get("output_dir") != old.get("output_dir")):
            self.agent = None

        if (s.get("theme") != old.get("theme") or s.get("language") != old.get("language") or
            s.get("font_size") != old.get("font_size") or s.get("bubble_color") != old.get("bubble_color")):
            need_rebuild = True

        if need_rebuild:
            self._rebuild_ui()

    def _new_chat(self):
        self._save_current()
        self.chat_id = uuid.uuid4().hex[:12]
        self.chat_title = T("new_chat"); self.chat_messages = []
        for w in self.chat_scroll.winfo_children(): w.destroy()
        self._show_welcome()
        if self.agent:
            try:
                from claude_agent_v3 import make_session_config
                self.session_config = make_session_config(f"gui_{self.chat_id[:8]}")
            except ImportError: pass
        self._refresh_sidebar()


if __name__ == "__main__":
    ChatApp().mainloop()
