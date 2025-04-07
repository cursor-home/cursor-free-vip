"""
GitHub Cursor 注册工具

该模块提供了一个自动化的流程，用于通过GitHub OAuth认证注册Cursor账号。
该工具会自动完成以下步骤：
1. 创建临时邮箱
2. 注册新的GitHub账号
3. 验证GitHub邮箱
4. 使用GitHub账号注册登录Cursor
5. 重置机器ID（避免使用限制）
6. 保存认证信息

使用方法：
    python github_cursor_register.py

注意: 该过程可能需要人工干预来完成验证码验证。
"""

import os
import time
import uuid
import json
import random
import string
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import logging
import platform
from colorama import Fore, Style, init
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
import shutil

# Initialize colorama
init()

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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
    'INFO': 'ℹ️',
    'EMAIL': '📧',
    'REFRESH': '🔄',
    'LINK': '🔗',
    'WARNING': '⚠️'
}

class GitHubCursorRegistration:
    """
    GitHub Cursor注册类
    
    该类提供了一系列方法，用于自动化完成GitHub账号创建和Cursor注册过程。
    包括临时邮箱创建、GitHub账号注册、邮箱验证、Cursor账号注册和机器ID重置等功能。
    
    属性:
        translator: 国际化翻译器实例
        browser: 浏览器WebDriver实例
        email_address: 临时邮箱地址
        github_username: 随机生成的GitHub用户名
        github_password: 随机生成的GitHub密码
    """
    def __init__(self, translator=None):
        """
        初始化GitHub Cursor注册类
        
        设置基本属性并生成随机的GitHub账号凭据。
        
        参数:
            translator: 可选的翻译器实例，用于国际化
        """
        self.translator = translator
        # Set browser to visible mode
        os.environ['BROWSER_HEADLESS'] = 'False'
        self.browser = None
        self.email_address = None
        
        # Generate random credentials
        self.github_username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        self.github_password = ''.join(random.choices(string.ascii_letters + string.digits + string.punctuation, k=16))
    
    def setup_browser(self):
        """
        设置和配置Web浏览器
        
        初始化Chrome浏览器实例，配置必要的选项，如无痕模式、窗口大小和用户代理等。
        
        返回值:
            bool: 浏览器设置是否成功
        """
        try:
            print(f"{Fore.CYAN}{EMOJI['START']} {self.translator.get('github.setup_browser') if self.translator else '正在设置浏览器...'}{Style.RESET_ALL}")
            
            options = Options()
            options.add_argument('--incognito')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-notifications')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36')
            
            self.browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            self.browser.set_page_load_timeout(30)
            return True
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('github.browser_setup_failed', error=str(e)) if self.translator else f'浏览器设置失败: {str(e)}'}{Style.RESET_ALL}")
            return False
    
    def get_temp_email(self):
        """
        获取临时邮箱地址
        
        使用YOPmail服务创建一个临时邮箱，生成一个看起来真实的用户名（firstname.lastname+number）。
        
        返回值:
            bool: 临时邮箱创建是否成功
        """
        try:
            if not self.browser:
                if not self.setup_browser():
                    return False
            
            print(f"{Fore.CYAN}{EMOJI['MAIL']} {self.translator.get('github.generating_temp_email') if self.translator else '正在生成临时邮箱地址...'}{Style.RESET_ALL}")
            self.browser.get("https://yopmail.com/")
            time.sleep(2)
            
            # Generate a realistic username
            first_names = ["john", "sara", "michael", "emma", "david", "jennifer", "robert", "lisa"]
            last_names = ["smith", "johnson", "williams", "brown", "jones", "miller", "davis", "garcia"]
            
            random_first = random.choice(first_names)
            random_last = random.choice(last_names)
            random_num = random.randint(100, 999)
            
            username = f"{random_first}.{random_last}{random_num}"
            
            # Enter the username and check inbox
            email_field = self.browser.find_element(By.XPATH, "//input[@id='login']")
            if email_field:
                email_field.clear()
                email_field.send_keys(username)
                time.sleep(1)
                
                # Click the check button
                check_button = self.browser.find_element(By.XPATH, "//button[@title='Check Inbox' or @class='sbut' or contains(@onclick, 'ver')]")
                if check_button:
                    check_button.click()
                    time.sleep(2)
                    self.email_address = f"{username}@yopmail.com"
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('github.temp_email_created', email=self.email_address) if self.translator else f'临时邮箱创建成功: {self.email_address}'}{Style.RESET_ALL}")
                    return True
            
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('github.temp_email_failed') if self.translator else '创建YOPmail地址失败'}{Style.RESET_ALL}")
            return False
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('github.temp_email_error', error=str(e)) if self.translator else f'获取临时邮箱时出错: {str(e)}'}{Style.RESET_ALL}")
            return False
    
    def register_github(self):
        """
        注册新的GitHub账号
        
        使用临时邮箱地址和随机生成的用户名、密码注册GitHub账号。
        自动填写注册表单并处理可能出现的验证码。如有验证码，需要用户手动完成。
        
        返回值:
            bool: GitHub账号注册是否成功
        """
        if not self.email_address:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('github.no_email') if self.translator else '没有可用的邮箱地址'}{Style.RESET_ALL}")
            return False
            
        if not self.browser:
            if not self.setup_browser():
                return False
        
        try:
            print(f"{Fore.CYAN}{EMOJI['FORM']} {self.translator.get('github.registering_account') if self.translator else '正在注册GitHub账号...'}{Style.RESET_ALL}")
            self.browser.get("https://github.com/join")
            time.sleep(3)

            # Fill in the registration form
            WebDriverWait(self.browser, 15).until(EC.visibility_of_element_located((By.ID, "user_login")))
            self.browser.find_element(By.ID, "user_login").send_keys(self.github_username)
            self.browser.find_element(By.ID, "user_email").send_keys(self.email_address)
            self.browser.find_element(By.ID, "user_password").send_keys(self.github_password)
            
            print(f"{Fore.CYAN}{EMOJI['INFO']} GitHub username: {self.github_username}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{EMOJI['INFO']} GitHub password: {self.github_password}{Style.RESET_ALL}")
            
            # Check for any notice or popup and handle it
            try:
                signup_button = self.browser.find_element(By.ID, "signup_button")
                print(f"{Fore.CYAN}{EMOJI['INFO']} Clicking sign up button...{Style.RESET_ALL}")
                signup_button.click()
            except NoSuchElementException:
                print(f"{Fore.YELLOW}{EMOJI['INFO']} Signup button not found, trying alternative selector{Style.RESET_ALL}")
                buttons = self.browser.find_elements(By.TAG_NAME, "button")
                for button in buttons:
                    if "Sign up" in button.text:
                        button.click()
                        break

            # Wait for page transition and check for CAPTCHA
            time.sleep(5)
            
            # Check if registration was successful or if CAPTCHA appeared
            current_url = self.browser.current_url
            
            # Look for CAPTCHA in URL or on page
            if "captcha" in current_url.lower() or "are you a robot" in self.browser.page_source.lower():
                print(f"{Fore.YELLOW}{EMOJI['WAIT']} CAPTCHA detected, please complete it manually{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}{EMOJI['INFO']} You have 60 seconds to solve the CAPTCHA...{Style.RESET_ALL}")
                
                # Wait for user to solve CAPTCHA (60 seconds max)
                for i in range(60):
                    current_url = self.browser.current_url
                    if "captcha" not in current_url.lower() and "are you a robot" not in self.browser.page_source.lower():
                        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} CAPTCHA completed successfully{Style.RESET_ALL}")
                        break
                    time.sleep(1)
                    if i % 10 == 0 and i > 0:
                        print(f"{Fore.YELLOW}{EMOJI['WAIT']} Still waiting for CAPTCHA completion... {60-i} seconds remaining{Style.RESET_ALL}")
                
                # Check if CAPTCHA was solved after waiting
                if "captcha" in self.browser.current_url.lower() or "are you a robot" in self.browser.page_source.lower():
                    print(f"{Fore.RED}{EMOJI['ERROR']} CAPTCHA not solved within time limit{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} Do you want more time to solve the CAPTCHA? (yes/no){Style.RESET_ALL}")
                    response = input().lower().strip()
                    if response in ['yes', 'y']:
                        print(f"{Fore.YELLOW}{EMOJI['INFO']} Press Enter when you've completed the CAPTCHA...{Style.RESET_ALL}")
                        input()
                        if "captcha" in self.browser.current_url.lower() or "are you a robot" in self.browser.page_source.lower():
                            print(f"{Fore.RED}{EMOJI['ERROR']} CAPTCHA still not solved{Style.RESET_ALL}")
                            return False
                    else:
                        return False
            
            # Wait for registration to complete
            time.sleep(5)
            
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} GitHub account registered{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} Failed to register GitHub account: {str(e)}{Style.RESET_ALL}")
            return False
    
    def check_email_verification(self):
        """
        检查邮箱验证
        
        检查GitHub发送的验证邮件，并点击验证链接完成账号验证。
        会打开YOPmail收件箱并刷新直到收到验证邮件，然后提取并访问验证链接。
        
        返回值:
            bool: 邮箱验证是否成功
        """
        if not self.browser:
            if not self.setup_browser():
                return False
        
        try:
            print(f"{Fore.CYAN}{EMOJI['VERIFY']} {self.translator.get('github.checking_email_verification') if self.translator else '正在检查邮箱验证...'}{Style.RESET_ALL}")
            
            # Go to YOPmail
            self.browser.get("https://yopmail.com/")
            time.sleep(2)
            
            # Enter the email address
            email_field = self.browser.find_element(By.XPATH, "//input[@id='login']")
            if email_field:
                email_field.clear()
                email_field.send_keys(self.email_address.split('@')[0])  # Just the username part
                time.sleep(1)
                
                # Click the check button
                check_button = self.browser.find_element(By.XPATH, "//button[@title='Check Inbox' or @class='sbut' or contains(@onclick, 'ver')]")
                if check_button:
                    check_button.click()
                    time.sleep(2)
            
            # Maximum number of refresh attempts
            max_attempts = 15
            current_attempt = 0
            verification_link = None
            
            # Switch to the inbox iframe
            while current_attempt < max_attempts and not verification_link:
                current_attempt += 1
                print(f"{Fore.CYAN}{EMOJI['REFRESH']} {self.translator.get('github.refreshing_inbox', attempt=current_attempt, max=max_attempts) if self.translator else f'刷新收件箱... ({current_attempt}/{max_attempts})'}{Style.RESET_ALL}")
                
                # Refresh the inbox
                refresh_button = self.browser.find_element(By.XPATH, "//button[@id='refresh' or contains(@onclick, 'refresh') or contains(@title, 'Refresh')]")
                if refresh_button:
                    refresh_button.click()
                    time.sleep(3)
                
                try:
                    # Look for GitHub email
                    inbox_frame = self.browser.find_element(By.XPATH, "//iframe[@id='ifmail' or @name='ifmail']")
                    self.browser.switch_to.frame(inbox_frame)
                    
                    # Check if verification email exists
                    github_emails = self.browser.find_elements(By.XPATH, "//div[contains(text(), 'GitHub') or contains(text(), 'github')]")
                    
                    if github_emails:
                        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('github.verification_email_found') if self.translator else '找到GitHub验证邮件'}{Style.RESET_ALL}")
                        
                        # Find verification link
                        verify_links = self.browser.find_elements(By.XPATH, "//a[contains(@href, 'github.com/') and (contains(text(), 'Verify') or contains(text(), 'verify') or contains(text(), 'Confirm') or contains(text(), 'confirm'))]")
                        
                        if verify_links:
                            verification_link = verify_links[0].get_attribute('href')
                            print(f"{Fore.GREEN}{EMOJI['LINK']} {self.translator.get('github.verification_link_found') if self.translator else '找到验证链接'}{Style.RESET_ALL}")
                            break
                        else:
                            print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('github.verification_link_not_found') if self.translator else '未找到验证链接'}{Style.RESET_ALL}")
                    
                    # Switch back to main content
                    self.browser.switch_to.default_content()
                    
                except Exception as frame_error:
                    print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('github.frame_switch_error', error=str(frame_error)) if self.translator else f'切换iframe时出错: {str(frame_error)}'}{Style.RESET_ALL}")
                    self.browser.switch_to.default_content()
                
                time.sleep(5)  # Wait before next refresh
            
            # If verification link found, open it
            if verification_link:
                print(f"{Fore.CYAN}{EMOJI['LINK']} {self.translator.get('github.opening_verification_link') if self.translator else '正在打开验证链接...'}{Style.RESET_ALL}")
                self.browser.get(verification_link)
                time.sleep(5)
                
                # Check if verification was successful
                if "github.com" in self.browser.current_url and not "/join" in self.browser.current_url:
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('github.email_verification_success') if self.translator else 'GitHub邮箱验证成功'}{Style.RESET_ALL}")
                    return True
                else:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('github.email_verification_failed') if self.translator else 'GitHub邮箱验证失败'}{Style.RESET_ALL}")
                    return False
            else:
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('github.verification_link_not_found_timeout') if self.translator else '超时未找到验证链接'}{Style.RESET_ALL}")
                return False
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('github.email_verification_error', error=str(e)) if self.translator else f'邮箱验证过程中出错: {str(e)}'}{Style.RESET_ALL}")
            return False

    def register_cursor(self):
        """
        注册Cursor账号
        
        使用已验证的GitHub账号通过OAuth授权注册Cursor账号。
        访问Cursor注册页面，选择GitHub登录方式，并完成授权流程。
        
        返回值:
            bool: Cursor注册是否成功
        """
        if not self.browser:
            if not self.setup_browser():
                return False
                
        try:
            print(f"{Fore.CYAN}{EMOJI['START']} {self.translator.get('github.registering_cursor') if self.translator else '正在注册Cursor账号...'}{Style.RESET_ALL}")
            
            # Navigate to Cursor sign-up page
            self.browser.get("https://www.cursor.com/")
            time.sleep(3)
            
            # Look for sign-up or login button
            signup_buttons = self.browser.find_elements(By.XPATH, "//a[contains(text(), 'Sign up') or contains(text(), 'Log in')]")
            if signup_buttons:
                signup_buttons[0].click()
                time.sleep(3)
            
            # Wait for authentication page to load
            try:
                WebDriverWait(self.browser, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'GitHub') or contains(@class, 'github') or //img[contains(@src, 'github')]]"))
                )
            except:
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('github.waiting_for_auth_page') if self.translator else '等待认证页面加载...'}{Style.RESET_ALL}")
            
            # Click on GitHub login button
            github_buttons = self.browser.find_elements(By.XPATH, "//button[contains(text(), 'GitHub') or contains(@class, 'github')]") or \
                            self.browser.find_elements(By.XPATH, "//a[contains(text(), 'GitHub') or contains(@class, 'github')]") or \
                            self.browser.find_elements(By.XPATH, "//div[contains(text(), 'GitHub') or contains(@class, 'github')]")
            
            if github_buttons:
                print(f"{Fore.CYAN}{EMOJI['LINK']} {self.translator.get('github.clicking_github_login') if self.translator else '点击GitHub登录按钮...'}{Style.RESET_ALL}")
                github_buttons[0].click()
                time.sleep(5)
            else:
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('github.github_login_button_not_found') if self.translator else '未找到GitHub登录按钮'}{Style.RESET_ALL}")
                return False
            
            # Check if redirected to GitHub login
            if "github.com" in self.browser.current_url:
                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('github.logging_into_github') if self.translator else '正在登录GitHub...'}{Style.RESET_ALL}")
                
                # Enter credentials
                try:
                    username_field = WebDriverWait(self.browser, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//input[@id='login_field' or @name='login']"))
                    )
                    password_field = self.browser.find_element(By.XPATH, "//input[@id='password' or @name='password']")
                    
                    username_field.send_keys(self.github_username)
                    time.sleep(1)
                    password_field.send_keys(self.github_password)
                    time.sleep(1)
                    
                    # Click sign in
                    signin_button = self.browser.find_element(By.XPATH, "//input[@type='submit' or @value='Sign in']")
                    signin_button.click()
                    time.sleep(5)
                    
                except Exception as login_error:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('github.github_login_error', error=str(login_error)) if self.translator else f'GitHub登录过程中出错: {str(login_error)}'}{Style.RESET_ALL}")
                    return False
            
            # Check for authorization page and authorize if needed
            if "github.com/login/oauth/authorize" in self.browser.current_url:
                try:
                    authorize_button = WebDriverWait(self.browser, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Authorize') or @id='js-oauth-authorize-btn']"))
                    )
                    print(f"{Fore.CYAN}{EMOJI['LINK']} {self.translator.get('github.authorizing_cursor') if self.translator else '正在授权Cursor访问...'}{Style.RESET_ALL}")
                    authorize_button.click()
                    time.sleep(5)
                except:
                    print(f"{Fore.YELLOW}{EMOJI['WARNING']} {self.translator.get('github.no_authorization_needed') if self.translator else '无需额外授权或授权按钮未找到'}{Style.RESET_ALL}")
            
            # Wait for redirection to Cursor
            max_wait = 30
            cursor_redirected = False
            
            for _ in range(max_wait):
                if "cursor.com" in self.browser.current_url:
                    cursor_redirected = True
                    break
                time.sleep(1)
            
            if cursor_redirected:
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('github.cursor_registration_complete') if self.translator else 'Cursor注册完成'}{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('github.cursor_registration_failed') if self.translator else 'Cursor注册失败，未重定向到Cursor'}{Style.RESET_ALL}")
                return False
                
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('github.cursor_registration_error', error=str(e)) if self.translator else f'Cursor注册过程中出错: {str(e)}'}{Style.RESET_ALL}")
            return False

    def reset_machine_id(self):
        """
        重置机器ID
        
        通过修改Cursor应用程序的机器ID文件实现设备标识重置，
        避免不同账号之间的使用限制。自动备份原始文件并生成新的唯一ID。
        
        返回值:
            bool: 机器ID重置是否成功
        """
        try:
            print(f"{Fore.CYAN}{EMOJI['UPDATE']} Resetting Cursor machine ID...{Style.RESET_ALL}")
            
            # Find Cursor app data location based on platform
            cursor_data_dir = None
            if platform.system() == "Windows":
                appdata = os.getenv('APPDATA')
                if appdata:
                    cursor_data_dir = os.path.join(appdata, "cursor", "Local Storage", "leveldb")
            elif platform.system() == "Darwin":  # macOS
                home = os.path.expanduser("~")
                cursor_data_dir = os.path.join(home, "Library", "Application Support", "cursor", "Local Storage", "leveldb")
            elif platform.system() == "Linux":
                home = os.path.expanduser("~")
                cursor_data_dir = os.path.join(home, ".config", "cursor", "Local Storage", "leveldb")
            
            if not cursor_data_dir or not os.path.exists(cursor_data_dir):
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} Cursor data directory not found at: {cursor_data_dir}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}{EMOJI['INFO']} You may need to reset the machine ID manually{Style.RESET_ALL}")
                
                # Try to find the Cursor data directory
                if platform.system() == "Linux":
                    possible_paths = [
                        os.path.join(os.path.expanduser("~"), ".config", "cursor"),
                        os.path.join(os.path.expanduser("~"), ".cursor")
                    ]
                    for path in possible_paths:
                        if os.path.exists(path):
                            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} Found Cursor directory at: {path}{Style.RESET_ALL}")
                            # Look for Local Storage subfolder
                            for root, dirs, files in os.walk(path):
                                if "Local Storage" in dirs:
                                    cursor_data_dir = os.path.join(root, "Local Storage", "leveldb")
                                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} Found Cursor data directory at: {cursor_data_dir}{Style.RESET_ALL}")
                                    break
                            break
            
            if cursor_data_dir and os.path.exists(cursor_data_dir):
                # Generate a new UUID
                new_machine_id = str(uuid.uuid4())
                print(f"{Fore.CYAN}{EMOJI['KEY']} New machine ID: {new_machine_id}{Style.RESET_ALL}")
                
                # Ask for permission to modify files
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} This operation will modify Cursor app data files{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}{EMOJI['INFO']} Do you want to continue? (yes/no){Style.RESET_ALL}")
                response = input().lower().strip()
                if response not in ['yes', 'y']:
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} Machine ID reset aborted{Style.RESET_ALL}")
                    return False
                
                # Backup the directory
                backup_dir = cursor_data_dir + "_backup_" + time.strftime("%Y%m%d%H%M%S")
                print(f"{Fore.CYAN}{EMOJI['INFO']} Creating backup of data directory to: {backup_dir}{Style.RESET_ALL}")
                try:
                    shutil.copytree(cursor_data_dir, backup_dir)
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} Backup created successfully{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.YELLOW}{EMOJI['WARNING']} Failed to create backup: {str(e)}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} Continuing without backup...{Style.RESET_ALL}")
                
                # Find and modify files containing the machine ID
                modified = False
                for filename in os.listdir(cursor_data_dir):
                    if filename.endswith(".log") or filename.endswith(".ldb"):
                        file_path = os.path.join(cursor_data_dir, filename)
                        try:
                            with open(file_path, "rb") as f:
                                content = f.read()
                                
                            # Look for patterns that might contain machine ID
                            if b"machineId" in content:
                                print(f"{Fore.CYAN}{EMOJI['INFO']} Found machineId reference in: {filename}{Style.RESET_ALL}")
                                modified = True
                                
                                # For safety, don't modify the binary files directly
                                # Instead, instruct user to uninstall and reinstall Cursor
                                print(f"{Fore.YELLOW}{EMOJI['WARNING']} Binary files found that may contain machine ID{Style.RESET_ALL}")
                                print(f"{Fore.YELLOW}{EMOJI['INFO']} For best results, please:{Style.RESET_ALL}")
                                print(f"{Fore.YELLOW}{EMOJI['INFO']} 1. Close Cursor if it's running{Style.RESET_ALL}")
                                print(f"{Fore.YELLOW}{EMOJI['INFO']} 2. Uninstall Cursor completely{Style.RESET_ALL}")
                                print(f"{Fore.YELLOW}{EMOJI['INFO']} 3. Reinstall Cursor{Style.RESET_ALL}")
                                print(f"{Fore.YELLOW}{EMOJI['INFO']} 4. Login with your new GitHub account{Style.RESET_ALL}")
                                break
                                
                        except Exception as e:
                            print(f"{Fore.YELLOW}{EMOJI['WARNING']} Error processing file {filename}: {str(e)}{Style.RESET_ALL}")
                
                if not modified:
                    print(f"{Fore.YELLOW}{EMOJI['WARNING']} No machine ID references found in data files{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} You may need to reinstall Cursor for a complete reset{Style.RESET_ALL}")
                
                # Save credentials before returning
                self.save_credentials()
                
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} Machine ID reset process completed{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} Cursor data directory not found{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}{EMOJI['INFO']} You may need to manually reset the machine ID by reinstalling Cursor{Style.RESET_ALL}")
                
                # Still save credentials
                self.save_credentials()
                return True
                
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} Failed to reset machine ID: {str(e)}{Style.RESET_ALL}")
            # Still save credentials even if machine ID reset fails
            self.save_credentials()
            return False
            
    def save_credentials(self):
        """
        保存账号凭据
        
        将生成的GitHub账号和Cursor访问信息保存到本地文件，
        便于日后查看和管理。包括邮箱地址、GitHub用户名和密码等。
        
        返回值:
            bool: 凭据保存是否成功
        """
        try:
            if not self.email_address or not self.github_username or not self.github_password:
                print(f"{Fore.RED}{EMOJI['ERROR']} No credentials to save{Style.RESET_ALL}")
                return False
                
            output_file = "github_cursor_accounts.txt"
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            
            credentials = {
                "timestamp": timestamp,
                "github_username": self.github_username,
                "github_password": self.github_password,
                "email": self.email_address
            }
            
            credentials_json = json.dumps(credentials)
            
            # Check if file exists and create if not
            file_exists = os.path.exists(output_file)
            
            with open(output_file, "a") as f:
                if not file_exists:
                    f.write("# GitHub + Cursor AI Accounts\n")
                    f.write("# Format: JSON with timestamp, github_username, github_password, email\n\n")
                
                f.write(credentials_json + "\n")
            
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} Credentials saved to: {output_file}{Style.RESET_ALL}")
            
            # Print a summary
            print(f"\n{Fore.GREEN}{EMOJI['SUCCESS']} Registration Summary:{Style.RESET_ALL}")
            print(f"{Fore.CYAN}  • GitHub Username: {self.github_username}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}  • GitHub Password: {self.github_password}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}  • Email Address: {self.email_address}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}  • Saved to: {output_file}{Style.RESET_ALL}\n")
            
            return True
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} Failed to save credentials: {str(e)}{Style.RESET_ALL}")
            print(f"\n{Fore.YELLOW}{EMOJI['WARNING']} Make sure to copy these credentials manually:{Style.RESET_ALL}")
            print(f"{Fore.CYAN}  • GitHub Username: {self.github_username}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}  • GitHub Password: {self.github_password}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}  • Email Address: {self.email_address}{Style.RESET_ALL}\n")
            return False
    
    def cleanup(self):
        """
        清理资源
        
        关闭浏览器实例并释放相关资源，确保程序结束时无残留进程。
        
        返回值:
            bool: 清理是否成功
        """
        if self.browser:
            try:
                self.browser.quit()
            except:
                pass
    
    def start_registration(self):
        """
        启动注册流程
        
        执行完整的注册流程，按顺序调用各个步骤方法，包括：
        1. 获取临时邮箱
        2. 注册GitHub账号
        3. 验证邮箱
        4. 注册Cursor
        5. 重置机器ID
        6. 保存凭据
        
        返回值:
            bool: 整个注册流程是否成功
        """
        try:
            # Step 1: Get temporary email
            if not self.get_temp_email():
                return False
            
            # Step 2: Register GitHub account
            if not self.register_github():
                return False
            
            # Step 3: Check and verify email
            if not self.check_email_verification():
                return False
            
            # Step 4: Register Cursor with GitHub
            if not self.register_cursor():
                return False
            
            # Step 5: Reset machine ID
            self.reset_machine_id()
            
            return True
        finally:
            self.cleanup()

def display_features_and_warnings(translator=None):
    """
    显示功能说明和警告信息
    
    在开始注册流程前显示工具的功能、注意事项和可能的风险，
    包括GitHub账号创建、临时邮箱使用和自动化流程可能需要手动干预的部分。
    
    参数:
        translator: 翻译器对象，用于多语言支持，可以为None
    """
    if translator:
        print(f"\n🚀 {translator.get('github_register.title')}")
        print("=====================================")
        print(f"{translator.get('github_register.features_header')}:")
        print(f"  - {translator.get('github_register.feature1')}")
        print(f"  - {translator.get('github_register.feature2')}")
        print(f"  - {translator.get('github_register.feature3')}")
        print(f"  - {translator.get('github_register.feature4')}")
        print(f"  - {translator.get('github_register.feature5')}")
        print(f"  - {translator.get('github_register.feature6')}")
        print(f"\n⚠️ {translator.get('github_register.warnings_header')}:")
        print(f"  - {translator.get('github_register.warning1')}")
        print(f"  - {translator.get('github_register.warning2')}")
        print(f"  - {translator.get('github_register.warning3')}")
        print(f"  - {translator.get('github_register.warning4')}")
        print("=====================================\n")
    else:
        print("\n🚀 GitHub + Cursor AI Registration Automation")
        print("=====================================")
        print("Features:")
        print("  - Creates a temporary email using YOPmail")
        print("  - Registers a new GitHub account with random credentials")
        print("  - Verifies the GitHub email automatically")
        print("  - Logs into Cursor AI using GitHub authentication")
        print("  - Resets the machine ID to bypass trial detection")
        print("  - Saves all credentials to a file")
        print("\n⚠️ Warnings:")
        print("  - This script automates account creation, which may violate GitHub/Cursor terms of service")
        print("  - Requires internet access and administrative privileges")
        print("  - CAPTCHA or additional verification may interrupt automation")
        print("  - Use responsibly and at your own risk")
        print("=====================================\n")

def get_user_confirmation(translator=None):
    """
    获取用户确认
    
    提示用户确认是否继续执行注册流程，要求用户输入"YES"来确认。
    这是一个安全措施，确保用户理解并同意该工具的操作。
    
    参数:
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        bool: 用户是否确认继续
    """
    while True:
        if translator:
            response = input(f"{translator.get('github_register.confirm')} (yes/no): ").lower().strip()
        else:
            response = input("Do you want to proceed with GitHub + Cursor AI registration? (yes/no): ").lower().strip()
            
        if response in ['yes', 'y']:
            return True
        elif response in ['no', 'n']:
            if translator:
                print(f"❌ {translator.get('github_register.cancelled')}")
            else:
                print("❌ Operation cancelled.")
            return False
        else:
            if translator:
                print(f"{translator.get('github_register.invalid_choice')}")
            else:
                print("Please enter 'yes' or 'no'.")

def main(translator=None):
    """
    主函数
    
    执行GitHub Cursor注册工具的入口点，显示功能说明，
    获取用户确认，然后启动注册流程。处理可能的异常并提供友好的错误信息。
    
    参数:
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        bool: 注册是否成功完成
    """
    logging.info(f"{Fore.CYAN} {translator.get('github_register.starting_automation')}{Style.RESET_ALL}")
    
    # Display features and warnings
    display_features_and_warnings(translator)
    
    # Get user confirmation
    if not get_user_confirmation(translator):
        return
    
    # Start registration process
    registration = GitHubCursorRegistration(translator)
    success = registration.start_registration()
    
    # Display final message
    if success:
        print(f"\n{Fore.GREEN}{EMOJI['DONE']} {translator.get('github_register.completed_successfully')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('github_register.github_username')}: {registration.github_username}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('github_register.github_password')}: {registration.github_password}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('github_register.email')}: {registration.email_address}{Style.RESET_ALL}")
        print(f"\n{Fore.CYAN}{EMOJI['INFO']} {translator.get('github_register.credentials_saved')}{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.RED}{EMOJI['ERROR']} {translator.get('github_register.registration_encountered_issues')}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('github_register.check_browser_windows_for_manual_intervention_or_try_again_later')}{Style.RESET_ALL}")
    
    # Wait for user acknowledgment
    if translator:
        input(f"\n{EMOJI['INFO']} {translator.get('register.press_enter')}...")
    else:
        input(f"\n{EMOJI['INFO']} Press Enter to continue...")

if __name__ == "__main__":
    main()
