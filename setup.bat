@echo off
rem ============================================================
rem OmniFuse 一括環境構築スクリプト (Windows)
rem 使い方:  setup.bat をダブルクリック、またはコマンドプロンプトで実行
rem ============================================================
setlocal
cd /d "%~dp0"
chcp 65001 >nul

echo ============================================
echo  OmniFuse セットアップを開始します
echo ============================================

rem --- 1. Python の確認 ---------------------------------------
set "PYTHON="
where python >nul 2>nul && set "PYTHON=python"
if not defined PYTHON (
    where py >nul 2>nul && set "PYTHON=py -3"
)
if not defined PYTHON (
    echo [エラー] Python が見つかりません。
    echo   https://www.python.org/downloads/ からインストールしてください。
    echo   インストール時に「Add Python to PATH」へ必ずチェックを入れてください。
    pause
    exit /b 1
)
%PYTHON% -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 (
    echo [エラー] Python 3.10 以上が必要です。
    pause
    exit /b 1
)
echo [OK] Python を検出しました

rem --- 2. 仮想環境の作成 ---------------------------------------
if not exist ".venv" (
    echo 仮想環境 (.venv) を作成しています...
    %PYTHON% -m venv .venv
    if errorlevel 1 (
        echo [エラー] 仮想環境の作成に失敗しました。
        pause
        exit /b 1
    )
)
set "VENV_PY=.venv\Scripts\python.exe"

rem --- 3. 依存ライブラリの一括インストール ----------------------
echo 依存ライブラリをインストールしています（数分かかる場合があります）...
"%VENV_PY%" -m pip install --upgrade pip --quiet
"%VENV_PY%" -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [エラー] ライブラリのインストールに失敗しました。
    echo   ネットワーク接続を確認して再実行してください。
    pause
    exit /b 1
)
echo [OK] 依存ライブラリをインストールしました

rem --- 4. 動作チェック ------------------------------------------
"%VENV_PY%" -c "import pandas, openpyxl, matplotlib, requests, yaml, omnifuse.cli"
if errorlevel 1 (
    echo [エラー] 動作チェックに失敗しました。
    pause
    exit /b 1
)
echo [OK] すべての依存ライブラリが正常に読み込めました

rem --- 5. 設定ファイルと起動コマンドの作成 ------------------------
if not exist "config.yaml" if exist "config.example.yaml" (
    copy /y config.example.yaml config.yaml >nul
    echo [OK] config.example.yaml から config.yaml を作成しました
)
(
    echo @echo off
    echo "%%~dp0.venv\Scripts\python.exe" -m omnifuse %%*
) > omnifuse.bat
echo [OK] 起動コマンド omnifuse.bat を作成しました

echo.
echo ============================================
echo  セットアップが完了しました！
echo ============================================
echo.
echo  使い方:
echo    omnifuse              ... 対話メニューを起動
echo    omnifuse chart data.csv   ... グラフ整形
echo    omnifuse tone report.md   ... 文章3トーン生成
echo.
echo  APIキーの設定方法は USER_GUIDE.md をご覧ください。
pause
