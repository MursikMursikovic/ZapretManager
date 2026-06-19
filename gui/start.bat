@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo = ZapretManager v1.0.2                 =
echo ========================================
echo.

:: Проверяем наличие Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден!
    echo Установите Python с https://www.python.org/downloads/
    echo и убедитесь, что он добавлен в PATH.
    pause
    exit /b 1
)

:: 3. Устанавливаем зависимости (если они не установлены)
echo Проверка зависимостей...
pip show psutil >nul 2>&1
if errorlevel 1 (
    echo Установка psutil...
    pip install psutil
)
pip show requests >nul 2>&1
if errorlevel 1 (
    echo Установка requests...
    pip install requests
)

:: 4. Запускаем скрипт
echo Запуск zapret_gui.py
python zapret_gui.py

:: Если скрипт завершился с ошибкой – показываем сообщение
if errorlevel 1 (
    echo.
    echo Произошла ошибка. Проверьте вывод выше.
    pause
)