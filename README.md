# Carbon Emissions Trading Experiment Platform

**Language / 語言**: [English](#english) | [中文](#中文版本)

---

## English

An experimental economics platform built on the oTree framework, specifically designed to study the impact of different carbon reduction policies on firm production behavior.

### Platform Features

This platform supports four experimental treatment groups, providing a comprehensive research environment for carbon emission policies:

- **Control Group**: Baseline experiment without carbon emission restrictions
- **Carbon Tax Group**: Policy experiment with carbon tax based on emission levels
- **Carbon Trading Group**: Carbon permit market experiment with real-time trading functionality
- **MUDA Practice Group**: Trading system operation training experiment

Core features include real-time trading system, intelligent matching engine, comprehensive data tracking, flexible configuration management, and modern user interface.

### Quick Start

#### System Requirements

- Python 3.7 or higher
- oTree 5.10.0 or higher
- PostgreSQL (production) or SQLite (development)

#### Installation Steps

1. **Download the project**
```bash
git clone <repository-url>
cd Carbon-Emissions-Trading-Experiment
```

2. **Create virtual environment**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Initialize and start**
```bash
otree resetdb
otree devserver
```

After starting, visit `http://localhost:8000` to begin the experiment.

### Configuration Settings

#### Test Mode and Production Mode

The platform supports two operating modes, which can be switched by editing `configs/experiment_config.yaml`:

```yaml
experiment_mode:
  test_mode_enabled: true  # true = test mode, false = production mode
```

**Mode Comparison**

| Item | Test Mode | Production Mode |
|------|----------|-----------------|
| Players per group | 2 players | 15 players |
| Number of rounds | 3 rounds | 15 rounds |
| Dominant firms | 1 firm | 3 firms |
| Trading time | 60 seconds | 120-180 seconds |

#### Main Parameter Settings

The configuration file contains complete experimental settings including firm role parameters, carbon tax settings, and trading parameters:

```yaml
general:
  dominant_firm:
    mc_range: [1, 5]        # Marginal cost coefficient range
    emission_per_unit: 2    # Carbon emission per unit
    max_production: 20      # Maximum production capacity
    
  non_dominant_firm:
    mc_range: [2, 7]
    emission_per_unit: 1
    max_production: 8

stages:
  carbon_tax:
    tax_random_selection:
      rates: [1, 2, 3]      # Carbon tax rate options
      
  carbon_trading:
    trading_time: 120       # Trading time (seconds)
    carbon_allowance_per_player: 10  # Initial carbon allowance
```

### Experimental Groups Description

#### Control Group
**Experimental Flow**: Introduction → Production Decision → Results Display  
**Features**: No carbon emission restrictions, establishing baseline data for pure market mechanisms

#### Carbon Tax Group
**Experimental Flow**: Introduction → Production Decision → Results Display  
**Features**: Carbon tax levied based on emission levels, with tax calculation formula: Carbon Tax = Emission Level × Tax Rate

#### Carbon Trading Group
**Experimental Flow**: Introduction → Carbon Permit Trading → Production Decision → Results Display  
**Features**: Participants must first engage in carbon permit trading, production is limited by carbon permit holdings, using real-time matching trading mechanism

#### MUDA Practice Group
**Experimental Flow**: Introduction → Trading Practice → Results Display  
**Features**: Pure trading operation practice without production decisions, used for familiarizing with the trading interface

### Core Technical Mechanisms

#### Production Cost Calculation
Total cost uses an increasing marginal cost structure:
```
Total Cost = Σ(Marginal Cost Coefficient × i + Random Disturbance) for i = 1 to Production Quantity
```

#### Carbon Permit Trading Mechanism
- **Order Types**: Limit buy and sell orders
- **Matching Rules**: Price priority, time priority
- **Trading Restrictions**: Sell order quantity cannot exceed holdings
- **Real-time Updates**: Using WebSocket technology for real-time market status synchronization

#### Data Collection Scope
- **Production Decisions**: Output, cost, revenue, profit data
- **Trading Behavior**: Complete records of orders, transactions, cancellations
- **Market Dynamics**: Price trends, trading volume, market depth changes

### Project Architecture

```
Carbon-Emissions-Trading-Experiment/
├── configs/                # Experimental configuration files
│   ├── experiment_config.yaml
│   └── config.py
├── utils/                  # Shared utility modules
│   └── shared_utils.py
├── Stage_Control/          # Control group experiment
├── Stage_CarbonTax/        # Carbon tax group experiment
├── Stage_MUDA/             # Practice group experiment
├── Stage_CarbonTrading/    # Carbon trading group experiment
├── docs/                   # Related documentation
└── requirements.txt        # Dependency list
```

### Data Analysis Support

The platform automatically collects experimental data and supports export in multiple formats:
- **CSV Format**: Suitable for statistical software analysis
- **JSON Format**: Suitable for programmatic processing
- **Excel Format**: Suitable for manual inspection and preliminary analysis

All data includes integrity checking mechanisms to ensure analysis-ready data quality.

### Deployment Instructions

#### Environment Variables Setup
```bash
OTREE_ADMIN_PASSWORD=your_password
OTREE_SECRET_KEY=your_secret_key
DATABASE_URL=postgresql://user:pass@host:port/dbname
```

#### Docker Containerized Deployment
```dockerfile
FROM python:3.9
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["otree", "prodserver", "0.0.0.0:8000"]
```

### Related Documentation

- [System Functions and Operating Logic](docs/系統功能與運作邏輯說明.md)
- [Development Work Log](docs/工作日誌_碳排放交易實驗平台.md)
- [Data Codebook](docs/codebook.md)
- [Database Cleaner Tool Instructions](docs/資料庫清理工具.md)

### Technical Support

For technical issues or research collaboration inquiries, please submit through GitHub Issues.

---

## 中文版本

基於 oTree 框架開發的經濟學實驗平台，專門用於研究不同碳減排政策對廠商生產行為的影響。

### 平台特色

本平台支援四種實驗處理組別，提供完整的碳排放政策研究環境：

- **對照組**：無碳排放限制的基準實驗
- **碳稅組**：基於碳排放量徵收稅金的政策實驗
- **碳交易組**：具備即時交易功能的碳權市場實驗
- **MUDA 練習組**：交易系統操作訓練實驗

核心功能包括即時交易系統、智慧撮合引擎、完整數據追蹤、靈活配置管理和現代化使用者介面。

### 快速開始

#### 系統需求

- Python 3.7 或更高版本
- oTree 5.10.0 或更高版本
- PostgreSQL（生產環境）或 SQLite（開發環境）

#### 安裝步驟

1. **下載專案**
```bash
git clone <repository-url>
cd Carbon-Emissions-Trading-Experiment
```

2. **建立虛擬環境**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

3. **安裝相依套件**
```bash
pip install -r requirements.txt
```

4. **初始化並啟動**
```bash
otree resetdb
otree devserver
```

啟動後請造訪 `http://localhost:8000` 開始實驗。

### 配置設定

#### 測試模式與正式模式

平台支援兩種運行模式，可透過編輯 `configs/experiment_config.yaml` 進行切換：

```yaml
experiment_mode:
  test_mode_enabled: true  # true = 測試模式, false = 正式模式
```

**模式差異對比**

| 項目 | 測試模式 | 正式模式 |
|------|----------|----------|
| 每組人數 | 2 人 | 15 人 |
| 回合數 | 3 回合 | 15 回合 |
| 主導廠商數量 | 1 個 | 3 個 |
| 交易時間 | 60 秒 | 120-180 秒 |

#### 主要參數設定

配置檔案包含廠商角色參數、碳稅設定、交易參數等完整實驗設定：

```yaml
general:
  dominant_firm:
    mc_range: [1, 5]        # 邊際成本係數範圍
    emission_per_unit: 2    # 每單位碳排放量
    max_production: 20      # 最大生產能力
    
  non_dominant_firm:
    mc_range: [2, 7]
    emission_per_unit: 1
    max_production: 8

stages:
  carbon_tax:
    tax_random_selection:
      rates: [1, 2, 3]      # 碳稅率選項
      
  carbon_trading:
    trading_time: 120       # 交易時間（秒）
    carbon_allowance_per_player: 10  # 初始碳權配額
```

### 實驗組別說明

#### 對照組
**實驗流程**：介紹 → 生產決策 → 結果顯示  
**特點**：無碳排放限制，建立純市場機制的基準數據

#### 碳稅組
**實驗流程**：介紹 → 生產決策 → 結果顯示  
**特點**：根據碳排放量徵收稅金，稅額計算公式為：碳稅 = 碳排放量 × 稅率

#### 碳交易組
**實驗流程**：介紹 → 碳權交易 → 生產決策 → 結果顯示  
**特點**：參與者需先進行碳權交易，生產量受碳權持有量限制，採用即時撮合交易機制

#### MUDA 練習組
**實驗流程**：介紹 → 交易練習 → 結果顯示  
**特點**：純交易操作練習，不涉及生產決策，用於熟悉交易介面

### 核心技術機制

#### 生產成本計算
總成本採用遞增邊際成本結構：
```
總成本 = Σ(邊際成本係數 × i + 隨機擾動) for i = 1 to 生產量
```

#### 碳權交易機制
- **訂單類型**：限價買單和賣單
- **撮合規則**：價格優先、時間優先
- **交易限制**：賣單數量不得超過持有量
- **即時更新**：使用 WebSocket 技術實現即時市場狀態同步

#### 數據收集範圍
- **生產決策**：產量、成本、收益、利潤數據
- **交易行為**：掛單、成交、撤單完整記錄
- **市場動態**：價格走勢、成交量、市場深度變化

### 專案架構

```
Carbon-Emissions-Trading-Experiment/
├── configs/                # 實驗配置檔案
│   ├── experiment_config.yaml
│   └── config.py
├── utils/                  # 共用工具模組
│   └── shared_utils.py
├── Stage_Control/          # 對照組實驗
├── Stage_CarbonTax/        # 碳稅組實驗
├── Stage_MUDA/             # 練習組實驗
├── Stage_CarbonTrading/    # 碳交易組實驗
├── docs/                   # 相關文檔
└── requirements.txt        # 相依套件清單
```

### 數據分析支援

平台自動收集的實驗數據支援多種格式匯出：
- **CSV 格式**：適用於統計軟體分析
- **JSON 格式**：適用於程式化處理
- **Excel 格式**：適用於人工檢視和初步分析

所有數據均包含完整性檢查機制，確保分析就緒的數據品質。

### 部署說明

#### 環境變數設定
```bash
OTREE_ADMIN_PASSWORD=your_password
OTREE_SECRET_KEY=your_secret_key
DATABASE_URL=postgresql://user:pass@host:port/dbname
```

#### Docker 容器化部署
```dockerfile
FROM python:3.9
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["otree", "prodserver", "0.0.0.0:8000"]
```

### 相關文檔

- [系統功能與運作邏輯說明](docs/系統功能與運作邏輯說明.md)
- [開發工作日誌](docs/工作日誌_碳排放交易實驗平台.md)
- [數據編碼簿](docs/codebook.md)
- [資料庫清理工具說明](docs/資料庫清理工具.md)

### 技術支援

如有技術問題或研究合作需求，請透過 GitHub Issues 提出。
