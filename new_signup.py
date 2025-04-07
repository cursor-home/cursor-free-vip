"""
new_signup.py - Cursor新用户注册模块

这个模块负责自动化注册Cursor账号的流程，主要功能包括：
- 启动Chrome浏览器并自动填写注册表单
- 处理验证码和Turnstile人机验证
- 完成邮箱验证和密码设置
- 自动登录新创建的账号

本模块模拟人类操作，加入随机等待时间，以避免被反自动化系统检测。
"""
from DrissionPage import ChromiumOptions, ChromiumPage
import time
import os
import signal
import random
from colorama import Fore, Style
import configparser
from pathlib import Path
import sys
from config import get_config 

# Add global variable at the beginning of the file
_translator = None

# Add global variable to track our Chrome processes
_chrome_process_ids = []

def cleanup_chrome_processes(translator=None):
    """
    清理由本脚本启动的Chrome进程。
    
    在脚本退出时调用，确保不会留下孤立的Chrome进程。
    只清理本脚本启动的进程，不影响用户自己打开的Chrome窗口。
    
    参数:
        translator: 翻译器对象，用于多语言支持，可以为None
    """
    global _chrome_process_ids
    
    if not _chrome_process_ids:
        print("\nNo Chrome processes to clean...")
        return
        
    print("\nCleaning Chrome processes launched by this script...")
    try:
        if os.name == 'nt':
            for pid in _chrome_process_ids:
                try:
                    os.system(f'taskkill /F /PID {pid} /T 2>nul')
                except:
                    pass
        else:
            for pid in _chrome_process_ids:
                try:
                    os.kill(pid, signal.SIGTERM)
                except:
                    pass
        _chrome_process_ids = []  # Reset the list after cleanup
    except Exception as e:
        if translator:
            print(f"{Fore.RED}❌ {translator.get('register.cleanup_error', error=str(e))}{Style.RESET_ALL}")
        else:
            print(f"清理进程时出错: {e}")

def signal_handler(signum, frame):
    """
    处理Ctrl+C等中断信号。
    
    当用户按下Ctrl+C或发送中断信号时，确保脚本能够优雅地退出，
    并清理所有启动的Chrome进程。
    
    参数:
        signum: 信号编号
        frame: 当前栈帧
    """
    global _translator
    if _translator:
        print(f"{Fore.CYAN}{_translator.get('register.exit_signal')}{Style.RESET_ALL}")
    else:
        print("\n接收到退出信号，正在关闭...")
    cleanup_chrome_processes(_translator)
    os._exit(0)

def simulate_human_input(page, url, config, translator=None):
    """
    模拟人类访问网页行为。
    
    先访问空白页面，然后再访问目标URL，并添加随机等待时间，
    使行为更像真实用户。
    
    参数:
        page: ChromiumPage对象
        url: 要访问的目标URL
        config: 配置对象，包含等待时间设置
        translator: 翻译器对象，用于多语言支持，可以为None
    """
    if translator:
        print(f"{Fore.CYAN}🚀 {translator.get('register.visiting_url')}: {url}{Style.RESET_ALL}")
    
    # First visit blank page
    page.get('about:blank')
    time.sleep(get_random_wait_time(config, 'page_load_wait'))
    
    # Visit target page
    page.get(url)
    time.sleep(get_random_wait_time(config, 'page_load_wait'))

def fill_signup_form(page, first_name, last_name, email, config, translator=None):
    """
    填写Cursor注册表单。
    
    自动填写姓名和邮箱信息，并提交表单。
    在每个操作之间添加随机等待时间，模拟真实人类输入。
    
    参数:
        page: ChromiumPage对象
        first_name: 名字
        last_name: 姓氏
        email: 电子邮箱地址
        config: 配置对象，包含等待时间设置
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        bool: 表单填写成功返回True，否则返回False
    """
    try:
        if translator:
            print(f"{Fore.CYAN}📧 {translator.get('register.filling_form')}{Style.RESET_ALL}")
        else:
            print("\n正在填写注册表单...")
        
        # Fill first name
        first_name_input = page.ele("@name=first_name")
        if first_name_input:
            first_name_input.input(first_name)
            time.sleep(get_random_wait_time(config, 'input_wait'))
        
        # Fill last name
        last_name_input = page.ele("@name=last_name")
        if last_name_input:
            last_name_input.input(last_name)
            time.sleep(get_random_wait_time(config, 'input_wait'))
        
        # Fill email
        email_input = page.ele("@name=email")
        if email_input:
            email_input.input(email)
            time.sleep(get_random_wait_time(config, 'input_wait'))
        
        # Click submit button
        submit_button = page.ele("@type=submit")
        if submit_button:
            submit_button.click()
            time.sleep(get_random_wait_time(config, 'submit_wait'))
            
        if translator:
            print(f"{Fore.GREEN}✅ {translator.get('register.form_success')}{Style.RESET_ALL}")
        else:
            print("Form filled successfully")
        return True
        
    except Exception as e:
        if translator:
            print(f"{Fore.RED}❌ {translator.get('register.form_error', error=str(e))}{Style.RESET_ALL}")
        else:
            print(f"Error filling form: {e}")
        return False

def get_default_chrome_path():
    """
    获取默认Chrome浏览器路径。
    
    根据不同操作系统返回Chrome可执行文件的可能路径。
    按优先级顺序检查多个常见安装位置。
    
    返回值:
        str: Chrome可执行文件的路径，如果找不到则返回空字符串
    """
    if sys.platform == "win32":
        paths = [
            os.path.join(os.environ.get('PROGRAMFILES', ''), 'Google/Chrome/Application/chrome.exe'),
            os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Google/Chrome/Application/chrome.exe'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google/Chrome/Application/chrome.exe')
        ]
    elif sys.platform == "darwin":
        paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        ]
    else:  # Linux
        paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable"
        ]

    for path in paths:
        if os.path.exists(path):
            return path
    return ""

def get_user_documents_path():
    """
    获取用户文档目录路径。
    
    根据不同操作系统返回用户文档目录的路径。
    对于Linux系统，会特别处理sudo用户的情况。
    
    返回值:
        str: 用户文档目录的完整路径
    """
    if sys.platform == "win32":
        return os.path.join(os.path.expanduser("~"), "Documents")
    elif sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~"), "Documents")
    else:  # Linux
        # Get actual user's home directory
        sudo_user = os.environ.get('SUDO_USER')
        if sudo_user:
            return os.path.join("/home", sudo_user, "Documents")
        return os.path.join(os.path.expanduser("~"), "Documents")

def get_random_wait_time(config, timing_type='page_load_wait'):
    """
    根据配置获取随机等待时间。
    
    从配置中读取等待时间设置，支持固定时间和时间范围。
    用于模拟人类操作的随机延迟，避免被检测为自动化程序。
    
    参数:
        config: ConfigParser配置对象
        timing_type: 等待时间类型(如page_load_wait, input_wait, submit_wait等)
    
    返回值:
        float: 随机等待时间（秒）
        
    说明:
        - 支持固定值格式: "0.5"
        - 支持范围格式: "0.5-1.5"或"0.5,1.5"
        - 如果配置有误，使用默认值0.1-0.8秒
    """
    try:
        if not config.has_section('Timing'):
            return random.uniform(0.1, 0.8)  # Default value
            
        if timing_type == 'random':
            min_time = float(config.get('Timing', 'min_random_time', fallback='0.1'))
            max_time = float(config.get('Timing', 'max_random_time', fallback='0.8'))
            return random.uniform(min_time, max_time)
            
        time_value = config.get('Timing', timing_type, fallback='0.1-0.8')
        
        # Check if it's a fixed time value
        if '-' not in time_value and ',' not in time_value:
            return float(time_value)  # Return fixed time
            
        # Process range time
        min_time, max_time = map(float, time_value.split('-' if '-' in time_value else ','))
        return random.uniform(min_time, max_time)
    except:
        return random.uniform(0.1, 0.8)  # Return default value when error

def setup_driver(translator=None):
    """
    设置并启动Chrome浏览器。
    
    配置Chrome启动选项，包括隐身模式、扩展加载等，
    并记录启动的Chrome进程ID，便于后续清理。
    
    参数:
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        tuple: (config, ChromiumPage) 配置对象和已配置的浏览器页面对象
    """
    global _chrome_process_ids  # 全局变量，用于存储Chrome进程ID，便于程序退出时清理
    
    try:
        # 获取配置信息
        config = get_config(translator)  # 从配置文件加载设置
        
        # 获取Chrome浏览器路径
        chrome_path = config.get('Chrome', 'chromepath', fallback=get_default_chrome_path())  # 尝试从配置获取路径，如果没有则使用默认路径
        
        # 验证Chrome路径是否有效
        if not chrome_path or not os.path.exists(chrome_path):
            # 路径无效时显示警告并使用默认路径
            if translator:
                print(f"{Fore.YELLOW}⚠️ {translator.get('register.chrome_path_invalid') if translator else 'Chrome路径无效，使用默认路径'}{Style.RESET_ALL}")
            chrome_path = get_default_chrome_path()  # 使用系统默认Chrome路径

        # 创建浏览器选项对象
        co = ChromiumOptions()  # 初始化ChromiumOptions对象，用于配置浏览器启动参数
        
        # 设置Chrome浏览器路径
        co.set_browser_path(chrome_path)  # 指定Chrome可执行文件的位置
        
        # 启用隐身模式，避免使用现有配置文件和缓存
        co.set_argument("--incognito")  # 使用隐身模式，避免历史记录和cookie干扰

        # 在Linux系统上添加额外的安全参数
        if sys.platform == "linux":
            co.set_argument("--no-sandbox")  # Linux系统下禁用沙盒模式，解决某些权限问题
            
        # 设置随机端口，避免端口冲突
        co.auto_port()  # 自动选择可用端口，防止多个实例冲突
        
        # 设置无头模式（必须为False，以模拟人类操作）
        co.headless(False)  # 显示浏览器界面，便于调试和模拟真实用户行为
        
        # 尝试加载Turnstile验证码辅助扩展
        try:
            # 加载扩展程序，帮助处理Turnstile验证
            extension_path = os.path.join(os.getcwd(), "turnstilePatch")  # 扩展程序路径
            if os.path.exists(extension_path):
                co.set_argument("--allow-extensions-in-incognito")  # 允许在隐身模式下使用扩展
                co.add_extension(extension_path)  # 添加扩展到浏览器
        except Exception as e:
            # 扩展加载失败时显示错误信息
            if translator:
                print(f"{Fore.RED}❌ {translator.get('register.extension_load_error', error=str(e))}{Style.RESET_ALL}")
            else:
                print(f"Error loading extension: {e}")
        
        # 显示浏览器启动提示
        if translator:
            print(f"{Fore.CYAN}🚀 {translator.get('register.starting_browser')}{Style.RESET_ALL}")
        else:
            print("Starting browser...")
        
        # 记录启动前的Chrome进程，用于后续识别新进程
        before_pids = []
        try:
            import psutil  # 导入进程管理模块
            before_pids = [p.pid for p in psutil.process_iter() if 'chrome' in p.name().lower()]  # 获取所有Chrome进程ID
        except:
            pass  # 忽略psutil导入或使用错误
            
        # 启动浏览器
        page = ChromiumPage(co)  # 使用配置好的选项创建浏览器页面对象
        
        # 等待Chrome完全启动
        time.sleep(1)  # 短暂等待，确保浏览器进程完全初始化
        
        # 记录启动后的Chrome进程，并找出新增的进程
        try:
            import psutil
            after_pids = [p.pid for p in psutil.process_iter() if 'chrome' in p.name().lower()]  # 获取启动后的所有Chrome进程
            # 找出新增的Chrome进程
            new_pids = [pid for pid in after_pids if pid not in before_pids]  # 计算差集，获取新启动的进程
            _chrome_process_ids.extend(new_pids)  # 将新进程ID添加到全局列表
            
            # 显示进程跟踪信息
            if _chrome_process_ids:
                print(f"Tracking {len(_chrome_process_ids)} Chrome processes")  # 显示跟踪的进程数量
            else:
                print(f"{Fore.YELLOW}Warning: No new Chrome processes detected to track{Style.RESET_ALL}")  # 警告：未检测到新进程
        except Exception as e:
            print(f"Warning: Could not track Chrome processes: {e}")  # 进程跟踪失败的警告
            
        # 返回配置对象和浏览器页面对象
        return config, page

    except Exception as e:
        # 处理浏览器设置过程中的任何异常
        if translator:
            print(f"{Fore.RED}❌ {translator.get('register.browser_setup_error', error=str(e))}{Style.RESET_ALL}")
        else:
            print(f"Error setting up browser: {e}")
        raise  # 重新抛出异常，让调用者处理

def handle_turnstile(page, config, translator=None):
    """Handle Turnstile verification"""
    try:
        if translator:
            print(f"{Fore.CYAN}🔄 {translator.get('register.handling_turnstile')}{Style.RESET_ALL}")
        else:
            print("\nHandling Turnstile verification...")
        
        # from config
        turnstile_time = float(config.get('Turnstile', 'handle_turnstile_time', fallback='2'))
        random_time_str = config.get('Turnstile', 'handle_turnstile_random_time', fallback='1-3')
        
        # Parse random time range
        try:
            min_time, max_time = map(float, random_time_str.split('-'))
        except:
            min_time, max_time = 1, 3  # Default value
        
        max_retries = 2
        retry_count = 0

        while retry_count < max_retries:
            retry_count += 1
            if translator:
                print(f"{Fore.CYAN}🔄 {translator.get('register.retry_verification', attempt=retry_count)}{Style.RESET_ALL}")
            else:
                print(f"Attempt {retry_count} of verification...")

            try:
                # Try to reset turnstile
                page.run_js("try { turnstile.reset() } catch(e) { }")
                time.sleep(turnstile_time)  # from config

                # Locate verification box element
                challenge_check = (
                    page.ele("@id=cf-turnstile", timeout=2)
                    .child()
                    .shadow_root.ele("tag:iframe")
                    .ele("tag:body")
                    .sr("tag:input")
                )

                if challenge_check:
                    if translator:
                        print(f"{Fore.CYAN}🔄 {translator.get('register.detect_turnstile')}{Style.RESET_ALL}")
                    else:
                        print("Detected verification box...")
                    
                    # from config
                    time.sleep(random.uniform(min_time, max_time))
                    challenge_check.click()
                    time.sleep(turnstile_time)  # from config

                    # check verification result
                    if check_verification_success(page, translator):
                        if translator:
                            print(f"{Fore.GREEN}✅ {translator.get('register.verification_success')}{Style.RESET_ALL}")
                        else:
                            print("Verification successful!")
                        return True

            except Exception as e:
                if translator:
                    print(f"{Fore.RED}❌ {translator.get('register.verification_failed')}{Style.RESET_ALL}")
                else:
                    print(f"Verification attempt failed: {e}")

            # Check if verification has been successful
            if check_verification_success(page, translator):
                if translator:
                    print(f"{Fore.GREEN}✅ {translator.get('register.verification_success')}{Style.RESET_ALL}")
                else:
                    print("Verification successful!")
                return True

            time.sleep(random.uniform(min_time, max_time))

        if translator:
            print(f"{Fore.RED}❌ {translator.get('register.verification_failed')}{Style.RESET_ALL}")
        else:
            print("Exceeded maximum retry attempts")
        return False

    except Exception as e:
        if translator:
            print(f"{Fore.RED}❌ {translator.get('register.verification_error', error=str(e))}{Style.RESET_ALL}")
        else:
            print(f"Error in verification process: {e}")
        return False

def check_verification_success(page, translator=None):
    """Check if verification is successful"""
    try:
        # Check if there is a subsequent form element, indicating verification has passed
        if (page.ele("@name=password", timeout=0.5) or 
            page.ele("@name=email", timeout=0.5) or
            page.ele("@data-index=0", timeout=0.5) or
            page.ele("Account Settings", timeout=0.5)):
            return True
        
        # Check if there is an error message
        error_messages = [
            'xpath://div[contains(text(), "Can\'t verify the user is human")]',
            'xpath://div[contains(text(), "Error: 600010")]',
            'xpath://div[contains(text(), "Please try again")]'
        ]
        
        for error_xpath in error_messages:
            if page.ele(error_xpath):
                return False
            
        return False
    except:
        return False

def generate_password(length=12):
    """Generate random password"""
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    return ''.join(random.choices(chars, k=length))

def fill_password(page, password: str, config, translator=None):
    """
    Fill password form
    """
    try:
        print(f"{Fore.CYAN}🔑 {translator.get('register.setting_password') if translator else 'Setting password'}{Style.RESET_ALL}")
        
        # Fill password
        password_input = page.ele("@name=password")
        print(f"{Fore.CYAN}🔑 {translator.get('register.setting_on_password')}: {password}{Style.RESET_ALL}")
        if password_input:
            password_input.input(password)

        # Click submit button
        submit_button = page.ele("@type=submit")
        if submit_button:
            submit_button.click()
            time.sleep(get_random_wait_time(config, 'submit_wait'))
            
        print(f"{Fore.GREEN}✅ {translator.get('register.password_submitted') if translator else 'Password submitted'}{Style.RESET_ALL}")
        
        return True
        
    except Exception as e:
        print(f"{Fore.RED}❌ {translator.get('register.password_error', error=str(e)) if translator else f'Error setting password: {str(e)}'}{Style.RESET_ALL}")

        return False

def handle_verification_code(browser_tab, email_tab, controller, config, translator=None):
    """Handle verification code"""
    try:
        if translator:
            print(f"\n{Fore.CYAN}🔄 {translator.get('register.waiting_for_verification_code')}{Style.RESET_ALL}")
            
        # Check if using manual input verification code
        if hasattr(controller, 'get_verification_code') and email_tab is None:  # Manual mode
            verification_code = controller.get_verification_code()
            if verification_code:
                # Fill verification code in registration page
                for i, digit in enumerate(verification_code):
                    browser_tab.ele(f"@data-index={i}").input(digit)
                    time.sleep(get_random_wait_time(config, 'verification_code_input'))
                
                print(f"{translator.get('register.verification_success')}")
                time.sleep(get_random_wait_time(config, 'verification_success_wait'))
                
                # Handle last Turnstile verification
                if handle_turnstile(browser_tab, config, translator):
                    if translator:
                        print(f"{Fore.GREEN}✅ {translator.get('register.verification_success')}{Style.RESET_ALL}")
                    time.sleep(get_random_wait_time(config, 'verification_retry_wait'))
                    
                    # Visit settings page
                    print(f"{Fore.CYAN}🔑 {translator.get('register.visiting_url')}: https://www.cursor.com/settings{Style.RESET_ALL}")
                    browser_tab.get("https://www.cursor.com/settings")
                    time.sleep(get_random_wait_time(config, 'settings_page_load_wait'))
                    return True, browser_tab
                    
                return False, None
                
        # Automatic verification code logic
        elif email_tab:
            print(f"{Fore.CYAN}🔄 {translator.get('register.waiting_for_verification_code')}{Style.RESET_ALL}")
            time.sleep(get_random_wait_time(config, 'email_check_initial_wait'))

            # Use existing email_tab to refresh email
            email_tab.refresh_inbox()
            time.sleep(get_random_wait_time(config, 'email_refresh_wait'))

            # Check if there is a verification code email
            if email_tab.check_for_cursor_email():
                verification_code = email_tab.get_verification_code()
                if verification_code:
                    # Fill verification code in registration page
                    for i, digit in enumerate(verification_code):
                        browser_tab.ele(f"@data-index={i}").input(digit)
                        time.sleep(get_random_wait_time(config, 'verification_code_input'))
                    
                    if translator:
                        print(f"{Fore.GREEN}✅ {translator.get('register.verification_success')}{Style.RESET_ALL}")
                    time.sleep(get_random_wait_time(config, 'verification_success_wait'))
                    
                    # Handle last Turnstile verification
                    if handle_turnstile(browser_tab, config, translator):
                        if translator:
                            print(f"{Fore.GREEN}✅ {translator.get('register.verification_success')}{Style.RESET_ALL}")
                        time.sleep(get_random_wait_time(config, 'verification_retry_wait'))
                        
                        # Visit settings page
                        if translator:
                            print(f"{Fore.CYAN}🔑 {translator.get('register.visiting_url')}: https://www.cursor.com/settings{Style.RESET_ALL}")
                        browser_tab.get("https://www.cursor.com/settings")
                        time.sleep(get_random_wait_time(config, 'settings_page_load_wait'))
                        return True, browser_tab
                        
                    else:
                        if translator:
                            print(f"{Fore.RED}❌ {translator.get('register.verification_failed')}{Style.RESET_ALL}")
                        else:
                            print("最后一次验证失败")
                        return False, None
                        
            # Get verification code, set timeout
            verification_code = None
            max_attempts = 20
            retry_interval = get_random_wait_time(config, 'retry_interval')  # Use get_random_wait_time
            start_time = time.time()
            timeout = float(config.get('Timing', 'max_timeout', fallback='160'))  # This can be kept unchanged because it is a fixed value

            if translator:
                print(f"{Fore.CYAN}{translator.get('register.start_getting_verification_code')}{Style.RESET_ALL}")
            
            for attempt in range(max_attempts):
                # Check if timeout
                if time.time() - start_time > timeout:
                    if translator:
                        print(f"{Fore.RED}❌ {translator.get('register.verification_timeout')}{Style.RESET_ALL}")
                    break
                    
                verification_code = controller.get_verification_code()
                if verification_code:
                    if translator:
                        print(f"{Fore.GREEN}✅ {translator.get('register.verification_success')}{Style.RESET_ALL}")
                    break
                    
                remaining_time = int(timeout - (time.time() - start_time))
                if translator:
                    print(f"{Fore.CYAN}{translator.get('register.try_get_code', attempt=attempt + 1, time=remaining_time)}{Style.RESET_ALL}")
                
                # Refresh email
                email_tab.refresh_inbox()
                time.sleep(retry_interval)  # Use get_random_wait_time
            
            if verification_code:
                # Fill verification code in registration page
                for i, digit in enumerate(verification_code):
                    browser_tab.ele(f"@data-index={i}").input(digit)
                    time.sleep(get_random_wait_time(config, 'verification_code_input'))
                
                if translator:
                    print(f"{Fore.GREEN}✅ {translator.get('register.verification_success')}{Style.RESET_ALL}")
                time.sleep(get_random_wait_time(config, 'verification_success_wait'))
                
                # Handle last Turnstile verification
                if handle_turnstile(browser_tab, config, translator):
                    if translator:
                        print(f"{Fore.GREEN}✅ {translator.get('register.verification_success')}{Style.RESET_ALL}")
                    time.sleep(get_random_wait_time(config, 'verification_retry_wait'))
                    
                    # Visit settings page
                    if translator:
                        print(f"{Fore.CYAN}{translator.get('register.visiting_url')}: https://www.cursor.com/settings{Style.RESET_ALL}")
                    browser_tab.get("https://www.cursor.com/settings")
                    time.sleep(get_random_wait_time(config, 'settings_page_load_wait'))
                    
                    # Return success directly, let cursor_register.py handle account information acquisition
                    return True, browser_tab
                    
                else:
                    if translator:
                        print(f"{Fore.RED}❌ {translator.get('register.verification_failed')}{Style.RESET_ALL}")
                    return False, None
                
            return False, None
            
    except Exception as e:
        if translator:
            print(f"{Fore.RED}❌ {translator.get('register.verification_error', error=str(e))}{Style.RESET_ALL}")
        return False, None

def handle_sign_in(browser_tab, email, password, translator=None):
    """Handle login process"""
    try:
        # Check if on login page
        sign_in_header = browser_tab.ele('xpath://h1[contains(text(), "Sign in")]')
        if not sign_in_header:
            return True  # If not on login page, it means login is successful
            
        print(f"{Fore.CYAN}检测到登录页面，开始登录...{Style.RESET_ALL}")
        
        # Fill email
        email_input = browser_tab.ele('@name=email')
        if email_input:
            email_input.input(email)
            time.sleep(1)
            
            # Click Continue
            continue_button = browser_tab.ele('xpath://button[contains(@class, "BrandedButton") and text()="Continue"]')
            if continue_button:
                continue_button.click()
                time.sleep(2)
                
                # Handle Turnstile verification
                if handle_turnstile(browser_tab, translator):
                    # Fill password
                    password_input = browser_tab.ele('@name=password')
                    if password_input:
                        password_input.input(password)
                        time.sleep(1)
                        
                        # Click Sign in
                        sign_in_button = browser_tab.ele('xpath://button[@name="intent" and @value="password"]')
                        if sign_in_button:
                            sign_in_button.click()
                            time.sleep(2)
                            
                            # Handle last Turnstile verification
                            if handle_turnstile(browser_tab, translator):
                                print(f"{Fore.GREEN}Login successful!{Style.RESET_ALL}")
                                time.sleep(3)
                                return True
                                
        print(f"{Fore.RED}Login failed{Style.RESET_ALL}")
        return False
        
    except Exception as e:
        print(f"{Fore.RED}Login process error: {str(e)}{Style.RESET_ALL}")
        return False

def main(email=None, password=None, first_name=None, last_name=None, email_tab=None, controller=None, translator=None):
    """
    主函数，执行Cursor账号注册流程
    
    接收账号信息、邮箱标签页和翻译器实例，协调整个注册过程，
    包括浏览器启动、表单填写、验证码处理等步骤。
    
    参数:
        email (str, 可选): 用户邮箱地址
        password (str, 可选): 用户密码
        first_name (str, 可选): 用户名
        last_name (str, 可选): 用户姓
        email_tab (WebDriver, 可选): 邮箱标签页实例，用于自动获取验证码
        controller (object, 可选): 控制器实例，用于手动获取验证码
        translator (Translator, 可选): 翻译器实例，用于多语言支持
        
    返回值:
        tuple: (bool, WebDriver) 注册是否成功及浏览器标签页实例
    """
    global _translator
    global _chrome_process_ids
    _translator = translator  # 保存翻译器到全局变量，便于其他函数使用
    _chrome_process_ids = []  # 重置Chrome进程ID列表，用于后续清理
    
    # 注册信号处理器，确保程序被中断时能够清理资源
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    page = None
    success = False
    try:
        # 设置并启动WebDriver
        config, page = setup_driver(translator)
        if translator:
            print(f"{Fore.CYAN}🚀 {translator.get('register.browser_started')}{Style.RESET_ALL}")
        
        # 设置注册页面URL
        url = "https://authenticator.cursor.sh/sign-up"
        
        # 访问注册页面，模拟人类输入行为
        simulate_human_input(page, url, config, translator)
        if translator:
            print(f"{Fore.CYAN}🔄 {translator.get('register.waiting_for_page_load')}{Style.RESET_ALL}")
        # 等待页面加载，使用随机等待时间增加真实性
        time.sleep(get_random_wait_time(config, 'page_load_wait'))
        
        # 如果未提供账号信息，则生成随机信息
        if not all([email, password, first_name, last_name]):
            # 生成随机名字和姓氏
            first_name = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=6)).capitalize()
            last_name = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=6)).capitalize()
            # 生成随机邮箱
            email = f"{first_name.lower()}{random.randint(100,999)}@example.com"
            # 生成随机密码
            password = generate_password()
            
            # 将生成的账号信息保存到文件中，便于后续使用
            with open('test_accounts.txt', 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"Email: {email}\n")
                f.write(f"Password: {password}\n")
                f.write(f"{'='*50}\n")
        
        # 填写注册表单（名字、姓氏、邮箱）
        if fill_signup_form(page, first_name, last_name, email, config, translator):
            if translator:
                print(f"\n{Fore.GREEN}✅ {translator.get('register.form_submitted')}{Style.RESET_ALL}")
            
            # 处理第一次Turnstile人机验证
            if handle_turnstile(page, config, translator):
                if translator:
                    print(f"\n{Fore.GREEN}✅ {translator.get('register.first_verification_passed')}{Style.RESET_ALL}")
                
                # 填写密码
                if fill_password(page, password, config, translator):
                    if translator:
                        print(f"\n{Fore.CYAN}🔄 {translator.get('register.waiting_for_second_verification')}{Style.RESET_ALL}")
                                        
                    # 处理第二次Turnstile人机验证
                    if handle_turnstile(page, config, translator):
                        if translator:
                            print(f"\n{Fore.CYAN}🔄 {translator.get('register.waiting_for_verification_code')}{Style.RESET_ALL}")
                        # 处理邮箱验证码
                        if handle_verification_code(page, email_tab, controller, config, translator):
                            success = True
                            return True, page  # 注册成功，返回成功状态和浏览器实例
                        else:
                            print(f"\n{Fore.RED}❌ {translator.get('register.verification_code_processing_failed') if translator else 'Verification code processing failed'}{Style.RESET_ALL}")
                    else:
                        print(f"\n{Fore.RED}❌ {translator.get('register.second_verification_failed') if translator else 'Second verification failed'}{Style.RESET_ALL}")
                else:
                    print(f"\n{Fore.RED}❌ {translator.get('register.second_verification_failed') if translator else 'Second verification failed'}{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.RED}❌ {translator.get('register.first_verification_failed') if translator else 'First verification failed'}{Style.RESET_ALL}")
        
        return False, None  # 注册失败，返回失败状态和None
        
    except Exception as e:
        # 捕获并处理所有异常
        print(f"发生错误: {e}")
        return False, None
    finally:
        # 确保在失败时清理资源
        if page and not success:  # 只有在失败时才清理资源
            try:
                page.quit()  # 关闭浏览器
            except:
                pass
            cleanup_chrome_processes(translator)  # 清理残留的Chrome进程
if __name__ == "__main__":
    main()  # Run without parameters, use randomly generated information 