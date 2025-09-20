"""
碳排放交易實驗配置文件
統一管理所有實驗參數和設定
"""
import yaml
import os
import random
from typing import Dict, Any, List, Tuple, Optional, Union
from pathlib import Path

class ExperimentConfig:
    """實驗配置管理類別"""
    
    def __init__(self, config_file: str = 'configs/experiment_config.yaml'):
        self.config_file = config_file
        self._config: Dict[str, Any] = {}
        self._test_mode_enabled: Optional[bool] = None
        self.load_config()
    
    def load_config(self) -> None:
        """載入配置檔案"""
        try:
            config_path = Path(self.config_file)
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f)
            else:
                print(f"配置文件 {self.config_file} 未找到，使用默認配置")
                self._config = self._get_default_config()
        except yaml.YAMLError as e:
            print(f"配置文件解析錯誤: {e}")
            self._config = self._get_default_config()
        except Exception as e:
            print(f"載入配置時發生錯誤: {e}")
            self._config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """獲取默認配置"""
        return {
            'experiment_mode': {
                'test_mode_enabled': False
            },
            'general': {
                'players_per_group': 15,
                'num_rounds': 15,
                'max_production': 50,
                'role_assignment': {
                    'dominant_firm_count': 3,
                    'non_dominant_firm_count': 12,
                    'ensure_player1_dominant': False
                }
            }
        }
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        獲取配置值，優先從測試模式配置獲取（如果啟用）
        
        Args:
            key_path: 配置鍵路徑，使用點號分隔
            default: 默認值
            
        Returns:
            配置值
        """
        # 檢查是否啟用測試模式
        if self.is_test_mode_enabled() and not key_path.startswith('experiment_mode'):
            # 嘗試從測試模式覆蓋配置獲取
            test_mode_path = f'test_mode_overrides.{key_path}'
            test_value = self._get_value(test_mode_path)
            if test_value is not None:
                return test_value
        
        # 從正式配置獲取
        return self._get_value(key_path, default)
    
    def _get_value(self, key_path: str, default: Any = None) -> Any:
        """從配置中獲取值的內部方法"""
        keys = key_path.split('.')
        value = self._config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def is_test_mode_enabled(self) -> bool:
        """檢查是否啟用測試模式"""
        if self._test_mode_enabled is None:
            self._test_mode_enabled = self._get_value('experiment_mode.test_mode_enabled', False)
        return self._test_mode_enabled
    
    def set_test_mode(self, enabled: bool) -> None:
        """設置測試模式狀態"""
        self._test_mode_enabled = enabled

    # ========== 基本屬性 ==========
    
    @property
    def players_per_group(self) -> int:
        """每組玩家數量"""
        return self.get('general.players_per_group', 15)
    
    @property
    def num_rounds(self) -> int:
        """回合數"""
        return self.get('general.num_rounds', 15)
    
    @property
    def max_production(self) -> int:
        """最大生產量"""
        return self.get('general.max_production', 50)
    
    @property
    def random_dominant_firm_each_round(self) -> bool:
        """是否每回合重抽主導廠商"""
        return self.get('general.random_dominant_firm_each_round', False)

    @property
    def carbon_real_world_rate(self) -> bool:
        """實驗碳排轉換成真實碳排的比例"""
        return self.get('general.carbon_real_world_rate', False)

    @property
    def test_mode(self) -> bool:
        """是否為測試模式（兼容舊代碼）"""
        return self.is_test_mode_enabled()
    
    @property
    def production_mode(self) -> bool:
        """是否為正式模式（兼容舊代碼）"""
        return not self.is_test_mode_enabled()
    
    # ========== 角色分配 ==========
    
    @property
    def dominant_firm_count(self) -> int:
        """主導廠商數量"""
        return self.get('general.role_assignment.dominant_firm_count', 3)
    
    @property
    def non_dominant_firm_count(self) -> int:
        """非主導廠商數量"""
        return self.get('general.role_assignment.non_dominant_firm_count', 9)
    
    @property
    def ensure_player1_dominant(self) -> bool:
        """是否確保玩家1為主導廠商"""
        return self.get('general.role_assignment.ensure_player1_dominant', False)
    
    # ========== 廠商參數 ==========
    @property
    def parameter_sets(self) -> List[Dict[str, Any]]:
        """從矩陣格式的 preset_parameter_matrix 轉換成 list of dicts"""
        matrix = self._config.get('preset_parameter_matrix', {})
        columns = matrix.get('columns', [])
        values = matrix.get('values', [])
        return [dict(zip(columns, row)) for row in values]

    @property
    def dominant_mc_range(self) -> Tuple[int, int]:
        """主導廠商邊際成本係數範圍"""
        return tuple(self.get('general.dominant_firm.mc_range', [1, 5]))
    
    @property
    def non_dominant_mc_range(self) -> Tuple[int, int]:
        """非主導廠商邊際成本係數範圍"""
        return tuple(self.get('general.non_dominant_firm.mc_range', [2, 7]))
    
    @property
    def dominant_emission_per_unit(self) -> float:
        """主導廠商每單位碳排放"""
        return self.get('general.dominant_firm.emission_per_unit', 2)
    
    @property
    def non_dominant_emission_per_unit(self) -> float:
        """非主導廠商每單位碳排放"""
        return self.get('general.non_dominant_firm.emission_per_unit', 1)
    
    @property
    def dominant_max_production(self) -> int:
        """主導廠商最大生產量"""
        return self.get('general.dominant_firm.max_production', 20)
    
    @property
    def non_dominant_max_production(self) -> int:
        """非主導廠商最大生產量"""
        return self.get('general.non_dominant_firm.max_production', 8)
    
    @property
    def random_disturbance_range(self) -> Tuple[float, float]:
        """隨機擾動範圍"""
        return tuple(self.get('general.random_disturbance.range', [-1, 1]))
    
    # ========== 階段設定 ==========
    
    def get_stage_name_in_url(self, stage: str) -> str:
        """獲取階段在URL中的名稱"""
        return self.get(f'stages.{stage}.name_in_url', stage)
    
    def get_stage_description(self, stage: str) -> str:
        """獲取階段描述"""
        return self.get(f'stages.{stage}.description', f'{stage} 階段')
    
    def get_stage_display_name(self, stage: str) -> str:
        """獲取階段顯示名稱"""
        return self.get(f'stages.{stage}.display_name', f'{stage.title()} 階段')
    
    def get_stage_initial_capital(self, stage: str) -> 'Currency':
        """獲取階段初始資金"""
        from otree.api import cu
        return cu(self.get(f'stages.{stage}.initial_capital', 1000))
    
    # ========== 碳稅設定 ==========
    
    @property
    def carbon_tax_rates(self) -> List[int]:
        """碳稅率選項"""
        return self.get('stages.carbon_tax.tax_random_selection.rates', [1, 2, 3])
    
    @property
    def tax_rate_options(self) -> List['Currency']:
        """碳稅率選項（Currency格式）"""
        from otree.api import cu
        return [cu(rate) for rate in self.carbon_tax_rates]
    
    # ========== MUDA設定 ==========
    
    @property
    def muda_trading_time(self) -> int:
        """MUDA交易時間（秒）"""
        return self.get('stages.muda.trading_time', 180)

    @property
    def muda_num_rounds(self) -> int:
        """MUDA 回合數"""
        return self.get('stages.muda.num_rounds', 4)
    
    @property
    def muda_initial_capital(self) -> 'Currency':
        """MUDA初始資金"""
        from otree.api import cu
        return cu(self.get('stages.muda.initial_capital', 10000))
    
    @property
    def muda_item_price_options(self) -> List[int]:
        """MUDA物品價格選項"""
        return self.get('stages.muda.item_price_options', [25, 30, 35, 40])

    @property
    def muda_item_price_option_sets(self) -> Dict[str, List[int]]:
        """MUDA物品價格選項組"""
        return self.get('stages.muda.item_price_option_sets', {})

    @property
    def muda_item_name(self) -> str:
        """MUDA物品名稱"""
        return self.get('stages.muda.item_name', '碳權')
    
    @property
    def muda_reset_cash_each_round(self) -> bool:
        """MUDA是否每輪重置現金"""
        return self.get('stages.muda.reset_cash_each_round', True)
    
    # ========== 碳交易設定 ==========
    
    @property
    def carbon_trading_initial_capital(self) -> 'Currency':
        """碳交易初始資金"""
        from otree.api import cu
        return cu(self.get('stages.carbon_trading.initial_capital', 10000))
    
    @property
    def carbon_trading_initial_permits(self) -> int:
        """碳交易初始碳權"""
        return self.get('stages.carbon_trading.carbon_allowance_per_player', 10)
    
    @property
    def carbon_trading_time(self) -> int:
        """碳交易時間（秒）"""
        return self.get('stages.carbon_trading.trading_time', 120)
    
    @property
    def carbon_trading_reset_cash_each_round(self) -> bool:
        """碳交易是否每輪重置現金"""
        return self.get('stages.carbon_trading.reset_cash_each_round', True)
    
    @property
    def carbon_allowance_per_player(self) -> int:
        """每玩家碳權配額"""
        return self.get('stages.carbon_trading.carbon_allowance_per_player', 10)
    
    # ========== 碳權分配計算參數 ==========
    
    @property
    def carbon_trading_use_fixed_price(self) -> bool:
        """是否使用固定價格"""
        return self.get('stages.carbon_trading.optimal_allocation.use_fixed_price', True)
    
    @property
    def carbon_trading_fixed_market_price(self) -> float:
        """固定市場價格"""
        return self.get('stages.carbon_trading.optimal_allocation.fixed_market_price', 10)
    
    @property
    def carbon_trading_social_cost_per_unit_carbon(self) -> float:
        """每單位碳的社會成本"""
        return self.get('stages.carbon_trading.optimal_allocation.social_cost_per_unit_carbon', 2)
    
    @property
    def carbon_trading_cap_multipliers(self) -> List[float]:
        """配額倍率選項"""
        return self.get('stages.carbon_trading.optimal_allocation.cap_multipliers', [0.8, 1.0, 1.2])
    
    @property
    def carbon_trading_allocation_method(self) -> str:
        """分配方法"""
        return self.get('stages.carbon_trading.optimal_allocation.allocation_method', 'equal_with_random_remainder')
    
    @property
    def carbon_trading_round_cap_total(self) -> bool:
        """是否將配額總數四捨五入"""
        return self.get('stages.carbon_trading.optimal_allocation.round_cap_total', True)
    
    @property
    def grandfathering_rule(self) -> Dict[str, Any]:
        return self.get(
            'stages.carbon_trading.optimal_allocation.grandfathering_rule',{})

    @property
    def carbon_trading_show_detailed_calculation(self) -> bool:
        """是否顯示詳細計算"""
        return self.get('stages.carbon_trading.output.show_detailed_calculation', True)
    
    @property
    def carbon_trading_decimal_places(self) -> int:
        """小數位數"""
        return self.get('stages.carbon_trading.output.decimal_places', 2)
    
    @property
    def carbon_trading_console_output_format(self) -> str:
        """控制台輸出格式"""
        return self.get('stages.carbon_trading.output.console_output_format', 'detailed')
    
    # ========== 市場價格 ==========
    
    @property
    def market_price_options(self) -> List['Currency']:
        """市場價格選項"""
        from otree.api import cu
        base_prices = self.get('general.market_price_random_draw.base_prices', [25, 30, 35, 40])
        variations = self.get('general.market_price_random_draw.variations', [-2, -1, 1, 2])
        min_price = self.get('general.market_price_random_draw.min_price', 1)
        
        # 生成所有可能的價格組合
        all_prices = []
        for base in base_prices:
            for var in variations:
                price = max(base + var, min_price)
                all_prices.append(price)
        
        return [cu(price) for price in all_prices]
    
    # ========== UI文字 ==========
    
    def get_treatment_name(self, treatment: str) -> str:
        """獲取處理組別名稱"""
        treatment_names = self.get('ui_text.zh_tw.treatment_names', {})
        return treatment_names.get(treatment, treatment)
    
    def get_page_sequence(self, stage: str) -> List[str]:
        """獲取頁面序列"""
        return self.get(f'page_sequences.{stage}', [])

# 創建全局配置實例
config = ExperimentConfig()

class ConfigConstants:
    """配置常數類別（兼容舊代碼）"""
    
    @property
    def PLAYERS_PER_GROUP(self) -> int:
        return config.players_per_group
    
    @property
    def NUM_ROUNDS(self) -> int:
        return config.num_rounds
    
    @property
    def MAX_PRODUCTION(self) -> int:
        return config.max_production
    
    @property
    def INITIAL_CAPITAL(self) -> 'Currency':
        from otree.api import cu
        return cu(1000)
    
    @property
    def TRADING_TIME(self) -> int:
        return config.muda_trading_time
    
    @property
    def CARBON_TRADING_INITIAL_PERMITS(self) -> int:
        return config.carbon_trading_initial_permits

# 創建全局常數實例
config_constants = ConfigConstants() 
