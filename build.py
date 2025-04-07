"""
build.py - 程序构建模块

这个模块负责将程序打包成可执行文件，主要功能包括：
- 清理旧的构建缓存
- 显示构建进度和动画
- 根据不同操作系统生成相应的可执行文件
- 使用PyInstaller进行打包

运行此脚本可以自动将项目打包成独立的可执行程序。
"""
import warnings
import os
import platform
import subprocess
import time
import threading
import shutil
from logo import print_logo
from dotenv import load_dotenv

# Ignore specific warnings
warnings.filterwarnings("ignore", category=SyntaxWarning)

class LoadingAnimation:
    """
    加载动画类
    
    在终端中显示动画效果，表示正在进行构建过程，
    提供视觉反馈，让用户知道程序仍在运行。
    """
    def __init__(self):
        """
        初始化加载动画
        
        创建一个新的加载动画实例，设置初始状态和线程。
        """
        self.is_running = False
        self.animation_thread = None

    def start(self, message="Building"):
        """
        启动加载动画
        
        创建并启动一个新线程来显示动画。
        
        参数:
            message (str): 显示在动画前的消息文本
        """
        self.is_running = True
        self.animation_thread = threading.Thread(target=self._animate, args=(message,))
        self.animation_thread.start()

    def stop(self):
        """
        停止加载动画
        
        终止动画线程并清理终端行。
        """
        self.is_running = False
        if self.animation_thread:
            self.animation_thread.join()
        print("\r" + " " * 70 + "\r", end="", flush=True)

    def _animate(self, message):
        """
        动画显示逻辑
        
        在终端中循环显示旋转动画字符。
        
        参数:
            message (str): 显示在动画前的消息文本
        """
        animation = "|/-\\"
        idx = 0
        while self.is_running:
            print(f"\r{message} {animation[idx % len(animation)]}", end="", flush=True)
            idx += 1
            time.sleep(0.1)

def progress_bar(progress, total, prefix="", length=50):
    """
    显示进度条
    
    在终端中显示一个文本进度条，表示完成的百分比。
    
    参数:
        progress (int): 当前进度值
        total (int): 总进度值
        prefix (str): 进度条前显示的文本
        length (int): 进度条的长度（字符数）
    """
    filled = int(length * progress // total)
    bar = "█" * filled + "░" * (length - filled)
    percent = f"{100 * progress / total:.1f}"
    print(f"\r{prefix} |{bar}| {percent}% Complete", end="", flush=True)
    if progress == total:
        print()

def simulate_progress(message, duration=1.0, steps=20):
    """
    模拟进度条
    
    显示一个模拟的进度条，用于表示正在进行的过程。
    
    参数:
        message (str): 显示的消息
        duration (float): 完成进度的总时间（秒）
        steps (int): 进度条的步数
    """
    print(f"\033[94m{message}\033[0m")
    for i in range(steps + 1):
        time.sleep(duration / steps)
        progress_bar(i, steps, prefix="Progress:", length=40)

def build():
    """
    主构建函数
    
    执行整个构建过程，包括:
    1. 清理旧的构建缓存
    2. 获取版本信息
    3. 根据操作系统类型设置输出文件名
    4. 调用PyInstaller进行打包
    5. 验证输出文件是否存在
    
    返回值:
        bool: 构建成功返回True，失败返回False
    """
    # Clean screen
    os.system("cls" if platform.system().lower() == "windows" else "clear")
    
    # Display logo
    print_logo()
    
    # Clean PyInstaller cache
    print("\033[93m🧹 Cleaning build cache...\033[0m")
    if os.path.exists('build'):
        shutil.rmtree('build')
    
    # Reload environment variables to ensure getting the latest version
    load_dotenv(override=True)
    version = os.getenv('VERSION', '1.0.0')
    print(f"\033[93m📦 Building version: v{version}\033[0m")

    try:
        simulate_progress("Preparing build environment...", 0.5)
        
        loading = LoadingAnimation()
        loading.start("Building in progress")
        
        # Set output name based on system type
        system = platform.system().lower()
        if system == "windows":
            os_type = "windows"
            ext = ".exe"
        elif system == "linux":
            os_type = "linux"
            ext = ""
        else:  # Darwin
            os_type = "mac"
            ext = ""
            
        output_name = f"CursorFreeVIP_{version}_{os_type}"
        
        # Build command
        build_command = f'pyinstaller --clean --noconfirm build.spec'
        output_path = os.path.join('dist', f'{output_name}{ext}')
        
        os.system(build_command)
        
        loading.stop()

        if os.path.exists(output_path):
            print(f"\n\033[92m✅ Build completed!")
            print(f"📦 Executable file located: {output_path}\033[0m")
        else:
            print("\n\033[91m❌ Build failed: Output file not found\033[0m")
            return False

    except Exception as e:
        if loading:
            loading.stop()
        print(f"\n\033[91m❌ Build process error: {str(e)}\033[0m")
        return False

    return True

if __name__ == "__main__":
    build() 