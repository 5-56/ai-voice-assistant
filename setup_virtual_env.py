#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虚拟环境设置工具
自动创建和配置Edge TTS项目的虚拟环境
"""

import subprocess
import sys
import os
from pathlib import Path
import json

class VirtualEnvManager:
    """虚拟环境管理器"""
    
    def __init__(self, project_name="edge_tts_project"):
        self.project_name = project_name
        self.venv_name = "venv"
        self.venv_path = Path(self.venv_name)
        self.requirements_file = "requirements.txt"
        
    def check_python_version(self):
        """检查Python版本"""
        print("🐍 检查Python版本...")
        version = sys.version_info
        print(f"  当前Python版本: {version.major}.{version.minor}.{version.micro}")
        
        if version.major < 3 or (version.major == 3 and version.minor < 7):
            print("❌ Python版本过低，需要3.7+")
            return False
        else:
            print("✅ Python版本符合要求")
            return True
    
    def create_requirements_file(self):
        """创建requirements.txt文件"""
        print("📋 创建requirements.txt文件...")
        
        requirements = [
            "# Edge TTS项目依赖",
            "# 核心TTS功能",
            "edge-tts>=6.1.0",
            "pywin32>=306",
            "",
            "# 音频播放支持",
            "pygame>=2.5.0",
            "playsound==1.2.2",
            "",
            "# GUI界面支持（通常已内置）",
            "# tkinter  # 通常Python自带",
            "",
            "# 系统监控（可选）",
            "psutil>=5.9.0",
            "",
            "# 网络请求支持",
            "requests>=2.28.0",
            "aiohttp>=3.8.0",
            "",
            "# 开发工具（可选）",
            "# pytest>=7.0.0",
            "# black>=22.0.0",
            "# flake8>=5.0.0",
        ]
        
        try:
            with open(self.requirements_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(requirements))
            
            print(f"✅ requirements.txt已创建")
            return True
            
        except Exception as e:
            print(f"❌ 创建requirements.txt失败: {e}")
            return False
    
    def create_virtual_environment(self):
        """创建虚拟环境"""
        print(f"🏗️ 创建虚拟环境: {self.venv_name}")
        
        if self.venv_path.exists():
            print(f"⚠️ 虚拟环境已存在: {self.venv_path}")
            response = input("是否删除并重新创建？(y/N): ").lower().strip()
            if response == 'y':
                print("🗑️ 删除现有虚拟环境...")
                try:
                    import shutil
                    shutil.rmtree(self.venv_path)
                    print("✅ 现有虚拟环境已删除")
                except Exception as e:
                    print(f"❌ 删除失败: {e}")
                    return False
            else:
                print("📦 使用现有虚拟环境")
                return True
        
        try:
            # 创建虚拟环境
            result = subprocess.run([
                sys.executable, "-m", "venv", str(self.venv_path)
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(f"✅ 虚拟环境创建成功: {self.venv_path}")
                return True
            else:
                print(f"❌ 虚拟环境创建失败: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ 虚拟环境创建异常: {e}")
            return False
    
    def get_venv_python(self):
        """获取虚拟环境的Python路径"""
        if os.name == 'nt':  # Windows
            return self.venv_path / "Scripts" / "python.exe"
        else:  # Unix/Linux/macOS
            return self.venv_path / "bin" / "python"
    
    def get_venv_pip(self):
        """获取虚拟环境的pip路径"""
        if os.name == 'nt':  # Windows
            return self.venv_path / "Scripts" / "pip.exe"
        else:  # Unix/Linux/macOS
            return self.venv_path / "bin" / "pip"
    
    def get_activation_script(self):
        """获取激活脚本路径"""
        if os.name == 'nt':  # Windows
            return self.venv_path / "Scripts" / "activate.bat"
        else:  # Unix/Linux/macOS
            return self.venv_path / "bin" / "activate"
    
    def upgrade_pip(self):
        """升级虚拟环境中的pip"""
        print("📦 升级虚拟环境中的pip...")
        
        try:
            venv_python = self.get_venv_python()
            result = subprocess.run([
                str(venv_python), "-m", "pip", "install", "--upgrade", "pip"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print("✅ pip升级成功")
                return True
            else:
                print(f"⚠️ pip升级失败: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ pip升级异常: {e}")
            return False
    
    def install_dependencies(self):
        """安装项目依赖"""
        print("📦 安装项目依赖...")
        
        if not Path(self.requirements_file).exists():
            print(f"❌ 找不到{self.requirements_file}文件")
            return False
        
        try:
            venv_python = self.get_venv_python()
            
            # 设置环境变量解决编码问题
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONUTF8'] = '1'
            
            result = subprocess.run([
                str(venv_python), "-m", "pip", "install", 
                "-r", self.requirements_file,
                "--no-cache-dir"
            ], capture_output=True, text=True, env=env, timeout=300)
            
            if result.returncode == 0:
                print("✅ 依赖安装成功")
                print("📋 安装的包:")
                # 显示安装的包
                self.list_installed_packages()
                return True
            else:
                print(f"❌ 依赖安装失败: {result.stderr}")
                # 尝试逐个安装
                return self.install_dependencies_individually()
                
        except Exception as e:
            print(f"❌ 依赖安装异常: {e}")
            return False
    
    def install_dependencies_individually(self):
        """逐个安装依赖（fallback方案）"""
        print("🔄 尝试逐个安装依赖...")
        
        # 核心依赖列表
        core_packages = [
            "edge-tts",
            "pywin32",
            "requests",
            "aiohttp"
        ]
        
        # 可选依赖列表
        optional_packages = [
            "pygame",
            "playsound==1.2.2",
            "psutil"
        ]
        
        venv_python = self.get_venv_python()
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'
        
        success_count = 0
        
        # 安装核心依赖
        print("📦 安装核心依赖...")
        for package in core_packages:
            try:
                print(f"  安装 {package}...")
                result = subprocess.run([
                    str(venv_python), "-m", "pip", "install", package, "--no-cache-dir"
                ], capture_output=True, text=True, env=env, timeout=120)
                
                if result.returncode == 0:
                    print(f"  ✅ {package} 安装成功")
                    success_count += 1
                else:
                    print(f"  ❌ {package} 安装失败")
                    
            except Exception as e:
                print(f"  ❌ {package} 安装异常: {e}")
        
        # 安装可选依赖
        print("📦 安装可选依赖...")
        for package in optional_packages:
            try:
                print(f"  安装 {package}...")
                result = subprocess.run([
                    str(venv_python), "-m", "pip", "install", package, "--no-cache-dir"
                ], capture_output=True, text=True, env=env, timeout=120)
                
                if result.returncode == 0:
                    print(f"  ✅ {package} 安装成功")
                    success_count += 1
                else:
                    print(f"  ⚠️ {package} 安装失败（可选依赖）")
                    
            except Exception as e:
                print(f"  ⚠️ {package} 安装异常（可选依赖）: {e}")
        
        total_packages = len(core_packages) + len(optional_packages)
        print(f"📊 安装结果: {success_count}/{total_packages} 个包安装成功")
        
        return success_count >= len(core_packages)  # 核心依赖都安装成功就算成功
    
    def list_installed_packages(self):
        """列出已安装的包"""
        try:
            venv_python = self.get_venv_python()
            result = subprocess.run([
                str(venv_python), "-m", "pip", "list"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                packages = []
                for line in lines[2:]:  # 跳过标题行
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            packages.append(f"  • {parts[0]} {parts[1]}")
                
                if packages:
                    for package in packages[:10]:  # 显示前10个
                        print(package)
                    if len(packages) > 10:
                        print(f"  ... 还有 {len(packages) - 10} 个包")
                
        except Exception as e:
            print(f"⚠️ 无法列出已安装包: {e}")
    
    def test_installation(self):
        """测试安装是否成功"""
        print("🧪 测试安装...")
        
        test_script = '''
import sys
print(f"Python版本: {sys.version}")

# 测试核心模块
try:
    import edge_tts
    print("✅ edge_tts 导入成功")
except ImportError as e:
    print(f"❌ edge_tts 导入失败: {e}")

try:
    import win32com.client
    print("✅ win32com 导入成功")
except ImportError as e:
    print(f"❌ win32com 导入失败: {e}")

try:
    import tkinter
    print("✅ tkinter 导入成功")
except ImportError as e:
    print(f"❌ tkinter 导入失败: {e}")

# 测试可选模块
try:
    import pygame
    print("✅ pygame 导入成功")
except ImportError:
    print("⚠️ pygame 未安装（可选）")

try:
    import playsound
    print("✅ playsound 导入成功")
except ImportError:
    print("⚠️ playsound 未安装（可选）")

try:
    import psutil
    print("✅ psutil 导入成功")
except ImportError:
    print("⚠️ psutil 未安装（可选）")

print("🎉 测试完成")
'''
        
        try:
            venv_python = self.get_venv_python()
            result = subprocess.run([
                str(venv_python), "-c", test_script
            ], capture_output=True, text=True, timeout=30)
            
            print("测试结果:")
            print(result.stdout)
            
            if result.returncode == 0:
                return True
            else:
                print(f"测试错误: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            return False
    
    def create_activation_scripts(self):
        """创建激活脚本"""
        print("📝 创建激活脚本...")
        
        # Windows批处理脚本
        bat_script = f'''@echo off
echo 🎵 激活Edge TTS项目虚拟环境
call {self.venv_name}\\Scripts\\activate.bat
echo ✅ 虚拟环境已激活
echo 💡 使用以下命令运行项目:
echo    python enhanced_tts_demo.py
echo    python test_edge_tts_playback.py
echo 🔄 使用 deactivate 命令退出虚拟环境
cmd /k
'''
        
        # PowerShell脚本
        ps1_script = f'''Write-Host "🎵 激活Edge TTS项目虚拟环境" -ForegroundColor Green
& .\\{self.venv_name}\\Scripts\\Activate.ps1
Write-Host "✅ 虚拟环境已激活" -ForegroundColor Green
Write-Host "💡 使用以下命令运行项目:" -ForegroundColor Yellow
Write-Host "   python enhanced_tts_demo.py" -ForegroundColor Cyan
Write-Host "   python test_edge_tts_playback.py" -ForegroundColor Cyan
Write-Host "🔄 使用 deactivate 命令退出虚拟环境" -ForegroundColor Yellow
'''
        
        try:
            # 创建批处理脚本
            with open("activate_env.bat", 'w', encoding='utf-8') as f:
                f.write(bat_script)
            print("✅ activate_env.bat 已创建")
            
            # 创建PowerShell脚本
            with open("activate_env.ps1", 'w', encoding='utf-8') as f:
                f.write(ps1_script)
            print("✅ activate_env.ps1 已创建")
            
            return True
            
        except Exception as e:
            print(f"❌ 创建激活脚本失败: {e}")
            return False
    
    def create_project_info(self):
        """创建项目信息文件"""
        print("📄 创建项目信息文件...")
        
        project_info = {
            "name": self.project_name,
            "description": "Edge TTS免费集成项目",
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "venv_path": str(self.venv_path),
            "main_scripts": [
                "enhanced_tts_demo.py",
                "test_edge_tts_playback.py",
                "edge_tts_installer.py"
            ],
            "activation_scripts": [
                "activate_env.bat",
                "activate_env.ps1"
            ]
        }
        
        try:
            with open("project_info.json", 'w', encoding='utf-8') as f:
                json.dump(project_info, f, indent=2, ensure_ascii=False)
            
            print("✅ project_info.json 已创建")
            return True
            
        except Exception as e:
            print(f"❌ 创建项目信息失败: {e}")
            return False
    
    def setup_complete_environment(self):
        """设置完整的虚拟环境"""
        print("🎵 Edge TTS 虚拟环境设置")
        print("=" * 60)
        
        # 1. 检查Python版本
        if not self.check_python_version():
            return False
        
        # 2. 创建requirements.txt
        if not self.create_requirements_file():
            return False
        
        # 3. 创建虚拟环境
        if not self.create_virtual_environment():
            return False
        
        # 4. 升级pip
        self.upgrade_pip()
        
        # 5. 安装依赖
        if not self.install_dependencies():
            return False
        
        # 6. 测试安装
        if not self.test_installation():
            print("⚠️ 部分功能可能不可用，但核心功能应该正常")
        
        # 7. 创建激活脚本
        self.create_activation_scripts()
        
        # 8. 创建项目信息
        self.create_project_info()
        
        # 9. 显示使用说明
        self.show_usage_instructions()
        
        return True
    
    def show_usage_instructions(self):
        """显示使用说明"""
        print("\n" + "=" * 60)
        print("🎉 虚拟环境设置完成！")
        print("=" * 60)
        
        print(f"\n📁 项目结构:")
        print(f"  • {self.venv_name}/          - 虚拟环境目录")
        print(f"  • requirements.txt    - 依赖列表")
        print(f"  • activate_env.bat    - Windows激活脚本")
        print(f"  • activate_env.ps1    - PowerShell激活脚本")
        print(f"  • project_info.json   - 项目信息")
        
        print(f"\n🚀 使用方法:")
        print(f"1. 激活虚拟环境:")
        print(f"   Windows: activate_env.bat")
        print(f"   PowerShell: .\\activate_env.ps1")
        print(f"   手动: {self.get_activation_script()}")
        
        print(f"\n2. 运行项目:")
        print(f"   python enhanced_tts_demo.py")
        print(f"   python test_edge_tts_playback.py")
        
        print(f"\n3. 退出虚拟环境:")
        print(f"   deactivate")
        
        print(f"\n💡 优势:")
        print(f"  ✅ 依赖隔离，不影响系统Python")
        print(f"  ✅ 版本管理，便于项目维护")
        print(f"  ✅ 环境复制，便于部署")
        print(f"  ✅ 清理简单，删除{self.venv_name}目录即可")

def main():
    """主函数"""
    manager = VirtualEnvManager()
    
    print("🎵 Edge TTS 项目虚拟环境管理器")
    print("=" * 60)
    print("这个工具将为您创建一个独立的Python虚拟环境")
    print("所有依赖将安装在虚拟环境中，不会影响系统Python")
    print()
    
    response = input("是否继续创建虚拟环境？(Y/n): ").lower().strip()
    if response in ['', 'y', 'yes']:
        success = manager.setup_complete_environment()
        if success:
            print("\n🎉 设置成功！现在您可以使用虚拟环境运行Edge TTS项目了。")
        else:
            print("\n❌ 设置失败，请检查错误信息并重试。")
    else:
        print("❌ 用户取消操作")

if __name__ == "__main__":
    main()
