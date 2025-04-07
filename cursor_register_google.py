"""
cursor_register_google.py - Google OAuth注册模块

这个模块提供了使用Google OAuth认证方式注册Cursor账号的功能。
它是一个简单的包装器，调用oauth_auth模块中的主函数来完成注册过程。

主要功能:
- 使用Google账号注册Cursor
- 处理OAuth认证流程
- 支持多语言界面
"""

# 导入oauth_auth模块中的main函数并重命名为oauth_main
# 这个函数负责处理OAuth认证的全部流程
from oauth_auth import main as oauth_main

def main(translator=None):
    """
    处理Google OAuth注册
    
    调用oauth_auth模块的主函数，并指定使用'google'作为认证类型。
    
    参数:
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        bool: 注册成功返回True，失败返回False
    """
    # 调用oauth_main函数，传递'google'作为认证类型和翻译器对象
    oauth_main('google', translator) 