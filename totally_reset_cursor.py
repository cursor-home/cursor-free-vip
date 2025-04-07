"""
totally_reset_cursor.py - Cursor完全重置工具

本模块提供了重置Cursor应用所有痕迹的功能，包括：
- 删除所有Cursor相关配置文件
- 重置机器ID和设备识别码
- 清除所有登录凭证和会话数据
- 重置使用统计和遥测数据
- 重新安装或修补Cursor关键文件

与reset_machine_manual.py不同，此模块执行更彻底的重置，
确保完全清除Cursor的所有数据和标识，适用于需要完全"重新开始"的情况。
"""
import os
import sys
import json
import uuid
import hashlib
import shutil
import sqlite3
import platform
import re
import tempfile
from colorama import Fore, Style, init
from typing import Tuple
import configparser
from new_signup import get_user_documents_path
import traceback
from config import get_config
import glob

# Initialize colorama
init()

# Define emoji constants
EMOJI = {
    "FILE": "📄",
    "BACKUP": "💾",
    "SUCCESS": "✅",
    "ERROR": "❌",
    "INFO": "ℹ️",
    "RESET": "🔄",
    "WARNING": "⚠️",
}

def get_cursor_paths(translator=None) -> Tuple[str, str]:
    """
    获取Cursor应用程序的重要文件路径
    
    根据不同操作系统确定Cursor应用的package.json和main.js文件路径。
    支持Windows、macOS和Linux系统，并处理不同的安装位置情况。
    
    参数:
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        Tuple[str, str]: 包含package.json和main.js路径的元组
        
    异常:
        OSError: 当找不到必要的文件或路径时抛出
    """
    system = platform.system()
    
    # Read config file
    config = configparser.ConfigParser()
    config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip")
    config_file = os.path.join(config_dir, "config.ini")
    
    # Create config directory if it doesn't exist
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    
    # Default paths for different systems
    default_paths = {
        "Darwin": "/Applications/Cursor.app/Contents/Resources/app",
        "Windows": os.path.join(os.getenv("LOCALAPPDATA", ""), "Programs", "Cursor", "resources", "app"),
        "Linux": ["/opt/Cursor/resources/app", "/usr/share/cursor/resources/app", os.path.expanduser("~/.local/share/cursor/resources/app")]
    }
    
    if system == "Linux":
        # Look for extracted AppImage directories - with usr structure
        extracted_usr_paths = glob.glob(os.path.expanduser("~/squashfs-root/usr/share/cursor/resources/app"))
        # Check current directory for extraction without home path prefix
        current_dir_paths = glob.glob("squashfs-root/usr/share/cursor/resources/app")
        
        # Add all paths to the Linux paths list
        default_paths["Linux"].extend(extracted_usr_paths)
        default_paths["Linux"].extend(current_dir_paths)

        # Print debug info for troubleshooting
        print(f"{Fore.CYAN}{EMOJI['INFO']} Available paths found:{Style.RESET_ALL}")
        for path in default_paths["Linux"]:
            if os.path.exists(path):
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {path} (exists){Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}{EMOJI['ERROR']} {path} (not found){Style.RESET_ALL}")
    
    # If config doesn't exist, create it with default paths
    if not os.path.exists(config_file):
        for section in ['MacPaths', 'WindowsPaths', 'LinuxPaths']:
            if not config.has_section(section):
                config.add_section(section)
        
        if system == "Darwin":
            config.set('MacPaths', 'cursor_path', default_paths["Darwin"])
        elif system == "Windows":
            config.set('WindowsPaths', 'cursor_path', default_paths["Windows"])
        elif system == "Linux":
            # For Linux, try to find the first existing path
            for path in default_paths["Linux"]:
                if os.path.exists(path):
                    config.set('LinuxPaths', 'cursor_path', path)
                    break
            else:
                # If no path exists, use the first one as default
                config.set('LinuxPaths', 'cursor_path', default_paths["Linux"][0])
        
        with open(config_file, 'w', encoding='utf-8') as f:
            config.write(f)
    else:
        config.read(config_file, encoding='utf-8')
    
    # Get path based on system
    if system == "Darwin":
        section = 'MacPaths'
    elif system == "Windows":
        section = 'WindowsPaths'
    elif system == "Linux":
        section = 'LinuxPaths'
    else:
        raise OSError(translator.get('reset.unsupported_os', system=system) if translator else f"不支持的操作系统: {system}")
    
    if not config.has_section(section) or not config.has_option(section, 'cursor_path'):
        raise OSError(translator.get('reset.path_not_configured') if translator else "未配置 Cursor 路徑")
    
    base_path = config.get(section, 'cursor_path')
    
    # For Linux, try to find the first existing path if the configured one doesn't exist
    if system == "Linux" and not os.path.exists(base_path):
        for path in default_paths["Linux"]:
            if os.path.exists(path):
                base_path = path
                # Update config with the found path
                config.set(section, 'cursor_path', path)
                with open(config_file, 'w', encoding='utf-8') as f:
                    config.write(f)
                break
    
    if not os.path.exists(base_path):
        raise OSError(translator.get('reset.path_not_found', path=base_path) if translator else f"找不到 Cursor 路徑: {base_path}")
    
    pkg_path = os.path.join(base_path, "package.json")
    main_path = os.path.join(base_path, "out/main.js")
    
    # Check if files exist
    if not os.path.exists(pkg_path):
        raise OSError(translator.get('reset.package_not_found', path=pkg_path) if translator else f"找不到 package.json: {pkg_path}")
    if not os.path.exists(main_path):
        raise OSError(translator.get('reset.main_not_found', path=main_path) if translator else f"找不到 main.js: {main_path}")
    
    return (pkg_path, main_path)

def get_cursor_machine_id_path(translator=None) -> str:
    """
    获取Cursor机器ID文件的路径
    
    根据操作系统类型确定machineId文件的存储位置，
    从配置文件中读取路径或使用默认路径。
    
    参数:
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        str: machineId文件的完整路径
        
    异常:
        OSError: 当不支持的操作系统时抛出
    """
    # Read configuration
    config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip")
    config_file = os.path.join(config_dir, "config.ini")
    config = configparser.ConfigParser()
    
    if os.path.exists(config_file):
        config.read(config_file)
    
    if sys.platform == "win32":  # Windows
        if not config.has_section('WindowsPaths'):
            config.add_section('WindowsPaths')
            config.set('WindowsPaths', 'machine_id_path', 
                os.path.join(os.getenv("APPDATA"), "Cursor", "machineId"))
        return config.get('WindowsPaths', 'machine_id_path')
        
    elif sys.platform == "linux":  # Linux
        if not config.has_section('LinuxPaths'):
            config.add_section('LinuxPaths')
            config.set('LinuxPaths', 'machine_id_path',
                os.path.expanduser("~/.config/cursor/machineid"))
        return config.get('LinuxPaths', 'machine_id_path')
        
    elif sys.platform == "darwin":  # macOS
        if not config.has_section('MacPaths'):
            config.add_section('MacPaths')
            config.set('MacPaths', 'machine_id_path',
                os.path.expanduser("~/Library/Application Support/Cursor/machineId"))
        return config.get('MacPaths', 'machine_id_path')
        
    else:
        raise OSError(f"Unsupported operating system: {sys.platform}")

    # Save any changes to config file
    with open(config_file, 'w', encoding='utf-8') as f:
        config.write(f)

def get_workbench_cursor_path(translator=None) -> str:
    """
    获取Cursor工作台JS文件路径
    
    找到workbench.desktop.main.js文件的位置，该文件包含Cursor的
    核心功能代码，根据不同的操作系统类型确定文件路径。
    
    参数:
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        str: workbench.desktop.main.js文件的完整路径
        
    异常:
        OSError: 当找不到文件或不支持的操作系统时抛出
    """
    system = platform.system()
    
    paths_map = {
        "Darwin": {  # macOS
            "base": "/Applications/Cursor.app/Contents/Resources/app",
            "main": "out/vs/workbench/workbench.desktop.main.js"
        },
        "Windows": {
            "base": os.path.join(os.getenv("LOCALAPPDATA", ""), "Programs", "Cursor", "resources", "app"),
            "main": "out/vs/workbench/workbench.desktop.main.js"
        },
        "Linux": {
            "bases": ["/opt/Cursor/resources/app", "/usr/share/cursor/resources/app"],
            "main": "out/vs/workbench/workbench.desktop.main.js"
        }
    }

    if system == "Linux":
        # Look for extracted AppImage with correct usr structure
        extracted_usr_paths = glob.glob(os.path.expanduser("~/squashfs-root/usr/share/cursor/resources/app"))
        # Check current directory for extraction
        current_dir_paths = glob.glob("squashfs-root/usr/share/cursor/resources/app")
  
        
        paths_map["Linux"]["bases"].extend(extracted_usr_paths)
        paths_map["Linux"]["bases"].extend(current_dir_paths)

        for base in paths_map["Linux"]["bases"]:
            main_path = os.path.join(base, paths_map["Linux"]["main"])
            if os.path.exists(main_path):
                return main_path
        raise OSError(translator.get('reset.linux_path_not_found') if translator else "在 Linux 系统上未找到 Cursor 安装路径")

    base_path = paths_map[system]["base"]
    main_path = os.path.join(base_path, paths_map[system]["main"])
    
    if not os.path.exists(main_path):
        raise OSError(translator.get('reset.file_not_found', path=main_path) if translator else f"未找到 Cursor main.js 文件: {main_path}")
        
    return main_path

def version_check(version: str, min_version: str = "", max_version: str = "", translator=None) -> bool:
    """
    版本号检查功能
    
    验证给定的版本号格式是否正确，并检查其是否在指定的最小和最大版本范围内。
    用于确保程序只在兼容的Cursor版本上运行。
    
    参数:
        version (str): 要检查的版本号，格式为"x.y.z"
        min_version (str): 最小支持的版本号，格式为"x.y.z"
        max_version (str): 最大支持的版本号，格式为"x.y.z"
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        bool: 版本检查通过返回True，否则返回False
    """
    version_pattern = r"^\d+\.\d+\.\d+$"
    try:
        if not re.match(version_pattern, version):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.invalid_version_format', version=version)}{Style.RESET_ALL}")
            return False

        def parse_version(ver: str) -> Tuple[int, ...]:
            """
            解析版本号字符串为整数元组
            
            参数:
                ver (str): 版本号字符串，格式为"x.y.z"
                
            返回值:
                Tuple[int, ...]: 版本号的整数元组表示，如(1, 2, 3)
            """
            return tuple(map(int, ver.split(".")))

        current = parse_version(version)

        if min_version and current < parse_version(min_version):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_too_low', version=version, min_version=min_version)}{Style.RESET_ALL}")
            return False

        if max_version and current > parse_version(max_version):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_too_high', version=version, max_version=max_version)}{Style.RESET_ALL}")
            return False

        return True

    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_check_error', error=str(e))}{Style.RESET_ALL}")
        return False

def check_cursor_version(translator) -> bool:
    """
    检查Cursor版本
    
    读取Cursor的package.json文件，解析其版本号并验证是否
    符合程序的兼容性要求。会处理各种可能的错误情况，如
    文件不存在、JSON解析错误、格式无效等。
    
    参数:
        translator: 翻译器对象，用于多语言支持
        
    返回值:
        bool: 版本检查通过返回True，否则返回False
    """
    try:
        pkg_path, _ = get_cursor_paths(translator)
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.reading_package_json', path=pkg_path)}{Style.RESET_ALL}")
        
        try:
            with open(pkg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except UnicodeDecodeError:
            # If UTF-8 reading fails, try other encodings
            with open(pkg_path, "r", encoding="latin-1") as f:
                data = json.load(f)
                
        if not isinstance(data, dict):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.invalid_json_object')}{Style.RESET_ALL}")
            return False
            
        if "version" not in data:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.no_version_field')}{Style.RESET_ALL}")
            return False
            
        version = str(data["version"]).strip()
        if not version:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_field_empty')}{Style.RESET_ALL}")
            return False
            
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.found_version', version=version)}{Style.RESET_ALL}")
        
        # Check version format
        if not re.match(r"^\d+\.\d+\.\d+$", version):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.invalid_version_format', version=version)}{Style.RESET_ALL}")
            return False
            
        # Compare versions
        try:
            current = tuple(map(int, version.split(".")))
            min_ver = (0, 45, 0)  # Use tuple directly instead of string
            
            if current >= min_ver:
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.version_check_passed', version=version, min_version='0.45.0')}{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.version_too_low', version=version, min_version='0.45.0')}{Style.RESET_ALL}")
                return False
        except ValueError as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_parse_error', error=str(e))}{Style.RESET_ALL}")
            return False
            
    except FileNotFoundError as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.package_not_found', path=pkg_path)}{Style.RESET_ALL}")
        return False
    except json.JSONDecodeError as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.invalid_json_object')}{Style.RESET_ALL}")
        return False
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.check_version_failed', error=str(e))}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.stack_trace')}: {traceback.format_exc()}{Style.RESET_ALL}")
        return False

def modify_workbench_js(file_path: str, translator=None) -> bool:
    """
    修改Cursor工作台JS文件
    
    修改workbench.desktop.main.js文件中的界面元素，替换"升级到Pro"按钮，
    移除试用标记，并隐藏通知提示。保留原始文件的权限并创建备份。
    根据不同操作系统使用不同的替换模式。
    
    参数:
        file_path (str): 要修改的文件路径
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        bool: 修改成功返回True，否则返回False
    """
    try:
        # Save original file permissions
        original_stat = os.stat(file_path)
        original_mode = original_stat.st_mode
        original_uid = original_stat.st_uid
        original_gid = original_stat.st_gid

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", errors="ignore", delete=False) as tmp_file:
            # Read original content
            with open(file_path, "r", encoding="utf-8", errors="ignore") as main_file:
                content = main_file.read()

            if sys.platform == "win32":
                # Define replacement patterns
                CButton_old_pattern = r'$(k,E(Ks,{title:"Upgrade to Pro",size:"small",get codicon(){return F.rocket},get onClick(){return t.pay}}),null)'
                CButton_new_pattern = r'$(k,E(Ks,{title:"yeongpin GitHub",size:"small",get codicon(){return F.rocket},get onClick(){return function(){window.open("https://github.com/yeongpin/cursor-free-vip","_blank")}}}),null)'
            elif sys.platform == "linux":
                CButton_old_pattern = r'$(k,E(Ks,{title:"Upgrade to Pro",size:"small",get codicon(){return F.rocket},get onClick(){return t.pay}}),null)'
                CButton_new_pattern = r'$(k,E(Ks,{title:"yeongpin GitHub",size:"small",get codicon(){return F.rocket},get onClick(){return function(){window.open("https://github.com/yeongpin/cursor-free-vip","_blank")}}}),null)'
            elif sys.platform == "darwin":
                CButton_old_pattern = r'M(x,I(as,{title:"Upgrade to Pro",size:"small",get codicon(){return $.rocket},get onClick(){return t.pay}}),null)'
                CButton_new_pattern = r'M(x,I(as,{title:"yeongpin GitHub",size:"small",get codicon(){return $.rocket},get onClick(){return function(){window.open("https://github.com/yeongpin/cursor-free-vip","_blank")}}}),null)'

            CBadge_old_pattern = r'<div>Pro Trial'
            CBadge_new_pattern = r'<div>Pro'

            CToast_old_pattern = r'notifications-toasts'
            CToast_new_pattern = r'notifications-toasts hidden'

            # Replace content
            content = content.replace(CButton_old_pattern, CButton_new_pattern)
            content = content.replace(CBadge_old_pattern, CBadge_new_pattern)
            content = content.replace(CToast_old_pattern, CToast_new_pattern)

            # Write to temporary file
            tmp_file.write(content)
            tmp_path = tmp_file.name

        # Backup original file
        backup_path = file_path + ".backup"
        if os.path.exists(backup_path):
            os.remove(backup_path)
        shutil.copy2(file_path, backup_path)
        
        # Move temporary file to original position
        if os.path.exists(file_path):
            os.remove(file_path)
        shutil.move(tmp_path, file_path)

        # Restore original permissions
        os.chmod(file_path, original_mode)
        if os.name != "nt":  # Not Windows
            os.chown(file_path, original_uid, original_gid)

        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.file_modified')}{Style.RESET_ALL}")
        return True

    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.modify_file_failed', error=str(e))}{Style.RESET_ALL}")
        if "tmp_path" in locals():
            try:
                os.unlink(tmp_path)
            except:
                pass
        return False

def modify_main_js(main_path: str, translator) -> bool:
    """
    修改Cursor主JS文件
    
    替换main.js文件中获取机器ID的函数实现，确保Cursor使用固定的机器ID，
    而不是动态生成的ID。会创建原始文件的备份，并保留文件的原始权限设置。
    
    参数:
        main_path (str): main.js文件的路径
        translator: 翻译器对象，用于多语言支持
        
    返回值:
        bool: 修改成功返回True，否则返回False
    """
    try:
        original_stat = os.stat(main_path)
        original_mode = original_stat.st_mode
        original_uid = original_stat.st_uid
        original_gid = original_stat.st_gid

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_file:
            with open(main_path, "r", encoding="utf-8") as main_file:
                content = main_file.read()

            patterns = {
                r"async getMachineId\(\)\{return [^??]+\?\?([^}]+)\}": r"async getMachineId(){return \1}",
                r"async getMacMachineId\(\)\{return [^??]+\?\?([^}]+)\}": r"async getMacMachineId(){return \1}",
            }

            for pattern, replacement in patterns.items():
                content = re.sub(pattern, replacement, content)

            tmp_file.write(content)
            tmp_path = tmp_file.name

        shutil.copy2(main_path, main_path + ".old")
        shutil.move(tmp_path, main_path)

        os.chmod(main_path, original_mode)
        if os.name != "nt":
            os.chown(main_path, original_uid, original_gid)

        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.file_modified')}{Style.RESET_ALL}")
        return True

    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.modify_file_failed', error=str(e))}{Style.RESET_ALL}")
        if "tmp_path" in locals():
            os.unlink(tmp_path)
        return False

def patch_cursor_get_machine_id(translator) -> bool:
    """
    修补Cursor获取机器ID的功能
    
    检查Cursor版本，创建文件备份，然后修改main.js文件中的getMachineId函数，
    使其返回固定的ID而不是系统生成的ID，从而绕过使用限制。
    
    参数:
        translator: 翻译器对象，用于多语言支持
        
    返回值:
        bool: 修补成功返回True，失败返回False
    """
    try:
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.start_patching')}...{Style.RESET_ALL}")
        
        # Get paths
        pkg_path, main_path = get_cursor_paths(translator)
        
        # Check file permissions
        for file_path in [pkg_path, main_path]:
            if not os.path.isfile(file_path):
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.file_not_found', path=file_path)}{Style.RESET_ALL}")
                return False
            if not os.access(file_path, os.W_OK):
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.no_write_permission', path=file_path)}{Style.RESET_ALL}")
                return False

        # Get version number
        try:
            with open(pkg_path, "r", encoding="utf-8") as f:
                version = json.load(f)["version"]
            print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.current_version', version=version)}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.read_version_failed', error=str(e))}{Style.RESET_ALL}")
            return False

        # Check version
        if not version_check(version, min_version="0.45.0", translator=translator):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_not_supported')}{Style.RESET_ALL}")
            return False

        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.version_check_passed')}{Style.RESET_ALL}")

        # Backup file
        backup_path = main_path + ".bak"
        if not os.path.exists(backup_path):
            shutil.copy2(main_path, backup_path)
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.backup_created', path=backup_path)}{Style.RESET_ALL}")

        # Modify file
        if not modify_main_js(main_path, translator):
            return False

        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.patch_completed')}{Style.RESET_ALL}")
        return True

    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.patch_failed', error=str(e))}{Style.RESET_ALL}")
        return False

class MachineIDResetter:
    """
    机器ID重置器类
    
    负责管理和重置Cursor应用程序使用的机器ID和相关标识符，
    包括存储在JSON文件和SQLite数据库中的ID。支持不同操作系统，
    自动处理不同平台的文件路径差异。
    """
    def __init__(self, translator=None):
        """
        初始化机器ID重置器
        
        读取配置文件，根据操作系统确定Cursor数据文件的路径，
        并准备重置所需的文件路径信息。
        
        参数:
            translator: 翻译器对象，用于多语言支持，可以为None
            
        异常:
            FileNotFoundError: 当找不到配置文件时抛出
            EnvironmentError: 当环境变量未设置时抛出
        """
        self.translator = translator

        # Read configuration
        config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip")
        config_file = os.path.join(config_dir, "config.ini")
        config = configparser.ConfigParser()
        
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Config file not found: {config_file}")
        
        config.read(config_file, encoding='utf-8')

        # Check operating system
        if sys.platform == "win32":  # Windows
            appdata = os.getenv("APPDATA")
            if appdata is None:
                raise EnvironmentError("APPDATA Environment Variable Not Set")
            
            if not config.has_section('WindowsPaths'):
                config.add_section('WindowsPaths')
                config.set('WindowsPaths', 'storage_path', os.path.join(
                    appdata, "Cursor", "User", "globalStorage", "storage.json"
                ))
                config.set('WindowsPaths', 'sqlite_path', os.path.join(
                    appdata, "Cursor", "User", "globalStorage", "state.vscdb"
                ))
                
            self.db_path = config.get('WindowsPaths', 'storage_path')
            self.sqlite_path = config.get('WindowsPaths', 'sqlite_path')
            
        elif sys.platform == "darwin":  # macOS
            if not config.has_section('MacPaths'):
                config.add_section('MacPaths')
                config.set('MacPaths', 'storage_path', os.path.abspath(os.path.expanduser(
                    "~/Library/Application Support/Cursor/User/globalStorage/storage.json"
                )))
                config.set('MacPaths', 'sqlite_path', os.path.abspath(os.path.expanduser(
                    "~/Library/Application Support/Cursor/User/globalStorage/state.vscdb"
                )))
                
            self.db_path = config.get('MacPaths', 'storage_path')
            self.sqlite_path = config.get('MacPaths', 'sqlite_path')
            
        elif sys.platform == "linux":  # Linux
            if not config.has_section('LinuxPaths'):
                config.add_section('LinuxPaths')
                # Get actual user's home directory
                sudo_user = os.environ.get('SUDO_USER')
                actual_home = f"/home/{sudo_user}" if sudo_user else os.path.expanduser("~")
                
                config.set('LinuxPaths', 'storage_path', os.path.abspath(os.path.join(
                    actual_home,
                    ".config/cursor/User/globalStorage/storage.json"
                )))
                config.set('LinuxPaths', 'sqlite_path', os.path.abspath(os.path.join(
                    actual_home,
                    ".config/cursor/User/globalStorage/state.vscdb"
                )))
                
            self.db_path = config.get('LinuxPaths', 'storage_path')
            self.sqlite_path = config.get('LinuxPaths', 'sqlite_path')
            
        else:
            raise NotImplementedError(f"Not Supported OS: {sys.platform}")

        # Save any changes to config file
        with open(config_file, 'w', encoding='utf-8') as f:
            config.write(f)

    def generate_new_ids(self):
        """
        生成新的机器ID和相关标识符
        
        创建一组新的随机标识符，包括UUID、机器ID、Mac机器ID和遥测ID，
        并更新machineId文件。这些新ID将被用于替换Cursor使用的旧ID。
        
        返回值:
            dict: 包含各种新生成ID的字典，键为ID名称，值为ID值
        """
        # Generate new UUID
        dev_device_id = str(uuid.uuid4())

        # Generate new machineId (64 characters of hexadecimal)
        machine_id = hashlib.sha256(os.urandom(32)).hexdigest()

        # Generate new macMachineId (128 characters of hexadecimal)
        mac_machine_id = hashlib.sha512(os.urandom(64)).hexdigest()

        # Generate new sqmId
        sqm_id = "{" + str(uuid.uuid4()).upper() + "}"

        self.update_machine_id_file(dev_device_id)

        return {
            "telemetry.devDeviceId": dev_device_id,
            "telemetry.macMachineId": mac_machine_id,
            "telemetry.machineId": machine_id,
            "telemetry.sqmId": sqm_id,
            "storage.serviceMachineId": dev_device_id,  # Add storage.serviceMachineId
        }

    def update_sqlite_db(self, new_ids):
        """
        更新SQLite数据库中的机器ID
        
        将新生成的ID写入Cursor使用的SQLite数据库中，
        创建或更新ItemTable表中的相关键值对，确保
        Cursor使用新的机器标识。
        
        参数:
            new_ids (dict): 包含新ID的字典，键为ID名称，值为ID值
            
        返回值:
            bool: 更新成功返回True，失败返回False
        """
        try:
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.updating_sqlite')}...{Style.RESET_ALL}")
            
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ItemTable (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            updates = [
                (key, value) for key, value in new_ids.items()
            ]

            for key, value in updates:
                cursor.execute("""
                    INSERT OR REPLACE INTO ItemTable (key, value) 
                    VALUES (?, ?)
                """, (key, value))
                print(f"{EMOJI['INFO']} {Fore.CYAN} {self.translator.get('reset.updating_pair')}: {key}{Style.RESET_ALL}")

            conn.commit()
            conn.close()
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.sqlite_success')}{Style.RESET_ALL}")
            return True

        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.sqlite_error', error=str(e))}{Style.RESET_ALL}")
            return False

    def update_system_ids(self, new_ids):
        """
        更新系统级别的机器ID
        
        根据操作系统类型更新系统级别的机器标识符，包括Windows注册表中的
        MachineGuid和MachineId，以及macOS平台的UUID，确保系统提供一致的
        机器标识。
        
        参数:
            new_ids (dict): 包含新ID的字典，键为ID名称，值为ID值
            
        返回值:
            bool: 更新成功返回True，失败返回False
        """
        try:
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.updating_system_ids')}...{Style.RESET_ALL}")
            
            if sys.platform.startswith("win"):
                self._update_windows_machine_guid()
                self._update_windows_machine_id()
            elif sys.platform == "darwin":
                self._update_macos_platform_uuid(new_ids)
                
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.system_ids_updated')}{Style.RESET_ALL}")
            return True
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.system_ids_update_failed', error=str(e))}{Style.RESET_ALL}")
            return False

    def _update_windows_machine_guid(self):
        """
        更新Windows MachineGuid
        
        在Windows注册表中更新加密模块使用的MachineGuid值，
        这个值常被应用程序用于识别Windows设备。需要管理员权限。
        
        异常:
            PermissionError: 当没有足够权限访问注册表时抛出
            Exception: 其他更新失败时抛出
        """
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                "SOFTWARE\\Microsoft\\Cryptography",
                0,
                winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY
            )
            new_guid = str(uuid.uuid4())
            winreg.SetValueEx(key, "MachineGuid", 0, winreg.REG_SZ, new_guid)
            winreg.CloseKey(key)
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.windows_machine_guid_updated')}{Style.RESET_ALL}")
        except PermissionError:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.permission_denied')}{Style.RESET_ALL}")
            raise
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.update_windows_machine_guid_failed', error=str(e))}{Style.RESET_ALL}")
            raise
    
    def _update_windows_machine_id(self):
        """
        更新Windows SQMClient MachineId
        
        在Windows注册表中更新SQMClient使用的MachineId值，
        这个值通常用于软件质量监测和遥测系统。如果注册表项
        不存在，会创建相应的项。需要管理员权限。
        
        返回值:
            bool: 更新成功返回True，失败返回False
        """
        try:
            import winreg
            # 1. Generate new GUID
            new_guid = "{" + str(uuid.uuid4()).upper() + "}"
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.new_machine_id')}: {new_guid}{Style.RESET_ALL}")
            
            # 2. Open the registry key
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\SQMClient",
                    0,
                    winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY
                )
            except FileNotFoundError:
                # If the key does not exist, create it
                key = winreg.CreateKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\SQMClient"
                )
            
            # 3. Set MachineId value
            winreg.SetValueEx(key, "MachineId", 0, winreg.REG_SZ, new_guid)
            winreg.CloseKey(key)
            
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.windows_machine_id_updated')}{Style.RESET_ALL}")
            return True
            
        except PermissionError:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.permission_denied')}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.run_as_admin')}{Style.RESET_ALL}")
            return False
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.update_windows_machine_id_failed', error=str(e))}{Style.RESET_ALL}")
            return False
                    

    def _update_macos_platform_uuid(self, new_ids):
        """
        更新macOS平台UUID
        
        修改macOS系统配置中的平台UUID值，这个值用于识别macOS设备。
        使用plutil命令更新com.apple.platform.uuid.plist文件，
        需要root权限才能执行。
        
        参数:
            new_ids (dict): 包含新ID的字典，键为ID名称，值为ID值
            
        异常:
            Exception: 当执行plutil命令失败时抛出
        """
        try:
            uuid_file = "/var/root/Library/Preferences/SystemConfiguration/com.apple.platform.uuid.plist"
            if os.path.exists(uuid_file):
                # Use sudo to execute plutil command
                cmd = f'sudo plutil -replace "UUID" -string "{new_ids["telemetry.macMachineId"]}" "{uuid_file}"'
                result = os.system(cmd)
                if result == 0:
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.macos_platform_uuid_updated')}{Style.RESET_ALL}")
                else:
                    raise Exception(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.failed_to_execute_plutil_command')}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.update_macos_platform_uuid_failed', error=str(e))}{Style.RESET_ALL}")
            raise

    def reset_machine_ids(self):
        """
        重置所有机器ID
        
        执行完整的机器ID重置流程，包括：
        1. 读取和备份原始配置文件
        2. 生成新的随机ID
        3. 更新各种配置文件和数据库
        4. 更新系统级ID
        5. 修补Cursor代码文件
        
        会检查Cursor版本并根据版本选择合适的修补方式。
        
        返回值:
            bool: 重置成功返回True，失败返回False
        """
        try:
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.checking')}...{Style.RESET_ALL}")

            if not os.path.exists(self.db_path):
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.not_found')}: {self.db_path}{Style.RESET_ALL}")
                return False

            if not os.access(self.db_path, os.R_OK | os.W_OK):
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.no_permission')}{Style.RESET_ALL}")
                return False

            print(f"{Fore.CYAN}{EMOJI['FILE']} {self.translator.get('reset.reading')}...{Style.RESET_ALL}")
            with open(self.db_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            backup_path = self.db_path + ".bak"
            if not os.path.exists(backup_path):
                print(f"{Fore.YELLOW}{EMOJI['BACKUP']} {self.translator.get('reset.creating_backup')}: {backup_path}{Style.RESET_ALL}")
                shutil.copy2(self.db_path, backup_path)
            else:
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.backup_exists')}{Style.RESET_ALL}")

            print(f"{Fore.CYAN}{EMOJI['RESET']} {self.translator.get('reset.generating')}...{Style.RESET_ALL}")
            new_ids = self.generate_new_ids()

            # Update configuration file
            config.update(new_ids)

            print(f"{Fore.CYAN}{EMOJI['FILE']} {self.translator.get('reset.saving_json')}...{Style.RESET_ALL}")
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)

            # Update SQLite database
            self.update_sqlite_db(new_ids)

            # Update system IDs
            self.update_system_ids(new_ids)


            # Modify workbench.desktop.main.js
            workbench_path = get_workbench_cursor_path(self.translator)
            modify_workbench_js(workbench_path, self.translator)

            # Check Cursor version and perform corresponding actions
            
            greater_than_0_45 = check_cursor_version(self.translator)
            if greater_than_0_45:
                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.detecting_version')} >= 0.45.0，{self.translator.get('reset.patching_getmachineid')}{Style.RESET_ALL}")
                patch_cursor_get_machine_id(self.translator)
            else:
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.version_less_than_0_45')}{Style.RESET_ALL}")

            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.success')}{Style.RESET_ALL}")
            print(f"\n{Fore.CYAN}{self.translator.get('reset.new_id')}:{Style.RESET_ALL}")
            for key, value in new_ids.items():
                print(f"{EMOJI['INFO']} {key}: {Fore.GREEN}{value}{Style.RESET_ALL}")

            return True

        except PermissionError as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.permission_error', error=str(e))}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.run_as_admin')}{Style.RESET_ALL}")
            return False
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.process_error', error=str(e))}{Style.RESET_ALL}")
            return False

    def update_machine_id_file(self, machine_id: str) -> bool:
        """
        更新machineId文件
        
        用新生成的机器ID覆盖Cursor使用的machineId文件，
        会自动创建目录（如果不存在）和备份原始文件。
        
        参数:
            machine_id (str): 新的机器ID字符串
            
        返回值:
            bool: 更新成功返回True，失败返回False
        """
        try:
            # Get the machineId file path
            machine_id_path = get_cursor_machine_id_path()
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(machine_id_path), exist_ok=True)

            # Create backup if file exists
            if os.path.exists(machine_id_path):
                backup_path = machine_id_path + ".backup"
                try:
                    shutil.copy2(machine_id_path, backup_path)
                    print(f"{Fore.GREEN}{EMOJI['INFO']} {self.translator.get('reset.backup_created', path=backup_path) if self.translator else f'Backup created at: {backup_path}'}{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.backup_creation_failed', error=str(e)) if self.translator else f'Could not create backup: {str(e)}'}{Style.RESET_ALL}")

            # Write new machine ID to file
            with open(machine_id_path, "w", encoding="utf-8") as f:
                f.write(machine_id)

            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.update_success') if self.translator else 'Successfully updated machineId file'}{Style.RESET_ALL}")
            return True

        except Exception as e:
            error_msg = f"Failed to update machineId file: {str(e)}"
            if self.translator:
                error_msg = self.translator.get('reset.update_failed', error=str(e))
            print(f"{Fore.RED}{EMOJI['ERROR']} {error_msg}{Style.RESET_ALL}")
            return False

def run(translator=None):
    """
    运行Cursor完全重置程序
    
    获取配置信息，创建MachineIDResetter实例，并执行重置操作。
    这是从主程序或命令行调用时的入口函数。
    
    参数:
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        bool: 操作成功返回True，失败返回False
    """
    config = get_config(translator)
    if not config:
        return False
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{EMOJI['RESET']} {translator.get('reset.title')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")

    resetter = MachineIDResetter(translator)  # Correctly pass translator
    resetter.reset_machine_ids()

    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    input(f"{EMOJI['INFO']} {translator.get('reset.press_enter')}...")

if __name__ == "__main__":
    from main import translator as main_translator
    run(main_translator)