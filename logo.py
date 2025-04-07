"""
logo.py - 程序标志和版本显示模块

这个模块负责显示程序的ASCII艺术标志和版本信息。
主要功能包括：
- 从环境变量获取版本号
- 生成格式化的彩色ASCII标志
- 居中显示文本，支持中文字符处理
- 提供统一的标志打印函数
"""
from colorama import Fore, Style, init
from dotenv import load_dotenv
import os
import shutil
import re

# Get the current script directory
current_dir = os.path.dirname(os.path.abspath(__file__))
# Build the full path to the .env file
env_path = os.path.join(current_dir, '.env')

# Load environment variables, specifying the .env file path
load_dotenv(env_path)
# Get the version number, using the default value if not found
version = os.getenv('VERSION', '1.0.0')

# Initialize colorama
init()

# get terminal width
def get_terminal_width():
    """
    获取当前终端的宽度。
    
    尝试使用shutil获取终端宽度，如果失败则使用默认值80。
    
    返回值:
        int: 终端宽度（字符数）
    """
    try:
        columns, _ = shutil.get_terminal_size()/2
        return columns
    except:
        return 80  # default width

# center display text (not handling Chinese characters)
def center_multiline_text(text, handle_chinese=False):
    """
    对多行文本进行居中处理。
    
    计算每行文本的实际显示宽度（考虑ANSI颜色代码和中文字符），
    并添加适当的空格使其在终端中居中显示。
    
    参数:
        text (str): 要居中的多行文本
        handle_chinese (bool): 是否处理中文字符宽度（中文字符占两个位置）
        
    返回值:
        str: 居中后的文本
        
    说明:
        - 会移除ANSI颜色代码以计算实际显示宽度
        - 当handle_chinese=True时，会考虑中文字符占用两个位置的情况
    """
    width = get_terminal_width()
    lines = text.split('\n')
    centered_lines = []
    
    for line in lines:
        # calculate actual display width (remove ANSI color codes)
        clean_line = line
        for color in [Fore.CYAN, Fore.YELLOW, Fore.GREEN, Fore.RED, Fore.BLUE, Style.RESET_ALL]:
            clean_line = clean_line.replace(color, '')
        
        # remove all ANSI escape sequences to get the actual length
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_line = ansi_escape.sub('', clean_line)
        
        # calculate display width
        if handle_chinese:
            # consider Chinese characters occupying two positions
            display_width = 0
            for char in clean_line:
                if ord(char) > 127:  # non-ASCII characters
                    display_width += 2
                else:
                    display_width += 1
        else:
            # not handling Chinese characters
            display_width = len(clean_line)
        
        # calculate the number of spaces to add
        padding = max(0, (width - display_width) // 2)
        centered_lines.append(' ' * padding + line)
    
    return '\n'.join(centered_lines)

# original LOGO text - ASCII艺术风格的Cursor Pro标志
LOGO_TEXT = f"""{Fore.CYAN}
   ██████╗██╗   ██╗██████╗ ███████╗ ██████╗ ██████╗      ██████╗ ██████╗  ██████╗   
  ██╔════╝██║   ██║██╔══██╗██╔════╝██╔═══██╗██╔══██╗     ██╔══██╗██╔══██╗██╔═══██╗  
  ██║     ██║   ██║██████╔╝███████╗██║   ██║██████╔╝     ██████╔╝██████╔╝██║   ██║  
  ██║     ██║   ██║██╔══██╗╚════██║██║   ██║██╔══██╗     ██╔═══╝ ██╔══██╗██║   ██║  
  ╚██████╗╚██████╔╝██║  ██║███████║╚██████╔╝██║  ██║     ██║     ██║  ██║╚██████╔╝  
   ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝     ╚═╝     ╚═╝  ╚═╝ ╚═════╝  
{Style.RESET_ALL}"""

# 程序描述，显示版本号和作者信息
DESCRIPTION_TEXT = f"""{Fore.YELLOW}
Pro Version Activator v{version}{Fore.GREEN}
Author: Pin Studios (yeongpin)"""

# 贡献者列表
CONTRIBUTORS_TEXT = f"""{Fore.BLUE}
Contributors:
BasaiCorp  aliensb  handwerk2016  Nigel1992
UntaDotMy  RenjiYuusei  imbajin  ahmed98Osama
bingoohuang  mALIk-sHAHId  MFaiqKhan  httpmerak
muhammedfurkan plamkatawe Lucaszmv
"""

# 其他信息，包括GitHub链接和语言切换提示
OTHER_INFO_TEXT = f"""{Fore.YELLOW}
Github: https://github.com/yeongpin/cursor-free-vip{Fore.RED}
Press 8 to change language | 按下 8 键切换语言{Style.RESET_ALL}"""

# 对所有文本进行居中处理
CURSOR_LOGO = center_multiline_text(LOGO_TEXT, handle_chinese=False)
CURSOR_DESCRIPTION = center_multiline_text(DESCRIPTION_TEXT, handle_chinese=False)
CURSOR_CONTRIBUTORS = center_multiline_text(CONTRIBUTORS_TEXT, handle_chinese=False)
CURSOR_OTHER_INFO = center_multiline_text(OTHER_INFO_TEXT, handle_chinese=True)

def print_logo():
    """
    打印程序标志和相关信息。
    
    这个函数会在终端中显示:
    1. ASCII艺术风格的Cursor Pro标志
    2. 版本和作者信息
    3. GitHub链接和语言切换提示
    
    一般在程序启动时调用，作为欢迎界面。
    """
    print(CURSOR_LOGO)
    print(CURSOR_DESCRIPTION)
    # print(CURSOR_CONTRIBUTORS)
    print(CURSOR_OTHER_INFO)

if __name__ == "__main__":
    print_logo()
