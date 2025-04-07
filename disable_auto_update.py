"""
disable_auto_update.py - Cursor自动更新禁用模块

本模块提供了禁用Cursor自动更新功能的实现，主要功能包括：
- 删除Cursor更新程序目录
- 清空更新配置文件
- 创建阻止文件防止更新
- 修改产品配置文件移除更新URL

通过这些方法的组合使用，可以有效防止Cursor自动更新，
保持当前安装的版本不变。
"""
import os
import sys
import platform
import shutil
from colorama import Fore, Style, init
import subprocess
from config import get_config
import re
import tempfile

# Initialize colorama
init()

# Define emoji constants
EMOJI = {
    "PROCESS": "🔄",
    "SUCCESS": "✅",
    "ERROR": "❌",
    "INFO": "ℹ️",
    "FOLDER": "📁",
    "FILE": "📄",
    "STOP": "🛑",
    "CHECK": "✔️"
}

class AutoUpdateDisabler:
    """
    自动更新禁用类
    
    负责处理禁用Cursor自动更新的各种操作，包括：
    - 结束Cursor进程
    - 删除更新器目录
    - 清空更新配置文件
    - 创建阻止文件
    - 移除更新URL
    
    根据不同操作系统自动选择适当的文件路径和禁用方法。
    """
    def __init__(self, translator=None):
        """
        初始化自动更新禁用器
        
        设置各种文件路径，包括更新程序目录、更新配置文件和产品信息文件。
        会从配置文件获取路径，如果配置不可用则使用默认路径。
        
        参数:
            translator: 翻译器对象，用于多语言支持，可以为None
        """
        self.translator = translator
        self.system = platform.system()
        
        # Get path from configuration file
        config = get_config(translator)
        if config:
            if self.system == "Windows":
                self.updater_path = config.get('WindowsPaths', 'updater_path', fallback=os.path.join(os.getenv("LOCALAPPDATA", ""), "cursor-updater"))
                self.update_yml_path = config.get('WindowsPaths', 'update_yml_path', fallback=os.path.join(os.getenv("LOCALAPPDATA", ""), "Programs", "Cursor", "resources", "app", "update.yml"))
                self.product_json_path = config.get('WindowsPaths', 'product_json_path', fallback=os.path.join(os.getenv("LOCALAPPDATA", ""), "Programs", "Cursor", "resources", "app", "product.json"))
            elif self.system == "Darwin":
                self.updater_path = config.get('MacPaths', 'updater_path', fallback=os.path.expanduser("~/Library/Application Support/cursor-updater"))
                self.update_yml_path = config.get('MacPaths', 'update_yml_path', fallback="/Applications/Cursor.app/Contents/Resources/app-update.yml")
                self.product_json_path = config.get('MacPaths', 'product_json_path', fallback="/Applications/Cursor.app/Contents/Resources/app/product.json")
            elif self.system == "Linux":
                self.updater_path = config.get('LinuxPaths', 'updater_path', fallback=os.path.expanduser("~/.config/cursor-updater"))
                self.update_yml_path = config.get('LinuxPaths', 'update_yml_path', fallback=os.path.expanduser("~/.config/cursor/resources/app-update.yml"))
                self.product_json_path = config.get('LinuxPaths', 'product_json_path', fallback=os.path.expanduser("~/.config/cursor/resources/app/product.json"))
        else:
            # If configuration loading fails, use default paths
            self.updater_paths = {
                "Windows": os.path.join(os.getenv("LOCALAPPDATA", ""), "cursor-updater"),
                "Darwin": os.path.expanduser("~/Library/Application Support/cursor-updater"),
                "Linux": os.path.expanduser("~/.config/cursor-updater")
            }
            self.updater_path = self.updater_paths.get(self.system)
            
            self.update_yml_paths = {
                "Windows": os.path.join(os.getenv("LOCALAPPDATA", ""), "Programs", "Cursor", "resources", "app", "update.yml"),
                "Darwin": "/Applications/Cursor.app/Contents/Resources/app-update.yml",
                "Linux": os.path.expanduser("~/.config/cursor/resources/app-update.yml")
            }
            self.update_yml_path = self.update_yml_paths.get(self.system)

            self.product_json_paths = {
                "Windows": os.path.join(os.getenv("LOCALAPPDATA", ""), "Programs", "Cursor", "resources", "app", "product.json"),
                "Darwin": "/Applications/Cursor.app/Contents/Resources/app/product.json",
                "Linux": os.path.expanduser("~/.config/cursor/resources/app/product.json")
            }
            self.product_json_path = self.product_json_paths.get(self.system)

    def _remove_update_url(self):
        """
        移除更新URL
        
        修改product.json文件，删除所有更新相关的URL，
        防止应用检查和下载更新。会创建原文件备份。
        
        返回值:
            bool: 操作成功返回True，失败返回False
        """
        try:
            original_stat = os.stat(self.product_json_path)
            original_mode = original_stat.st_mode
            original_uid = original_stat.st_uid
            original_gid = original_stat.st_gid

            with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_file:
                with open(self.product_json_path, "r", encoding="utf-8") as product_json_file:
                    content = product_json_file.read()
                
                patterns = {
                    r"https://api2.cursor.sh/aiserver.v1.AuthService/DownloadUpdate": r"",
                    r"https://api2.cursor.sh/updates": r"",
                    r"http://cursorapi.com/updates": r"",
                }
                
                for pattern, replacement in patterns.items():
                    content = re.sub(pattern, replacement, content)

                tmp_file.write(content)
                tmp_path = tmp_file.name

            shutil.copy2(self.product_json_path, self.product_json_path + ".old")
            shutil.move(tmp_path, self.product_json_path)

            os.chmod(self.product_json_path, original_mode)
            if os.name != "nt":
                os.chown(self.product_json_path, original_uid, original_gid)

            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.file_modified')}{Style.RESET_ALL}")
            return True

        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.modify_file_failed', error=str(e))}{Style.RESET_ALL}")
            if "tmp_path" in locals():
                os.unlink(tmp_path)
            return False

    def _kill_cursor_processes(self):
        """
        结束所有Cursor进程
        
        在执行更新禁用操作前，需要确保所有Cursor进程已关闭，
        以避免文件锁定和权限问题。根据不同操作系统使用不同的命令。
        
        返回值:
            bool: 操作成功返回True，失败返回False
        """
        try:
            print(f"{Fore.CYAN}{EMOJI['PROCESS']} {self.translator.get('update.killing_processes') if self.translator else '正在结束 Cursor 进程...'}{Style.RESET_ALL}")
            
            if self.system == "Windows":
                subprocess.run(['taskkill', '/F', '/IM', 'Cursor.exe', '/T'], capture_output=True)
            else:
                subprocess.run(['pkill', '-f', 'Cursor'], capture_output=True)
                
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('update.processes_killed') if self.translator else 'Cursor 进程已结束'}{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('update.kill_process_failed', error=str(e)) if self.translator else f'结束进程失败: {e}'}{Style.RESET_ALL}")
            return False

    def _remove_updater_directory(self):
        """
        删除更新程序目录
        
        完全删除Cursor更新程序目录，阻止更新程序的运行。
        如果目录被锁定，则会跳过并继续执行其他操作。
        
        返回值:
            bool: 操作成功返回True，失败返回False
        """
        try:
            updater_path = self.updater_path
            if not updater_path:
                raise OSError(self.translator.get('update.unsupported_os', system=self.system) if self.translator else f"不支持的操作系统: {self.system}")

            print(f"{Fore.CYAN}{EMOJI['FOLDER']} {self.translator.get('update.removing_directory') if self.translator else '正在删除更新程序目录...'}{Style.RESET_ALL}")
            
            if os.path.exists(updater_path):
                try:
                    if os.path.isdir(updater_path):
                        shutil.rmtree(updater_path)
                    else:
                        os.remove(updater_path)
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('update.directory_removed') if self.translator else '更新程序目录已删除'}{Style.RESET_ALL}")
                except PermissionError:
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('update.directory_locked', path=updater_path) if self.translator else f'更新程序目录已被锁定，跳过删除: {updater_path}'}{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('update.remove_directory_failed', error=str(e)) if self.translator else f'删除目录失败: {e}'}{Style.RESET_ALL}")
            return True
    
    def _clear_update_yml_file(self):
        """
        清空更新配置文件
        
        将update.yml文件内容清空，防止应用检索更新信息。
        如果文件被锁定，则会跳过并继续执行其他操作。
        
        返回值:
            bool: 操作成功返回True，失败返回False
        """
        try:
            update_yml_path = self.update_yml_path
            if not update_yml_path:
                raise OSError(self.translator.get('update.unsupported_os', system=self.system) if self.translator else f"不支持的操作系统: {self.system}")
            
            print(f"{Fore.CYAN}{EMOJI['FILE']} {self.translator.get('update.clearing_update_yml') if self.translator else '正在清空更新配置文件...'}{Style.RESET_ALL}")
            
            if os.path.exists(update_yml_path):
                try:
                    with open(update_yml_path, 'w') as f:
                        f.write('')
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('update.update_yml_cleared') if self.translator else '更新配置文件已清空'}{Style.RESET_ALL}")
                except PermissionError:
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('update.yml_locked') if self.translator else '更新配置文件已被锁定，跳过清空'}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('update.update_yml_not_found') if self.translator else '更新配置文件不存在'}{Style.RESET_ALL}")
            return True
                
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('update.clear_update_yml_failed', error=str(e)) if self.translator else f'清空更新配置文件失败: {e}'}{Style.RESET_ALL}")
            return False

    def _create_blocking_file(self):
        """
        创建阻止文件
        
        创建只读文件替代更新程序目录和配置文件，
        防止应用创建或修改这些文件，从而阻止更新过程。
        
        返回值:
            bool: 操作成功返回True，失败返回False
        """
        try:
            # 检查 updater_path
            updater_path = self.updater_path
            if not updater_path:
                raise OSError(self.translator.get('update.unsupported_os', system=self.system) if self.translator else f"不支持的操作系统: {self.system}")

            print(f"{Fore.CYAN}{EMOJI['FILE']} {self.translator.get('update.creating_block_file') if self.translator else '正在创建阻止文件...'}{Style.RESET_ALL}")
            
            # 创建 updater_path 阻止文件
            try:
                os.makedirs(os.path.dirname(updater_path), exist_ok=True)
                open(updater_path, 'w').close()
                
                # 设置 updater_path 为只读
                if self.system == "Windows":
                    os.system(f'attrib +r "{updater_path}"')
                else:
                    os.chmod(updater_path, 0o444)  # 设置为只读
                
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('update.block_file_created') if self.translator else '阻止文件已创建'}: {updater_path}{Style.RESET_ALL}")
            except PermissionError:
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('update.block_file_locked') if self.translator else '阻止文件已被锁定，跳过创建'}{Style.RESET_ALL}")
            
            # 检查 update_yml_path
            update_yml_path = self.update_yml_path
            if update_yml_path and os.path.exists(os.path.dirname(update_yml_path)):
                try:
                    # 创建 update_yml_path 阻止文件
                    with open(update_yml_path, 'w') as f:
                        f.write('# This file is locked to prevent auto-updates\nversion: 0.0.0\n')
                    
                    # 设置 update_yml_path 为只读
                    if self.system == "Windows":
                        os.system(f'attrib +r "{update_yml_path}"')
                    else:
                        os.chmod(update_yml_path, 0o444)  # 设置为只读
                    
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('update.yml_locked') if self.translator else '更新配置文件已锁定'}: {update_yml_path}{Style.RESET_ALL}")
                except PermissionError:
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('update.yml_already_locked') if self.translator else '更新配置文件已被锁定，跳过修改'}{Style.RESET_ALL}")
            
            return True
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('update.create_block_file_failed', error=str(e)) if self.translator else f'创建阻止文件失败: {e}'}{Style.RESET_ALL}")
            return True  # 返回 True 以继续执行后续步骤

    def disable_auto_update(self):
        """
        禁用自动更新
        
        执行完整的禁用自动更新流程，包括结束进程、
        删除目录、清空配置、创建阻止文件和移除更新URL。
        综合使用多种方法确保更新被彻底禁用。
        
        返回值:
            bool: 所有操作都成功完成返回True，否则返回False
        """
        try:
            print(f"{Fore.CYAN}{EMOJI['STOP']} {self.translator.get('update.disabling_auto_update') if self.translator else '正在禁用 Cursor 自动更新...'}{Style.RESET_ALL}")
            
            self._kill_cursor_processes()
            self._remove_updater_directory()
            self._clear_update_yml_file()
            self._create_blocking_file()
            self._remove_update_url()
            
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('update.auto_update_disabled') if self.translator else 'Cursor 自动更新已禁用'}{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('update.disable_failed', error=str(e)) if self.translator else f'禁用自动更新失败: {e}'}{Style.RESET_ALL}")
            return False

def run(translator=None):
    """
    运行自动更新禁用程序
    
    创建AutoUpdateDisabler实例并执行禁用流程。
    作为模块的主入口点，可以从其他脚本调用。
    
    参数:
        translator: 翻译器对象，用于多语言支持，可以为None
        
    返回值:
        bool: 禁用操作成功返回True，失败返回False
    """
    print(f"\n{Fore.CYAN}{EMOJI['STOP']} {translator.get('update.disable_auto_update_title') if translator else '禁用 Cursor 自动更新'}{Style.RESET_ALL}")
    
    try:
        disabler = AutoUpdateDisabler(translator)
        result = disabler.disable_auto_update()
        
        if result:
            print(f"{Fore.GREEN}{EMOJI['CHECK']} {translator.get('update.auto_update_disabled_success') if translator else 'Cursor 自动更新已成功禁用'}{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('update.auto_update_disabled_partial') if translator else 'Cursor 自动更新可能未完全禁用，请检查上述错误'}{Style.RESET_ALL}")
        
        return result
        
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('update.unexpected_error', error=str(e)) if translator else f'发生意外错误: {e}'}{Style.RESET_ALL}")
        return False

if __name__ == "__main__":
    run() 