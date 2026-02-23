#!/usr/bin/env python3
"""
Сборка Claude Agent Desktop в .app (macOS) или .exe (Windows).

Использование:
  python build.py          — авто-определение ОС
  python build.py windows  — собрать .exe
  python build.py macos    — собрать .app
"""

import os, sys, platform, subprocess
from pathlib import Path

APP_NAME = "Claude Agent"
MAIN_SCRIPT = "claude_agent_gui.py"
AGENT_SCRIPT = "claude_agent_v3.py"

BASE_DIR = Path(__file__).resolve().parent


def check(name):
    p = BASE_DIR / name
    if not p.exists():
        print(f"  ОШИБКА: {name} не найден!")
        sys.exit(1)
    return p


def find_icon(ext):
    """Ищет иконку с нужным расширением."""
    p = BASE_DIR / f"icon.{ext}"
    if p.exists():
        return p
    # Fallback: png
    p = BASE_DIR / "icon_1024.png"
    if p.exists():
        return p
    return None


def build(target):
    is_mac = target == "macos"
    sep = ":" if is_mac else ";"
    ext = "icns" if is_mac else "ico"

    print(f"\n{'=' * 50}")
    print(f"  Сборка для {'macOS (.app)' if is_mac else 'Windows (.exe)'}")
    print(f"{'=' * 50}\n")

    try:
        import PyInstaller
        print(f"  PyInstaller: {PyInstaller.__version__}")
    except ImportError:
        print("  Устанавливаю PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    main = check(MAIN_SCRIPT)
    agent = check(AGENT_SCRIPT)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onedir" if is_mac else "--onefile",
        "--windowed",
        "--name", APP_NAME,
        "--add-data", f"{agent}{sep}.",
    ]

    # Иконка
    icon = find_icon(ext)
    if icon:
        cmd.extend(["--icon", str(icon)])
        print(f"  Иконка: {icon}")
    else:
        # Для macOS можно использовать PNG напрямую
        png = BASE_DIR / "icon_1024.png"
        if png.exists():
            cmd.extend(["--icon", str(png)])
            print(f"  Иконка (PNG): {png}")
        else:
            print("  Иконка: не найдена (будет стандартная)")

    if is_mac:
        cmd.extend(["--osx-bundle-identifier", "com.claude-agent.desktop"])

    # Hidden imports
    for mod in ["langchain", "langchain_openai", "langchain_community",
                "langchain_core", "langgraph", "openpyxl", "pandas",
                "customtkinter", "duckduckgo_search"]:
        cmd.extend(["--hidden-import", mod])

    cmd.append(str(main))

    print(f"\n  Запускаю сборку (2-7 минут)...\n")
    subprocess.check_call(cmd, cwd=str(BASE_DIR))

    dist = BASE_DIR / "dist"
    if is_mac:
        app = dist / f"{APP_NAME}.app"
        alt = dist / APP_NAME
        target_path = app if app.exists() else alt
        print(f"\n  ГОТОВО: {target_path}")
        print(f'  Запуск: open "{target_path}"')
        print(f"  Или перетащите в Applications")
    else:
        exe = dist / f"{APP_NAME}.exe"
        if exe.exists():
            mb = exe.stat().st_size / (1024 * 1024)
            print(f"\n  ГОТОВО: {exe}  ({mb:.1f} MB)")
        else:
            print(f"\n  Результат в: {dist}")


def main():
    print(f"\n  Claude Agent Desktop Builder")
    print(f"  Python {sys.version.split()[0]} • {platform.system()} {platform.machine()}\n")

    if len(sys.argv) > 1:
        t = sys.argv[1].lower()
        if t in ("win", "windows", "exe"):
            build("windows")
        elif t in ("mac", "macos", "app"):
            build("macos")
        else:
            print(f"  Неизвестно: {t}. Используйте: python build.py [windows|macos]")
            return
    else:
        build("macos" if platform.system() == "Darwin" else "windows")

    print("\n  Готово!\n")


if __name__ == "__main__":
    main()
