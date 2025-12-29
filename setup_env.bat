@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: 定义颜色（优化输出）
set "red=[91m"
set "green=[92m"
set "yellow=[93m"
set "reset=[0m"

echo %green%=== 开始配置Python虚拟环境 ===%reset%

:: 1. 创建虚拟环境（已存在则跳过）
if not exist ".env" (
    echo %yellow%正在创建Python虚拟环境...%reset%
    python -m venv .env
    if errorlevel 1 (
        echo %red%❌ 创建虚拟环境失败！请检查Python是否加入系统环境变量%reset%
        pause
        exit /b 1
    )
) else (
    echo %yellow%虚拟环境已存在，跳过创建%reset%
)

:: 2. 激活虚拟环境（关键：call确保生效，避免乱码）
echo %yellow%激活虚拟环境...%reset%
call ".env\Scripts\activate.bat"
if errorlevel 1 (
    echo %red%❌ 激活虚拟环境失败！%reset%
    pause
    exit /b 1
)

:: 3. 升级pip
echo %yellow%升级pip...%reset%
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo %red%❌ pip升级失败！%reset%
    pause
    exit /b 1
)

pip install -r requirements.txt
:: 6. 成功提示
echo.
echo %green%✅ 环境配置完成！%reset%
echo 📌 激活环境命令：.env\Scripts\activate.bat
echo 📌 退出环境命令：deactivate
pause

endlocal