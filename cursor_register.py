"""
cursor_register.py - Cursor账号注册流程控制模块

这个模块负责Cursor注册流程的整体控制，主要功能包括：
- 创建临时邮箱
- 使用随机生成的个人信息注册账号
- 获取并保存访问令牌
- 更新Cursor登录状态
- 重置机器ID

通过整合各个子模块的功能，实现全自动化的Cursor账号注册和激活过程。
"""
import os
from colorama import Fore, Style, init
import time
import random
from cursor_auth import CursorAuth
from reset_machine_manual import MachineIDResetter

os.environ["PYTHONVERBOSE"] = "0"
os.environ["PYINSTALLER_VERBOSE"] = "0"

# Initialize colorama
init()

# Define emoji constants
EMOJI = {
    'START': '🚀',
    'FORM': '📝',
    'VERIFY': '🔄',
    'PASSWORD': '🔑',
    'CODE': '📱',
    'DONE': '✨',
    'ERROR': '❌',
    'WAIT': '⏳',
    'SUCCESS': '✅',
    'MAIL': '📧',
    'KEY': '🔐',
    'UPDATE': '🔄',
    'INFO': 'ℹ️'
}

class CursorRegistration:
    """
    Cursor注册流程管理类
    
    负责协调整个注册流程，包括生成随机账号信息、
    创建临时邮箱、注册账号、处理验证码、获取令牌等步骤。
    """
    def __init__(self, translator=None):
        """
        初始化注册流程管理器
        
        生成随机的个人信息（姓名、密码等），并准备注册环境。
        
        参数:
            translator: 翻译器对象，用于多语言支持，可以为None
        """
        # 保存翻译器对象，用于多语言支持
        self.translator = translator
        # 设置浏览器为显示模式（非无头模式）
        os.environ['BROWSER_HEADLESS'] = 'False'
        # 初始化浏览器对象为None
        self.browser = None
        # 初始化控制器对象为None
        self.controller = None
        # 设置临时邮箱网站URL
        self.mail_url = "https://yopmail.com/zh/email-generator"
        # 设置Cursor注册页面URL
        self.sign_up_url = "https://authenticator.cursor.sh/sign-up"
        # 设置Cursor设置页面URL
        self.settings_url = "https://www.cursor.com/settings"
        # 初始化邮箱地址为None
        self.email_address = None
        # 初始化注册页面标签为None
        self.signup_tab = None
        # 初始化邮箱页面标签为None
        self.email_tab = None
        
        # 生成随机密码
        self.password = self._generate_password()
        # 从预设列表中随机选择一个名字
        first_name = random.choice([
            "James", "John", "Robert", "Michael", "William", "David", "Joseph", "Thomas",
            "Emma", "Olivia", "Ava", "Isabella", "Sophia", "Mia", "Charlotte", "Amelia",
            "Liam", "Noah", "Oliver", "Elijah", "Lucas", "Mason", "Logan", "Alexander"
        ])
        # 从预设列表中随机选择一个姓氏
        self.last_name = random.choice([
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
            "Anderson", "Wilson", "Taylor", "Thomas", "Moore", "Martin", "Jackson", "Lee",
            "Thompson", "White", "Harris", "Clark", "Lewis", "Walker", "Hall", "Young"
        ])
        
        # 修改名字的首字母，增加随机性
        new_first_letter = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        self.first_name = new_first_letter + first_name[1:]
        
        # 打印生成的密码信息
        print(f"\n{Fore.CYAN}{EMOJI['PASSWORD']} {self.translator.get('register.password')}: {self.password} {Style.RESET_ALL}")
        # 打印生成的名字信息
        print(f"{Fore.CYAN}{EMOJI['FORM']} {self.translator.get('register.first_name')}: {self.first_name} {Style.RESET_ALL}")
        # 打印生成的姓氏信息
        print(f"{Fore.CYAN}{EMOJI['FORM']} {self.translator.get('register.last_name')}: {self.last_name} {Style.RESET_ALL}")

    def _generate_password(self, length=12):
        """
        生成随机密码
        
        创建一个包含字母、数字和特殊字符的随机密码。
        
        参数:
            length (int): 密码长度，默认为12
            
        返回值:
            str: 生成的随机密码
        """
        # 定义密码可能包含的字符集
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
        # 从字符集中随机选择指定长度的字符，并拼接成密码
        return ''.join(random.choices(chars, k=length))

    def setup_email(self):
        """
        设置临时邮箱
        
        创建一个临时邮箱地址用于注册，并准备接收验证邮件。
        
        返回值:
            bool: 设置成功返回True，否则返回False
        """
        try:
            # 打印开始设置临时邮箱的信息
            print(f"{Fore.CYAN}{EMOJI['START']} {self.translator.get('register.browser_start')}...{Style.RESET_ALL}")
            
            # 导入临时邮箱模块
            from new_tempemail import NewTempEmail
            # 创建临时邮箱对象，传入翻译器
            self.temp_email = NewTempEmail(self.translator)
            
            # 创建临时邮箱地址
            email_address = self.temp_email.create_email()
            # 如果创建失败，打印错误信息并返回False
            if not email_address:
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.email_create_failed')}{Style.RESET_ALL}")
                return False
            
            # 保存创建的邮箱地址
            self.email_address = email_address
            # 保存临时邮箱对象实例
            self.email_tab = self.temp_email
            
            return True
            
        except Exception as e:
            # 捕获异常，打印错误信息
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.email_setup_failed', error=str(e))}{Style.RESET_ALL}")
            return False

    def register_cursor(self):
        """
        注册Cursor账号
        
        使用准备好的个人信息和临时邮箱注册Cursor账号。
        该过程涉及填写注册表单、处理验证码和设置密码。
        
        返回值:
            bool: 注册成功返回True，否则返回False
        """
        browser_tab = None
        try:
            # 打印开始注册的信息
            print(f"{Fore.CYAN}{EMOJI['START']} {self.translator.get('register.register_start')}...{Style.RESET_ALL}")
            
            # 导入注册模块
            from new_signup import main as new_signup_main
            
            # 执行注册流程，传入所有必要参数
            result, browser_tab = new_signup_main(
                email=self.email_address,          # 邮箱地址
                password=self.password,            # 密码
                first_name=self.first_name,        # 名字
                last_name=self.last_name,          # 姓氏
                email_tab=self.email_tab,          # 邮箱标签页
                controller=self.controller,        # 控制器
                translator=self.translator         # 翻译器
            )
            
            # 如果注册成功
            if result:
                # 保存浏览器实例
                self.signup_tab = browser_tab
                # 获取账号信息
                success = self._get_account_info()
                
                # 获取信息后关闭浏览器
                if browser_tab:
                    try:
                        browser_tab.quit()
                    except:
                        pass
                
                return success
            
            return False
            
        except Exception as e:
            # 捕获异常，打印错误信息
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.register_process_error', error=str(e))}{Style.RESET_ALL}")
            return False
        finally:
            # 确保在任何情况下浏览器都会被关闭
            if browser_tab:
                try:
                    browser_tab.quit()
                except:
                    pass
                
    def _get_account_info(self):
        """
        获取账号信息和访问令牌
        
        在注册成功后，从设置页面获取账号的使用量信息和访问令牌。
        
        返回值:
            bool: 获取成功返回True，否则返回False
        """
        try:
            # 导航到设置页面
            self.signup_tab.get(self.settings_url)
            # 等待页面加载
            time.sleep(2)
            
            # 定义使用量信息的CSS选择器
            usage_selector = (
                "css:div.col-span-2 > div > div > div > div > "
                "div:nth-child(1) > div.flex.items-center.justify-between.gap-2 > "
                "span.font-mono.text-sm\\/\\[0\\.875rem\\]"
            )
            # 查找使用量元素
            usage_ele = self.signup_tab.ele(usage_selector)
            # 默认使用量为"未知"
            total_usage = "未知"
            # 如果找到使用量元素，提取使用量信息
            if usage_ele:
                total_usage = usage_ele.text.split("/")[-1].strip()

            # 打印使用量信息
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('register.total_usage', usage=total_usage)}{Style.RESET_ALL}")
            # 打印开始获取令牌的信息
            print(f"{Fore.CYAN}{EMOJI['WAIT']} {self.translator.get('register.get_token')}...{Style.RESET_ALL}")
            # 设置最大尝试次数
            max_attempts = 30
            # 设置重试间隔（秒）
            retry_interval = 2
            # 初始化尝试次数
            attempts = 0

            # 循环尝试获取令牌
            while attempts < max_attempts:
                try:
                    # 获取所有cookies
                    cookies = self.signup_tab.cookies()
                    # 遍历cookies寻找会话令牌
                    for cookie in cookies:
                        if cookie.get("name") == "WorkosCursorSessionToken":
                            # 提取令牌值
                            token = cookie["value"].split("%3A%3A")[1]
                            # 打印获取令牌成功的信息
                            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('register.token_success')}{Style.RESET_ALL}")
                            # 保存账号信息
                            self._save_account_info(token, total_usage)
                            return True

                    # 增加尝试次数
                    attempts += 1
                    # 如果未达到最大尝试次数，等待后重试
                    if attempts < max_attempts:
                        print(f"{Fore.YELLOW}{EMOJI['WAIT']} {self.translator.get('register.token_attempt', attempt=attempts, time=retry_interval)}{Style.RESET_ALL}")
                        time.sleep(retry_interval)
                    else:
                        # 达到最大尝试次数，打印失败信息
                        print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.token_max_attempts', max=max_attempts)}{Style.RESET_ALL}")

                except Exception as e:
                    # 捕获异常，打印错误信息
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.token_failed', error=str(e))}{Style.RESET_ALL}")
                    # 增加尝试次数
                    attempts += 1
                    # 如果未达到最大尝试次数，等待后重试
                    if attempts < max_attempts:
                        print(f"{Fore.YELLOW}{EMOJI['WAIT']} {self.translator.get('register.token_attempt', attempt=attempts, time=retry_interval)}{Style.RESET_ALL}")
                        time.sleep(retry_interval)

            return False

        except Exception as e:
            # 捕获异常，打印错误信息
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.account_error', error=str(e))}{Style.RESET_ALL}")
            return False

    def _save_account_info(self, token, total_usage):
        """
        保存账号信息
        
        将注册成功的账号信息（邮箱、密码、令牌等）保存到文件，
        同时更新Cursor认证信息和重置机器ID。
        
        参数:
            token (str): 账号访问令牌
            total_usage (str): 账号使用量限制
            
        返回值:
            bool: 保存成功返回True，否则返回False
        """
        try:
            # 打印开始更新认证信息的消息
            print(f"{Fore.CYAN}{EMOJI['KEY']} {self.translator.get('register.update_cursor_auth_info')}...{Style.RESET_ALL}")
            # 更新Cursor认证信息
            if self.update_cursor_auth(email=self.email_address, access_token=token, refresh_token=token):
                # 更新成功，打印成功信息
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('register.cursor_auth_info_updated')}...{Style.RESET_ALL}")
            else:
                # 更新失败，打印失败信息
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.cursor_auth_info_update_failed')}...{Style.RESET_ALL}")

            # 打印开始重置机器ID的信息
            print(f"{Fore.CYAN}{EMOJI['UPDATE']} {self.translator.get('register.reset_machine_id')}...{Style.RESET_ALL}")
            # 创建机器ID重置器，传入翻译器
            resetter = MachineIDResetter(self.translator)
            # 执行机器ID重置
            if not resetter.reset_machine_ids():
                # 重置失败，抛出异常
                raise Exception("Failed to reset machine ID")
            
            # 将账号信息保存到文件
            with open('cursor_accounts.txt', 'a', encoding='utf-8') as f:
                # 写入分隔线
                f.write(f"\n{'='*50}\n")
                # 写入邮箱信息
                f.write(f"Email: {self.email_address}\n")
                # 写入密码信息
                f.write(f"Password: {self.password}\n")
                # 写入令牌信息
                f.write(f"Token: {token}\n")
                # 写入使用量限制信息
                f.write(f"Usage Limit: {total_usage}\n")
                # 写入分隔线
                f.write(f"{'='*50}\n")
                
            # 打印保存成功的信息
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('register.account_info_saved')}...{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            # 捕获异常，打印错误信息
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.save_account_info_failed', error=str(e))}{Style.RESET_ALL}")
            return False

    def start(self):
        """
        启动注册流程
        
        协调执行整个注册流程，包括邮箱设置、账号注册等步骤。
        
        返回值:
            bool: 注册流程成功返回True，否则返回False
        """
        try:
            # 设置临时邮箱
            if self.setup_email():
                # 如果邮箱设置成功，进行Cursor注册
                if self.register_cursor():
                    # 注册成功，打印完成信息
                    print(f"\n{Fore.GREEN}{EMOJI['DONE']} {self.translator.get('register.cursor_registration_completed')}...{Style.RESET_ALL}")
                    return True
            return False
        finally:
            # 确保在任何情况下都关闭临时邮箱标签页
            if hasattr(self, 'temp_email'):
                try:
                    self.temp_email.close()
                except:
                    pass

    def update_cursor_auth(self, email=None, access_token=None, refresh_token=None):
        """
        更新Cursor认证信息
        
        调用CursorAuth模块更新本地的Cursor认证信息，
        使Cursor应用程序能够识别为已登录的Pro账号。
        
        参数:
            email (str, optional): 邮箱地址
            access_token (str, optional): 访问令牌
            refresh_token (str, optional): 刷新令牌
            
        返回值:
            bool: 更新成功返回True，否则返回False
        """
        # 创建认证管理器，传入翻译器
        auth_manager = CursorAuth(translator=self.translator)
        # 调用更新认证方法，传入邮箱和令牌信息
        return auth_manager.update_auth(email, access_token, refresh_token)

def main(translator=None):
    """
    主函数
    
    创建并启动Cursor注册流程。
    
    参数:
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        bool: 注册成功返回True，否则返回False
    """
    cursor_registration = CursorRegistration(translator)
    return cursor_registration.start()

if __name__ == "__main__":
    main() 