import os
import humanize
from pathlib import Path
from glob import glob
import shutil

# Carpetas comunes de basura
DIRS_TO_SCAN = {
    "Papelera": Path.home() / ".Trash",
    "Caches del sistema": Path.home() / "Library" / "Caches",
    "Temporales": Path("/tmp"),
    "Xcode DerivedData": Path.home() / "Library" / "Developer" / "Xcode" / "DerivedData",
    "Gradle": Path.home() / ".gradle" / "caches",
    "Android SDK": Path.home() / "Library" / "Android" / "sdk" / ".android",
    "AWS CLI Cache": Path.home() / ".aws" / "cli" / "cache",
}

# Agregar perfiles de Firefox dinámicamente
firefox_profiles = glob(str(Path.home() / "Library/Application Support/Firefox/Profiles/*/cache2"))
for i, path in enumerate(firefox_profiles):
    DIRS_TO_SCAN[f"Firefox Perfil {i+1}"] = Path(path)

def scan_folder(folder_path):
    total_size = 0
    file_list = []

    if not folder_path.exists():
        return 0, []

    for root, _, files in os.walk(folder_path):
        for file in files:
            try:
                file_path = Path(root) / file
                size = file_path.stat().st_size
                total_size += size
                file_list.append((file_path, size))
            except Exception:
                pass

    return total_size, file_list

def show_results(name, size, files):
    print(f"\n📁 {name}: {humanize.naturalsize(size)} en {len(files)} archivos")
    for path, sz in sorted(files, key=lambda x: -x[1])[:10]:
        print(f"  - {path} ({humanize.naturalsize(sz)})")
    if len(files) > 10:
        print("  ...")

def clean_files(files):
    for path, _ in files:
        try:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
        except Exception as e:
            print(f"Error al borrar {path}: {e}")

def main():
    print("🧹 Escaneando archivos basura...\n")
    total_global = 0
    all_files = []

    for name, folder in DIRS_TO_SCAN.items():
        size, files = scan_folder(folder)
        show_results(name, size, files)
        all_files.extend(files)
        total_global += size

    print(f"\n🧼 Total estimado para limpiar: {humanize.naturalsize(total_global)}")

    if not all_files:
        print("\n✅ No hay archivos basura para limpiar.")
        return

    respuesta = input("\n¿Deseas eliminar estos archivos? (s/n): ").strip().lower()
    if respuesta == "s":
        print("🧽 Limpiando archivos...")
        clean_files(all_files)
        print("✅ Limpieza completada.")
    else:
        print("🚫 Limpieza cancelada.")

if __name__ == "__main__":
    main()
