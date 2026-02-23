#!/usr/bin/env python3
"""
Генерация иконок из icon_1024.png
Запустите перед сборкой: python3 make_icons.py

Создаёт:
  icon.ico   — для Windows
  icon.icns  — для macOS (если запущен на macOS)
"""

from pathlib import Path
import subprocess, sys

try:
    from PIL import Image
except ImportError:
    print("Устанавливаю Pillow...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image

BASE = Path(__file__).resolve().parent
SRC = BASE / "icon_1024.png"

if not SRC.exists():
    print(f"Не найден {SRC}")
    sys.exit(1)

img = Image.open(SRC)

# === ICO (Windows) ===
ico_sizes = [(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]
imgs = [img.resize(s, Image.LANCZOS) for s in ico_sizes]
imgs[0].save(BASE / "icon.ico", format="ICO", sizes=ico_sizes, append_images=imgs[1:])
print(f"✓ icon.ico")

# === ICNS (macOS) — через iconutil ===
import platform
if platform.system() == "Darwin":
    iconset = BASE / "icon.iconset"
    iconset.mkdir(exist_ok=True)

    pairs = [
        (16, "icon_16x16.png"), (32, "icon_16x16@2x.png"),
        (32, "icon_32x32.png"), (64, "icon_32x32@2x.png"),
        (128, "icon_128x128.png"), (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"), (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"), (1024, "icon_512x512@2x.png"),
    ]
    for size, name in pairs:
        img.resize((size, size), Image.LANCZOS).save(iconset / name, "PNG")

    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(BASE / "icon.icns")])

    # Cleanup
    import shutil
    shutil.rmtree(iconset)
    print(f"✓ icon.icns")
else:
    print(f"  icon.icns — пропущен (не macOS). Для сборки .app используйте icon_1024.png")

print("\nГотово!")
