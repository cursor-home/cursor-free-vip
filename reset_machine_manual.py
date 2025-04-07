"""
reset_machine_manual.py - 机器ID重置工具

本模块负责重置Cursor应用程序使用的机器ID和相关标识符，主要功能包括：
- 生成新的唯一标识符(UUID)
- 修改Cursor应用程序中的machineId文件
- 更新系统中的机器ID相关配置
- 修补Cursor代码中获取机器ID的函数
- 备份和恢复重要文件

通过重置机器ID，可以解除Cursor对同一设备的使用限制，便于多账号使用。
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
import glob
from colorama import Fore, Style, init
from typing import Tuple
import configparser
from new_signup import get_user_documents_path
import traceback
from config import get_config

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
    
    根据操作系统确定Cursor应用程序package.json和main.js文件的路径。
    支持Windows、macOS和Linux系统，会自动检测可能的安装位置。
    
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
        "Linux": ["/opt/Cursor/resources/app", "/usr/share/cursor/resources/app", os.path.expanduser("~/.local/share/cursor/resources/app"), "/usr/lib/cursor/app/"]
    }
    
    if system == "Linux":
        # Look for extracted AppImage with correct usr structure
        extracted_usr_paths = glob.glob(os.path.expanduser("~/squashfs-root/usr/share/cursor/resources/app"))
        # Also check current directory for extraction without home path prefix
        current_dir_paths = glob.glob("squashfs-root/usr/share/cursor/resources/app")
        
        # Add any found paths to the Linux paths list
        default_paths["Linux"].extend(extracted_usr_paths)
        default_paths["Linux"].extend(current_dir_paths)
        
        # Print debug information
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
    
    根据不同操作系统确定machineId文件的存储位置，
    并从配置文件读取或写入默认路径。
    
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
    获取Cursor工作台主JS文件路径
    
    根据操作系统确定workbench.desktop.main.js文件的位置，
    这个文件包含Cursor应用程序的核心功能代码。
    
    参数:
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        str: workbench.desktop.main.js文件的完整路径
        
    异常:
        OSError: 当找不到文件或不支持的操作系统时抛出
    """
    system = platform.system()

    # Read configuration
    config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip")
    config_file = os.path.join(config_dir, "config.ini")
    config = configparser.ConfigParser()

    if os.path.exists(config_file):
        config.read(config_file)
    
    paths_map = {
        "Darwin": {  # macOS
            "base": "/Applications/Cursor.app/Contents/Resources/app",
            "main": "out/vs/workbench/workbench.desktop.main.js"
        },
        "Windows": {
            "main": "out\\vs\\workbench\\workbench.desktop.main.js"
        },
        "Linux": {
            "bases": ["/opt/Cursor/resources/app", "/usr/share/cursor/resources/app", "/usr/lib/cursor/app/"],
            "main": "out/vs/workbench/workbench.desktop.main.js"
        }
    }
    
    if system == "Linux":
        # Add extracted AppImage with correct usr structure
        extracted_usr_paths = glob.glob(os.path.expanduser("~/squashfs-root/usr/share/cursor/resources/app"))
            
        paths_map["Linux"]["bases"].extend(extracted_usr_paths)

    if system not in paths_map:
        raise OSError(translator.get('reset.unsupported_os', system=system) if translator else f"不支持的操作系统: {system}")

    if system == "Linux":
        for base in paths_map["Linux"]["bases"]:
            main_path = os.path.join(base, paths_map["Linux"]["main"])
            print(f"{Fore.CYAN}{EMOJI['INFO']} Checking path: {main_path}{Style.RESET_ALL}")
            if os.path.exists(main_path):
                return main_path

    if system == "Windows":
        base_path = config.get('WindowsPaths', 'cursor_path')
    else:
        base_path = paths_map[system]["base"]

    main_path = os.path.join(base_path, paths_map[system]["main"])
    
    if not os.path.exists(main_path):
        raise OSError(translator.get('reset.file_not_found', path=main_path) if translator else f"未找到 Cursor main.js 文件: {main_path}")
        
    return main_path

def version_check(version: str, min_version: str = "", max_version: str = "", translator=None) -> bool:
    """
    版本号检查函数
    
    检查给定的版本号是否在指定的最小和最大版本范围内，
    确保程序只在兼容的Cursor版本上运行。
    
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
    
    读取Cursor的package.json文件获取版本号，并验证是否在支持的版本范围内。
    同时显示当前版本和支持的版本范围。
    
    参数:
        translator: 翻译器对象，用于多语言支持
        
    返回值:
        bool: 版本检查通过返回True，否则返回False
    """
    # Read config
    config = get_config(translator)
    
    # Get min and max version from config
    min_version = config.get('Version', 'min_cursor_version', fallback='0.0.1')
    max_version = config.get('Version', 'max_cursor_version', fallback='999.999.999')
    
    try:
        # Get Cursor paths
        pkg_path, _ = get_cursor_paths(translator)
        
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.loading_package')}: {pkg_path}{Style.RESET_ALL}")
        
        # Read package.json
        with open(pkg_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                cursor_version = data.get('version', '')
                
                # Print current version
                print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.cursor_version')}: {cursor_version}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.supported_version')}: {min_version} - {max_version}{Style.RESET_ALL}")
                
                # Check version compatibility
                if version_check(cursor_version, min_version, max_version, translator):
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.version_supported')}{Style.RESET_ALL}")
                    return True
                else:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_not_supported')}{Style.RESET_ALL}")
                    return False
                    
            except json.JSONDecodeError:
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.invalid_json')}{Style.RESET_ALL}")
                return False
                
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_check_failed', error=str(e))}{Style.RESET_ALL}")
        return False

def modify_workbench_js(file_path: str, translator=None) -> bool:
    """
    修改Cursor工作台JS文件
    
    修改workbench.desktop.main.js文件中的机器ID获取功能，
    使其返回固定的ID而不是真实的机器ID，以绕过使用限制。
    
    参数:
        file_path (str): workbench.desktop.main.js文件的路径
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        bool: 修改成功返回True，否则返回False
    """
    print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.modifying_workbench') if translator else '修改 workbench.js'}: {file_path}{Style.RESET_ALL}")
    
    # Create backup first
    backup_path = f"{file_path}.backup"
    if not os.path.exists(backup_path):
        try:
            shutil.copy2(file_path, backup_path)
            print(f"{Fore.GREEN}{EMOJI['BACKUP']} {translator.get('reset.backup_created') if translator else '创建备份'}: {backup_path}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.backup_failed', error=str(e)) if translator else f'备份失败: {str(e)}'}{Style.RESET_ALL}")
            return False
    
    try:
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Define the code pattern to match
        code_pattern = r'(getUniqueIdentifier\(\)[^}]+return\s+)([^}]+)(;?\s*\})'
        
        # Define the replacement code
        replacement = r'\1"f74c5e8a-0e20-4c1c-a48c-a5cbe71f4240"\3'
        
        # Check if pattern exists
        if re.search(code_pattern, content):
            # Already modified?
            if '"f74c5e8a-0e20-4c1c-a48c-a5cbe71f4240"' in content:
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('reset.already_modified') if translator else '文件已被修改'}{Style.RESET_ALL}")
                return True
                
            # Apply modification
            modified_content = re.sub(code_pattern, replacement, content)
            
            # Write modified content back to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
                
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.modification_success') if translator else '修改成功'}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.pattern_not_found') if translator else '未找到匹配模式'}{Style.RESET_ALL}")
            return False
            
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.modification_failed', error=str(e)) if translator else f'修改失败: {str(e)}'}{Style.RESET_ALL}")
        traceback.print_exc()
        return False

def modify_main_js(main_path: str, translator) -> bool:
    """
    修改Cursor主JS文件
    
    修改main.js文件中的设备ID验证逻辑，
    使其无论何时都返回成功结果，绕过验证限制。
    
    参数:
        main_path (str): main.js文件的路径
        translator: 翻译器对象，用于多语言支持
        
    返回值:
        bool: 修改成功返回True，否则返回False
    """
    print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.modifying_main')}: {main_path}{Style.RESET_ALL}")
    
    # Create backup first
    backup_path = f"{main_path}.backup"
    if not os.path.exists(backup_path):
        try:
            shutil.copy2(main_path, backup_path)
            print(f"{Fore.GREEN}{EMOJI['BACKUP']} {translator.get('reset.backup_created')}: {backup_path}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.backup_failed', error=str(e))}{Style.RESET_ALL}")
            return False
    
    try:
        # Read file content
        with open(main_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if already modified
        if "true" in content and re.search(r'new Promise\(\(\w+,\w+\)=>{(\w+)\("true"\)', content):
            print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('reset.already_modified')}{Style.RESET_ALL}")
            return True
            
        # Apply modification
        modified_content = re.sub(
            r'validateDeviceId\(\w+\)\{return new Promise\(\(\w+,\w+\)=>{',
            r'validateDeviceId(e){return new Promise((t,n)=>{t("true");return;',
            content
        )
        
        # Write modified content back to file
        with open(main_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
            
        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.modification_success')}{Style.RESET_ALL}")
        return True
            
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.modification_failed', error=str(e))}{Style.RESET_ALL}")
        return False

def patch_cursor_get_machine_id(translator) -> bool:
    """
    修补Cursor获取机器ID的功能
    
    修改Cursor应用程序中获取机器ID的相关代码，
    使其绕过机器ID检查或返回固定值。
    
    参数:
        translator: 翻译器对象，用于多语言支持
        
    返回值:
        bool: 修补成功返回True，否则返回False
    """
    try:
        # Get paths
        pkg_path, main_path = get_cursor_paths(translator)
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.cursor_paths_found')}{Style.RESET_ALL}")
        
        # Print paths
        print(f"{Fore.CYAN}{EMOJI['INFO']} package.json: {pkg_path}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{EMOJI['INFO']} main.js: {main_path}{Style.RESET_ALL}")
        
        # Check if files exist and are readable
        if not os.path.exists(pkg_path) or not os.access(pkg_path, os.R_OK):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.file_not_readable', path=pkg_path)}{Style.RESET_ALL}")
            return False
            
        if not os.path.exists(main_path) or not os.access(main_path, os.R_OK):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.file_not_readable', path=main_path)}{Style.RESET_ALL}")
            return False
            
        # Check if we have write permissions
        if not os.access(os.path.dirname(main_path), os.W_OK):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.no_write_permission', path=main_path)}{Style.RESET_ALL}")
            return False
            
        # Get workbench.js path
        workbench_path = get_workbench_cursor_path(translator)
        print(f"{Fore.CYAN}{EMOJI['INFO']} workbench.js: {workbench_path}{Style.RESET_ALL}")
        
        # Modify main.js
        if not modify_main_js(main_path, translator):
            return False
            
        # Modify workbench.js
        if not modify_workbench_js(workbench_path, translator):
            return False
            
        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.patch_success')}{Style.RESET_ALL}")
        return True
        
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.patch_failed', error=str(e))}{Style.RESET_ALL}")
        traceback.print_exc()
        return False

class MachineIDResetter:
    """
    机器ID重置器类
    
    负责管理和重置Cursor应用程序使用的所有机器ID相关标识符，
    包括本地存储的ID、SQLite数据库中的ID和系统级的ID。
    支持Windows、macOS和Linux系统，并自动处理不同平台的路径差异。
    """
    def __init__(self, translator=None):
        """
        初始化机器ID重置器
        
        根据操作系统自动配置各种文件路径和数据库位置，
        支持从配置文件读取和保存设置。
        
        参数:
            translator: 翻译器对象，用于多语言支持，可以为None
            
        异常:
            FileNotFoundError: 当找不到配置文件时抛出
            EnvironmentError: 当环境变量未设置时抛出
            NotImplementedError: 当不支持当前操作系统时抛出
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
        
        创建一组新的随机标识符，包括UUID、机器ID和遥测ID，
        并更新machineId文件。
        
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
        
        将新生成的ID写入Cursor应用程序的SQLite数据库，
        确保应用程序使用新的标识符。
        
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
        
        根据不同操作系统更新系统级别的机器标识符，
        包括Windows注册表中的MachineGuid和macOS平台UUID等。
        
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
        这个值常被应用程序用于识别设备。
        
        异常:
            PermissionError: 当没有足够权限访问注册表时抛出
            Exception: 更新失败时抛出
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
        这个值通常用于软件质量监测和遥测系统。
        
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
        
        在macOS系统中更新平台UUID，这个值常被应用程序用于
        识别macOS设备。对于普通用户，此方法通常不做任何操作。
        
        参数:
            new_ids (dict): 包含新ID的字典，键为ID名称，值为ID值
            
        注意:
            此方法在macOS系统上通常是无操作的，因为修改系统级UUID需要root权限
            并可能导致系统不稳定。
        """
        # This is a no-op for normal users as changing the platform UUID
        # requires root permissions and can destabilize macOS
        print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.macos_uuid_warning')}{Style.RESET_ALL}")
        pass

    def update_machine_id_file(self, new_id):
        """
        更新Cursor机器ID文件
        
        将新生成的ID写入Cursor应用程序的machineId文件，
        这是Cursor识别设备的主要方式。
        
        参数:
            new_id (str): 新生成的UUID字符串
            
        返回值:
            bool: 更新成功返回True，失败返回False
        """
        try:
            # Get the machineId file path
            machine_id_path = get_cursor_machine_id_path(self.translator)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(machine_id_path), exist_ok=True)
            
            # Write new ID to file
            with open(machine_id_path, 'w', encoding='utf-8') as f:
                f.write(new_id)
                
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.machine_id_updated')}: {machine_id_path}{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.update_machine_id_failed', error=str(e))}{Style.RESET_ALL}")
            return False
            
    def update_storage_json(self, new_ids):
        """
        更新storage.json文件中的机器ID
        
        修改Cursor应用程序的storage.json文件，更新里面的
        机器ID和相关标识符，使其使用新生成的值。
        
        参数:
            new_ids (dict): 包含新ID的字典，键为ID名称，值为ID值
            
        返回值:
            bool: 更新成功返回True，失败返回False
        """
        try:
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.updating_storage')}...{Style.RESET_ALL}")
            
            # Create storage.json backup
            if os.path.exists(self.db_path):
                backup_path = f"{self.db_path}.bak"
                shutil.copy2(self.db_path, backup_path)
                print(f"{Fore.GREEN}{EMOJI['BACKUP']} {self.translator.get('reset.storage_backup_created')}: {backup_path}{Style.RESET_ALL}")
                
                # Load existing JSON data
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                # Create new storage.json if it doesn't exist
                os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
                data = {}
                
            # Update telemetry IDs
            for key, value in new_ids.items():
                if key.startswith("telemetry."):
                    data[key] = value
                    print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.updating_pair')}: {key}{Style.RESET_ALL}")
            
            # Special handling for storage.serviceMachineId
            service_machine_id_key = "storage.serviceMachineId"
            if service_machine_id_key in new_ids:
                data[service_machine_id_key] = new_ids[service_machine_id_key]
                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.updating_pair')}: {service_machine_id_key}{Style.RESET_ALL}")
            
            # Write updated data back to file
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.storage_updated')}{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.storage_update_failed', error=str(e))}{Style.RESET_ALL}")
            return False
            
    def reset(self):
        """
        执行完整的机器ID重置流程
        
        生成新的ID，并更新所有相关文件和数据库：
        1. 生成新的UUID和机器ID
        2. 更新machineId文件
        3. 更新storage.json文件
        4. 更新SQLite数据库
        5. 更新系统级ID
        6. 修补Cursor代码
        
        返回值:
            bool: 重置流程完全成功返回True，任何步骤失败返回False
        """
        try:
            print(f"{Fore.CYAN}{EMOJI['RESET']} {self.translator.get('reset.starting_reset')}{Style.RESET_ALL}")
            
            # Generate new IDs
            new_ids = self.generate_new_ids()
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.ids_generated')}{Style.RESET_ALL}")
            
            # Update storage.json
            if not self.update_storage_json(new_ids):
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.storage_update_warning')}{Style.RESET_ALL}")
            
            # Update SQLite database if it exists
            if os.path.exists(self.sqlite_path):
                if not self.update_sqlite_db(new_ids):
                    print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.sqlite_update_warning')}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.sqlite_not_found')}: {self.sqlite_path}{Style.RESET_ALL}")
                
            # Update system-level IDs
            if not self.update_system_ids(new_ids):
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.system_ids_update_warning')}{Style.RESET_ALL}")
                
            # Patch Cursor code
            if not patch_cursor_get_machine_id(self.translator):
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('reset.patch_warning')}{Style.RESET_ALL}")
                
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.reset_complete')}{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.reset_failed', error=str(e))}{Style.RESET_ALL}")
            traceback.print_exc()
            return False

def run(translator=None):
    """
    运行机器ID重置程序
    
    加载配置，创建重置器实例并执行重置操作，
    作为独立模块或从main.py调用时的入口函数。
    
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
    resetter.reset()

    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    input(f"{EMOJI['INFO']} {translator.get('reset.press_enter')}...")

def main():
    """
    重置机器ID的主函数入口
    
    当脚本直接运行时调用，负责加载翻译器并调用run函数
    执行机器ID重置流程。处理基本的命令行参数并设置
    程序的国际化支持。
    
    无参数和返回值。
    """
    try:
        # Setup translator
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from utils import Translator
        translator = Translator()
        
        run(translator)
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}操作已被用户中断{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}发生错误: {str(e)}{Style.RESET_ALL}")
        traceback.print_exc()
        
if __name__ == "__main__":
    main()
