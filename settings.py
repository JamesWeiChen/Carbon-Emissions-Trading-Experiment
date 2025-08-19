from os import environ
from configs.config import config


SESSION_CONFIGS = [
    {
        'name': config.get_stage_name_in_url('control'),
        'app_sequence': [config.get_stage_name_in_url('control')],
        'num_demo_participants': config.players_per_group,
        'display_name': config.get_stage_display_name('control'),
    },

    {
        'name': config.get_stage_name_in_url('carbon_tax'),
        'app_sequence': [config.get_stage_name_in_url('carbon_tax')],
        'num_demo_participants': config.players_per_group,
        'display_name': config.get_stage_display_name('carbon_tax'),
    },

    {
        'name': config.get_stage_name_in_url('muda'),
        'app_sequence': [config.get_stage_name_in_url('muda')],
        'num_demo_participants': config.players_per_group,
        'display_name': config.get_stage_display_name('muda'),
    },

    {
        'name': config.get_stage_name_in_url('carbon_trading'),
        'app_sequence': [config.get_stage_name_in_url('carbon_trading')],
        'num_demo_participants': config.players_per_group,
        'display_name': config.get_stage_display_name('carbon_trading'),
        'allocation_method': 'grandfathering',
    },

    {
        'name': config.get_stage_name_in_url('payment_info'),
        'app_sequence': [config.get_stage_name_in_url('payment_info')],
        'num_demo_participants': config.players_per_group,
        'display_name': config.get_stage_display_name('payment_info'),
    },

    {
        'name': 'Survey',
        'app_sequence': [config.get_stage_name_in_url('survey')],
        'num_demo_participants': config.players_per_group,
        'display_name': "問卷",
    },

    
    {
        'name': 'Experiment_Carbon_Grandfathering',
        'app_sequence': ['wait_start', config.get_stage_name_in_url('control'), config.get_stage_name_in_url('carbon_tax'), config.get_stage_name_in_url('muda'), config.get_stage_name_in_url('carbon_trading'),config.get_stage_name_in_url('payment_info'), config.get_stage_name_in_url('survey')],
        'num_demo_participants': config.players_per_group,
        'display_name': "正式實驗：祖父權力",
        'allocation_method': 'grandfathering',
    },

    {
        'name': 'Experiment_Carbon_Equal',
        'app_sequence': ['wait_start', config.get_stage_name_in_url('control'), config.get_stage_name_in_url('carbon_tax'), config.get_stage_name_in_url('muda'), config.get_stage_name_in_url('carbon_trading'),config.get_stage_name_in_url('payment_info'), config.get_stage_name_in_url('survey')],
        'num_demo_participants': config.players_per_group,
        'display_name': "正式實驗：平均分配",
        'allocation_method': 'equal',
    },

]


SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.0, participation_fee=150.00, doc=""
)

PARTICIPANT_FIELDS = []
SESSION_FIELDS = []

POINTS_CUSTOM_NAME = '法幣'

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'en'

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = 'TWD'
USE_POINTS = True

ROOMS = [
    dict(
        name='tassel',
        display_name='TASSEL',
        participant_label_file='_rooms/tassel.txt',
    ),
]

ADMIN_USERNAME = 'admin'
# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """
Here are some oTree games.
"""


SECRET_KEY = '5406477812875'

INSTALLED_APPS = ['otree']

# 新增：確保共享工具庫模組可被正確導入
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# DEBUG = environ.get('OTREE_PRODUCTION') in {None, '', '0'}
