@echo off
echo 🤖 启动智能语音助手...
echo.

REM 检查虚拟环境
if not exist "venv\Scripts\python.exe" (
    echo ❌ 虚拟环境不存在，请先运行 setup_virtual_env.py
    pause
    exit /b 1
)

REM 检查主程序
if not exist "ai_voice_assistant.py" (
    echo ❌ 主程序文件不存在
    pause
    exit /b 1
)

echo ✅ 环境检查通过
echo 🚀 正在启动程序...
echo.

REM 启动程序
venv\Scripts\python.exe ai_voice_assistant.py

REM 如果程序异常退出，显示错误信息
if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ 程序启动失败，错误代码: %ERRORLEVEL%
    echo 💡 请检查日志文件: ai_voice_assistant.log
    echo.
    pause
)
