"""
main.py - Cursor Free VIP 工具主程序

这是Cursor Free VIP工具的主入口程序，允许用户选择运行各种功能脚本。
主要功能包括：
- 提供多语言支持的交互式菜单
- 根据用户选择执行不同的功能脚本
- 检查更新和版本信息
- 提供语言切换功能

使用方法：直接运行此脚本，然后从菜单中选择所需功能

作者: CC11001100
版本: 见下方version变量
"""
# main.py
# This script allows the user to choose which script to run.
import os
import sys
import json
from logo import print_logo, version
from colorama import Fore, Style, init
import locale
import platform
import requests
import subprocess
from config import get_config, force_update_config
import shutil
import re

# Only import windll on Windows systems
if platform.system() == 'Windows':
    import ctypes
    # Only import windll on Windows systems
    from ctypes import windll

# Initialize colorama
init()

# Define emoji and color constants
EMOJI = {
    "FILE": "📄",
    "BACKUP": "💾",
    "SUCCESS": "✅",
    "ERROR": "❌",
    "INFO": "ℹ️",
    "RESET": "🔄",
    "MENU": "📋",
    "ARROW": "➜",
    "LANG": "🌐",
    "UPDATE": "🔄",
    "ADMIN": "🔐",
    "AIRDROP": "💰",
    "ROCKET": "🚀",
    "STAR": "⭐",
    "SUN": "🌟",
    "CONTRIBUTE": "🤝",
    "SETTINGS": "⚙️"
}

# Function to check if running as frozen executable
def is_frozen():
    """
    检查脚本是否作为冻结的可执行文件运行。
    
    冻结的可执行文件是指通过PyInstaller或类似工具打包后的独立可执行程序。
    
    返回值:
        bool: 如果是冻结的可执行文件返回True，否则返回False
    """
    return getattr(sys, 'frozen', False)

# Function to check admin privileges (Windows only)
def is_admin():
    """
    检查脚本是否以管理员权限运行（仅适用于Windows系统）。
    
    对于非Windows系统，总是返回True以避免改变行为。
    
    返回值:
        bool: 如果以管理员权限运行返回True，否则返回False
    """
    if platform.system() == 'Windows':
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    # Always return True for non-Windows to avoid changing behavior
    return True

# Function to restart with admin privileges
def run_as_admin():
    """
    以管理员权限重启当前脚本（仅适用于Windows系统）。
    
    通过Windows的ShellExecute API请求提升权限，重新启动当前程序。
    
    返回值:
        bool: 如果重启成功返回True，否则返回False
    """
    if platform.system() != 'Windows':
        return False
        
    try:
        args = [sys.executable] + sys.argv
        
        # Request elevation via ShellExecute
        print(f"{Fore.YELLOW}{EMOJI['ADMIN']} Requesting administrator privileges...{Style.RESET_ALL}")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", args[0], " ".join('"' + arg + '"' for arg in args[1:]), None, 1)
        return True
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} Failed to restart with admin privileges: {e}{Style.RESET_ALL}")
        return False

class Translator:
    """
    翻译器类，负责管理和提供多语言支持。
    
    特点:
    - 自动检测系统语言
    - 加载可用的翻译文件
    - 支持在不同语言之间切换
    - 提供回退机制，当翻译缺失时使用默认语言（英语）
    """
    def __init__(self):
        """
        初始化翻译器。
        
        设置当前语言为系统检测语言，并加载所有可用的翻译文件。
        """
        self.translations = {}
        self.current_language = self.detect_system_language()  # Use correct method name
        self.fallback_language = 'en'  # Fallback language if translation is missing
        self.load_translations()
    
    def detect_system_language(self):
        """
        检测系统语言并返回相应的语言代码。
        
        会根据不同操作系统调用相应的检测方法。
        
        返回值:
            str: 检测到的语言代码，如'en', 'zh_cn'等。如果检测失败，默认返回'en'
        """
        try:
            system = platform.system()
            
            if system == 'Windows':
                return self._detect_windows_language()
            else:
                return self._detect_unix_language()
                
        except Exception as e:
            print(f"{Fore.YELLOW}{EMOJI['INFO']} Failed to detect system language: {e}{Style.RESET_ALL}")
            return 'en'
    
    def _detect_windows_language(self):
        """
        检测Windows系统的语言。
        
        通过获取键盘布局ID来识别当前系统语言。
        
        返回值:
            str: 检测到的语言代码
        """
        try:
            # Ensure we are on Windows
            if platform.system() != 'Windows':
                return 'en'
                
            # Get keyboard layout
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            threadid = user32.GetWindowThreadProcessId(hwnd, 0)
            layout_id = user32.GetKeyboardLayout(threadid) & 0xFFFF
            
            # Map language ID to our language codes
            language_map = {
                0x0409: 'en',      # English
                0x0404: 'zh_tw',   # Traditional Chinese
                0x0804: 'zh_cn',   # Simplified Chinese
                0x0422: 'vi',      # Vietnamese
                0x0419: 'ru',      # Russian
                0x0415: 'tr',      # Turkish
                0x0402: 'bg',      # Bulgarian
            }
            
            return language_map.get(layout_id, 'en')
        except:
            return self._detect_unix_language()
    
    def _detect_unix_language(self):
        """
        检测Unix系统（Linux、macOS）的语言设置
        
        通过获取系统本地化设置来识别当前系统语言，
        并将其映射到我们支持的语言代码。
        
        返回值:
            str: 检测到的语言代码，如'en', 'zh_cn'等。如果检测失败或不支持，返回'en'
        """
        try:
            # Get the system locale
            system_locale = locale.getdefaultlocale()[0]
            if not system_locale:
                return 'en'
            
            system_locale = system_locale.lower()
            
            # Map the locale to our language codes
            if system_locale.startswith('zh_cn') or system_locale.startswith('zh_hans'):
                return 'zh_cn'
            elif system_locale.startswith('zh_tw') or system_locale.startswith('zh_hant'):
                return 'zh_tw'
            elif system_locale.startswith('vi'):
                return 'vi'
            elif system_locale.startswith('ru'):
                return 'ru'
            elif system_locale.startswith('tr'):
                return 'tr'
            elif system_locale.startswith('bg'):
                return 'bg'
            else:
                return 'en'
        except Exception as e:
            print(f"{Fore.YELLOW}{EMOJI['INFO']} Failed to detect Unix language: {e}{Style.RESET_ALL}")
            return 'en'
    
    def load_translations(self):
        """
        加载所有可用的翻译文件
        
        从本地translations目录中读取所有翻译JSON文件，并将它们加载到
        翻译器的内存中。支持从常规脚本执行和打包后的可执行文件两种方式加载翻译。
        
        如果找不到翻译文件，将使用默认的英语翻译。
        """
        # Find the translations directory
        if is_frozen():
            # For PyInstaller
            base_dir = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
            translations_dir = os.path.join(base_dir, 'locales')
        else:
            # For regular script execution
            script_dir = os.path.dirname(os.path.abspath(__file__))
            translations_dir = os.path.join(script_dir, 'locales')
        
        if not os.path.exists(translations_dir):
            print(f"{Fore.YELLOW}{EMOJI['INFO']} Translations directory not found. Using default English.{Style.RESET_ALL}")
            return
            
        # Load all translation files
        for filename in os.listdir(translations_dir):
            if filename.endswith('.json'):
                language_code = filename.split('.')[0]
                with open(os.path.join(translations_dir, filename), 'r', encoding='utf-8') as f:
                    try:
                        self.translations[language_code] = json.load(f)
                    except json.JSONDecodeError:
                        print(f"{Fore.RED}{EMOJI['ERROR']} Failed to parse translation file: {filename}{Style.RESET_ALL}")
                        continue
    
    def get(self, key, **kwargs):
        """
        获取指定键名的翻译文本
        
        根据当前设置的语言获取对应的翻译文本，如果当前语言中找不到该键，
        则尝试从默认语言（英语）中获取。支持通过关键字参数进行变量替换。
        
        参数:
            key (str): 要获取翻译的键名
            **kwargs: 用于替换翻译文本中的变量的关键字参数
            
        返回值:
            str: 翻译后的文本。如果找不到翻译，则返回键名本身
        """
        # Get translation for current language
        translation = self._get_translation(self.current_language, key)
        
        # If not found in current language, try fallback language
        if translation is None and self.current_language != self.fallback_language:
            translation = self._get_translation(self.fallback_language, key)
            
        # If still not found, use the key as fallback
        if translation is None:
            translation = key
            
        # Replace variables in the translation
        if kwargs:
            try:
                translation = translation.format(**kwargs)
            except KeyError as e:
                print(f"{Fore.YELLOW}{EMOJI['INFO']} Missing placeholder in translation: {e}{Style.RESET_ALL}")
                
        return translation
    
    def _get_translation(self, lang_code, key):
        """
        从指定语言中获取指定键名的翻译
        
        这是一个内部方法，用于实际查找翻译文本。支持使用点号分隔的嵌套键，
        如'menu.file.open'将会在翻译对象中查找menu->file->open这个嵌套路径。
        
        参数:
            lang_code (str): 语言代码，如'en', 'zh_cn'等
            key (str): 要获取翻译的键名，可以是点号分隔的嵌套键
            
        返回值:
            str或None: 找到的翻译文本，如果未找到则返回None
        """
        # Check if language exists
        if lang_code not in self.translations:
            return None
            
        # Split the key by dots for nested access
        parts = key.split('.')
        
        # Navigate through the nested dictionary
        translation = self.translations[lang_code]
        for part in parts:
            if isinstance(translation, dict) and part in translation:
                translation = translation[part]
            else:
                return None
                
        # Ensure we have a string
        if not isinstance(translation, str):
            return None
            
        return translation
    
    def set_language(self, lang_code):
        """
        设置当前使用的语言
        
        根据提供的语言代码，切换当前翻译器使用的语言。
        如果提供的语言代码不可用，将保持当前语言不变。
        
        参数:
            lang_code (str): 语言代码，如'en', 'zh_cn'等
            
        返回值:
            bool: 切换成功返回True，失败返回False
        """
        # Validate the language code
        if lang_code in self.translations:
            self.current_language = lang_code
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} Language set to: {lang_code}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}{EMOJI['ERROR']} Language '{lang_code}' not available.{Style.RESET_ALL}")
            return False
            
    def get_available_languages(self):
        """
        获取所有可用的语言列表
        
        返回所有已加载翻译文件的语言代码列表，
        这些语言可以通过set_language方法来设置使用。
        
        返回值:
            list: 可用语言代码的列表，如['en', 'zh_cn', 'zh_tw']
        """
        return list(self.translations.keys())

# Create translator instance
translator = Translator()

def print_menu():
    """
    打印主菜单界面。
    
    显示所有可用的功能选项，包括：
    - Cursor注册与登录
    - 版本检查与更新
    - 语言设置
    - 系统重置
    等功能。
    
    菜单会根据当前设置的语言显示对应的文本。
    """
    try:
        config = get_config()
        if config.getboolean('Utils', 'enabled_account_info'):
            import cursor_acc_info
            cursor_acc_info.display_account_info(translator)
    except Exception as e:
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('menu.account_info_error', error=str(e))}{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}{EMOJI['MENU']} {translator.get('menu.title')}:{Style.RESET_ALL}")
    if translator.current_language == 'zh_cn' or translator.current_language == 'zh_tw':
        print(f"{Fore.YELLOW}{'─' * 70}{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}{'─' * 110}{Style.RESET_ALL}")
    
    # Get terminal width
    try:
        terminal_width = shutil.get_terminal_size().columns
    except:
        terminal_width = 80  # Default width
    
    # Define all menu items
    menu_items = {
        0: f"{Fore.GREEN}0{Style.RESET_ALL}. {EMOJI['ERROR']} {translator.get('menu.exit')}",
        1: f"{Fore.GREEN}1{Style.RESET_ALL}. {EMOJI['RESET']} {translator.get('menu.reset')}",
        2: f"{Fore.GREEN}2{Style.RESET_ALL}. {EMOJI['SUCCESS']} {translator.get('menu.register')} ({Fore.RED}{translator.get('menu.outdate')}{Style.RESET_ALL})",
        3: f"{Fore.GREEN}3{Style.RESET_ALL}. {EMOJI['SUN']} {translator.get('menu.register_google')} {EMOJI['ROCKET']} ({Fore.YELLOW}{translator.get('menu.lifetime_access_enabled')}{Style.RESET_ALL})",
        4: f"{Fore.GREEN}4{Style.RESET_ALL}. {EMOJI['STAR']} {translator.get('menu.register_github')} {EMOJI['ROCKET']} ({Fore.YELLOW}{translator.get('menu.lifetime_access_enabled')}{Style.RESET_ALL})",
        5: f"{Fore.GREEN}5{Style.RESET_ALL}. {EMOJI['SUCCESS']} {translator.get('menu.register_manual')}",
        6: f"{Fore.GREEN}6{Style.RESET_ALL}. {EMOJI['RESET']} {translator.get('menu.temp_github_register')}",
        7: f"{Fore.GREEN}7{Style.RESET_ALL}. {EMOJI['ERROR']} {translator.get('menu.quit')}",
        8: f"{Fore.GREEN}8{Style.RESET_ALL}. {EMOJI['LANG']} {translator.get('menu.select_language')}",
        9: f"{Fore.GREEN}9{Style.RESET_ALL}. {EMOJI['UPDATE']} {translator.get('menu.disable_auto_update')}",
        10: f"{Fore.GREEN}10{Style.RESET_ALL}. {EMOJI['RESET']} {translator.get('menu.totally_reset')}",
        11: f"{Fore.GREEN}11{Style.RESET_ALL}. {EMOJI['CONTRIBUTE']} {translator.get('menu.contribute')}",
        12: f"{Fore.GREEN}12{Style.RESET_ALL}. {EMOJI['SETTINGS']}  {translator.get('menu.config')}",
        13: f"{Fore.GREEN}13{Style.RESET_ALL}. {EMOJI['SETTINGS']}  {translator.get('menu.select_chrome_profile')}",
        14: f"{Fore.GREEN}14{Style.RESET_ALL}. {EMOJI['ERROR']}  {translator.get('menu.delete_google_account', fallback='Delete Cursor Google Account')}",
        15: f"{Fore.GREEN}15{Style.RESET_ALL}. {EMOJI['UPDATE']}  {translator.get('menu.bypass_version_check', fallback='Bypass Cursor Version Check')}"
    }
    
    # Automatically calculate the number of menu items in the left and right columns
    total_items = len(menu_items)
    left_column_count = (total_items + 1) // 2  # The number of options displayed on the left (rounded up)
    
    # Build left and right columns of menus
    sorted_indices = sorted(menu_items.keys())
    left_menu = [menu_items[i] for i in sorted_indices[:left_column_count]]
    right_menu = [menu_items[i] for i in sorted_indices[left_column_count:]]
    
    # Calculate the maximum display width of left menu items
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    
    def get_display_width(s):
        """
        计算字符串的显示宽度
        
        考虑到中文字符和表情符号在终端中占用的宽度，准确计算字符串
        在终端中的实际显示宽度。中文字符和一些特殊符号通常占用两个
        字符位置，而ASCII字符只占一个位置。
        
        参数:
            s (str): 要计算宽度的字符串，可以包含ANSI颜色代码
            
        返回值:
            int: 字符串在终端中的显示宽度（不包括ANSI颜色代码）
        """
        # Remove ANSI color codes
        clean_s = ansi_escape.sub('', s)
        width = 0
        for c in clean_s:
            # Chinese characters and some emojis occupy two character widths
            if ord(c) > 127:
                width += 2
            else:
                width += 1
        return width
    
    max_left_width = 0
    for item in left_menu:
        width = get_display_width(item)
        max_left_width = max(max_left_width, width)
    
    # Set the starting position of right menu
    fixed_spacing = 4  # Fixed spacing
    right_start = max_left_width + fixed_spacing
    
    # Calculate the number of spaces needed for right menu items
    spaces_list = []
    for i in range(len(left_menu)):
        if i < len(left_menu):
            left_item = left_menu[i]
            left_width = get_display_width(left_item)
            spaces = right_start - left_width
            spaces_list.append(spaces)
    
    # Print menu items
    max_rows = max(len(left_menu), len(right_menu))
    
    for i in range(max_rows):
        # Print left menu items
        if i < len(left_menu):
            left_item = left_menu[i]
            print(left_item, end='')
            
            # Use pre-calculated spaces
            spaces = spaces_list[i]
        else:
            # If left side has no items, print only spaces
            spaces = right_start
            print('', end='')
        
        # Print right menu items
        if i < len(right_menu):
            print(' ' * spaces + right_menu[i])
        else:
            print()  # Change line
    if translator.current_language == 'zh_cn' or translator.current_language == 'zh_tw':
        print(f"{Fore.YELLOW}{'─' * 70}{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}{'─' * 110}{Style.RESET_ALL}")

def select_language():
    """
    语言选择功能。
    
    显示所有可用的语言选项，并让用户选择设置新的界面语言。
    设置成功后会保存到配置文件中。
    
    返回值:
        bool: 如果语言设置成功返回True，否则返回False
    """
    print(f"\n{Fore.CYAN}{EMOJI['LANG']} {translator.get('menu.select_language')}:{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'─' * 40}{Style.RESET_ALL}")
    
    languages = translator.get_available_languages()
    for i, lang in enumerate(languages):
        lang_name = translator.get(f"languages.{lang}")
        print(f"{Fore.GREEN}{i}{Style.RESET_ALL}. {lang_name}")
    
    try:
        choice = input(f"\n{EMOJI['ARROW']} {Fore.CYAN}{translator.get('menu.input_choice', choices=f'0-{len(languages)-1}')}: {Style.RESET_ALL}")
        if choice.isdigit() and 0 <= int(choice) < len(languages):
            translator.set_language(languages[int(choice)])
            return True
        else:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.invalid_choice')}{Style.RESET_ALL}")
            return False
    except (ValueError, IndexError):
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.invalid_choice')}{Style.RESET_ALL}")
        return False

def check_latest_version():
    """
    检查程序最新版本
    
    从GitHub仓库获取最新版本信息，与当前版本比较。
    如果有新版本可用，会提示用户升级并提供下载链接。
    处理了网络请求超时、GitHub API限制等异常情况。
    
    功能:
    - 获取GitHub仓库中的最新发布版本
    - 解析版本号并与当前版本比较
    - 提供下载链接和更新说明
    - 处理各种可能的错误情况
    
    返回值:
        bool: 如果检查成功返回True，否则返回False
    """
    try:
        print(f"\n{Fore.CYAN}{EMOJI['UPDATE']} {translator.get('updater.checking')}{Style.RESET_ALL}")
        
        # Get latest version from GitHub API with timeout and proper headers
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'CursorFreeVIP-Updater'
        }
        response = requests.get(
            "https://api.github.com/repos/yeongpin/cursor-free-vip/releases/latest",
            headers=headers,
            timeout=10
        )
        
        # Check if rate limit exceeded
        if response.status_code == 403 and "rate limit exceeded" in response.text.lower():
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('updater.rate_limit_exceeded', fallback='GitHub API rate limit exceeded. Skipping update check.')}{Style.RESET_ALL}")
            return
        
        # Check if response is successful
        if response.status_code != 200:
            raise Exception(f"GitHub API returned status code {response.status_code}")
            
        response_data = response.json()
        if "tag_name" not in response_data:
            raise Exception("No version tag found in GitHub response")
            
        latest_version = response_data["tag_name"].lstrip('v')
        
        # Validate version format
        if not latest_version:
            raise Exception("Invalid version format received")
        
        # Parse versions for proper comparison
        def parse_version(version_str):
            """
            解析版本号字符串为数字元组
            
            将形如"1.2.3"的版本号字符串转换为(1, 2, 3)的数字元组，
            便于进行版本号的大小比较。如果解析失败，则返回原始字符串。
            
            参数:
                version_str (str): 版本号字符串，如"1.0.0"
                
            返回值:
                tuple或str: 成功时返回包含版本号各部分的数字元组，如(1, 0, 0)；
                          失败时返回原始字符串
            """
            try:
                return tuple(map(int, version_str.split('.')))
            except ValueError:
                # Fallback to string comparison if parsing fails
                return version_str
                
        current_version_tuple = parse_version(version)
        latest_version_tuple = parse_version(latest_version)
        
        # Compare versions properly
        is_newer_version_available = False
        if isinstance(current_version_tuple, tuple) and isinstance(latest_version_tuple, tuple):
            is_newer_version_available = current_version_tuple < latest_version_tuple
        else:
            # Fallback to string comparison
            is_newer_version_available = version != latest_version
        
        if is_newer_version_available:
            print(f"\n{Fore.YELLOW}{EMOJI['INFO']} {translator.get('updater.new_version_available', current=version, latest=latest_version)}{Style.RESET_ALL}")
            
            # get and show changelog
            try:
                changelog_url = "https://raw.githubusercontent.com/yeongpin/cursor-free-vip/main/CHANGELOG.md"
                changelog_response = requests.get(changelog_url, timeout=10)
                
                if changelog_response.status_code == 200:
                    changelog_content = changelog_response.text
                    
                    # get latest version changelog
                    latest_version_pattern = f"## v{latest_version}"
                    changelog_sections = changelog_content.split("## v")
                    
                    latest_changes = None
                    for section in changelog_sections:
                        if section.startswith(latest_version):
                            latest_changes = section
                            break
                    
                    if latest_changes:
                        print(f"\n{Fore.CYAN}{'─' * 40}{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}{translator.get('updater.changelog_title')}:{Style.RESET_ALL}")
                        
                        # show changelog content (max 10 lines)
                        changes_lines = latest_changes.strip().split('\n')
                        for i, line in enumerate(changes_lines[1:11]):  # skip version number line, max 10 lines
                            if line.strip():
                                print(f"{Fore.WHITE}{line.strip()}{Style.RESET_ALL}")
                        
                        # if changelog more than 10 lines, show ellipsis
                        if len(changes_lines) > 11:
                            print(f"{Fore.WHITE}...{Style.RESET_ALL}")
                        
                        print(f"{Fore.CYAN}{'─' * 40}{Style.RESET_ALL}")
            except Exception as changelog_error:
                # get changelog failed
                pass
            
            # Ask user if they want to update
            while True:
                choice = input(f"\n{EMOJI['ARROW']} {Fore.CYAN}{translator.get('updater.update_confirm', choices='Y/n')}: {Style.RESET_ALL}").lower()
                if choice in ['', 'y', 'yes']:
                    break
                elif choice in ['n', 'no']:
                    print(f"\n{Fore.YELLOW}{EMOJI['INFO']} {translator.get('updater.update_skipped')}{Style.RESET_ALL}")
                    return
                else:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.invalid_choice')}{Style.RESET_ALL}")
            
            try:
                # Execute update command based on platform
                if platform.system() == 'Windows':
                    update_command = 'irm https://raw.githubusercontent.com/yeongpin/cursor-free-vip/main/scripts/install.ps1 | iex'
                    subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', update_command], check=True)
                else:
                    # For Linux/Mac, download and execute the install script
                    install_script_url = 'https://raw.githubusercontent.com/yeongpin/cursor-free-vip/main/scripts/install.sh'
                    
                    # First verify the script exists
                    script_response = requests.get(install_script_url, timeout=5)
                    if script_response.status_code != 200:
                        raise Exception("Installation script not found")
                        
                    # Save and execute the script
                    with open('install.sh', 'wb') as f:
                        f.write(script_response.content)
                    
                    os.chmod('install.sh', 0o755)  # Make executable
                    subprocess.run(['./install.sh'], check=True)
                    
                    # Clean up
                    if os.path.exists('install.sh'):
                        os.remove('install.sh')
                
                print(f"\n{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('updater.updating')}{Style.RESET_ALL}")
                sys.exit(0)
                
            except Exception as update_error:
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('updater.update_failed', error=str(update_error))}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('updater.manual_update_required')}{Style.RESET_ALL}")
                return
        else:
            # If current version is newer or equal to latest version
            if current_version_tuple > latest_version_tuple:
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('updater.development_version', current=version, latest=latest_version)}{Style.RESET_ALL}")
            else:
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('updater.up_to_date')}{Style.RESET_ALL}")
            
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('updater.network_error', error=str(e))}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('updater.continue_anyway')}{Style.RESET_ALL}")
        return
        
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('updater.check_failed', error=str(e))}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('updater.continue_anyway')}{Style.RESET_ALL}")
        return

def main():
    """
    主程序入口函数
    
    整体流程管理和用户交互控制中心，负责程序的初始化、菜单显示
    和功能调用。根据用户的选择执行不同的功能模块，并处理各种异常情况。
    
    主要功能:
    1. 权限检查: 检查Windows系统下是否需要管理员权限
    2. 初始化: 显示程序标志和版本信息
    3. 配置管理: 加载和更新配置文件
    4. 版本检查: 检查是否有新版本可用
    5. 菜单交互: 显示菜单并处理用户选择
    6. 功能调用: 根据用户选择执行相应的功能模块
    7. 异常处理: 捕获并处理程序运行期间的异常
    
    程序循环运行，直到用户选择退出选项。所有模块的功能都通过此函数调度。
    """
    # Check for admin privileges if running as executable on Windows only
    if platform.system() == 'Windows' and is_frozen() and not is_admin():
        print(f"{Fore.YELLOW}{EMOJI['ADMIN']} {translator.get('menu.admin_required')}{Style.RESET_ALL}")
        if run_as_admin():
            sys.exit(0)  # Exit after requesting admin privileges
        else:
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('menu.admin_required_continue')}{Style.RESET_ALL}")
    
    print_logo()
    
    # Initialize configuration
    config = get_config(translator)
    if not config:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.config_init_failed')}{Style.RESET_ALL}")
        return
    force_update_config(translator)

    if config.getboolean('Utils', 'enabled_update_check'):
        check_latest_version()  # Add version check before showing menu
    print_menu()
    
    while True:
        try:
            choice_num = 15
            choice = input(f"\n{EMOJI['ARROW']} {Fore.CYAN}{translator.get('menu.input_choice', choices=f'0-{choice_num}')}: {Style.RESET_ALL}")

            if choice == "0":
                # 退出程序
                print(f"\n{Fore.YELLOW}{EMOJI['INFO']} {translator.get('menu.exit')}...{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'═' * 50}{Style.RESET_ALL}")
                return
            elif choice == "1":
                # 手动重置机器ID
                import reset_machine_manual
                reset_machine_manual.run(translator)
                print_menu()
            elif choice == "2":
                # 使用临时邮箱注册Cursor
                import cursor_register
                cursor_register.main(translator)
                print_menu()
            elif choice == "3":
                # 使用Google账号注册Cursor
                import cursor_register_google
                cursor_register_google.main(translator)
                print_menu()
            elif choice == "4":
                # 使用GitHub账号注册Cursor
                import cursor_register_github
                cursor_register_github.main(translator)
                print_menu()
            elif choice == "5":
                # 手动输入认证信息注册Cursor
                import cursor_register_manual
                cursor_register_manual.main(translator)
                print_menu()
            elif choice == "6":
                # GitHub直接注册Cursor（未实现功能）
                import github_cursor_register
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('menu.coming_soon')}{Style.RESET_ALL}")
                # github_cursor_register.main(translator)
                print_menu()
            elif choice == "7":
                # 退出所有Cursor进程
                import quit_cursor
                quit_cursor.quit_cursor(translator)
                print_menu()
            elif choice == "8":
                # 选择界面语言
                if select_language():
                    print_menu()
                continue
            elif choice == "9":
                # 禁用Cursor自动更新
                import disable_auto_update
                disable_auto_update.run(translator)
                print_menu()
            elif choice == "10":
                # 完全重置Cursor（清除所有配置和缓存）
                import totally_reset_cursor
                totally_reset_cursor.run(translator)
                # print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('menu.fixed_soon')}{Style.RESET_ALL}")
                print_menu()
            elif choice == "11":
                # 显示贡献者信息
                import logo
                print(logo.CURSOR_CONTRIBUTORS)
                print_menu()
            elif choice == "12":
                # 显示当前配置信息
                from config import print_config
                print_config(get_config(), translator)
                print_menu()
            elif choice == "13":
                # 选择Chrome配置文件
                from oauth_auth import OAuthHandler
                oauth = OAuthHandler(translator)
                oauth._select_profile()
                print_menu()
            elif choice == "14":
                # 删除Cursor中的Google账号
                import delete_cursor_google
                delete_cursor_google.main(translator)
                print_menu()
            elif choice == "15":
                # 绕过Cursor版本检查
                import bypass_version
                bypass_version.main(translator)
                print_menu()
            else:
                # 无效的选择
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.invalid_choice')}{Style.RESET_ALL}")
                print_menu()

        except KeyboardInterrupt:
            # 处理Ctrl+C中断
            print(f"\n{Fore.YELLOW}{EMOJI['INFO']} {translator.get('menu.program_terminated')}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'═' * 50}{Style.RESET_ALL}")
            return
        except Exception as e:
            # 处理其他异常
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.error_occurred', error=str(e))}{Style.RESET_ALL}")
            print_menu()

if __name__ == "__main__":
    main()