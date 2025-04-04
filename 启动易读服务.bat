@echo off
chcp 65001
echo 正在启动易读服务...

:: 检查是否存在标记文件
if not exist .env_setup_done (
    :: 当venv不存在时，创建venv
    if not exist venv (
        echo 虚拟环境不存在，正在创建...
        python -m venv venv
    )
    :: 激活虚拟环境安装依赖
    call venv\Scripts\activate.bat
    echo 正在安装依赖...
    pip install -r requirements.txt
    :: 创建标记文件表示已完成初始化
    echo 初始化完成 > .env_setup_done
) else (
    echo 环境已经设置，跳过初始化步骤...
)


:: 激活虚拟环境
call venv\Scripts\activate.bat

:: 启动 Python 程序
python main.py

:: 如果程序正常启动，将显示以下信息
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ================================
    echo       易读服务启动成功！
    echo ================================
    echo.
) else (
    echo.
    echo 启动失败，请检查错误信息
    pause
)
