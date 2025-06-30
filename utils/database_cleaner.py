"""
碳排放交易實驗平台 - 資料庫清理腳本
處理所有實驗組的數據清理、驗證和異常值檢測

版本: 1.0
作者: Levi
最後更新: 2024/12/30
"""

import sqlite3
import pandas as pd
import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from pathlib import Path

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('database_cleaning.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DatabaseCleaner:
    """資料庫清理器主類別"""
    
    def __init__(self, db_path: str = "db.sqlite3"):
        """
        初始化資料庫清理器
        
        Args:
            db_path: SQLite資料庫文件路徑
        """
        self.db_path = db_path
        self.conn = None
        self.cleaning_report = {
            'timestamp': datetime.now().isoformat(),
            'total_records_processed': 0,
            'issues_found': [],
            'corrections_made': [],
            'warnings': [],
            'summary': {}
        }
        
        # 實驗組表格映射
        self.stage_tables = {
            'control': {
                'player': 'stage_control_player',
                'group': 'stage_control_group', 
                'subsession': 'stage_control_subsession'
            },
            'carbon_tax': {
                'player': 'stage_carbontax_player',
                'group': 'stage_carbontax_group',
                'subsession': 'stage_carbontax_subsession'
            },
            'muda': {
                'player': 'stage_muda_player',
                'group': 'stage_muda_group',
                'subsession': 'stage_muda_subsession'
            },
            'carbon_trading': {
                'player': 'stage_carbontrading_player',
                'group': 'stage_carbontrading_group',
                'subsession': 'stage_carbontrading_subsession'
            }
        }
        
        # 數據類型映射
        self.data_types = {
            'participant_id': int,
            'session_id': int,
            'group_id': int,
            'id_in_group': int,
            'round_number': int,
            'is_dominant': bool,
            'marginal_cost_coefficient': int,
            'carbon_emission_per_unit': float,
            'max_production': int,
            'market_price': float,
            'production': int,
            'revenue': float,
            'total_cost': float,
            'net_profit': float,
            'payoff': float
        }
    
    def connect_database(self) -> bool:
        """連接到資料庫"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            logger.info(f"成功連接到資料庫: {self.db_path}")
            return True
        except sqlite3.Error as e:
            logger.error(f"資料庫連接失敗: {e}")
            return False
    
    def close_database(self):
        """關閉資料庫連接"""
        if self.conn:
            self.conn.close()
            logger.info("已關閉資料庫連接")
    
    def get_table_list(self) -> List[str]:
        """獲取資料庫中所有表格列表"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        return tables
    
    def validate_table_exists(self, table_name: str) -> bool:
        """驗證表格是否存在"""
        tables = self.get_table_list()
        exists = table_name in tables
        if not exists:
            logger.warning(f"表格 {table_name} 不存在")
        return exists
    
    def clean_control_group_data(self):
        """清理對照組數據"""
        logger.info("開始清理對照組數據...")
        
        table_name = self.stage_tables['control']['player']
        if not self.validate_table_exists(table_name):
            return
        
        # 讀取數據
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", self.conn)
        if df.empty:
            logger.info("對照組無數據需要清理")
            return
        
        original_count = len(df)
        issues_found = 0
        
        # 1. 檢查生產量約束
        invalid_production = df[
            (df['production'] < 0) | 
            (df['production'] > df['max_production'])
        ]
        if not invalid_production.empty:
            issues_found += len(invalid_production)
            self.cleaning_report['issues_found'].append({
                'table': table_name,
                'issue': '生產量超出約束範圍',
                'count': len(invalid_production),
                'records': invalid_production[['id', 'production', 'max_production']].to_dict('records')
            })
            
            # 修正：將超出範圍的生產量設為最大值
            df.loc[df['production'] > df['max_production'], 'production'] = df['max_production']
            df.loc[df['production'] < 0, 'production'] = 0
        
        # 2. 驗證收益計算
        calculated_revenue = df['production'] * df['market_price']
        revenue_mismatch = df[abs(df['revenue'] - calculated_revenue) > 0.01]
        if not revenue_mismatch.empty:
            issues_found += len(revenue_mismatch)
            self.cleaning_report['issues_found'].append({
                'table': table_name,
                'issue': '收益計算不一致',
                'count': len(revenue_mismatch),
                'details': '實際收益與計算收益差異 > 0.01'
            })
            
            # 修正收益
            df['revenue'] = calculated_revenue
        
        # 3. 檢查負成本
        negative_cost = df[df['total_cost'] < 0]
        if not negative_cost.empty:
            issues_found += len(negative_cost)
            self.cleaning_report['issues_found'].append({
                'table': table_name,
                'issue': '總成本為負值',
                'count': len(negative_cost)
            })
            # 將負成本設為0
            df.loc[df['total_cost'] < 0, 'total_cost'] = 0
        
        # 4. 處理缺失值
        missing_data = df.isnull().sum()
        if missing_data.sum() > 0:
            self.cleaning_report['warnings'].append({
                'table': table_name,
                'warning': '發現缺失值',
                'missing_counts': missing_data[missing_data > 0].to_dict()
            })
            
            # 填補關鍵字段的缺失值
            df['production'].fillna(0, inplace=True)
            df['revenue'].fillna(0, inplace=True)
            df['total_cost'].fillna(0, inplace=True)
        
        # 更新數據庫
        if issues_found > 0:
            df.to_sql(table_name, self.conn, if_exists='replace', index=False)
            self.conn.commit()
            self.cleaning_report['corrections_made'].append({
                'table': table_name,
                'corrections': issues_found,
                'description': '對照組數據清理完成'
            })
        
        logger.info(f"對照組數據清理完成，処理了 {original_count} 筆記錄，發現 {issues_found} 個問題")
    
    def clean_carbon_tax_data(self):
        """清理碳稅組數據"""
        logger.info("開始清理碳稅組數據...")
        
        table_name = self.stage_tables['carbon_tax']['player']
        if not self.validate_table_exists(table_name):
            return
        
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", self.conn)
        if df.empty:
            logger.info("碳稅組無數據需要清理")
            return
        
        original_count = len(df)
        issues_found = 0
        
        # 1. 驗證碳稅計算
        if 'carbon_tax_paid' in df.columns:
            calculated_emissions = df['production'] * df['carbon_emission_per_unit']
            
            # 從subsession表獲取稅率
            subsession_table = self.stage_tables['carbon_tax']['subsession']
            if self.validate_table_exists(subsession_table):
                tax_df = pd.read_sql_query(f"SELECT * FROM {subsession_table}", self.conn)
                df = df.merge(tax_df[['id', 'tax_rate']], left_on='subsession_id', right_on='id', suffixes=('', '_sub'))
                
                calculated_tax = calculated_emissions * df['tax_rate']
                tax_mismatch = df[abs(df['carbon_tax_paid'] - calculated_tax) > 0.01]
                
                if not tax_mismatch.empty:
                    issues_found += len(tax_mismatch)
                    self.cleaning_report['issues_found'].append({
                        'table': table_name,
                        'issue': '碳稅計算不一致',
                        'count': len(tax_mismatch)
                    })
                    # 修正碳稅
                    df['carbon_tax_paid'] = calculated_tax
        
        # 2. 檢查稅率合理性
        if 'tax_rate' in df.columns:
            invalid_tax_rate = df[(df['tax_rate'] < 0) | (df['tax_rate'] > 10)]
            if not invalid_tax_rate.empty:
                issues_found += len(invalid_tax_rate)
                self.cleaning_report['issues_found'].append({
                    'table': table_name,
                    'issue': '稅率超出合理範圍',
                    'count': len(invalid_tax_rate)
                })
        
        # 3. 驗證利潤計算（含稅後）
        if all(col in df.columns for col in ['revenue', 'total_cost', 'carbon_tax_paid', 'net_profit']):
            calculated_profit = df['revenue'] - df['total_cost'] - df['carbon_tax_paid']
            profit_mismatch = df[abs(df['net_profit'] - calculated_profit) > 0.01]
            
            if not profit_mismatch.empty:
                issues_found += len(profit_mismatch)
                self.cleaning_report['issues_found'].append({
                    'table': table_name,
                    'issue': '稅後利潤計算不一致',
                    'count': len(profit_mismatch)
                })
                df['net_profit'] = calculated_profit
        
        # 更新數據庫
        if issues_found > 0:
            df.to_sql(table_name, self.conn, if_exists='replace', index=False)
            self.conn.commit()
            self.cleaning_report['corrections_made'].append({
                'table': table_name,
                'corrections': issues_found,
                'description': '碳稅組數據清理完成'
            })
        
        logger.info(f"碳稅組數據清理完成，処理了 {original_count} 筆記錄，發現 {issues_found} 個問題")
    
    def clean_muda_data(self):
        """清理MUDA訓練組數據"""
        logger.info("開始清理MUDA訓練組數據...")
        
        table_name = self.stage_tables['muda']['player']
        if not self.validate_table_exists(table_name):
            return
        
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", self.conn)
        if df.empty:
            logger.info("MUDA組無數據需要清理")
            return
        
        original_count = len(df)
        issues_found = 0
        
        # 1. 檢查現金餘額一致性
        if all(col in df.columns for col in ['cash', 'current_cash']):
            cash_mismatch = df[df['cash'] != df['current_cash']]
            if not cash_mismatch.empty:
                issues_found += len(cash_mismatch)
                self.cleaning_report['warnings'].append({
                    'table': table_name,
                    'warning': '現金餘額字段不一致',
                    'count': len(cash_mismatch)
                })
        
        # 2. 驗證交易數據完整性
        if 'submitted_offers' in df.columns:
            for idx, row in df.iterrows():
                if pd.notna(row['submitted_offers']):
                    try:
                        offers = json.loads(row['submitted_offers'])
                        if not isinstance(offers, list):
                            issues_found += 1
                            df.at[idx, 'submitted_offers'] = '[]'
                    except json.JSONDecodeError:
                        issues_found += 1
                        df.at[idx, 'submitted_offers'] = '[]'
                        self.cleaning_report['issues_found'].append({
                            'table': table_name,
                            'issue': 'JSON格式錯誤',
                            'record_id': row.get('id', idx)
                        })
        
        # 3. 檢查交易量與價格的合理性
        if all(col in df.columns for col in ['buy_quantity', 'buy_price', 'sell_quantity', 'sell_price']):
            # 檢查負值
            negative_values = df[
                (df['buy_quantity'] < 0) | (df['sell_quantity'] < 0) |
                (df['buy_price'] < 0) | (df['sell_price'] < 0)
            ]
            if not negative_values.empty:
                issues_found += len(negative_values)
                self.cleaning_report['issues_found'].append({
                    'table': table_name,
                    'issue': '交易數據包含負值',
                    'count': len(negative_values)
                })
                # 將負值設為0
                df.loc[df['buy_quantity'] < 0, 'buy_quantity'] = 0
                df.loc[df['sell_quantity'] < 0, 'sell_quantity'] = 0
                df.loc[df['buy_price'] < 0, 'buy_price'] = 0
                df.loc[df['sell_price'] < 0, 'sell_price'] = 0
        
        # 4. 驗證資產計算
        if all(col in df.columns for col in ['current_cash', 'current_items', 'personal_item_value', 'total_value']):
            calculated_value = df['current_cash'] + df['current_items'] * df['personal_item_value']
            value_mismatch = df[abs(df['total_value'] - calculated_value) > 0.01]
            
            if not value_mismatch.empty:
                issues_found += len(value_mismatch)
                self.cleaning_report['issues_found'].append({
                    'table': table_name,
                    'issue': '總資產價值計算不一致',
                    'count': len(value_mismatch)
                })
                df['total_value'] = calculated_value
        
        # 更新數據庫
        if issues_found > 0:
            df.to_sql(table_name, self.conn, if_exists='replace', index=False)
            self.conn.commit()
            self.cleaning_report['corrections_made'].append({
                'table': table_name,
                'corrections': issues_found,
                'description': 'MUDA組數據清理完成'
            })
        
        logger.info(f"MUDA組數據清理完成，処理了 {original_count} 筆記錄，發現 {issues_found} 個問題")
    
    def clean_carbon_trading_data(self):
        """清理碳交易組數據"""
        logger.info("開始清理碳交易組數據...")
        
        table_name = self.stage_tables['carbon_trading']['player']
        if not self.validate_table_exists(table_name):
            return
        
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", self.conn)
        if df.empty:
            logger.info("碳交易組無數據需要清理")
            return
        
        original_count = len(df)
        issues_found = 0
        
        # 1. 檢查碳權約束
        if all(col in df.columns for col in ['production', 'carbon_emission_per_unit', 'current_permits']):
            required_permits = df['production'] * df['carbon_emission_per_unit']
            permit_violation = df[required_permits > df['current_permits']]
            
            if not permit_violation.empty:
                issues_found += len(permit_violation)
                self.cleaning_report['issues_found'].append({
                    'table': table_name,
                    'issue': '生產量超出碳權約束',
                    'count': len(permit_violation),
                    'details': '生產所需碳權 > 現有碳權'
                })
                
                # 調整生產量以符合碳權約束
                max_feasible_production = df['current_permits'] / df['carbon_emission_per_unit']
                df.loc[required_permits > df['current_permits'], 'production'] = max_feasible_production.astype(int)
        
        # 2. 驗證交易數據完整性
        group_table = self.stage_tables['carbon_trading']['group']
        if self.validate_table_exists(group_table):
            group_df = pd.read_sql_query(f"SELECT * FROM {group_table}", self.conn)
            
            for _, group_row in group_df.iterrows():
                # 檢查交易歷史JSON格式
                if pd.notna(group_row['trade_history']):
                    try:
                        trade_history = json.loads(group_row['trade_history'])
                        if not isinstance(trade_history, list):
                            issues_found += 1
                    except json.JSONDecodeError:
                        issues_found += 1
                        self.cleaning_report['issues_found'].append({
                            'table': group_table,
                            'issue': '交易歷史JSON格式錯誤',
                            'group_id': group_row.get('id')
                        })
        
        # 3. 檢查現金餘額（可為負數）
        extremely_negative_cash = df[df['current_cash'] < -1000000]  # 極端負值檢查
        if not extremely_negative_cash.empty:
            self.cleaning_report['warnings'].append({
                'table': table_name,
                'warning': '發現極端負現金餘額',
                'count': len(extremely_negative_cash),
                'min_cash': float(extremely_negative_cash['current_cash'].min())
            })
        
        # 4. 驗證交易統計
        if all(col in df.columns for col in ['total_bought', 'total_sold', 'total_spent', 'total_earned']):
            # 檢查負值
            negative_trading = df[
                (df['total_bought'] < 0) | (df['total_sold'] < 0) |
                (df['total_spent'] < 0) | (df['total_earned'] < 0)
            ]
            if not negative_trading.empty:
                issues_found += len(negative_trading)
                self.cleaning_report['issues_found'].append({
                    'table': table_name,
                    'issue': '交易統計包含負值',
                    'count': len(negative_trading)
                })
                # 修正負值
                df.loc[df['total_bought'] < 0, 'total_bought'] = 0
                df.loc[df['total_sold'] < 0, 'total_sold'] = 0
                df.loc[df['total_spent'] < 0, 'total_spent'] = 0
                df.loc[df['total_earned'] < 0, 'total_earned'] = 0
        
        # 5. 驗證最終資產計算
        if all(col in df.columns for col in ['current_cash', 'revenue', 'total_cost', 'initial_capital']):
            # 計算最終資產價值（考慮生產收益和成本）
            calculated_final_value = df['current_cash'] + df['revenue'] - df['total_cost']
            calculated_profit = calculated_final_value - df['initial_capital']
            
            if 'net_profit' in df.columns:
                profit_mismatch = df[abs(df['net_profit'] - calculated_profit) > 0.01]
                if not profit_mismatch.empty:
                    issues_found += len(profit_mismatch)
                    self.cleaning_report['issues_found'].append({
                        'table': table_name,
                        'issue': '最終利潤計算不一致',
                        'count': len(profit_mismatch)
                    })
                    df['net_profit'] = calculated_profit
        
        # 更新數據庫
        if issues_found > 0:
            df.to_sql(table_name, self.conn, if_exists='replace', index=False)
            self.conn.commit()
            self.cleaning_report['corrections_made'].append({
                'table': table_name,
                'corrections': issues_found,
                'description': '碳交易組數據清理完成'
            })
        
        logger.info(f"碳交易組數據清理完成，処理了 {original_count} 筆記錄，發現 {issues_found} 個問題")
    
    def generate_data_quality_report(self) -> Dict[str, Any]:
        """生成數據品質報告"""
        logger.info("生成數據品質報告...")
        
        quality_report = {
            'database_info': {
                'file_path': self.db_path,
                'file_size_mb': round(os.path.getsize(self.db_path) / (1024*1024), 2) if os.path.exists(self.db_path) else 0,
                'tables_found': self.get_table_list()
            },
            'data_summary': {},
            'data_completeness': {},
            'outlier_detection': {}
        }
        
        # 為每個實驗組生成統計摘要
        for stage, tables in self.stage_tables.items():
            player_table = tables['player']
            if not self.validate_table_exists(player_table):
                continue
            
            try:
                df = pd.read_sql_query(f"SELECT * FROM {player_table}", self.conn)
                if df.empty:
                    continue
                
                quality_report['data_summary'][stage] = {
                    'total_records': len(df),
                    'participants': df['participant_id'].nunique() if 'participant_id' in df.columns else 0,
                    'rounds': df['round_number'].nunique() if 'round_number' in df.columns else 0,
                    'date_range': {
                        'earliest': df['created_at'].min() if 'created_at' in df.columns else None,
                        'latest': df['created_at'].max() if 'created_at' in df.columns else None
                    }
                }
                
                # 數據完整性檢查
                missing_data = df.isnull().sum()
                quality_report['data_completeness'][stage] = {
                    'missing_values': missing_data[missing_data > 0].to_dict(),
                    'completeness_rate': (1 - missing_data.sum() / (len(df) * len(df.columns))) * 100
                }
                
                # 異常值檢測
                numeric_columns = df.select_dtypes(include=[np.number]).columns
                outliers = {}
                for col in numeric_columns:
                    if len(df[col].dropna()) > 0:
                        Q1 = df[col].quantile(0.25)
                        Q3 = df[col].quantile(0.75)
                        IQR = Q3 - Q1
                        lower_bound = Q1 - 1.5 * IQR
                        upper_bound = Q3 + 1.5 * IQR
                        outlier_count = len(df[(df[col] < lower_bound) | (df[col] > upper_bound)])
                        if outlier_count > 0:
                            outliers[col] = {
                                'count': outlier_count,
                                'percentage': round(outlier_count / len(df) * 100, 2)
                            }
                
                quality_report['outlier_detection'][stage] = outliers
                
            except Exception as e:
                logger.error(f"生成 {stage} 組品質報告時出錯: {e}")
                quality_report['data_summary'][stage] = {'error': str(e)}
        
        return quality_report
    
    def export_cleaned_data(self, output_dir: str = "cleaned_data"):
        """導出清理後的數據"""
        logger.info(f"導出清理後的數據到 {output_dir}")
        
        # 創建輸出目錄
        os.makedirs(output_dir, exist_ok=True)
        
        # 導出各組數據
        for stage, tables in self.stage_tables.items():
            stage_dir = os.path.join(output_dir, stage)
            os.makedirs(stage_dir, exist_ok=True)
            
            for table_type, table_name in tables.items():
                if not self.validate_table_exists(table_name):
                    continue
                
                try:
                    df = pd.read_sql_query(f"SELECT * FROM {table_name}", self.conn)
                    if not df.empty:
                        # 導出為CSV
                        csv_path = os.path.join(stage_dir, f"{table_name}.csv")
                        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                        
                        # 導出為Excel（如果記錄數不太多）
                        if len(df) < 50000:
                            excel_path = os.path.join(stage_dir, f"{table_name}.xlsx")
                            df.to_excel(excel_path, index=False)
                        
                        logger.info(f"已導出 {table_name}: {len(df)} 筆記錄")
                
                except Exception as e:
                    logger.error(f"導出 {table_name} 時出錯: {e}")
    
    def run_full_cleaning(self, export_data: bool = True, generate_report: bool = True) -> Dict[str, Any]:
        """執行完整的數據清理流程"""
        logger.info("開始執行完整數據清理流程...")
        
        if not self.connect_database():
            return {'error': '無法連接到資料庫'}
        
        try:
            # 清理各組數據
            self.clean_control_group_data()
            self.clean_carbon_tax_data()
            self.clean_muda_data()
            self.clean_carbon_trading_data()
            
            # 生成品質報告
            if generate_report:
                quality_report = self.generate_data_quality_report()
                self.cleaning_report['quality_report'] = quality_report
            
            # 導出清理後的數據
            if export_data:
                self.export_cleaned_data()
            
            # 計算總結
            total_issues = sum(len(correction.get('corrections', 0)) for correction in self.cleaning_report['corrections_made'])
            total_warnings = len(self.cleaning_report['warnings'])
            
            self.cleaning_report['summary'] = {
                'status': 'completed',
                'total_issues_fixed': total_issues,
                'total_warnings': total_warnings,
                'cleaned_tables': len(self.cleaning_report['corrections_made'])
            }
            
            # 保存清理報告
            report_path = f"cleaning_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(self.cleaning_report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"數據清理完成！修復了 {total_issues} 個問題，產生了 {total_warnings} 個警告")
            logger.info(f"清理報告已保存至: {report_path}")
            
            return self.cleaning_report
            
        except Exception as e:
            logger.error(f"數據清理過程中發生錯誤: {e}")
            return {'error': str(e)}
        
        finally:
            self.close_database()

def main():
    """主函數 - 命令行界面"""
    import argparse
    
    parser = argparse.ArgumentParser(description='碳排放交易實驗平台 - 資料庫清理工具')
    parser.add_argument('--db', default='db.sqlite3', help='資料庫文件路徑 (默認: db.sqlite3)')
    parser.add_argument('--no-export', action='store_true', help='不導出清理後的數據')
    parser.add_argument('--no-report', action='store_true', help='不生成品質報告')
    parser.add_argument('--output-dir', default='cleaned_data', help='輸出目錄 (默認: cleaned_data)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("碳排放交易實驗平台 - 資料庫清理工具")
    print("=" * 60)
    print(f"資料庫文件: {args.db}")
    print(f"輸出目錄: {args.output_dir}")
    print("-" * 60)
    
    # 檢查資料庫文件是否存在
    if not os.path.exists(args.db):
        print(f"錯誤：資料庫文件 '{args.db}' 不存在！")
        return
    
    # 創建清理器並執行清理
    cleaner = DatabaseCleaner(args.db)
    result = cleaner.run_full_cleaning(
        export_data=not args.no_export,
        generate_report=not args.no_report
    )
    
    if 'error' in result:
        print(f"清理失敗: {result['error']}")
    else:
        print("\n清理完成！")
        if 'summary' in result:
            summary = result['summary']
            print(f"- 修復問題數: {summary['total_issues_fixed']}")
            print(f"- 警告數: {summary['total_warnings']}")
            print(f"- 清理表格數: {summary['cleaned_tables']}")
        
        if not args.no_export:
            print(f"- 清理後數據已導出至: {args.output_dir}")

if __name__ == "__main__":
    main()