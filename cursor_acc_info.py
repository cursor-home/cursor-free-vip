"""
cursor_acc_info.py - Cursor账号信息查询模块

这个模块负责获取和显示Cursor账号的信息，主要功能包括：
- 从各种位置获取账号令牌(token)
- 查询账号使用情况和订阅状态
- 显示账号的详细信息（GPT-4使用量、订阅类型等）
- 支持多语言显示

通过此模块可以验证账号是否已成功激活Pro版本，并查看使用额度。
"""
import os
import sys
import json
import requests
import sqlite3
from typing import Dict, Optional
import platform
from colorama import Fore, Style, init
import logging
import re

# Initialize colorama
init()

# Setup logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define emoji constants
EMOJI = {
    "USER": "👤",
    "USAGE": "📊",
    "PREMIUM": "⭐",
    "BASIC": "📝",
    "SUBSCRIPTION": "💳",
    "INFO": "ℹ️",
    "ERROR": "❌",
    "SUCCESS": "✅",
    "WARNING": "⚠️",
    "TIME": "🕒"
}

class Config:
    """
    配置类
    
    存储程序中使用的常量和配置信息，如API请求头信息等。
    """
    NAME_LOWER = "cursor"
    NAME_CAPITALIZE = "Cursor"
    BASE_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

class UsageManager:
    """
    使用量管理类
    
    负责通过API获取账号的使用情况和订阅信息。
    包含与Cursor服务器通信的各种方法。
    """
    
    @staticmethod
    def get_proxy():
        """
        获取代理设置
        
        从环境变量中读取HTTP/HTTPS代理设置，如果存在则返回代理配置。
        
        返回值:
            dict: 代理配置字典，如果没有配置则返回None
        """
        # from config import get_config
        proxy = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
        if proxy:
            return {"http": proxy, "https": proxy}
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
        url = f"https://www.{Config.NAME_LOWER}.com/api/usage"
        headers = Config.BASE_HEADERS.copy()
        headers.update({"Cookie": f"Workos{Config.NAME_CAPITALIZE}SessionToken=user_01OOOOOOOOOOOOOOOOOOOOOOOO%3A%3A{token}"})
        try:
            proxies = UsageManager.get_proxy()
            response = requests.get(url, headers=headers, timeout=10, proxies=proxies)
            response.raise_for_status()
            data = response.json()
            
            # get Premium usage and limit
            gpt4_data = data.get("gpt-4", {})
            premium_usage = gpt4_data.get("numRequestsTotal", 0)
            max_premium_usage = gpt4_data.get("maxRequestUsage", 999)
            
            # get Basic usage, but set limit to "No Limit"
            gpt35_data = data.get("gpt-3.5-turbo", {})
            basic_usage = gpt35_data.get("numRequestsTotal", 0)
            
            return {
                'premium_usage': premium_usage, 
                'max_premium_usage': max_premium_usage, 
                'basic_usage': basic_usage, 
                'max_basic_usage': "No Limit"  # set Basic limit to "No Limit"
            }
        except requests.RequestException as e:
            # only log error
            logger.error(f"Get usage info failed: {str(e)}")
            return None
        except Exception as e:
            # catch all other exceptions
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
        url = f"https://api2.{Config.NAME_LOWER}.sh/auth/full_stripe_profile"
        headers = Config.BASE_HEADERS.copy()
        headers.update({"Authorization": f"Bearer {token}"})
        try:
            proxies = UsageManager.get_proxy()
            response = requests.get(url, headers=headers, timeout=10, proxies=proxies)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
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
        from config import get_config
        config = get_config()
        if not config:
            return None
            
        system = platform.system()
        if system == "Windows" and config.has_section('WindowsPaths'):
            return {
                'storage_path': config.get('WindowsPaths', 'storage_path'),
                'sqlite_path': config.get('WindowsPaths', 'sqlite_path'),
                'session_path': os.path.join(os.getenv("APPDATA"), "Cursor", "Session Storage")
            }
        elif system == "Darwin" and config.has_section('MacPaths'):  # macOS
            return {
                'storage_path': config.get('MacPaths', 'storage_path'),
                'sqlite_path': config.get('MacPaths', 'sqlite_path'),
                'session_path': os.path.expanduser("~/Library/Application Support/Cursor/Session Storage")
            }
        elif system == "Linux" and config.has_section('LinuxPaths'):
            return {
                'storage_path': config.get('LinuxPaths', 'storage_path'),
                'sqlite_path': config.get('LinuxPaths', 'sqlite_path'),
                'session_path': os.path.expanduser("~/.config/Cursor/Session Storage")
            }
    except Exception as e:
        logger.error(f"Get config path failed: {str(e)}")
    
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
        if os.path.exists(storage_path):
            with open(storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                token = data.get("cursorAuth/accessToken")
                if token:
                    return token
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to read token from storage: {str(e)}")
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
        if os.path.exists(sqlite_path):
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM ItemTable WHERE key = 'cursorAuth/accessToken'")
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                return result[0]
    except sqlite3.Error as e:
        logger.error(f"Failed to read token from SQLite: {str(e)}")
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
        if os.path.exists(session_path):
            for file in os.listdir(session_path):
                if file.endswith(".log") or file.endswith(".ldb"):
                    file_path = os.path.join(session_path, file)
                    try:
                        with open(file_path, "rb") as f:
                            content = f.read().decode("utf-8", errors="ignore")
                            # Search for token in file content
                            match = re.search(r'"cursorAuth/accessToken"\s*:\s*"([^"]+)"', content)
                            if match:
                                return match.group(1)
                    except IOError:
                        continue
    except Exception as e:
        logger.error(f"Failed to read token from session storage: {str(e)}")
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
    # First try to get paths from config
    config_paths = get_token_from_config()
    
    if config_paths:
        # Try to get token from storage
        token = get_token_from_storage(config_paths.get('storage_path'))
        if token:
            return token
            
        # Try to get token from SQLite
        token = get_token_from_sqlite(config_paths.get('sqlite_path'))
        if token:
            return token
            
        # Try to get token from session
        token = get_token_from_session(config_paths.get('session_path'))
        if token:
            return token
    
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
        # If has subscription
        if subscription_data and 'stripeSubStatusText' in subscription_data:
            # Check if has a pro plan
            if subscription_data.get('hasPro', False):
                # Check if has a Team plan (larger than Pro)
                if subscription_data.get('hasTeams', False) or subscription_data.get('hasTeam', False):
                    # return "Team" plan
                    return f"{Fore.CYAN}Team{Style.RESET_ALL}"
                    
                # Not team, just Pro
                if 'trialPeriodDays' in subscription_data and subscription_data.get('trialPeriodDays') > 0:
                    # Just a trial
                    return f"{Fore.YELLOW}Pro (Trial){Style.RESET_ALL}"
                # Regular Pro account
                return f"{Fore.GREEN}Pro{Style.RESET_ALL}"
            
            # Falls back to basic
            return f"{Fore.WHITE}Basic{Style.RESET_ALL}"
        
        return f"{Fore.RED}Not Found{Style.RESET_ALL}"
    except Exception:
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
    try:
        if os.path.exists(storage_path):
            with open(storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                email = data.get("cursorAuth/cachedEmail")
                if email:
                    return email
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to read email from storage: {str(e)}")
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
    try:
        if os.path.exists(sqlite_path):
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM ItemTable WHERE key = 'cursorAuth/cachedEmail'")
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                return result[0]
    except sqlite3.Error as e:
        logger.error(f"Failed to read email from SQLite: {str(e)}")
    return None

def display_account_info(translator=None):
    """
    显示账号信息
    
    获取并显示Cursor账号的详细信息，包括:
    - 邮箱地址
    - 订阅类型和状态
    - GPT-4和GPT-3.5使用情况
    
    参数:
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        bool: 操作成功返回True，失败返回False
    """
    # Get token
    token = get_token()
    if not token:
        print(f"\n{Fore.RED}{EMOJI['ERROR']} {translator.get('acc_info.token_not_found') if translator else 'Token not found. Make sure Cursor is installed and you have logged in.'}{Style.RESET_ALL}")
    # handle new API response format
    if "membershipType" in subscription_data:
        membership_type = subscription_data.get("membershipType", "").lower()
        subscription_status = subscription_data.get("subscriptionStatus", "").lower()
        
        if subscription_status == "active":
            if membership_type == "pro":
                return "Pro"
            elif membership_type == "free_trial":
                return "Free Trial"
            elif membership_type == "pro_trial":
                return "Pro Trial"
            elif membership_type == "team":
                return "Team"
            elif membership_type == "enterprise":
                return "Enterprise"
            elif membership_type:
                return membership_type.capitalize()
            else:
                return "Active Subscription"
        elif subscription_status:
            return f"{membership_type.capitalize()} ({subscription_status})"
    
    # compatible with old API response format
    subscription = subscription_data.get("subscription")
    if subscription:
        plan = subscription.get("plan", {}).get("nickname", "Unknown")
        status = subscription.get("status", "unknown")
        
        if status == "active":
            if "pro" in plan.lower():
                return "Pro"
            elif "pro_trial" in plan.lower():
                return "Pro Trial"
            elif "free_trial" in plan.lower():
                return "Free Trial"
            elif "team" in plan.lower():
                return "Team"
            elif "enterprise" in plan.lower():
                return "Enterprise"
            else:
                return plan
        else:
            return f"{plan} ({status})"
    
    return "Free"

def get_email_from_storage(storage_path):
    """
    从storage.json文件获取邮箱
    
    尝试从Cursor的存储文件中提取用户邮箱地址。
    
    参数:
        storage_path (str): storage.json文件的路径
        
    返回值:
        str: 找到的邮箱地址，如果未找到则返回None
    """
    if not os.path.exists(storage_path):
        return None
        
    try:
        with open(storage_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # try to get cursorAuth/cachedEmail
            if 'cursorAuth/cachedEmail' in data:
                return data['cursorAuth/cachedEmail']
                
            # try other possible keys
            for key in data:
                if 'email' in key.lower() and isinstance(data[key], str) and '@' in data[key]:
                    return data[key]
    except Exception as e:
        logger.error(f"get email from storage.json failed: {str(e)}")
    
    return None

def get_email_from_sqlite(sqlite_path):
    """
    从SQLite数据库获取邮箱
    
    连接Cursor的SQLite数据库，尝试从中提取用户邮箱地址。
    
    参数:
        sqlite_path (str): SQLite数据库文件的路径
        
    返回值:
        str: 找到的邮箱地址，如果未找到则返回None
    """
    if not os.path.exists(sqlite_path):
        return None
        
    try:
        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM ItemTable WHERE key LIKE '%email%'")
        rows = cursor.fetchall()
        conn.close()
        
        for row in rows:
            try:
                value = row[0]
                if isinstance(value, str) and '@' in value and '.' in value.split('@')[1]:
                    return value
                # try to parse JSON
                data = json.loads(value)
                if isinstance(data, dict) and 'email' in data:
                    email = data['email']
                    if '@' in email and '.' in email.split('@')[1]:
                        return email
            except:
                continue
    except Exception as e:
        logger.error(f"get email from sqlite failed: {str(e)}")
    
    return None

def display_account_info(translator=None):
    """
    显示账号信息
    
    获取并格式化显示Cursor账号的详细信息，包括：
    - 邮箱地址
    - 订阅类型
    - GPT-4使用量和限制
    - GPT-3.5使用量
    - 订阅状态和剩余天数（如果适用）
    
    参数:
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        bool: 如果成功获取并显示信息返回True，否则返回False
    """
    try:
        # Get token
        token = get_token()
        if not token:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('account_info.token_not_found') if translator else 'Failed to get Cursor token'}{Style.RESET_ALL}")
            return False
            
        # Get paths
        paths = get_token_from_config()
        if not paths:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('account_info.config_path_failed') if translator else 'Failed to get paths from config'}{Style.RESET_ALL}")
            return False
            
        # Get email
        email = get_email_from_storage(paths['storage_path']) or get_email_from_sqlite(paths['sqlite_path']) or "Unknown"
            
        # Get usage info
        usage_info = UsageManager.get_usage(token)
        premium_usage = "Unknown"
        max_premium_usage = "Unknown"
        basic_usage = "Unknown"
        
        if usage_info:
            premium_usage = usage_info.get('premium_usage', "Unknown")
            max_premium_usage = usage_info.get('max_premium_usage', "Unknown")
            basic_usage = usage_info.get('basic_usage', "Unknown")
            
        # Get subscription info
        subscription_info = UsageManager.get_stripe_profile(token)
        subscription_type = format_subscription_type(subscription_info)
        
        # Calculate subscription end date and remaining days
        subscription_end_date = "N/A"
        remaining_days = "N/A"
        
        # Only process if we have subscription info
        if subscription_info:
            # Check if trial or paid subscription
            if "trialEndDate" in subscription_info and subscription_info["trialEndDate"]:
                end_timestamp = subscription_info["trialEndDate"] / 1000  # convert ms to s
                import datetime
                end_date = datetime.datetime.fromtimestamp(end_timestamp)
                subscription_end_date = end_date.strftime("%Y-%m-%d")
                
                # Calculate remaining days
                now = datetime.datetime.now()
                delta = end_date - now
                remaining_days = max(0, delta.days)
                
            # Check if paid subscription
            elif "subscriptionEndDate" in subscription_info and subscription_info["subscriptionEndDate"]:
                end_timestamp = subscription_info["subscriptionEndDate"] / 1000  # convert ms to s
                import datetime
                end_date = datetime.datetime.fromtimestamp(end_timestamp)
                subscription_end_date = end_date.strftime("%Y-%m-%d")
                
                # Calculate remaining days
                now = datetime.datetime.now()
                delta = end_date - now
                remaining_days = max(0, delta.days)
        
        # Print account info
        print(f"\n{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('account_info.account_info') if translator else 'Cursor Account Information'}:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}")
        
        # Email
        print(f"{Fore.GREEN}{EMOJI['USER']} {translator.get('account_info.email') if translator else 'Email'}: {email}{Style.RESET_ALL}")
        
        # Subscription Type
        subscription_color = Fore.GREEN if subscription_type != "Free" else Fore.YELLOW
        print(f"{subscription_color}{EMOJI['SUBSCRIPTION']} {translator.get('account_info.subscription_type') if translator else 'Subscription Type'}: {subscription_type}{Style.RESET_ALL}")
        
        # Premium Usage
        usage_percentage = "N/A"
        premium_color = Fore.GREEN
        
        if isinstance(premium_usage, int) and isinstance(max_premium_usage, int) and max_premium_usage > 0:
            usage_percentage = f"{(premium_usage / max_premium_usage) * 100:.1f}%"
            
            # Change color based on usage percentage
            if premium_usage / max_premium_usage > 0.8:
                premium_color = Fore.RED
            elif premium_usage / max_premium_usage > 0.5:
                premium_color = Fore.YELLOW
        
        print(f"{premium_color}{EMOJI['PREMIUM']} {translator.get('account_info.premium_usage') if translator else 'Premium Usage (GPT-4)'}: {premium_usage} / {max_premium_usage} ({usage_percentage}){Style.RESET_ALL}")
        
        # Basic Usage
        print(f"{Fore.GREEN}{EMOJI['BASIC']} {translator.get('account_info.basic_usage') if translator else 'Basic Usage (GPT-3.5)'}: {basic_usage} / {translator.get('account_info.no_limit') if translator else 'No Limit'}{Style.RESET_ALL}")
        
        # Subscription End Date
        if subscription_end_date != "N/A":
            end_date_color = Fore.RED if isinstance(remaining_days, int) and remaining_days < 7 else Fore.GREEN
            print(f"{end_date_color}{EMOJI['TIME']} {translator.get('account_info.subscription_end') if translator else 'Subscription End Date'}: {subscription_end_date}{Style.RESET_ALL}")
            
            # Remaining Days
            print(f"{end_date_color}{EMOJI['TIME']} {translator.get('account_info.remaining_days') if translator else 'Remaining Days'}: {remaining_days}{Style.RESET_ALL}")
        
        print(f"{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}")
        
        return True
    
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('account_info.error', error=str(e)) if translator else f'Error: {str(e)}'}{Style.RESET_ALL}")
        logger.error(f"display_account_info failed: {str(e)}")
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