"""
quit_cursor.py - Cursor进程终止模块

这个模块负责安全地结束Cursor相关进程，主要功能包括：
- 检测系统中运行的Cursor进程
- 尝试优雅地终止这些进程（先发送终止信号，等待一段时间）
- 提供超时机制和状态反馈
- 支持多语言显示

适用于需要重启Cursor或清理Cursor进程的情况。
"""
import psutil
import time
from colorama import Fore, Style, init
import sys
import os

# Initialize colorama
init()

# Define emoji constants
EMOJI = {
    "PROCESS": "⚙️",
    "SUCCESS": "✅",
    "ERROR": "❌",
    "INFO": "ℹ️",
    "WAIT": "⏳"
}

class CursorQuitter:
    """
    Cursor进程终止管理类
    
    提供安全、可控的方式来终止系统中运行的Cursor进程。
    使用非强制的方式先尝试优雅关闭，给进程一定时间自行关闭。
    """
    def __init__(self, timeout=5, translator=None):
        """
        初始化Cursor终止器
        
        参数:
            timeout (int): 等待进程自行关闭的最大时间（秒）
            translator: 翻译器对象，用于多语言支持，可以为None
        """
        self.timeout = timeout
        self.translator = translator  # Use the passed translator
        
    def quit_cursor(self):
        """
        优雅地关闭Cursor进程
        
        流程:
        1. 查找所有Cursor相关进程
        2. 对每个进程发送终止信号
        3. 等待进程自行关闭（最长等待self.timeout秒）
        4. 如果超时后仍有进程运行，报告失败
        
        返回值:
            bool: 如果所有进程成功终止返回True，否则返回False
        """
        try:
            print(f"{Fore.CYAN}{EMOJI['PROCESS']} {self.translator.get('quit_cursor.start')}...{Style.RESET_ALL}")
            cursor_processes = []
            
            # Collect all Cursor processes
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'].lower() in ['cursor.exe', 'cursor']:
                        cursor_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if not cursor_processes:
                print(f"{Fore.GREEN}{EMOJI['INFO']} {self.translator.get('quit_cursor.no_process')}{Style.RESET_ALL}")
                return True

            # Gently request processes to terminate
            for proc in cursor_processes:
                try:
                    if proc.is_running():
                        print(f"{Fore.YELLOW}{EMOJI['PROCESS']} {self.translator.get('quit_cursor.terminating', pid=proc.pid)}...{Style.RESET_ALL}")
                        proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Wait for processes to terminate naturally
            print(f"{Fore.CYAN}{EMOJI['WAIT']} {self.translator.get('quit_cursor.waiting')}...{Style.RESET_ALL}")
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                still_running = []
                for proc in cursor_processes:
                    try:
                        if proc.is_running():
                            still_running.append(proc)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                if not still_running:
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('quit_cursor.success')}{Style.RESET_ALL}")
                    return True
                    
                time.sleep(0.5)
                
            # If processes are still running after timeout
            if still_running:
                process_list = ", ".join([str(p.pid) for p in still_running])
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('quit_cursor.timeout', pids=process_list)}{Style.RESET_ALL}")
                return False
                
            return True

        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('quit_cursor.error', error=str(e))}{Style.RESET_ALL}")
            return False

def quit_cursor(translator=None, timeout=5):
    """
    便捷函数，用于直接调用终止Cursor进程的功能
    
    这是一个简单的封装函数，创建CursorQuitter实例并调用其quit_cursor方法。
    
    参数:
        translator: 翻译器对象，用于多语言支持，可以为None
        timeout (int): 等待进程自行关闭的最大时间（秒）
        
    返回值:
        bool: 如果所有进程成功终止返回True，否则返回False
    """
    quitter = CursorQuitter(timeout, translator)
    return quitter.quit_cursor()

if __name__ == "__main__":
    # If run directly, use the default translator
    from main import translator as main_translator
    quit_cursor(main_translator)