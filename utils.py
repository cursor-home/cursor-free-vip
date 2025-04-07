"""
utils.py - 实用工具函数集合

这个文件包含了程序中使用的各种通用工具函数，主要涉及：
- 获取系统路径（文档目录、Chrome路径、Cursor路径等）
- 随机等待时间生成
- 其他通用功能

这些函数被主程序和其他模块调用，提供基础功能支持。
"""
import os
import sys
import platform
import random

def get_user_documents_path():
    """
    获取用户文档目录路径。
    
    根据不同操作系统返回相应的文档目录：
    - Windows: ~/Documents
    - macOS/Linux: ~/Documents
    
    返回值:
        str: 用户文档目录的完整路径
    """
    if platform.system() == "Windows":
        return os.path.expanduser("~\\Documents")
    else:
        return os.path.expanduser("~/Documents")

def get_default_chrome_path():
    """
    获取默认Chrome浏览器可执行文件路径。
    
    根据不同操作系统返回相应的Chrome路径：
    - Windows: 优先尝试从PATH中查找，然后返回默认安装路径
    - macOS: 返回应用程序目录中的Chrome路径
    - Linux: 返回标准二进制位置
    
    返回值:
        str: Chrome可执行文件的完整路径
    """
    if sys.platform == "win32":
        #  Trying to find chrome in PATH
        try:
            import shutil
            chrome_in_path = shutil.which("chrome")
            if chrome_in_path:
                return chrome_in_path
        except:
            pass
        # Going to default path
        return r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    elif sys.platform == "darwin":
        return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    else:
        return "/usr/bin/google-chrome"

def get_linux_cursor_path():
    """
    获取Linux系统上Cursor应用程序的资源路径。
    
    按照优先级顺序检查以下可能的路径：
    - /opt/Cursor/resources/app
    - /usr/share/cursor/resources/app
    - /opt/cursor-bin/resources/app
    - /usr/lib/cursor/resources/app
    - ~/.local/share/cursor/resources/app
    
    返回值:
        str: 找到的第一个存在的Cursor资源路径，如果都不存在则返回默认路径
    """
    possible_paths = [
        "/opt/Cursor/resources/app",
        "/usr/share/cursor/resources/app",
        "/opt/cursor-bin/resources/app",
        "/usr/lib/cursor/resources/app",
        os.path.expanduser("~/.local/share/cursor/resources/app")
    ]
    
    # return the first path that exists
    return next((path for path in possible_paths if os.path.exists(path)), possible_paths[0])

def get_random_wait_time(config, timing_key=None, min_time=None, max_time=None):
    """
    根据配置获取随机等待时间。
    
    这个函数用于生成随机等待时间，使自动化操作更像人工操作，
    可以减少被反爬虫或反自动化系统检测的可能性。
    
    参数:
        config (dict或float): 包含时间设置的配置字典，或最小等待时间
        timing_key (str或float): 在配置中查找的时间设置键名，或最大等待时间
        min_time (float, 可选): 最小等待时间，覆盖配置设置
        max_time (float, 可选): 最大等待时间，覆盖配置设置
        
    返回值:
        float: 随机等待时间（秒）
        
    示例:
        如果config['Timing']['login_wait'] = "1.5-3.0"，
        则get_random_wait_time(config, 'login_wait')会返回
        1.5到3.0之间的随机浮点数
        
        也可以直接指定时间范围：
        get_random_wait_time(1.0, 2.0)会返回1.0到2.0之间的随机浮点数
    
    注意:
        - 支持的时间格式有: 单个数值, 范围格式("min-max"), 逗号分隔格式("min,max")
        - 如果配置不存在或解析出错，默认返回0.5到1.5秒之间的随机值
    """
    # 重载版本：直接接受min和max参数
    if isinstance(config, (int, float)) and isinstance(timing_key, (int, float)):
        return random.uniform(config, timing_key)
    
    # 如果提供了min_time和max_time，优先使用这些值
    if min_time is not None and max_time is not None:
        return random.uniform(min_time, max_time)
        
    try:
        # Get timing value from config
        timing = config.get('Timing', {}).get(timing_key)
        if not timing:
            # Default to 0.5-1.5 seconds if timing not found
            return random.uniform(0.5, 1.5)
            
        # Check if timing is a range (e.g., "0.5-1.5" or "0.5,1.5")
        if isinstance(timing, str):
            if '-' in timing:
                min_time, max_time = map(float, timing.split('-'))
            elif ',' in timing:
                min_time, max_time = map(float, timing.split(','))
            else:
                # Single value, use it as both min and max
                min_time = max_time = float(timing)
        else:
            # If timing is a number, use it as both min and max
            min_time = max_time = float(timing)
            
        return random.uniform(min_time, max_time)
        
    except (ValueError, TypeError, AttributeError):
        # Return default value if any error occurs
        return random.uniform(0.5, 1.5) 