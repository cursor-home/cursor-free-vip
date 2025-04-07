"""
cursor_register_manual.py - Cursor手动注册模块

本模块提供了通过手动输入邮箱和验证码来注册Cursor账号的功能，主要功能包括：
- 生成随机用户信息（姓名、密码）
- 引导用户手动输入邮箱地址
- 引导用户手动输入验证码
- 完成注册流程并获取访问令牌
- 保存账号信息到本地配置

此模块适用于需要使用自己的真实邮箱注册Cursor账号的用户，
与其他自动化注册模块相比，更加灵活且支持各类邮箱服务。
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
    Cursor手动注册类
    
    负责处理Cursor账号的手动注册流程，包括：
    - 生成随机账号信息
    - 处理邮箱输入和验证
    - 完成账号注册
    - 获取和保存访问令牌
    
    通过此类，用户可以使用自己的真实邮箱完成Cursor账号注册。
    """
    def __init__(self, translator=None):
        """
        初始化手动注册对象
        
        设置基本注册参数，生成随机用户信息，
        并打印生成的用户信息供用户参考。
        
        参数:
            translator: 翻译器对象，用于多语言支持，可以为None
        """
        self.translator = translator
        # Set to display mode
        os.environ['BROWSER_HEADLESS'] = 'False'
        self.browser = None
        self.controller = None
        self.sign_up_url = "https://authenticator.cursor.sh/sign-up"
        self.settings_url = "https://www.cursor.com/settings"
        self.email_address = None
        self.signup_tab = None
        self.email_tab = None
        
        # Generate account information
        self.password = self._generate_password()
        # Generate first name and last name separately
        first_name = random.choice([
            "James", "John", "Robert", "Michael", "William", "David", "Joseph", "Thomas",
            "Emma", "Olivia", "Ava", "Isabella", "Sophia", "Mia", "Charlotte", "Amelia",
            "Liam", "Noah", "Oliver", "Elijah", "Lucas", "Mason", "Logan", "Alexander"
        ])
        self.last_name = random.choice([
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
            "Anderson", "Wilson", "Taylor", "Thomas", "Moore", "Martin", "Jackson", "Lee",
            "Thompson", "White", "Harris", "Clark", "Lewis", "Walker", "Hall", "Young"
        ])
        
        # Modify first letter of first name
        new_first_letter = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        self.first_name = new_first_letter + first_name[1:]
        
        print(f"\n{Fore.CYAN}{EMOJI['PASSWORD']} {self.translator.get('register.password')}: {self.password} {Style.RESET_ALL}")
        print(f"{Fore.CYAN}{EMOJI['FORM']} {self.translator.get('register.first_name')}: {self.first_name} {Style.RESET_ALL}")
        print(f"{Fore.CYAN}{EMOJI['FORM']} {self.translator.get('register.last_name')}: {self.last_name} {Style.RESET_ALL}")

    def _generate_password(self, length=12):
        """
        生成随机密码
        
        创建一个包含字母、数字和特殊字符的随机密码，
        用于注册新的Cursor账号。
        
        参数:
            length: 密码长度，默认为12位
            
        返回值:
            str: 生成的随机密码
        """
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
        return ''.join(random.choices(chars, k=length))

    def setup_email(self):
        """
        设置邮箱地址
        
        引导用户手动输入邮箱地址，并进行简单的格式验证。
        用户需要提供一个可以接收验证码的有效邮箱。
        
        返回值:
            bool: 设置成功返回True，失败返回False
        """
        try:
            print(f"{Fore.CYAN}{EMOJI['START']} {self.translator.get('register.manual_email_input') if self.translator else '请输入您的邮箱地址:'}")
            self.email_address = input().strip()
            
            if '@' not in self.email_address:
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.invalid_email') if self.translator else '无效的邮箱地址'}{Style.RESET_ALL}")
                return False
                
            print(f"{Fore.CYAN}{EMOJI['MAIL']} {self.translator.get('register.email_address')}: {self.email_address}\n{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.email_setup_failed', error=str(e))}{Style.RESET_ALL}")
            return False

    def get_verification_code(self):
        """
        手动获取验证码
        
        引导用户从邮箱中获取验证码并手动输入。
        验证码通常是6位数字，由Cursor发送到用户提供的邮箱。
        
        返回值:
            str: 用户输入的验证码，输入无效则返回None
        """
        try:
            print(f"{Fore.CYAN}{EMOJI['CODE']} {self.translator.get('register.manual_code_input') if self.translator else '请输入验证码:'}")
            code = input().strip()
            
            if not code.isdigit() or len(code) != 6:
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.invalid_code') if self.translator else '无效的验证码'}{Style.RESET_ALL}")
                return None
                
            return code
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.code_input_failed', error=str(e))}{Style.RESET_ALL}")
            return None

    def register_cursor(self):
        """
        注册Cursor账号
        
        启动浏览器并执行完整的注册流程，包括填写注册表单、
        处理验证码、完成密码设置等步骤。使用new_signup.py
        模块实现主要注册逻辑。
        
        返回值:
            bool: 注册成功返回True，失败返回False
        """
        browser_tab = None
        try:
            print(f"{Fore.CYAN}{EMOJI['START']} {self.translator.get('register.register_start')}...{Style.RESET_ALL}")
            
            # Use new_signup.py directly for registration
            from new_signup import main as new_signup_main
            
            # Execute new registration process, passing translator
            result, browser_tab = new_signup_main(
                email=self.email_address,
                password=self.password,
                first_name=self.first_name,
                last_name=self.last_name,
                email_tab=None,  # No email tab needed
                controller=self,  # Pass self instead of self.controller
                translator=self.translator
            )
            
            if result:
                # Use the returned browser instance to get account information
                self.signup_tab = browser_tab  # Save browser instance
                success = self._get_account_info()
                
                # Close browser after getting information
                if browser_tab:
                    try:
                        browser_tab.quit()
                    except:
                        pass
                
                return success
            
            return False
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.register_process_error', error=str(e))}{Style.RESET_ALL}")
            return False
        finally:
            # Ensure browser is closed in any case
            if browser_tab:
                try:
                    browser_tab.quit()
                except:
                    pass
                
    def _get_account_info(self):
        """
        获取账号信息和访问令牌
        
        在注册完成后，访问设置页面并提取访问令牌、
        使用配额等账号信息，以便后续使用。
        
        返回值:
            bool: 获取成功返回True，失败返回False
        """
        try:
            self.signup_tab.get(self.settings_url)
            time.sleep(2)
            
            usage_selector = (
                "css:div.col-span-2 > div > div > div > div > "
                "div:nth-child(1) > div.flex.items-center.justify-between.gap-2 > "
                "span.font-mono.text-sm\\/\\[0\\.875rem\\]"
            )
            usage_ele = self.signup_tab.ele(usage_selector)
            total_usage = "未知"
            if usage_ele:
                total_usage = usage_ele.text.split("/")[-1].strip()

            print(f"Total Usage: {total_usage}\n")
            print(f"{Fore.CYAN}{EMOJI['WAIT']} {self.translator.get('register.get_token')}...{Style.RESET_ALL}")
            max_attempts = 30
            retry_interval = 2
            attempts = 0

            while attempts < max_attempts:
                try:
                    cookies = self.signup_tab.cookies()
                    for cookie in cookies:
                        if cookie.get("name") == "WorkosCursorSessionToken":
                            token = cookie["value"].split("%3A%3A")[1]
                            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('register.token_success')}{Style.RESET_ALL}")
                            self._save_account_info(token, total_usage)
                            return True

                    attempts += 1
                    if attempts < max_attempts:
                        print(f"{Fore.YELLOW}{EMOJI['WAIT']} {self.translator.get('register.token_attempt', attempt=attempts, time=retry_interval)}{Style.RESET_ALL}")
                        time.sleep(retry_interval)
                    else:
                        print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.token_max_attempts', max=max_attempts)}{Style.RESET_ALL}")

                except Exception as e:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.token_failed', error=str(e))}{Style.RESET_ALL}")
                    attempts += 1
                    if attempts < max_attempts:
                        print(f"{Fore.YELLOW}{EMOJI['WAIT']} {self.translator.get('register.token_attempt', attempt=attempts, time=retry_interval)}{Style.RESET_ALL}")
                        time.sleep(retry_interval)

            return False

        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.account_error', error=str(e))}{Style.RESET_ALL}")
            return False

    def _save_account_info(self, token, total_usage):
        """
        保存账号信息到本地
        
        将获取到的访问令牌、邮箱地址和使用配额等信息
        保存到本地，并更新Cursor认证信息。
        
        参数:
            token: 访问令牌
            total_usage: 账号总使用量
        """
        try:
            print(f"{Fore.CYAN}{EMOJI['KEY']} {self.translator.get('register.saving_account_info') if self.translator else '正在保存账号信息...'}{Style.RESET_ALL}")
            
            print(f"\n{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('register.account_details')}:{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'─' * 50}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Email: {self.email_address}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Password: {self.password}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Token: {token}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Total Usage: {total_usage}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'─' * 50}{Style.RESET_ALL}")
            
            # Update token in auth
            self.update_cursor_auth(self.email_address, token)
            
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('register.account_saved') if self.translator else '账号信息已保存'}{Style.RESET_ALL}")
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.save_failed', error=str(e)) if self.translator else f'保存账号信息失败: {e}'}{Style.RESET_ALL}")

    def start(self):
        """
        启动注册流程
        
        执行完整的手动注册流程，包括邮箱设置、
        账号注册以及保存账号信息等所有步骤。
        
        返回值:
            bool: 注册成功返回True，失败返回False
        """
        try:
            # First setup email
            if not self.setup_email():
                return False
                
            # Register Cursor account
            if not self.register_cursor():
                return False
                
            return True
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('register.registration_failed', error=str(e)) if self.translator else f'注册过程失败: {e}'}{Style.RESET_ALL}")
            return False

    def update_cursor_auth(self, email=None, access_token=None, refresh_token=None):
        """
        更新Cursor认证信息
        
        将新注册的账号信息更新到Cursor认证系统中，
        使应用程序可以使用这些凭证进行身份验证。
        
        参数:
            email: 电子邮箱地址
            access_token: 访问令牌
            refresh_token: 刷新令牌，可选
        """
        auth = CursorAuth()
        auth.update_auth_info(email=email, access_token=access_token, refresh_token=refresh_token)

def main(translator=None):
    """
    执行手动注册的主函数
    
    创建CursorRegistration实例并执行注册流程。
    作为模块的主入口点，可以从其他脚本调用。
    
    参数:
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        bool: 注册操作成功返回True，失败返回False
    """
    print(f"\n{Fore.CYAN}{EMOJI['START']} {translator.get('register.manual_title') if translator else 'Cursor 手动注册'}{Style.RESET_ALL}")
    
    # Create registration instance
    registration = CursorRegistration(translator)
    
    # Start registration process
    result = registration.start()
    
    if result:
        print(f"\n{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('register.manual_success') if translator else 'Cursor账号已成功注册！'}{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.RED}{EMOJI['ERROR']} {translator.get('register.manual_failed') if translator else 'Cursor账号注册失败'}{Style.RESET_ALL}")
    
    return result

if __name__ == "__main__":
    main() 