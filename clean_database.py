#!/usr/bin/env python3
"""
碳排放交易實驗平台 - 資料庫清理執行腳本

這是一個簡單的執行腳本，用於啟動資料庫清理程序。
如果您需要更多自定義選項，請直接使用 utils/database_cleaner.py

使用方法:
python clean_database.py
"""

import sys
import os
from pathlib import Path

# 確保可以導入 utils 模組
sys.path.append(str(Path(__file__).parent / "utils"))

try:
    from database_cleaner import DatabaseCleaner
except ImportError as e:
    print(f"錯誤：無法導入資料庫清理模組: {e}")
    print("請確保 utils/database_cleaner.py 文件存在且可訪問")
    sys.exit(1)

def main():
    """主函數"""
    print("=" * 60)
    print("碳排放交易實驗平台 - 資料庫清理工具")
    print("=" * 60)
    
    # 檢查資料庫文件
    db_file = "db.sqlite3"
    if not os.path.exists(db_file):
        print(f"警告：找不到預設資料庫文件 '{db_file}'")
        print("請確保：")
        print("1. 您在正確的專案根目錄中")
        print("2. 已經運行過 oTree 實驗並生成了資料庫")
        print()
        custom_db = input("請輸入資料庫文件路徑（按 Enter 使用預設）: ").strip()
        if custom_db:
            db_file = custom_db
            if not os.path.exists(db_file):
                print(f"錯誤：資料庫文件 '{db_file}' 不存在！")
                return
    
    print(f"使用資料庫文件: {db_file}")
    print()
    
    # 創建清理器
    cleaner = DatabaseCleaner(db_file)
    
    # 執行清理
    print("開始資料庫清理程序...")
    result = cleaner.run_full_cleaning()
    
    if 'error' in result:
        print(f"[清理失敗]: {result['error']}")
    else:
        print("[資料庫清理完成]")
        
        if 'summary' in result:
            summary = result['summary']
            print(f"[清理統計]:")
            print(f"   - 修復問題數: {summary.get('total_issues_fixed', 0)}")
            print(f"   - 警告數: {summary.get('total_warnings', 0)}")
            print(f"   - 清理表格數: {summary.get('cleaned_tables', 0)}")
        
        print(f"清理後數據已導出至: cleaned_data/")  
        print(f"詳細報告請查看生成的 cleaning_report_*.json 文件]")

if __name__ == "__main__":
    main() 