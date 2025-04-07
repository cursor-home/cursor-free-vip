"""
cursor_acc_info.py - Cursor账号信息查询模块

这个模块负责获取和显示Cursor账号的信息，主要功能包括：
- 从各种位置获取账号令牌(token)
- 查询账号使用情况和订阅状态
- 显示账号的详细信息（GPT-4使用量、订阅类型等）
- 支持多语言显示

通过此模块可以验证账号是否已成功激活Pro版本，并查看使用额度。
"""
# 导入操作系统接口模块，用于处理路径、环境变量等操作系统相关功能
import os
# 导入系统相关模块，用于访问命令行参数、退出程序等系统级功能
import sys
# 导入JSON处理模块，用于解析和生成JSON格式数据（用于存储和读取配置文件）
import json
# 导入HTTP请求库，用于向Cursor API发送网络请求获取账号信息
import requests
# 导入SQLite数据库模块，用于从Cursor的SQLite数据库中读取账号信息
import sqlite3
# 导入类型注解模块，Dict表示字典类型，Optional表示可选类型（可能为None）
from typing import Dict, Optional
# 导入平台识别模块，用于检测操作系统类型（Windows/macOS/Linux）
import platform
# 导入终端文本颜色和样式模块，用于输出彩色文本
from colorama import Fore, Style, init
# 导入日志记录模块，用于记录程序运行状态和错误信息
import logging
# 导入正则表达式模块，用于从文本中提取令牌信息
import re

# 初始化colorama模块，启用终端彩色文本支持（在Windows上尤其重要）
init()

# 设置日志记录器的基本配置
# level=logging.INFO: 设置日志级别为INFO，会记录INFO及以上级别的日志
# format: 设置日志输出格式，包含时间、名称、级别和消息
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# 获取当前模块的日志记录器实例，用于记录本模块的日志信息
logger = logging.getLogger(__name__)

# 定义表情符号常量字典，用于在输出中显示各种状态和类型的图标
EMOJI = {
    "USER": "👤",         # 用户信息图标
    "USAGE": "📊",         # 使用量统计图标
    "PREMIUM": "⭐",       # 高级/付费服务图标
    "BASIC": "📝",         # 基本/免费服务图标
    "SUBSCRIPTION": "💳",  # 订阅信息图标
    "INFO": "ℹ️",          # 一般信息图标
    "ERROR": "❌",         # 错误信息图标
    "SUCCESS": "✅",       # 成功信息图标
    "WARNING": "⚠️",       # 警告信息图标
    "TIME": "🕒"           # 时间/日期相关信息图标
}

class Config:
    """
    配置类
    
    存储程序中使用的常量和配置信息，如API请求头信息等。
    """
    # Cursor应用名称的小写形式，用于构建API URL和文件路径
    NAME_LOWER = "cursor"
    # Cursor应用名称的首字母大写形式，用于构建请求头和显示信息
    NAME_CAPITALIZE = "Cursor"
    # 基本HTTP请求头信息，用于API请求
    BASE_HEADERS = {
        # 浏览器标识，模拟Chrome浏览器，避免被API拒绝访问
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        # 设置接受JSON格式的响应数据
        "Accept": "application/json",
        # 设置请求体的内容类型为JSON
        "Content-Type": "application/json"
    }

class UsageManager:
    """
    使用量管理类
    
    负责通过API获取账号的使用情况和订阅信息。
    包含与Cursor服务器通信的各种方法。
    """
    
    @staticmethod  # 静态方法装饰器，表示此方法不需要访问类的实例属性
    def get_proxy():
        """
        获取代理设置
        
        从环境变量中读取HTTP/HTTPS代理设置，如果存在则返回代理配置。
        
        返回值:
            dict: 代理配置字典，如果没有配置则返回None
        """
        # 尝试从环境变量中获取HTTP_PROXY或HTTPS_PROXY的值
        # 使用or运算符，如果第一个值不存在则尝试获取第二个值
        proxy = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
        # 如果找到了代理设置，返回包含代理信息的字典
        if proxy:
            return {"http": proxy, "https": proxy}
        # 如果没有找到代理设置，返回None
        return None
    
    @staticmethod
    def get_usage(token: str) -> Optional[Dict]:
        """
        获取账号使用情况
        
        通过API获取账号的GPT-4和GPT-3.5使用数据，包括使用量和限制。
        
        参数:
            token (str): 账号访问令牌
            
        返回值:
            dict: 包含使用情况的字典，如果请求失败则返回None
            
        字典格式:
            {
                'premium_usage': GPT-4使用次数,
                'max_premium_usage': GPT-4最大使用限制,
                'basic_usage': GPT-3.5使用次数,
                'max_basic_usage': "No Limit" (GPT-3.5无限制)
            }
        """
        # 构建API请求URL，使用Config类中定义的小写应用名
        url = f"https://www.{Config.NAME_LOWER}.com/api/usage"
        
        # 创建请求头字典的副本，避免修改原始字典
        headers = Config.BASE_HEADERS.copy()
        
        # 向请求头添加带有访问令牌的Cookie，格式为Workos{应用名}SessionToken=user_01...::令牌
        # 这里使用了一个固定的前缀user_01后跟一串O，然后是%3A%3A（URL编码的::）和实际的令牌
        headers.update({"Cookie": f"Workos{Config.NAME_CAPITALIZE}SessionToken=user_01OOOOOOOOOOOOOOOOOOOOOOOO%3A%3A{token}"})
        
        try:
            # 获取代理设置（如果环境中配置了代理）
            proxies = UsageManager.get_proxy()
            
            # 发送GET请求到API获取使用情况数据
            # timeout=10设置10秒超时，避免长时间等待
            # proxies传递代理配置（如果有）
            response = requests.get(url, headers=headers, timeout=10, proxies=proxies)
            
            # 检查响应状态码，如果不是2xx系列成功码，则抛出异常
            response.raise_for_status()
            
            # 解析响应内容为JSON格式
            data = response.json()
            
            # 获取GPT-4使用数据，如果data中没有"gpt-4"键或值不是字典，则返回空字典
            gpt4_data = data.get("gpt-4", {})
            
            # 从GPT-4数据中提取使用量，默认为0
            premium_usage = gpt4_data.get("numRequestsTotal", 0)
            
            # 从GPT-4数据中提取最大使用限制，默认为999
            max_premium_usage = gpt4_data.get("maxRequestUsage", 999)
            
            # 获取GPT-3.5使用数据，如果data中没有"gpt-3.5-turbo"键或值不是字典，则返回空字典
            gpt35_data = data.get("gpt-3.5-turbo", {})
            
            # 从GPT-3.5数据中提取使用量，默认为0
            basic_usage = gpt35_data.get("numRequestsTotal", 0)
            
            # 返回包含各项使用情况的字典
            # 'max_basic_usage'设为"No Limit"表示GPT-3.5没有使用限制
            return {
                'premium_usage': premium_usage,           # GPT-4使用次数
                'max_premium_usage': max_premium_usage,   # GPT-4最大使用限制
                'basic_usage': basic_usage,               # GPT-3.5使用次数
                'max_basic_usage': "No Limit"             # GPT-3.5无使用限制
            }
            
        except requests.RequestException as e:
            # 捕获请求异常（如连接错误、超时等）
            # 记录错误日志，但不抛出异常，而是返回None表示操作失败
            logger.error(f"Get usage info failed: {str(e)}")
            return None
            
        except Exception as e:
            # 捕获所有其他异常（如JSON解析错误等）
            # 同样记录错误日志并返回None
            logger.error(f"Get usage info failed: {str(e)}")
            return None

    @staticmethod
    def get_stripe_profile(token: str) -> Optional[Dict]:
        """
        获取用户订阅信息
        
        通过API获取账号的Stripe订阅信息，包括订阅状态、类型等。
        
        参数:
            token (str): 账号访问令牌
            
        返回值:
            dict: 包含订阅信息的字典，如果请求失败则返回None
        """
        # 构建API请求URL，使用Config类中定义的小写应用名
        # 这个API端点专门用于获取Stripe支付相关的订阅信息
        url = f"https://api2.{Config.NAME_LOWER}.sh/auth/full_stripe_profile"
        
        # 创建请求头字典的副本，避免修改原始字典
        headers = Config.BASE_HEADERS.copy()
        
        # 使用Bearer令牌认证方式更新请求头
        # 这与get_usage方法不同，这里使用Authorization头而不是Cookie
        headers.update({"Authorization": f"Bearer {token}"})
        
        try:
            # 获取代理设置（如果环境中配置了代理）
            proxies = UsageManager.get_proxy()
            
            # 发送GET请求到API获取订阅信息
            # timeout=10设置10秒超时，避免长时间等待
            # proxies传递代理配置（如果有）
            response = requests.get(url, headers=headers, timeout=10, proxies=proxies)
            
            # 检查响应状态码，如果不是2xx系列成功码，则抛出异常
            response.raise_for_status()
            
            # 直接返回解析后的JSON响应数据，包含完整的订阅信息
            # 不像get_usage方法那样提取特定字段，这里保留原始数据结构
            return response.json()
            
        except requests.RequestException as e:
            # 捕获请求异常（如连接错误、超时等）
            # 记录错误日志，但不抛出异常，而是返回None表示操作失败
            logger.error(f"Get subscription info failed: {str(e)}")
            return None

def get_token_from_config():
    """
    从配置中获取路径信息
    
    读取程序配置，获取不同操作系统下的存储路径信息。
    
    返回值:
        dict: 包含各种路径的字典，如果获取失败则返回None
        
    字典格式:
        {
            'storage_path': 存储JSON文件路径,
            'sqlite_path': SQLite数据库路径,
            'session_path': 会话存储路径
        }
    """
    try:
        # 从config模块导入get_config函数
        # 这个导入放在函数内部是为了避免循环导入问题
        from config import get_config
        
        # 调用get_config函数获取配置对象
        config = get_config()
        
        # 如果配置获取失败（返回None），直接返回None
        if not config:
            return None
            
        # 获取当前操作系统名称（Windows/Darwin/Linux）
        system = platform.system()
        
        # 针对Windows系统的路径设置
        # 检查配置中是否存在WindowsPaths部分
        if system == "Windows" and config.has_section('WindowsPaths'):
            # 返回包含Windows系统下各种路径的字典
            return {
                # 从配置文件获取存储文件路径
                'storage_path': config.get('WindowsPaths', 'storage_path'),
                # 从配置文件获取SQLite数据库路径
                'sqlite_path': config.get('WindowsPaths', 'sqlite_path'),
                # 会话存储路径基于APPDATA环境变量构建
                'session_path': os.path.join(os.getenv("APPDATA"), "Cursor", "Session Storage")
            }
        # 针对macOS系统的路径设置（Darwin是macOS的系统名）
        # 检查配置中是否存在MacPaths部分
        elif system == "Darwin" and config.has_section('MacPaths'):  # macOS
            # 返回包含macOS系统下各种路径的字典
            return {
                # 从配置文件获取存储文件路径
                'storage_path': config.get('MacPaths', 'storage_path'),
                # 从配置文件获取SQLite数据库路径
                'sqlite_path': config.get('MacPaths', 'sqlite_path'),
                # 会话存储路径基于用户主目录展开
                'session_path': os.path.expanduser("~/Library/Application Support/Cursor/Session Storage")
            }
        # 针对Linux系统的路径设置
        # 检查配置中是否存在LinuxPaths部分
        elif system == "Linux" and config.has_section('LinuxPaths'):
            # 返回包含Linux系统下各种路径的字典
            return {
                # 从配置文件获取存储文件路径
                'storage_path': config.get('LinuxPaths', 'storage_path'),
                # 从配置文件获取SQLite数据库路径
                'sqlite_path': config.get('LinuxPaths', 'sqlite_path'),
                # 会话存储路径基于用户主目录展开
                'session_path': os.path.expanduser("~/.config/Cursor/Session Storage")
            }
    except Exception as e:
        # 如果在获取配置过程中出现任何异常，记录错误日志
        logger.error(f"Get config path failed: {str(e)}")
    
    # 如果上面的所有条件都不满足，或者发生了异常，返回None表示获取失败
    return None

def get_token_from_storage(storage_path):
    """
    从存储文件中获取令牌
    
    从指定路径的JSON存储文件中读取访问令牌。
    
    参数:
        storage_path (str): 存储文件的路径
        
    返回值:
        str: 访问令牌，如果无法获取则返回None
    """
    try:
        # 检查存储文件是否存在
        # 如果文件不存在，后续操作会引发异常，所以提前检查可以避免异常
        if os.path.exists(storage_path):
            # 以只读模式打开文件，指定UTF-8编码以确保正确读取非ASCII字符
            with open(storage_path, "r", encoding="utf-8") as f:
                # 将文件内容解析为JSON对象（Python中表示为字典）
                data = json.load(f)
                
                # 从JSON数据中获取访问令牌
                # 使用get方法安全地获取值，如果键不存在则返回None
                token = data.get("cursorAuth/accessToken")
                
                # 如果成功获取到令牌（非None、非空）则返回
                if token:
                    return token
    except (json.JSONDecodeError, IOError) as e:
        # 捕获JSON解析错误和IO错误（如文件不存在、权限问题等）
        # 记录错误日志但不中断程序流程
        logger.error(f"Failed to read token from storage: {str(e)}")
    
    # 如果上述过程中遇到任何问题，或者没有找到令牌，返回None
    return None

def get_token_from_sqlite(sqlite_path):
    """
    从SQLite数据库中获取令牌
    
    连接SQLite数据库并查询访问令牌。
    
    参数:
        sqlite_path (str): SQLite数据库文件的路径
        
    返回值:
        str: 访问令牌，如果无法获取则返回None
    """
    try:
        # 检查SQLite数据库文件是否存在
        # 如果文件不存在，后续连接操作会引发异常
        if os.path.exists(sqlite_path):
            # 连接到SQLite数据库文件
            # 这会创建一个数据库连接对象
            conn = sqlite3.connect(sqlite_path)
            
            # 创建一个游标对象，用于执行SQL查询
            cursor = conn.cursor()
            
            # 执行SQL查询，从ItemTable表中查找键为'cursorAuth/accessToken'的记录
            # 键是Cursor应用存储访问令牌的固定字段名
            cursor.execute("SELECT value FROM ItemTable WHERE key = 'cursorAuth/accessToken'")
            
            # 获取查询结果的第一行（如果有）
            # fetchone返回单个结果行，如果没有结果则返回None
            result = cursor.fetchone()
            
            # 关闭数据库连接，释放资源
            # 一定要关闭连接，否则可能导致数据库锁定
            conn.close()
        
            # 检查是否有结果，并且结果的第一个字段（列索引0）非空
            # 结果格式应为(token_value,)，即单个元素的元组
            if result and result[0]:
                # 返回查询到的令牌值
                return result[0]
    except sqlite3.Error as e:
        # 捕获SQLite数据库相关的所有错误
        # 如连接失败、表不存在、SQL语法错误等
        logger.error(f"Failed to read token from SQLite: {str(e)}")
    
    # 如果上述过程中遇到任何问题，或者没有找到令牌，返回None
    return None

def get_token_from_session(session_path):
    """
    从会话存储中获取令牌
    
    从Cursor的会话存储文件中提取访问令牌。
    这个方法处理LevelDB/Session Storage格式的文件。
    
    参数:
        session_path (str): 会话存储文件夹的路径
        
    返回值:
        str: 访问令牌，如果无法获取则返回None
    """
    try:
        # 检查会话存储目录是否存在
        if os.path.exists(session_path):
            # 遍历目录中的所有文件
            for file in os.listdir(session_path):
                # 只处理.log和.ldb文件，这些是LevelDB存储的文件格式
                # 这些文件可能包含会话数据，包括访问令牌
                if file.endswith(".log") or file.endswith(".ldb"):
                    # 构建完整的文件路径
                    file_path = os.path.join(session_path, file)
                    try:
                        # 以二进制模式打开文件，因为LevelDB文件是二进制格式
                        with open(file_path, "rb") as f:
                            # 读取文件内容并尝试解码为UTF-8
                            # errors="ignore"参数表示忽略无法解码的字符
                            # 这很重要，因为二进制文件可能包含无法用UTF-8解码的字节
                            content = f.read().decode("utf-8", errors="ignore")
                            
                            # 使用正则表达式在文件内容中搜索令牌
                            # 正则表达式查找形如"cursorAuth/accessToken":"令牌值"的模式
                            # 中间的\s*表示可能有任意数量的空白字符
                            # ([^"]+)捕获组匹配一个或多个非引号字符，即令牌本身
                            match = re.search(r'"cursorAuth/accessToken"\s*:\s*"([^"]+)"', content)
                            
                            # 如果找到匹配项
                            if match:
                                # 返回匹配到的第一个捕获组（令牌值）
                                return match.group(1)
                    except IOError:
                        # 如果读取特定文件时出错（如权限问题），
                        # 不终止整个处理，而是继续处理下一个文件
                        continue
    except Exception as e:
        # 捕获所有可能的异常，包括目录不存在、权限问题等
        # 记录错误日志但不中断程序流程
        logger.error(f"Failed to read token from session storage: {str(e)}")
    
    # 如果上述过程中遇到任何问题，或者没有找到令牌，返回None
    return None

def get_token():
    """
    获取访问令牌
    
    尝试从多个来源获取访问令牌，按优先级顺序：
    1. 配置文件
    2. 存储文件
    3. SQLite数据库
    4. 会话存储
    
    返回值:
        str: 访问令牌，如果所有来源都失败则返回None
    """
    # 首先尝试从配置文件获取各种存储路径信息
    # 这些路径将用于后续检查不同位置的令牌
    config_paths = get_token_from_config()
    
    # 如果成功获取到路径信息
    if config_paths:
        # 第一步：尝试从JSON存储文件获取令牌
        # 将路径字典中的'storage_path'值传递给get_token_from_storage函数
        token = get_token_from_storage(config_paths.get('storage_path'))
        # 如果成功获取到令牌，直接返回，不再检查其他来源
        if token:
            return token
        
        # 第二步：如果存储文件中没有令牌，尝试从SQLite数据库获取
        # 将路径字典中的'sqlite_path'值传递给get_token_from_sqlite函数
        token = get_token_from_sqlite(config_paths.get('sqlite_path'))
        # 如果成功获取到令牌，直接返回，不再检查其他来源
        if token:
            return token
        
        # 第三步：如果SQLite数据库中没有令牌，尝试从会话存储文件获取
        # 将路径字典中的'session_path'值传递给get_token_from_session函数
        token = get_token_from_session(config_paths.get('session_path'))
        # 如果成功获取到令牌，返回
        if token:
            return token
    
    # 如果所有来源都没有找到令牌，或者配置路径获取失败，返回None
    return None

def format_subscription_type(subscription_data: Dict) -> str:
    """
    格式化订阅类型信息
    
    根据订阅数据格式化为可读的订阅类型和状态。
    
    参数:
        subscription_data (Dict): 包含订阅信息的字典
        
    返回值:
        str: 格式化后的订阅类型字符串
        
    支持的订阅类型:
    - Pro: 专业版
    - Pro (Trial): 专业版试用
    - Team: 团队版
    - Basic: 基础版
    - Not Found: 未发现订阅信息
    """
    try:
        # 首先检查subscription_data是否存在并且包含stripeSubStatusText字段
        # 这表明用户有某种形式的订阅
        if subscription_data and 'stripeSubStatusText' in subscription_data:
            # 检查用户是否有Pro权限
            # hasPro是一个布尔值，表明用户是否有专业版特权
            if subscription_data.get('hasPro', False):
                # 如果用户有Team或Teams权限（比Pro级别更高）
                # hasTeams或hasTeam为True表示用户属于团队或企业账号
                if subscription_data.get('hasTeams', False) or subscription_data.get('hasTeam', False):
                    # 返回带颜色格式的"Team"文本
                    # Fore.CYAN设置为青色，Style.RESET_ALL重置颜色设置
                    return f"{Fore.CYAN}Team{Style.RESET_ALL}"
                    
                # 用户有Pro权限但不是Team，检查是否是试用账号
                # trialPeriodDays表示试用期天数
                if 'trialPeriodDays' in subscription_data and subscription_data.get('trialPeriodDays') > 0:
                    # 如果是试用账号，返回带黄色的"Pro (Trial)"文本
                    return f"{Fore.YELLOW}Pro (Trial){Style.RESET_ALL}"
                
                # 如果是常规Pro账号（不是试用，不是团队），返回带绿色的"Pro"文本
                return f"{Fore.GREEN}Pro{Style.RESET_ALL}"
            
            # 如果用户没有Pro权限，则为基础版用户
            # 返回白色的"Basic"文本
            return f"{Fore.WHITE}Basic{Style.RESET_ALL}"
        
        # 如果subscription_data不存在或没有stripeSubStatusText字段
        # 返回红色的"Not Found"文本，表示找不到订阅信息
        return f"{Fore.RED}Not Found{Style.RESET_ALL}"
    
    except Exception:
        # 如果处理过程中发生任何异常
        # 返回红色的"Error"文本，表示解析订阅信息时出错
        return f"{Fore.RED}Error{Style.RESET_ALL}"

def get_email_from_storage(storage_path):
    """
    从存储文件中获取邮箱地址
    
    从指定路径的JSON存储文件中读取用户邮箱地址。
    
    参数:
        storage_path (str): 存储文件的路径
        
    返回值:
        str: 用户邮箱地址，如果无法获取则返回None
    """
    # 首先检查存储文件是否存在
    # 如果文件不存在，直接返回None，避免后续操作出错
    if not os.path.exists(storage_path):
        return None
        
    try:
        # 以只读模式打开存储文件，使用UTF-8编码
        with open(storage_path, 'r', encoding='utf-8') as f:
            # 将文件内容解析为JSON对象（Python中表示为字典）
            data = json.load(f)
            
            # 首先尝试获取标准的邮箱字段
            # 'cursorAuth/cachedEmail'是Cursor应用存储邮箱的标准字段名
            if 'cursorAuth/cachedEmail' in data:
                # 如果找到标准字段，直接返回其值
                return data['cursorAuth/cachedEmail']
                
            # 如果标准字段不存在，尝试查找其他可能包含邮箱的字段
            # 遍历数据字典中的所有键
            for key in data:
                # 检查键名是否包含'email'字符串（不区分大小写）
                # 并且对应的值是字符串类型
                # 并且值中包含'@'符号（邮箱的基本特征）
                if 'email' in key.lower() and isinstance(data[key], str) and '@' in data[key]:
                    # 如果找到符合条件的字段，返回其值
                    return data[key]
    except Exception as e:
        # 捕获所有可能的异常，包括文件读取错误、JSON解析错误等
        # 记录错误但不中断程序流程
        logger.error(f"get email from storage.json failed: {str(e)}")
    
    # 如果上述所有尝试都失败，返回None表示未找到邮箱
    return None

def get_email_from_sqlite(sqlite_path):
    """
    从SQLite数据库中获取邮箱地址
    
    连接SQLite数据库并查询用户邮箱地址。
    
    参数:
        sqlite_path (str): SQLite数据库文件的路径
        
    返回值:
        str: 用户邮箱地址，如果无法获取则返回None
    """
    # 首先检查数据库文件是否存在
    # 如果文件不存在，直接返回None，避免后续连接操作出错
    if not os.path.exists(sqlite_path):
        return None
        
    try:
        # 连接到SQLite数据库文件
        # 这会创建一个数据库连接对象
        conn = sqlite3.connect(sqlite_path)
        
        # 创建一个游标对象，用于执行SQL查询
        cursor = conn.cursor()
        
        # 执行SQL查询，查找所有键名包含'email'的记录
        # LIKE操作符和%通配符用于模糊匹配包含'email'的键名
        cursor.execute("SELECT value FROM ItemTable WHERE key LIKE '%email%'")
        
        # 获取查询结果的所有行
        # fetchall返回一个元组列表，每个元组代表一行结果
        rows = cursor.fetchall()
        
        # 关闭数据库连接，释放资源
        conn.close()
        
        # 遍历查询结果的每一行
        for row in rows:
            try:
                # 获取当前行的第一个字段（列索引0）值
                value = row[0]
                
                # 检查值是否为字符串、包含@符号、@后面的域名部分包含点号
                # 这是判断一个字符串是否为有效邮箱的基本检查
                if isinstance(value, str) and '@' in value and '.' in value.split('@')[1]:
                    # 如果是有效的邮箱格式，直接返回
                    return value
                
                # 如果值不是直接的邮箱字符串，尝试将其解析为JSON对象
                # 某些应用可能将邮箱存储在JSON结构中
                data = json.loads(value)
                
                # 检查解析后的对象是否是字典，且包含'email'键
                if isinstance(data, dict) and 'email' in data:
                    # 获取字典中的email值
                    email = data['email']
                    
                    # 检查提取的email是否符合基本邮箱格式
                    if '@' in email and '.' in email.split('@')[1]:
                        # 如果是有效的邮箱格式，返回
                        return email
            except:
                # 如果处理当前行时出现任何异常（如JSON解析错误）
                # 忽略错误并继续处理下一行
                continue
    except Exception as e:
        # 捕获所有可能的异常，包括数据库连接错误等
        # 记录错误但不中断程序流程
        logger.error(f"get email from sqlite failed: {str(e)}")
    
    # 如果上述所有尝试都失败，返回None表示未找到邮箱
    return None

def display_account_info(translator=None):
    """
    显示账号信息
    
    获取并显示Cursor账号的详细信息，包括:
    - 邮箱地址
    - 订阅类型和状态
    - GPT-4和GPT-3.5使用情况
    - 订阅到期日期和剩余天数（如果有）
    
    参数:
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        bool: 操作成功返回True，失败返回False
    """
    try:
        # 获取访问令牌
        # 令牌是与Cursor API交互的必要凭证
        token = get_token()
        # 如果无法获取令牌，显示错误消息并退出函数
        if not token:
            # 使用红色文字和错误图标显示错误消息
            # 如果有翻译器对象，使用翻译后的消息，否则使用默认英文消息
            print(f"\n{Fore.RED}{EMOJI['ERROR']} {translator.get('acc_info.token_not_found') if translator else 'Token not found. Make sure Cursor is installed and you have logged in.'}{Style.RESET_ALL}")
            return False
        
        # 获取存储路径信息
        # 这些路径用于从不同位置读取邮箱等信息
        paths = get_token_from_config()
        # 如果无法获取路径信息，显示错误消息并退出函数
        if not paths:
            print(f"\n{Fore.RED}{EMOJI['ERROR']} {translator.get('acc_info.paths_not_found') if translator else 'Could not determine Cursor paths. Make sure Cursor is properly installed.'}{Style.RESET_ALL}")
            return False
        
        # 获取用户邮箱地址
        # 依次尝试从存储文件和SQLite数据库获取，如果都失败则使用"Unknown"
        email = get_email_from_storage(paths['storage_path']) or get_email_from_sqlite(paths['sqlite_path']) or "Unknown"
        
        # 获取使用情况数据
        # 包括GPT-4和GPT-3.5的使用量和限制
        usage_info = UsageManager.get_usage(token)
        # 默认设置为"Unknown"，如果API请求失败
        premium_usage = "Unknown"
        max_premium_usage = "Unknown"
        basic_usage = "Unknown"
        
        # 如果成功获取使用情况数据，提取相关字段
        if usage_info:
            premium_usage = usage_info.get('premium_usage', "Unknown")  # GPT-4使用量
            max_premium_usage = usage_info.get('max_premium_usage', "Unknown")  # GPT-4使用限制
            basic_usage = usage_info.get('basic_usage', "Unknown")  # GPT-3.5使用量
        
        # 获取订阅信息
        # 包括订阅类型、状态、到期日期等
        subscription_info = UsageManager.get_stripe_profile(token)
        # 格式化订阅类型为易读的字符串，包含颜色
        subscription_type = format_subscription_type(subscription_info)
        
        # 初始化订阅到期日期和剩余天数
        # 默认设为"N/A"表示不适用或未知
        subscription_end_date = "N/A"
        remaining_days = "N/A"
        
        # 如果成功获取订阅信息，计算到期日期和剩余天数
        if subscription_info:
            # 检查是否为试用账号
            if "trialEndDate" in subscription_info and subscription_info["trialEndDate"]:
                # 将毫秒时间戳转换为秒时间戳
                end_timestamp = subscription_info["trialEndDate"] / 1000
                
                # 导入日期时间模块，用于时间计算
                import datetime
                # 将时间戳转换为日期时间对象
                end_date = datetime.datetime.fromtimestamp(end_timestamp)
                # 格式化日期为YYYY-MM-DD格式
                subscription_end_date = end_date.strftime("%Y-%m-%d")
                
                # 计算剩余天数
                # 当前日期时间
                now = datetime.datetime.now()
                # 计算时间差
                delta = end_date - now
                # 获取剩余天数，如果为负数则设为0
                remaining_days = max(0, delta.days)
            
            # 检查是否为付费订阅
            elif "subscriptionEndDate" in subscription_info and subscription_info["subscriptionEndDate"]:
                # 将毫秒时间戳转换为秒时间戳
                end_timestamp = subscription_info["subscriptionEndDate"] / 1000
                
                # 导入日期时间模块，用于时间计算
                import datetime
                # 将时间戳转换为日期时间对象
                end_date = datetime.datetime.fromtimestamp(end_timestamp)
                # 格式化日期为YYYY-MM-DD格式
                subscription_end_date = end_date.strftime("%Y-%m-%d")
                
                # 计算剩余天数
                # 当前日期时间
                now = datetime.datetime.now()
                # 计算时间差
                delta = end_date - now
                # 获取剩余天数，如果为负数则设为0
                remaining_days = max(0, delta.days)
        
        # 打印账号信息
        # 首先打印分隔线和标题
        print(f"\n{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('account_info.account_info') if translator else 'Cursor Account Information'}:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}")
        
        # 打印邮箱地址（绿色）
        print(f"{Fore.GREEN}{EMOJI['USER']} {translator.get('account_info.email') if translator else 'Email'}: {email}{Style.RESET_ALL}")
        
        # 打印订阅类型（颜色取决于订阅类型）
        print(f"{EMOJI['SUBSCRIPTION']} {translator.get('account_info.subscription_type') if translator else 'Subscription Type'}: {subscription_type}")
        
        # 打印GPT-4使用情况
        # 默认使用绿色，但根据使用百分比可能变为黄色或红色
        usage_percentage = "N/A"
        premium_color = Fore.GREEN
        
        # 如果使用量和限制数据都是数字且限制大于0，计算使用百分比
        if isinstance(premium_usage, int) and isinstance(max_premium_usage, int) and max_premium_usage > 0:
            # 计算使用百分比并格式化为一位小数
            usage_percentage = f"{(premium_usage / max_premium_usage) * 100:.1f}%"
            
            # 根据使用百分比设置颜色
            # 超过80%使用量时显示红色警告
            if premium_usage / max_premium_usage > 0.8:
                premium_color = Fore.RED
            # 超过50%使用量时显示黄色警告
            elif premium_usage / max_premium_usage > 0.5:
                premium_color = Fore.YELLOW
        
        # 打印GPT-4使用情况（高级使用）
        print(f"{premium_color}{EMOJI['PREMIUM']} {translator.get('account_info.premium_usage') if translator else 'Premium Usage (GPT-4)'}: {premium_usage} / {max_premium_usage} ({usage_percentage}){Style.RESET_ALL}")
        
        # 打印GPT-3.5使用情况（基础使用）
        # GPT-3.5通常没有使用限制，所以显示"No Limit"
        print(f"{Fore.GREEN}{EMOJI['BASIC']} {translator.get('account_info.basic_usage') if translator else 'Basic Usage (GPT-3.5)'}: {basic_usage} / {translator.get('account_info.no_limit') if translator else 'No Limit'}{Style.RESET_ALL}")
        
        # 如果有订阅到期日期，打印到期日期和剩余天数
        if subscription_end_date != "N/A":
            # 如果剩余天数少于7天，使用红色警告，否则使用绿色
            end_date_color = Fore.RED if isinstance(remaining_days, int) and remaining_days < 7 else Fore.GREEN
            
            # 打印订阅到期日期
            print(f"{end_date_color}{EMOJI['TIME']} {translator.get('account_info.subscription_end') if translator else 'Subscription End Date'}: {subscription_end_date}{Style.RESET_ALL}")
            
            # 打印剩余天数
            print(f"{end_date_color}{EMOJI['TIME']} {translator.get('account_info.remaining_days') if translator else 'Remaining Days'}: {remaining_days}{Style.RESET_ALL}")
        
        # 打印底部分隔线
        print(f"{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}")
        
        # 操作成功，返回True
        return True
    
    except Exception as e:
        # 捕获所有可能的异常
        # 打印错误消息（红色）
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('account_info.error', error=str(e)) if translator else f'Error: {str(e)}'}{Style.RESET_ALL}")
        # 记录详细错误日志
        logger.error(f"display_account_info failed: {str(e)}")
        # 操作失败，返回False
        return False

def get_display_width(s):
    """
    获取字符串的显示宽度
    
    计算字符串在终端中的实际显示宽度，
    中文字符通常占用两个单位宽度。
    
    参数:
        s (str): 要计算宽度的字符串
        
    返回值:
        int: 字符串的显示宽度
    """
    if not s:
        return 0
            
    width = 0
    for c in s:
        if ord(c) > 127:  # Unicode characters (for CJK languages)
            width += 2
        else:
            width += 1
    return width
    
def main(translator=None):
    """
    主函数
    
    程序的入口点，调用display_account_info函数显示账号信息。
    
    参数:
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        bool: 如果成功获取并显示信息返回True，否则返回False
    """
    return display_account_info(translator)

if __name__ == "__main__":
    main() 