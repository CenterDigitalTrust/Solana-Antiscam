@echo off
chcp 65001 > nul
title Solana Meme Research Lab - Autonomous Daemon
echo ===============================================================================
echo   SOLANA MEME RESEARCH LAB - АВТОНОМНЫЙ РЕЖИМ (DAEMON)
echo   ПАПКА ДЛЯ ОТЧЕТОВ: ОТЧЕТЫ\
echo ===============================================================================
echo.
echo Запуск непрерывной аналитики и симуляции...
echo Каждые 30 минут создается новый аналитический файл в папке 'ОТЧЕТЫ'.
echo Чтобы остановить работу, нажмите Ctrl+C или закройте это окно.
echo.

echo Запуск через Python...
python main.py --daemon --report-interval 30
pause
