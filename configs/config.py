"""
碳排放交易實驗配置文件
統一管理所有實驗參數和設定
"""
import yaml
import os
import random

class ExperimentConfig:
    def __init__(self, config_file='configs/experiment_config.yaml'):
        self.config_file = config_file
        self.load_config()
        self._test_mode_enabled = None  # 緩存測試模式狀態
    
    def load_config(self):
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
        except FileNotFoundError:
            print(f"配置文件 {self.config_file} 未找到，使用默認配置")
            self._config = self._get_default_config()
        except yaml.YAMLError as e:
            print(f"配置文件解析錯誤: {e}")
            self._config = self._get_default_config()
    
    def _get_default_config(self):
        return {
            'general': {
                'players_per_group': 15,
                'num_rounds': 15,
                'max_production': 50,
                'role_assignment': {
                    'test_mode': False,
                    'production_mode': True,
                    'dominant_firm_count': 3,
                    'non_dominant_firm_count': 12
                }
            },
            'test_mode': {
                'enabled': False
            }
        }
    
    def get(self, key_path, default=None):
        """獲取配置值，優先從測試模式配置獲取（如果啟用）"""
        # 檢查是否啟用測試模式
        if self.is_test_mode_enabled() and not key_path.startswith('test_mode'):
            # 嘗試從測試模式配置獲取
            test_mode_path = f'test_mode.{key_path}'
            test_value = self._get_value(test_mode_path)
            if test_value is not None:
                return test_value
        
        # 從正式配置獲取
        return self._get_value(key_path, default)
    
    def _get_value(self, key_path, default=None):
        """從配置中獲取值的內部方法"""
        keys = key_path.split('.')
        value = self._config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def is_test_mode_enabled(self):
        """檢查是否啟用測試模式"""
        if self._test_mode_enabled is None:
            self._test_mode_enabled = self._get_value('test_mode.enabled', False)
        return self._test_mode_enabled
    
    def set_test_mode(self, enabled):
        """設置測試模式狀態"""
        self._test_mode_enabled = enabled

    @property
    def players_per_group(self):
        return self.get('general.players_per_group', 15)
    
    @property
    def num_rounds(self):
        return self.get('general.num_rounds', 15)
    
    @property
    def max_production(self):
        return self.get('general.max_production', 50)
    
    @property
    def test_mode(self):
        """兼容舊代碼：返回是否為測試模式"""
        return self.is_test_mode_enabled()
    
    @property
    def production_mode(self):
        """兼容舊代碼：返回是否為正式模式"""
        return not self.is_test_mode_enabled()
    
    @property
    def dominant_firm_count(self):
        """獲取主導廠商數量"""
        if self.is_test_mode_enabled():
            # 測試模式根據比例計算
            ratio = self.get('general.role_assignment.dominant_firm_ratio', 0.5)
            return max(1, int(self.players_per_group * ratio))
        else:
            # 正式模式使用固定數量
            return self.get('general.role_assignment.dominant_firm_count', 3)
    
    @property
    def non_dominant_firm_count(self):
        """獲取非主導廠商數量"""
        return self.players_per_group - self.dominant_firm_count
    
    def get_stage_initial_capital(self, stage):
        from otree.api import cu
        return cu(self.get(f'stages.{stage}.initial_capital', 1000))
    
    @property
    def dominant_mc_range(self):
        return tuple(self.get('general.dominant_firm.mc_range', [1, 5]))
    
    @property
    def non_dominant_mc_range(self):
        return tuple(self.get('general.non_dominant_firm.mc_range', [2, 7]))
    
    @property
    def dominant_emission_per_unit(self):
        return self.get('general.dominant_firm.emission_per_unit', 2)
    
    @property
    def non_dominant_emission_per_unit(self):
        return self.get('general.non_dominant_firm.emission_per_unit', 1)
    
    @property
    def dominant_max_production(self):
        return self.get('general.dominant_firm.max_production', 20)
    
    @property
    def non_dominant_max_production(self):
        return self.get('general.non_dominant_firm.max_production', 8)
    
    @property
    def ensure_player1_dominant(self):
        return self.get('general.role_assignment.ensure_player1_dominant', False)
    
    @property
    def random_disturbance_range(self):
        return tuple(self.get('general.random_disturbance.range', [-1, 1]))
    
    def get_stage_name_in_url(self, stage):
        return self.get(f'stages.{stage}.name_in_url', stage)
    
    def get_stage_description(self, stage):
        return self.get(f'stages.{stage}.description', f'{stage} 階段')
    
    def get_stage_display_name(self, stage):
        return self.get(f'stages.{stage}.display_name', f'{stage.title()} 階段')
    
    @property
    def carbon_tax_rates(self):
        return self.get('stages.carbon_tax.tax_random_selection.rates', [1, 2, 3])
    
    @property
    def tax_rate_options(self):
        from otree.api import cu
        return [cu(rate) for rate in self.carbon_tax_rates]
    
    @property
    def muda_trading_time(self):
        return self.get('stages.muda.trading_time', 180)
    
    @property
    def muda_initial_capital(self):
        from otree.api import cu
        return cu(self.get('stages.muda.initial_capital', 10000))
    
    @property
    def muda_item_price_options(self):
        return self.get('stages.muda.item_price_options', [25, 30, 35, 40])
    
    @property
    def muda_item_name(self):
        return self.get('stages.muda.item_name', '碳權')
    
    @property
    def muda_reset_cash_each_round(self):
        return self.get('stages.muda.reset_cash_each_round', True)
    
    @property
    def carbon_trading_initial_capital(self):
        from otree.api import cu
        return cu(self.get('stages.carbon_trading.initial_capital', 10000))
    
    @property
    def carbon_trading_initial_permits(self):
        return self.get('stages.carbon_trading.carbon_allowance_per_player', 10)
    
    @property
    def carbon_trading_time(self):
        return self.get('stages.carbon_trading.trading_time', 120)
    
    @property
    def carbon_trading_reset_cash_each_round(self):
        return self.get('stages.carbon_trading.reset_cash_each_round', True)
    
    @property
    def carbon_allowance_per_player(self):
        return self.get('stages.carbon_trading.carbon_allowance_per_player', 10)
    
    # 碳權分配計算相關參數
    @property
    def carbon_trading_use_fixed_price(self):
        return self.get('stages.carbon_trading.optimal_allocation.use_fixed_price', True)
    
    @property
    def carbon_trading_fixed_market_price(self):
        return self.get('stages.carbon_trading.optimal_allocation.fixed_market_price', 10)
    
    @property
    def carbon_trading_social_cost_per_unit_carbon(self):
        return self.get('stages.carbon_trading.optimal_allocation.social_cost_per_unit_carbon', 2)
    
    @property
    def carbon_trading_cap_multipliers(self):
        return self.get('stages.carbon_trading.optimal_allocation.cap_multipliers', [0.8, 1.0, 1.2])
    
    @property
    def carbon_trading_allocation_method(self):
        return self.get('stages.carbon_trading.optimal_allocation.allocation_method', 'equal_with_random_remainder')
    
    @property
    def carbon_trading_round_cap_total(self):
        return self.get('stages.carbon_trading.optimal_allocation.round_cap_total', True)
    
    @property
    def carbon_trading_show_detailed_calculation(self):
        return self.get('stages.carbon_trading.output.show_detailed_calculation', True)
    
    @property
    def carbon_trading_decimal_places(self):
        return self.get('stages.carbon_trading.output.decimal_places', 2)
    
    @property
    def carbon_trading_console_output_format(self):
        return self.get('stages.carbon_trading.output.console_output_format', 'detailed')
    
    @property
    def market_price_options(self):
        from otree.api import cu
        # 使用新的隨機抽取機制
        base_prices = self.get('general.market_price_random_draw.base_prices', [25, 30, 35, 40])
        variations = self.get('general.market_price_random_draw.variations', [-2, -1, 1, 2])
        min_price = self.get('general.market_price_random_draw.min_price', 1)
        
        # 生成所有可能的價格組合
        all_prices = []
        for base in base_prices:
            for var in variations:
                price = max(base + var, min_price)  # 確保不低於最低價格
                all_prices.append(price)
        
        return [cu(price) for price in all_prices]
    
    def get_treatment_name(self, treatment):
        treatment_names = self.get('ui_text.zh_tw.treatment_names', {})
        return treatment_names.get(treatment, treatment)
    
    def get_page_sequence(self, stage):
        return self.get(f'page_sequences.{stage}', [])

config = ExperimentConfig()

class ConfigConstants:
    @property
    def PLAYERS_PER_GROUP(self):
        return config.players_per_group
    
    @property
    def NUM_ROUNDS(self):
        return config.num_rounds
    
    @property
    def MAX_PRODUCTION(self):
        return config.max_production
    
    @property
    def INITIAL_CAPITAL(self):
        from otree.api import cu
        return cu(1000)
    
    @property
    def TRADING_TIME(self):
        return config.muda_trading_time
    
    @property
    def CARBON_TRADING_INITIAL_PERMITS(self):
        return config.carbon_trading_initial_permits

config_constants = ConfigConstants() 