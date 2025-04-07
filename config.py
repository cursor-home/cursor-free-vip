"""
config.py - 配置管理模块

这个模块负责管理程序的配置信息，包括：
- 创建和读取配置文件
- 设置默认配置项
- 根据不同操作系统设置特定路径
- 提供配置读取和更新功能

配置文件存储在用户文档目录下的.cursor-free-vip/config.ini
"""
import os
import sys
import configparser
from colorama import Fore, Style
from utils import get_user_documents_path, get_default_chrome_path, get_linux_cursor_path
import shutil
import datetime

EMOJI = {
    "INFO": "ℹ️",
    "WARNING": "⚠️",
    "ERROR": "❌",
    "SUCCESS": "✅",
    "ADMIN": "🔒",
    "ARROW": "➡️",
    "USER": "👤",
    "KEY": "🔑",
    "SETTINGS": "⚙️"
}

def setup_config(translator=None):
    """
    设置和初始化配置文件，根据需要创建默认配置。
    
    这个函数会检查配置文件是否存在，如果不存在则创建并填充默认值。
    如果配置文件已存在，则会根据默认配置检查是否缺少配置项，并添加缺失的项。
    
    同时，函数会根据不同的操作系统(Windows/Mac/Linux)设置不同的路径配置。
    
    参数:
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        configparser.ConfigParser: 配置对象，如果出错则返回None
    """
    try:
        config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip")
        config_file = os.path.join(config_dir, "config.ini")
        os.makedirs(config_dir, exist_ok=True)
        
        config = configparser.ConfigParser()
        
        # Default configuration
        default_config = {
            'Chrome': {
                'chromepath': get_default_chrome_path()
            },
            'Turnstile': {
                'handle_turnstile_time': '2',
                'handle_turnstile_random_time': '1-3'
            },
            'Timing': {
                'min_random_time': '0.1',
                'max_random_time': '0.8',
                'page_load_wait': '0.1-0.8',
                'input_wait': '0.3-0.8',
                'submit_wait': '0.5-1.5',
                'verification_code_input': '0.1-0.3',
                'verification_success_wait': '2-3',
                'verification_retry_wait': '2-3',
                'email_check_initial_wait': '4-6',
                'email_refresh_wait': '2-4',
                'settings_page_load_wait': '1-2',
                'failed_retry_time': '0.5-1',
                'retry_interval': '8-12',
                'max_timeout': '160'
            },
            'Utils': {
                'enabled_update_check': 'True',
                'enabled_account_info': 'True'
            }
        }

        # Add system-specific path configuration
        if sys.platform == "win32":
            # Windows系统路径配置
            appdata = os.getenv("APPDATA")
            localappdata = os.getenv("LOCALAPPDATA", "")
            default_config['WindowsPaths'] = {
                'storage_path': os.path.join(appdata, "Cursor", "User", "globalStorage", "storage.json"),
                'sqlite_path': os.path.join(appdata, "Cursor", "User", "globalStorage", "state.vscdb"),
                'machine_id_path': os.path.join(appdata, "Cursor", "machineId"),
                'cursor_path': os.path.join(localappdata, "Programs", "Cursor", "resources", "app"),
                'updater_path': os.path.join(localappdata, "cursor-updater"),
                'update_yml_path': os.path.join(localappdata, "Programs", "Cursor", "resources", "app-update.yml"),
                'product_json_path': os.path.join(localappdata, "Programs", "Cursor", "resources", "app", "product.json")
            }
            # Create storage directory
            os.makedirs(os.path.dirname(default_config['WindowsPaths']['storage_path']), exist_ok=True)
            
        elif sys.platform == "darwin":
            # macOS系统路径配置
            default_config['MacPaths'] = {
                'storage_path': os.path.abspath(os.path.expanduser("~/Library/Application Support/Cursor/User/globalStorage/storage.json")),
                'sqlite_path': os.path.abspath(os.path.expanduser("~/Library/Application Support/Cursor/User/globalStorage/state.vscdb")),
                'machine_id_path': os.path.expanduser("~/Library/Application Support/Cursor/machineId"),
                'cursor_path': "/Applications/Cursor.app/Contents/Resources/app",
                'updater_path': os.path.expanduser("~/Library/Application Support/cursor-updater"),
                'update_yml_path': "/Applications/Cursor.app/Contents/Resources/app-update.yml",
                'product_json_path': "/Applications/Cursor.app/Contents/Resources/app/product.json"
            }
            # Create storage directory
            os.makedirs(os.path.dirname(default_config['MacPaths']['storage_path']), exist_ok=True)
            
        elif sys.platform == "linux":
            # Linux系统路径配置，需要更复杂的检查逻辑
            # Get the actual user's home directory, handling both sudo and normal cases
            sudo_user = os.environ.get('SUDO_USER')
            current_user = sudo_user if sudo_user else (os.getenv('USER') or os.getenv('USERNAME'))
            
            if not current_user:
                current_user = os.path.expanduser('~').split('/')[-1]
            
            # Handle sudo case
            if sudo_user:
                actual_home = f"/home/{sudo_user}"
                root_home = "/root"
            else:
                actual_home = f"/home/{current_user}"
                root_home = None
            
            if not os.path.exists(actual_home):
                actual_home = os.path.expanduser("~")
            
            # Define base config directory
            config_base = os.path.join(actual_home, ".config")
            
            # Try both "Cursor" and "cursor" directory names in both user and root locations
            cursor_dir = None
            possible_paths = [
                os.path.join(config_base, "Cursor"),
                os.path.join(config_base, "cursor"),
                os.path.join(root_home, ".config", "Cursor") if root_home else None,
                os.path.join(root_home, ".config", "cursor") if root_home else None
            ]
            
            for path in possible_paths:
                if path and os.path.exists(path):
                    cursor_dir = path
                    break
            
            if not cursor_dir:
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('config.neither_cursor_nor_cursor_directory_found', config_base=config_base) if translator else f'Neither Cursor nor cursor directory found in {config_base}'}{Style.RESET_ALL}")
                if root_home:
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('config.also_checked', path=f'{root_home}/.config') if translator else f'Also checked {root_home}/.config'}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('config.please_make_sure_cursor_is_installed_and_has_been_run_at_least_once') if translator else 'Please make sure Cursor is installed and has been run at least once'}{Style.RESET_ALL}")
            
            # Define Linux paths using the found cursor directory
            storage_path = os.path.abspath(os.path.join(cursor_dir, "User/globalStorage/storage.json")) if cursor_dir else ""
            storage_dir = os.path.dirname(storage_path) if storage_path else ""
            
            # Verify paths and permissions
            try:
                # Check storage directory
                if storage_dir and not os.path.exists(storage_dir):
                    print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('config.storage_directory_not_found', storage_dir=storage_dir) if translator else f'Storage directory not found: {storage_dir}'}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('config.please_make_sure_cursor_is_installed_and_has_been_run_at_least_once') if translator else 'Please make sure Cursor is installed and has been run at least once'}{Style.RESET_ALL}")
                
                # Check storage.json with more detailed verification
                if storage_path and os.path.exists(storage_path):
                    # Get file stats
                    try:
                        stat = os.stat(storage_path)
                        print(f"{Fore.GREEN}{EMOJI['INFO']} {translator.get('config.storage_file_found', storage_path=storage_path) if translator else f'Storage file found: {storage_path}'}{Style.RESET_ALL}")
                        print(f"{Fore.GREEN}{EMOJI['INFO']} {translator.get('config.file_size', size=stat.st_size) if translator else f'File size: {stat.st_size} bytes'}{Style.RESET_ALL}")
                        print(f"{Fore.GREEN}{EMOJI['INFO']} {translator.get('config.file_permissions', permissions=oct(stat.st_mode & 0o777)) if translator else f'File permissions: {oct(stat.st_mode & 0o777)}'}{Style.RESET_ALL}")
                        print(f"{Fore.GREEN}{EMOJI['INFO']} {translator.get('config.file_owner', owner=stat.st_uid) if translator else f'File owner: {stat.st_uid}'}{Style.RESET_ALL}")
                        print(f"{Fore.GREEN}{EMOJI['INFO']} {translator.get('config.file_group', group=stat.st_gid) if translator else f'File group: {stat.st_gid}'}{Style.RESET_ALL}")
                    except Exception as e:
                        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('config.error_getting_file_stats', error=str(e)) if translator else f'Error getting file stats: {str(e)}'}{Style.RESET_ALL}")
                    
                    # Check if file is readable and writable
                    if not os.access(storage_path, os.R_OK | os.W_OK):
                        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('config.permission_denied', storage_path=storage_path) if translator else f'Permission denied: {storage_path}'}{Style.RESET_ALL}")
                        if sudo_user:
                            print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('config.try_running', command=f'chown {sudo_user}:{sudo_user} {storage_path}') if translator else f'Try running: chown {sudo_user}:{sudo_user} {storage_path}'}{Style.RESET_ALL}")
                            print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('config.and') if translator else 'And'}: chmod 644 {storage_path}{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('config.try_running', command=f'chown {current_user}:{current_user} {storage_path}') if translator else f'Try running: chown {current_user}:{current_user} {storage_path}'}{Style.RESET_ALL}")
                            print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('config.and') if translator else 'And'}: chmod 644 {storage_path}{Style.RESET_ALL}")
                    
                    # Try to read the file to verify it's not corrupted
                    try:
                        with open(storage_path, 'r') as f:
                            content = f.read()
                            if not content.strip():
                                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('config.storage_file_is_empty', storage_path=storage_path) if translator else f'Storage file is empty: {storage_path}'}{Style.RESET_ALL}")
                                print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('config.the_file_might_be_corrupted_please_reinstall_cursor') if translator else 'The file might be corrupted, please reinstall Cursor'}{Style.RESET_ALL}")
                            else:
                                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('config.storage_file_is_valid_and_contains_data') if translator else 'Storage file is valid and contains data'}{Style.RESET_ALL}")
                    except Exception as e:
                        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('config.error_reading_storage_file', error=str(e)) if translator else f'Error reading storage file: {str(e)}'}{Style.RESET_ALL}")
                        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('config.the_file_might_be_corrupted_please_reinstall_cursor') if translator else 'The file might be corrupted. Please reinstall Cursor'}{Style.RESET_ALL}")
                elif storage_path:
                    print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('config.storage_file_not_found', storage_path=storage_path) if translator else f'Storage file not found: {storage_path}'}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('config.please_make_sure_cursor_is_installed_and_has_been_run_at_least_once') if translator else 'Please make sure Cursor is installed and has been run at least once'}{Style.RESET_ALL}")
                
            except (OSError, IOError) as e:
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('config.error_checking_linux_paths', error=str(e)) if translator else f'Error checking Linux paths: {str(e)}'}{Style.RESET_ALL}")
            
            # Define all paths using the found cursor directory
            default_config['LinuxPaths'] = {
                'storage_path': storage_path,
                'sqlite_path': os.path.abspath(os.path.join(cursor_dir, "User/globalStorage/state.vscdb")) if cursor_dir else "",
                'machine_id_path': os.path.join(cursor_dir, "machineid") if cursor_dir else "",
                'cursor_path': get_linux_cursor_path(),
                'updater_path': os.path.join(config_base, "cursor-updater"),
                'update_yml_path': os.path.join(cursor_dir, "resources/app-update.yml") if cursor_dir else "",
                'product_json_path': os.path.join(cursor_dir, "resources/app/product.json") if cursor_dir else ""
            }

        # Read existing configuration and merge
        if os.path.exists(config_file):
            config.read(config_file, encoding='utf-8')
            config_modified = False
            
            for section, options in default_config.items():
                if not config.has_section(section):
                    config.add_section(section)
                    config_modified = True
                for option, value in options.items():
                    if not config.has_option(section, option):
                        config.set(section, option, str(value))
                        config_modified = True
                        if translator:
                            print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('config.config_option_added', option=f'{section}.{option}') if translator else f'Config option added: {section}.{option}'}{Style.RESET_ALL}")

            if config_modified:
                with open(config_file, 'w', encoding='utf-8') as f:
                    config.write(f)
                if translator:
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('config.config_updated') if translator else 'Config updated'}{Style.RESET_ALL}")
        else:
            for section, options in default_config.items():
                config.add_section(section)
                for option, value in options.items():
                    config.set(section, option, str(value))

            with open(config_file, 'w', encoding='utf-8') as f:
                config.write(f)
            if translator:
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('config.config_created', config_file=config_file) if translator else f'Config created: {config_file}'}{Style.RESET_ALL}")

        return config

    except Exception as e:
        if translator:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('config.config_setup_error', error=str(e)) if translator else f'Error setting up config: {str(e)}'}{Style.RESET_ALL}")
        return None
    
def print_config(config, translator=None):
    """
    以可读格式打印配置信息
    
    将配置以分组和彩色方式打印出来，方便用户查看。
    对于布尔值配置项会显示为"已启用"或"已禁用"并使用不同颜色。
    
    参数:
        config: 配置对象
        translator: 翻译器对象，用于多语言支持，可以为None
    """
    if not config:
        print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('config.config_not_available') if translator else 'Configuration not available'}{Style.RESET_ALL}")
        return
        
    print(f"\n{Fore.CYAN}{EMOJI['INFO']} {translator.get('config.configuration') if translator else 'Configuration'}:{Style.RESET_ALL}")
    print(f"\n{Fore.CYAN}{'─' * 70}{Style.RESET_ALL}")
    for section in config.sections():
        print(f"{Fore.GREEN}[{section}]{Style.RESET_ALL}")
        for key, value in config.items(section):
            # 对布尔值进行特殊处理，使其显示为彩色
            if value.lower() in ('true', 'yes', 'on', '1'):
                value_display = f"{Fore.GREEN}{translator.get('config.enabled') if translator else 'Enabled'}{Style.RESET_ALL}"
            elif value.lower() in ('false', 'no', 'off', '0'):
                value_display = f"{Fore.RED}{translator.get('config.disabled') if translator else 'Disabled'}{Style.RESET_ALL}"
            else:
                value_display = value
                
            print(f"  {key} = {value_display}")
    
    print(f"\n{Fore.CYAN}{'─' * 70}{Style.RESET_ALL}")
    config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip", "config.ini")
    print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('config.config_directory') if translator else 'Config Directory'}: {config_dir}{Style.RESET_ALL}")

    print()  

def force_update_config(translator=None):
    """
    强制更新配置文件
    
    创建配置文件的备份，然后重新初始化配置。
    在需要重置配置或修复损坏的配置文件时使用。
    
    参数:
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        configparser.ConfigParser: 更新后的配置对象，如果出错则返回None
    """
    try:
        config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip")
        config_file = os.path.join(config_dir, "config.ini")
        current_time = datetime.datetime.now()
        
        if os.path.exists(config_file):
            try:
                # create backup
                backup_file = f"{config_file}.bak.{current_time.strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(config_file, backup_file)
                if translator:
                    print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('config.backup_created', path=backup_file) if translator else f'Backup created: {backup_file}'}{Style.RESET_ALL}")
                
                # delete original file
                os.remove(config_file)
                if translator:
                    print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('config.config_removed') if translator else 'Config file removed for forced update'}{Style.RESET_ALL}")
            except Exception as e:
                if translator:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('config.backup_failed', error=str(e)) if translator else f'Failed to backup config: {str(e)}'}{Style.RESET_ALL}")
        
        # use existing setup_config function to create new config
        return setup_config(translator)
    
    except Exception as e:
        if translator:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('config.force_update_failed', error=str(e)) if translator else f'Force update config failed: {str(e)}'}{Style.RESET_ALL}")
        return None

def get_config(translator=None):
    """
    获取配置对象
    
    从配置文件中读取配置，如果配置文件不存在则创建默认配置。
    这是程序中获取配置的主要接口。
    
    参数:
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        configparser.ConfigParser: 配置对象，如果出错则返回None
    """
    return setup_config(translator) 