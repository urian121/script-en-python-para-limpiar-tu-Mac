import os
import humanize
import subprocess
import stat
from pathlib import Path
from glob import glob
import shutil
import time
from send2trash import send2trash
import sys

# Carpetas comunes de archivos residuales de aplicaciones
RESIDUAL_APP_FILES = {
    "Preferencias de aplicaciones": Path.home() / "Library/Preferences",
    "Caché de aplicaciones": Path.home() / "Library/Caches",
    "Contenedores de aplicaciones": Path.home() / "Library/Containers",
    "Soporte de aplicaciones": Path.home() / "Library/Application Support",
    "Saved Application State": Path.home() / "Library/Saved Application State",
    "Agentes de inicio": Path.home() / "Library/LaunchAgents",
    "Agentes de inicio (sistema)": Path("/Library/LaunchAgents"),
    "Daemons de inicio": Path("/Library/LaunchDaemons"),
    "Extensiones de sistema": Path("/Library/Extensions"),
    "Extensiones del kernel": Path("/System/Library/Extensions"),
    "Extensiones de usuario": Path.home() / "Library/Extensions",
    "Preferencias del sistema": Path.home() / "Library/Preferences/SystemConfiguration"
}

# Carpetas comunes de basura
DIRS_TO_SCAN = {
    "Caches del sistema": Path.home() / "Library" / "Caches",
    "Temporales": Path("/tmp"),
    "Xcode DerivedData": Path.home() / "Library" / "Developer" / "Xcode" / "DerivedData",
    "Gradle": Path.home() / ".gradle" / "caches",
    "Android SDK": Path.home() / "Library" / "Android" / "sdk" / ".android",
    "AWS CLI Cache": Path.home() / ".aws" / "cli" / "cache",
    "Logs del sistema": Path.home() / "Library" / "Logs",
    "Dock Icons": Path.home() / "Library/Application Support/Dock",
    "Docker Data": Path.home() / "Library/Containers/com.docker.docker/Data",
    "Docker Cache": Path.home() / "Library/Caches/com.docker.docker",
    "Pip Cache": Path.home() / "Library/Caches/pip",
    "Homebrew Cache": Path("/Library/Caches/Homebrew"),
    "Xcode Cache": Path.home() / "Library/Developer/Xcode/iOS DeviceSupport",
    "Xcode Device Logs": Path.home() / "Library/Developer/Xcode/iOS Device Logs",
    "Xcode Archives": Path.home() / "Library/Developer/Xcode/Archives",
    "Spotlight Index": Path.home() / "Library/Metadata/com.apple.Spotlight",
    "Mail Downloads": Path.home() / "Library/Containers/com.apple.mail/Data/Library/Mail/Downloads",
    "Chrome Cache": Path.home() / "Library/Caches/Google/Chrome",
    "Firefox Cache": Path.home() / "Library/Caches/Firefox"
}

# Agregar perfiles de Firefox dinámicamente
firefox_profiles = glob(str(Path.home() / "Library/Application Support/Firefox/Profiles/*/cache2"))
for i, path in enumerate(firefox_profiles):
    DIRS_TO_SCAN[f"Firefox Perfil {i+1}"] = Path(path)

def scan_folder(folder_path):
    total_size = 0
    file_list = []

    # Si es un patrón glob, expandirlo
    if isinstance(folder_path, str) and ('*' in str(folder_path) or '?' in str(folder_path)):
        matches = glob(str(folder_path), recursive=True)
        for match in matches:
            match_path = Path(match)
            if match_path.exists():
                if match_path.is_file():
                    try:
                        size = match_path.stat().st_size
                        total_size += size
                        file_list.append((match_path, size))
                    except Exception:
                        pass
                elif match_path.is_dir():
                    size, files = scan_folder(match_path)
                    total_size += size
                    file_list.extend(files)
        return total_size, file_list

    # Si no es un patrón glob, procesar normalmente
    if not isinstance(folder_path, Path):
        folder_path = Path(folder_path)
    
    if not folder_path.exists():
        return 0, []

    try:
        if folder_path.is_file():
            size = folder_path.stat().st_size
            return size, [(folder_path, size)]
            
        for root, _, files in os.walk(folder_path):
            for file in files:
                try:
                    file_path = Path(root) / file
                    size = file_path.stat().st_size
                    total_size += size
                    file_list.append((file_path, size))
                except (PermissionError, FileNotFoundError, OSError):
                    continue
    except (PermissionError, FileNotFoundError, OSError):
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
            # Saltar archivos de sistema importantes o con permisos especiales
            skip_patterns = [
                'node_modules',
                '.npm',
                'Safari',
                '.s.PGSQL',  # Archivos de bloqueo de PostgreSQL
                'com.apple.launchd'  # Archivos del sistema de lanzamiento de macOS
            ]
            if any(pattern in str(path) for pattern in skip_patterns):
                continue
                
            if path.is_file():
                try:
                    # Intentar cambiar permisos
                    os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
                    path.unlink()
                except (PermissionError, OSError) as e:
                    if 'npm' in str(path) or 'node_modules' in str(path):
                        print(f"⚠️  Para limpiar la caché de NPM, ejecuta: npm cache clean --force")
                    else:
                        print(f"⚠️  No se pudo borrar {path}: {e}")
                    continue
            elif path.is_dir():
                try:
                    shutil.rmtree(path, ignore_errors=True, onerror=handle_remove_readonly)
                except Exception as e:
                    print(f"⚠️  No se pudo eliminar el directorio {path}: {e}")
        except Exception as e:
            print(f"⚠️  Error al procesar {path}: {e}")

def handle_remove_readonly(func, path, _):
    """Maneja los errores de solo lectura al eliminar archivos"""
    try:
        # No intentar modificar archivos de sistema protegidos
        if 'node_modules' in str(path) or '.npm' in str(path):
            return
            
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except (PermissionError, OSError) as e:
            if 'npm' in str(path):
                print(f"⚠️  Para limpiar la caché de NPM, ejecuta: npm cache clean --force")
            else:
                print(f"⚠️  No se pudo modificar permisos de {path}: {e}")
    except Exception as e:
        print(f"⚠️  Error al manejar archivo de solo lectura {path}: {e}")

def find_residual_files():
    """Busca archivos residuales de aplicaciones desinstaladas"""
    residual_files = []
    installed_apps = set()
    
    # Obtener lista de aplicaciones instaladas
    apps_dir = Path("/Applications")
    user_apps_dir = Path.home() / "Applications"
    
    # Escanear aplicaciones instaladas
    for app_dir in [apps_dir, user_apps_dir]:
        if app_dir.exists():
            for app in app_dir.glob("*.app"):
                installed_apps.add(app.stem.lower())
    
    # Buscar archivos residuales
    for category, folder in RESIDUAL_APP_FILES.items():
        if not folder.exists():
            continue
            
        for item in folder.glob("*"):
            # Obtener nombre base sin extensión
            name = item.stem.lower()
            
            # Verificar si es un archivo de una aplicación desinstalada
            is_residual = True
            for app_name in installed_apps:
                if app_name in name or name in app_name:
                    is_residual = False
                    break
            
            if is_residual and item.is_file():
                try:
                    size = item.stat().st_size
                    residual_files.append((item, size))
                except (PermissionError, FileNotFoundError):
                    continue
    
    return residual_files

def main():
    print("🧹 Escaneando archivos basura...\n")
    total_global = 0
    all_files = []

    # Buscar archivos residuales
    print("🔍 Buscando archivos residuales de aplicaciones desinstaladas...")
    residual_files = find_residual_files()
    
    if residual_files:
        total_size = sum(size for _, size in residual_files)
        print(f"\n📁 Archivos residuales encontrados: {humanize.naturalsize(total_size)} en {len(residual_files)} archivos")
        for path, size in sorted(residual_files, key=lambda x: -x[1])[:10]:
            print(f"  - {path} ({humanize.naturalsize(size)})")
        if len(residual_files) > 10:
            print("  ...")
        
        respuesta = input("\n¿Deseas ver los archivos residuales completos? (s/n): ").strip().lower()
        if respuesta == "s":
            for path, size in residual_files:
                print(f"  - {path} ({humanize.naturalsize(size)})")
        
        respuesta = input("\n¿Deseas eliminar estos archivos residuales? (s/n): ").strip().lower()
        if respuesta == "s":
            clean_files(residual_files)
    else:
        print("✅ No se encontraron archivos residuales de aplicaciones desinstaladas.")

    # Escanear carpetas de basura
    print("\n🔍 Escaneando archivos temporales...")
    for name, folder in DIRS_TO_SCAN.items():
        size, files = scan_folder(folder)
        show_results(name, size, files)
        all_files.extend(files)
        total_global += size

    print(f"\n🧼 Total estimado para limpiar: {humanize.naturalsize(total_global)}")

    if not all_files:
        print("\n✅ No se encontraron archivos basura para limpiar en las carpetas de sistema.")
    else:
        respuesta = input("\n¿Deseas eliminar estos archivos? (s/n): ").strip().lower()
        if respuesta == "s":
            print("🧽 Limpiando archivos...")
            clean_files(all_files)
            print("✅ Limpieza de archivos temporales completada.")
        else:
            print("🚫 Limpieza de archivos temporales cancelada.")

if __name__ == "__main__":
    main()
