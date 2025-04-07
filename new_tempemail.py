"""
new_tempemail.py - 临时邮箱创建和管理模块

本模块负责创建和管理临时邮箱账号，主要功能包括：
- 使用smailpro.com创建临时邮箱
- 过滤被屏蔽的邮箱域名
- 监控收件箱接收验证码邮件
- 解析并提取验证码
- 提供邮箱自动刷新功能

临时邮箱用于Cursor注册流程中接收验证码，避免使用个人邮箱。
"""
from DrissionPage import ChromiumPage, ChromiumOptions
import time
import os
import sys
from colorama import Fore, Style, init
import requests
import random
import string
from utils import get_random_wait_time

# Initialize colorama
init()

class NewTempEmail:
    """
    临时邮箱管理类
    
    负责创建临时邮箱、检查收件箱、获取验证码等功能。
    使用无头浏览器自动化操作，支持多语言环境。
    """
    def __init__(self, translator=None):
        """
        初始化临时邮箱对象
        
        参数:
            translator: 翻译器对象，用于多语言支持，可以为None
        """
        self.translator = translator
        self.page = None
        self.setup_browser()
        
    def get_blocked_domains(self):
        """
        获取被屏蔽的域名列表
        
        从GitHub获取最新的屏蔽域名列表，如果失败则从本地加载。
        这些域名在Cursor注册时可能会被拒绝。
        
        返回值:
            list: 被屏蔽的域名列表
        """
        try:
            block_url = "https://raw.githubusercontent.com/yeongpin/cursor-free-vip/main/block_domain.txt"
            response = requests.get(block_url, timeout=5)
            if response.status_code == 200:
                # Split text and remove empty lines
                domains = [line.strip() for line in response.text.split('\n') if line.strip()]
                if self.translator:
                    print(f"{Fore.CYAN}ℹ️  {self.translator.get('email.blocked_domains_loaded', count=len(domains))}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.CYAN}ℹ️ 已加载 {len(domains)} 个被屏蔽的域名{Style.RESET_ALL}")
                return domains
            return self._load_local_blocked_domains()
        except Exception as e:
            if self.translator:
                print(f"{Fore.YELLOW}⚠️ {self.translator.get('email.blocked_domains_error', error=str(e))}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠️ 获取被屏蔽域名列表失败: {str(e)}{Style.RESET_ALL}")
            return self._load_local_blocked_domains()
            
    def _load_local_blocked_domains(self):
        """
        从本地文件加载被屏蔽的域名列表（备用方法）
        
        当从GitHub获取列表失败时使用此方法从本地文件加载。
        
        返回值:
            list: 从本地加载的被屏蔽域名列表
        """
        try:
            local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "block_domain.txt")
            if os.path.exists(local_path):
                with open(local_path, 'r', encoding='utf-8') as f:
                    domains = [line.strip() for line in f.readlines() if line.strip()]
                if self.translator:
                    print(f"{Fore.CYAN}ℹ️  {self.translator.get('email.local_blocked_domains_loaded', count=len(domains))}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.CYAN}ℹ️ 已从本地加载 {len(domains)} 个被屏蔽的域名{Style.RESET_ALL}")
                return domains
            else:
                if self.translator:
                    print(f"{Fore.YELLOW}⚠️ {self.translator.get('email.local_blocked_domains_not_found')}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}⚠️ 本地被屏蔽域名文件不存在{Style.RESET_ALL}")
                return []
        except Exception as e:
            if self.translator:
                print(f"{Fore.YELLOW}⚠️ {self.translator.get('email.local_blocked_domains_error', error=str(e))}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠️ 读取本地被屏蔽域名文件失败: {str(e)}{Style.RESET_ALL}")
            return []
    
    def exclude_blocked_domains(self, domains):
        """
        过滤掉被屏蔽的域名
        
        从域名列表中排除被屏蔽的域名，确保使用合法有效的邮箱域名。
        
        参数:
            domains (list): 域名字典列表，每个字典包含'domain'键
            
        返回值:
            list: 过滤后的域名列表
        """
        if not self.blocked_domains:
            return domains
            
        filtered_domains = []
        for domain in domains:
            if domain['domain'] not in self.blocked_domains:
                filtered_domains.append(domain)
                
        excluded_count = len(domains) - len(filtered_domains)
        if excluded_count > 0:
            if self.translator:
                print(f"{Fore.YELLOW}⚠️ {self.translator.get('email.domains_excluded', domains=excluded_count)}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠️ 已排除 {excluded_count} 个被屏蔽的域名{Style.RESET_ALL}")
                
        return filtered_domains
        
        
    def get_extension_block(self):
        """
        获取广告拦截插件路径
        
        用于加载广告拦截插件，改善临时邮箱网站使用体验。
        自动处理正常运行与打包后的路径差异。
        
        返回值:
            str: 插件文件夹路径
            
        异常:
            FileNotFoundError: 当插件文件夹不存在时抛出
        """
        root_dir = os.getcwd()
        extension_path = os.path.join(root_dir, "PBlock")
        
        if hasattr(sys, "_MEIPASS"):
            extension_path = os.path.join(sys._MEIPASS, "PBlock")

        if not os.path.exists(extension_path):
            raise FileNotFoundError(f"插件不存在: {extension_path}")

        return extension_path
        
    def setup_browser(self):
        """
        设置并启动浏览器
        
        配置Chrome浏览器选项，包括无头模式、禁用沙盒等，
        并加载广告拦截插件，准备访问临时邮箱网站。
        
        返回值:
            bool: 设置成功返回True，否则返回False
        """
        try:
            if self.translator:
                print(f"{Fore.CYAN}ℹ️ {self.translator.get('email.starting_browser')}{Style.RESET_ALL}")
            else:
                print(f"{Fore.CYAN}ℹ️ 正在启动浏览器...{Style.RESET_ALL}")
            
            # 创建浏览器选项
            co = ChromiumOptions()
            
            # Only use headless for non-OAuth operations
            if not hasattr(self, 'auth_type') or self.auth_type != 'oauth':
                co.set_argument("--headless=new")

            if sys.platform == "linux":
                # Check if DISPLAY is set when not in headless mode
                if not co.arguments.get("--headless=new") and not os.environ.get('DISPLAY'):
                    print(f"{Fore.RED}❌ {self.translator.get('email.no_display_found') if self.translator else 'No display found. Make sure X server is running.'}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}ℹ️ {self.translator.get('email.try_export_display') if self.translator else 'Try: export DISPLAY=:0'}{Style.RESET_ALL}")
                    return False
                    
                co.set_argument("--no-sandbox")
                co.set_argument("--disable-dev-shm-usage")
                co.set_argument("--disable-gpu")
                
                # If running as root, try to use actual user's Chrome profile
                if os.geteuid() == 0:
                    sudo_user = os.environ.get('SUDO_USER')
                    if sudo_user:
                        actual_home = f"/home/{sudo_user}"
                        user_data_dir = os.path.join(actual_home, ".config", "google-chrome")
                        if os.path.exists(user_data_dir):
                            print(f"{Fore.CYAN}ℹ️ {self.translator.get('email.using_chrome_profile', user_data_dir=user_data_dir) if self.translator else f'Using Chrome profile from: {user_data_dir}'}{Style.RESET_ALL}")
                            co.set_argument(f"--user-data-dir={user_data_dir}")
            
            co.auto_port()  # 自动设置端口
            
            # 加载 uBlock 插件
            try:
                extension_path = self.get_extension_block()
                co.set_argument("--allow-extensions-in-incognito")
                co.add_extension(extension_path)
            except Exception as e:
                if self.translator:
                    print(f"{Fore.YELLOW}⚠️ {self.translator.get('email.extension_load_error')}: {str(e)}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}⚠️ 加载插件失败: {str(e)}{Style.RESET_ALL}")
            
            self.page = ChromiumPage(co)
            return True
        except Exception as e:
            if self.translator:
                print(f"{Fore.RED}❌ {self.translator.get('email.browser_start_error')}: {str(e)}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}❌ 启动浏览器失败: {str(e)}{Style.RESET_ALL}")
            
            if sys.platform == "linux":
                print(f"{Fore.YELLOW}ℹ️ {self.translator.get('email.make_sure_chrome_chromium_is_properly_installed') if self.translator else 'Make sure Chrome/Chromium is properly installed'}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}ℹ️ {self.translator.get('email.try_install_chromium') if self.translator else 'Try: sudo apt install chromium-browser'}{Style.RESET_ALL}")
            return False
            
    def create_email(self):
        """
        创建新的临时邮箱
        
        访问smailpro.com网站，获取临时邮箱地址，筛选出未被屏蔽的域名。
        会自动选择随机域名，确保邮箱可用于Cursor注册流程。
        
        返回值:
            str: 创建成功返回邮箱地址，失败返回None
        """
        try:
            # Load blocked domains
            self.blocked_domains = self.get_blocked_domains()
            
            if not self.page:
                if not self.setup_browser():
                    return None
            
            # Navigate to smailpro.com
            if self.translator:
                print(f"{Fore.CYAN}ℹ️ {self.translator.get('email.navigating')}{Style.RESET_ALL}")
            else:
                print(f"{Fore.CYAN}ℹ️ 正在访问临时邮箱网站...{Style.RESET_ALL}")
                
            self.page.get("https://smailpro.com/advanced")
            time.sleep(get_random_wait_time(1, 3))
            
            # Get available domains
            try:
                domain_elements = self.page.eles_xpath("//select[@id='form_domain']/option")
                domains = []
                
                if not domain_elements:
                    if self.translator:
                        print(f"{Fore.RED}❌ {self.translator.get('email.no_domains_found')}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}❌ 未找到可用域名{Style.RESET_ALL}")
                    return None
                    
                for element in domain_elements:
                    domain_value = element.attr('value')
                    if domain_value:
                        domains.append({"domain": domain_value, "element": element})
                
                # Filter out blocked domains
                filtered_domains = self.exclude_blocked_domains(domains)
                
                if not filtered_domains:
                    if self.translator:
                        print(f"{Fore.RED}❌ {self.translator.get('email.all_domains_blocked')}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}❌ 所有域名都被屏蔽{Style.RESET_ALL}")
                    return None
                    
                # Choose a random domain
                selected_domain = random.choice(filtered_domains)
                
                # Generate random username part
                username_length = random.randint(8, 12)
                username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=username_length))
                
                # Set username in the input field
                email_input = self.page.ele_xpath("//input[@id='form_username']")
                email_input.value = username
                
                # Select the domain
                domain_select = self.page.ele_xpath("//select[@id='form_domain']")
                domain_select.select(value=selected_domain['domain'])
                
                # Click create button
                create_button = self.page.ele_xpath("//button[@id='generate_button']")
                create_button.click()
                
                time.sleep(get_random_wait_time(1, 2))
                
                email_address = f"{username}@{selected_domain['domain']}"
                
                if self.translator:
                    print(f"{Fore.GREEN}✅ {self.translator.get('email.created', email=email_address)}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.GREEN}✅ 成功创建临时邮箱: {email_address}{Style.RESET_ALL}")
                    
                return email_address
                
            except Exception as e:
                if self.translator:
                    print(f"{Fore.RED}❌ {self.translator.get('email.error_getting_domains', error=str(e))}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}❌ 获取域名时发生错误: {str(e)}{Style.RESET_ALL}")
                return None
                
        except Exception as e:
            if self.translator:
                print(f"{Fore.RED}❌ {self.translator.get('email.create_failed', error=str(e))}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}❌ 创建临时邮箱失败: {str(e)}{Style.RESET_ALL}")
            return None
            
    def close(self):
        """
        关闭浏览器
        
        释放浏览器资源，在使用完临时邮箱后调用，
        确保系统资源被正确释放。
        """
        if self.page:
            self.page.quit()
            self.page = None
            
    def refresh_inbox(self):
        """
        刷新邮箱收件箱
        
        点击刷新按钮更新邮箱收件箱，获取最新邮件。
        在等待验证码邮件时使用，会自动处理可能出现的错误。
        
        返回值:
            bool: 刷新成功返回True，失败返回False
        """
        try:
            if not self.page:
                if self.translator:
                    print(f"{Fore.RED}❌ {self.translator.get('email.browser_not_initialized')}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}❌ 浏览器未初始化{Style.RESET_ALL}")
                return False
                
            # Find and click refresh button
            try:
                refresh_button = self.page.ele_xpath("//div[contains(@class, 'refresh-button')]")
                if refresh_button:
                    refresh_button.click()
                    time.sleep(get_random_wait_time(1, 2))
                    if self.translator:
                        print(f"{Fore.CYAN}ℹ️ {self.translator.get('email.inbox_refreshed')}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.CYAN}ℹ️ 已刷新收件箱{Style.RESET_ALL}")
                    return True
                else:
                    # Try alternative refresh methods
                    self.page.get("https://smailpro.com/advanced")
                    time.sleep(get_random_wait_time(1, 2))
                    if self.translator:
                        print(f"{Fore.CYAN}ℹ️ {self.translator.get('email.page_reloaded')}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.CYAN}ℹ️ 已重新加载页面{Style.RESET_ALL}")
                    return True
            except Exception as e:
                if self.translator:
                    print(f"{Fore.YELLOW}⚠️ {self.translator.get('email.refresh_error', error=str(e))}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}⚠️ 刷新时出错: {str(e)}{Style.RESET_ALL}")
                return False
                
        except Exception as e:
            if self.translator:
                print(f"{Fore.RED}❌ {self.translator.get('email.refresh_failed', error=str(e))}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}❌ 刷新收件箱失败: {str(e)}{Style.RESET_ALL}")
            return False
            
    def check_for_cursor_email(self):
        """
        检查是否收到Cursor验证邮件
        
        在收件箱中查找来自Cursor的验证码邮件，
        如果找到则点击打开该邮件。
        
        返回值:
            bool: 找到并打开邮件返回True，未找到返回False
        """
        try:
            if not self.page:
                if self.translator:
                    print(f"{Fore.RED}❌ {self.translator.get('email.browser_not_initialized')}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}❌ 浏览器未初始化{Style.RESET_ALL}")
                return False
                
            # Look for email from Cursor
            try:
                # Check for emails in the list
                email_elements = self.page.eles_xpath("//div[contains(@class, 'inbox-list')]//div[contains(@class, 'inbox-list-item')]")
                
                if not email_elements:
                    if self.translator:
                        print(f"{Fore.YELLOW}⚠️ {self.translator.get('email.no_emails')}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.YELLOW}⚠️ 收件箱中没有邮件{Style.RESET_ALL}")
                    return False
                    
                for email in email_elements:
                    # Check sender
                    sender_text = email.text
                    if "cursor" in sender_text.lower() or "verification" in sender_text.lower():
                        email.click()
                        time.sleep(get_random_wait_time(1, 2))
                        if self.translator:
                            print(f"{Fore.GREEN}✅ {self.translator.get('email.cursor_email_found')}{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.GREEN}✅ 找到Cursor验证邮件{Style.RESET_ALL}")
                        return True
                        
                if self.translator:
                    print(f"{Fore.YELLOW}⚠️ {self.translator.get('email.no_cursor_email')}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}⚠️ 未找到Cursor验证邮件{Style.RESET_ALL}")
                return False
                
            except Exception as e:
                if self.translator:
                    print(f"{Fore.YELLOW}⚠️ {self.translator.get('email.check_error', error=str(e))}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}⚠️ 检查邮件时出错: {str(e)}{Style.RESET_ALL}")
                return False
                
        except Exception as e:
            if self.translator:
                print(f"{Fore.RED}❌ {self.translator.get('email.check_failed', error=str(e))}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}❌ 检查Cursor验证邮件失败: {str(e)}{Style.RESET_ALL}")
            return False
            
    def get_verification_code(self):
        """
        提取邮件中的验证码
        
        从已打开的Cursor验证邮件中提取数字验证码，
        使用正则表达式或查找特定元素获取。
        
        返回值:
            str: 成功时返回验证码，失败返回None
        """
        try:
            if not self.page:
                if self.translator:
                    print(f"{Fore.RED}❌ {self.translator.get('email.browser_not_initialized')}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}❌ 浏览器未初始化{Style.RESET_ALL}")
                return None
                
            # Extract verification code from email
            try:
                # Wait for the email content to load
                time.sleep(get_random_wait_time(1, 2))
                
                # Try different methods to extract the code
                # Method 1: Look for specific elements with the code
                code_elements = self.page.eles_xpath("//div[contains(@class, 'mail-content')]//div[contains(text(), 'Code:') or contains(text(), 'code') or contains(text(), 'verification')]")
                
                for element in code_elements:
                    text = element.text
                    # Usually the code is a 6-digit number
                    import re
                    matches = re.findall(r'\b\d{6}\b', text)
                    if matches:
                        code = matches[0]
                        if self.translator:
                            print(f"{Fore.GREEN}✅ {self.translator.get('email.verification_code_found', code=code)}{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.GREEN}✅ 找到验证码: {code}{Style.RESET_ALL}")
                        return code
                
                # Method 2: Get the email content and look for the code
                email_content = self.page.ele_xpath("//div[contains(@class, 'mail-content')]").text
                matches = re.findall(r'\b\d{6}\b', email_content)
                if matches:
                    code = matches[0]
                    if self.translator:
                        print(f"{Fore.GREEN}✅ {self.translator.get('email.verification_code_found', code=code)}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.GREEN}✅ 找到验证码: {code}{Style.RESET_ALL}")
                    return code
                    
                if self.translator:
                    print(f"{Fore.YELLOW}⚠️ {self.translator.get('email.no_verification_code')}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}⚠️ 未找到验证码{Style.RESET_ALL}")
                return None
                
            except Exception as e:
                if self.translator:
                    print(f"{Fore.YELLOW}⚠️ {self.translator.get('email.extract_error', error=str(e))}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}⚠️ 提取验证码时出错: {str(e)}{Style.RESET_ALL}")
                return None
                
        except Exception as e:
            if self.translator:
                print(f"{Fore.RED}❌ {self.translator.get('email.extract_failed', error=str(e))}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}❌ 提取验证码失败: {str(e)}{Style.RESET_ALL}")
            return None

def main(translator=None):
    """
    临时邮箱模块主函数
    
    当脚本直接运行时调用，演示创建临时邮箱并等待验证邮件的完整流程。
    提供测试和用法示例。
    
    参数:
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        bool: 操作成功返回True，失败返回False
    """
    # Create a translator if needed
    if not translator:
        try:
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from utils import Translator
            translator = Translator()
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ 无法加载翻译器: {str(e)}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}⚠️ 将使用默认中文提示{Style.RESET_ALL}")
            
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}📧 {translator.get('email.title') if translator else '临时邮箱生成器'}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    
    email_manager = NewTempEmail(translator)
    try:
        # Create a new email
        email_address = email_manager.create_email()
        if not email_address:
            print(f"{Fore.RED}❌ {translator.get('email.failed_to_create') if translator else '无法创建临时邮箱'}{Style.RESET_ALL}")
            return False
            
        # Wait for verification email (for demo)
        print(f"{Fore.CYAN}ℹ️ {translator.get('email.waiting_for_email') if translator else '等待验证邮件(测试模式)...'}{Style.RESET_ALL}")
        
        # In a real scenario, you would loop checking for emails
        # Here we'll just wait a bit and then exit for the demo
        time.sleep(5)
        email_manager.refresh_inbox()
        
        print(f"\n{Fore.GREEN}✅ {translator.get('email.demo_completed') if translator else '临时邮箱创建演示完成'}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}ℹ️ {translator.get('email.press_enter') if translator else '按Enter键继续...'}{Style.RESET_ALL}")
        input()
        
        return True
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠️ {translator.get('email.interrupted') if translator else '操作被用户中断'}{Style.RESET_ALL}")
        return False
        
    except Exception as e:
        print(f"{Fore.RED}❌ {translator.get('email.error', error=str(e)) if translator else f'发生错误: {str(e)}'}{Style.RESET_ALL}")
        return False
        
    finally:
        # Always close the browser
        email_manager.close()
        
if __name__ == "__main__":
    main() 