"""
bypass_version.py - Cursor版本绕过模块

这个模块负责修改Cursor的产品信息文件，以绕过版本检查，主要功能包括：
- 查找并修改product.json文件
- 备份原始文件以防止问题
- 将版本号更新为兼容的高版本
- 支持多平台(Windows/macOS/Linux)

通过修改版本信息，可以防止Cursor强制更新，保持当前可用的破解状态。
"""
import os
import json
import shutil
import platform
import configparser
import time
from colorama import Fore, Style, init
import sys
import traceback
from utils import get_user_documents_path

# Initialize colorama
init()

# Define emoji constants
EMOJI = {
    'INFO': 'ℹ️',
    'SUCCESS': '✅',
    'ERROR': '❌',
    'WARNING': '⚠️',
    'FILE': '📄',
    'BACKUP': '💾',
    'RESET': '🔄',
    'VERSION': '🏷️'
}

def get_product_json_path(translator=None):
    """
    获取Cursor的product.json文件路径。
    
    根据不同操作系统查找product.json文件的位置。
    优先从配置文件读取路径，如果配置不存在，则使用默认路径。
    
    参数:
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        str: product.json文件的完整路径
        
    异常:
        OSError: 如果找不到文件或系统不支持
    """
    system = platform.system()
    
    # Read configuration
    config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip")
    config_file = os.path.join(config_dir, "config.ini")
    config = configparser.ConfigParser()
    
    if os.path.exists(config_file):
        config.read(config_file)
    
    if system == "Windows":
        localappdata = os.environ.get("LOCALAPPDATA")
        if not localappdata:
            raise OSError(translator.get('bypass.localappdata_not_found') if translator else "LOCALAPPDATA environment variable not found")
        
        product_json_path = os.path.join(localappdata, "Programs", "Cursor", "resources", "app", "product.json")
        
        # Check if path exists in config
        if 'WindowsPaths' in config and 'cursor_path' in config['WindowsPaths']:
            cursor_path = config.get('WindowsPaths', 'cursor_path')
            product_json_path = os.path.join(cursor_path, "product.json")
    
    elif system == "Darwin":  # macOS
        product_json_path = "/Applications/Cursor.app/Contents/Resources/app/product.json"
    
    elif system == "Linux":
        # Try multiple common paths
        possible_paths = [
            "/opt/Cursor/resources/app/product.json",
            "/usr/share/cursor/resources/app/product.json",
            "/usr/lib/cursor/app/product.json"
        ]
        
        # Add extracted AppImage paths
        extracted_usr_paths = os.path.expanduser("~/squashfs-root/usr/share/cursor/resources/app/product.json")
        if os.path.exists(extracted_usr_paths):
            possible_paths.append(extracted_usr_paths)
        
        for path in possible_paths:
            if os.path.exists(path):
                product_json_path = path
                break
        else:
            raise OSError(translator.get('bypass.product_json_not_found') if translator else "product.json not found in common Linux paths")
    
    else:
        raise OSError(translator.get('bypass.unsupported_os', system=system) if translator else f"Unsupported operating system: {system}")
    
    if not os.path.exists(product_json_path):
        raise OSError(translator.get('bypass.file_not_found', path=product_json_path) if translator else f"File not found: {product_json_path}")
    
    return product_json_path

def compare_versions(version1, version2):
    """
    比较两个版本号字符串。
    
    解析版本号字符串（如"1.2.3"）并进行数值比较，
    支持不同长度的版本号字符串比较。
    
    参数:
        version1 (str): 第一个版本号
        version2 (str): 第二个版本号
        
    返回值:
        int: 如果version1 < version2返回-1，
             如果version1 > version2返回1，
             如果相等返回0
    """
    v1_parts = [int(x) for x in version1.split('.')]
    v2_parts = [int(x) for x in version2.split('.')]
    
    for i in range(max(len(v1_parts), len(v2_parts))):
        v1 = v1_parts[i] if i < len(v1_parts) else 0
        v2 = v2_parts[i] if i < len(v2_parts) else 0
        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
    
    return 0

def bypass_version(translator=None):
    """
    通过修改product.json绕过Cursor版本检查。
    
    查找并修改Cursor的产品信息文件，将版本号更新为兼容的高版本，
    以防止Cursor强制更新，保持当前可用的破解状态。
    
    流程:
    1. 找到product.json文件
    2. 检查当前版本
    3. 如果版本低于0.46.0，则更新到0.48.7
    4. 在修改前创建备份文件
    
    参数:
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        bool: 操作成功返回True，失败返回False
    """
    try:
        print(f"\n{Fore.CYAN}{EMOJI['INFO']} {translator.get('bypass.starting') if translator else 'Starting Cursor version bypass...'}{Style.RESET_ALL}")
        
        # Get product.json path
        product_json_path = get_product_json_path(translator)
        print(f"{Fore.CYAN}{EMOJI['FILE']} {translator.get('bypass.found_product_json', path=product_json_path) if translator else f'Found product.json: {product_json_path}'}{Style.RESET_ALL}")
        
        # Check file permissions
        if not os.access(product_json_path, os.W_OK):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('bypass.no_write_permission', path=product_json_path) if translator else f'No write permission for file: {product_json_path}'}{Style.RESET_ALL}")
            return False
        
        # Read product.json
        try:
            with open(product_json_path, "r", encoding="utf-8") as f:
                product_data = json.load(f)
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('bypass.read_failed', error=str(e)) if translator else f'Failed to read product.json: {str(e)}'}{Style.RESET_ALL}")
            return False
        
        # Get current version
        current_version = product_data.get("version", "0.0.0")
        print(f"{Fore.CYAN}{EMOJI['VERSION']} {translator.get('bypass.current_version', version=current_version) if translator else f'Current version: {current_version}'}{Style.RESET_ALL}")
        
        # Check if version needs to be modified
        if compare_versions(current_version, "0.46.0") < 0:
            # Create backup
            timestamp = time.strftime("%Y%m%d%H%M%S")
            backup_path = f"{product_json_path}.{timestamp}"
            shutil.copy2(product_json_path, backup_path)
            print(f"{Fore.GREEN}{EMOJI['BACKUP']} {translator.get('bypass.backup_created', path=backup_path) if translator else f'Backup created: {backup_path}'}{Style.RESET_ALL}")
            
            # Modify version
            new_version = "0.48.7"
            product_data["version"] = new_version
            
            # Save modified product.json
            try:
                with open(product_json_path, "w", encoding="utf-8") as f:
                    json.dump(product_data, f, indent=2)
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('bypass.version_updated', old=current_version, new=new_version) if translator else f'Version updated from {current_version} to {new_version}'}{Style.RESET_ALL}")
                return True
            except Exception as e:
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('bypass.write_failed', error=str(e)) if translator else f'Failed to write product.json: {str(e)}'}{Style.RESET_ALL}")
                return False
        else:
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('bypass.no_update_needed', version=current_version) if translator else f'No update needed. Current version {current_version} is already >= 0.46.0'}{Style.RESET_ALL}")
            return True
    
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('bypass.bypass_failed', error=str(e)) if translator else f'Version bypass failed: {str(e)}'}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('bypass.stack_trace') if translator else 'Stack trace'}: {traceback.format_exc()}{Style.RESET_ALL}")
        return False

def main(translator=None):
    """
    主函数
    
    调用bypass_version函数并返回结果。
    
    参数:
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        bool: 操作成功返回True，失败返回False
    """
    return bypass_version(translator)

if __name__ == "__main__":
    main() 