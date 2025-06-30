# Carbon Emissions Trading Experiment Platform
# 碳排放交易實驗平台

An experimental economics platform built on the oTree framework, specifically designed to study the impact of different carbon reduction policies on firm production behavior.

基於 oTree 框架開發的經濟學實驗平台，專門用於研究不同碳減排政策對廠商生產行為的影響。

## Platform Features / 平台特色

This platform supports four experimental treatment groups, providing a comprehensive research environment for carbon emission policies:

本平台支援四種實驗處理組別，提供完整的碳排放政策研究環境：

- **Control Group / 對照組**: Baseline experiment without carbon emission restrictions / 無碳排放限制的基準實驗
- **Carbon Tax Group / 碳稅組**: Policy experiment with carbon tax based on emission levels / 基於碳排放量徵收稅金的政策實驗
- **Carbon Trading Group / 碳交易組**: Carbon permit market experiment with real-time trading functionality / 具備即時交易功能的碳權市場實驗
- **MUDA Practice Group / MUDA 練習組**: Trading system operation training experiment / 交易系統操作訓練實驗

Core features include real-time trading system, intelligent matching engine, comprehensive data tracking, flexible configuration management, and modern user interface.

核心功能包括即時交易系統、智慧撮合引擎、完整數據追蹤、靈活配置管理和現代化使用者介面。

## Quick Start / 快速開始

### System Requirements / 系統需求

- Python 3.7 or higher / Python 3.7 或更高版本
- oTree 5.10.0 or higher / oTree 5.10.0 或更高版本
- PostgreSQL (production) or SQLite (development) / PostgreSQL（生產環境）或 SQLite（開發環境）

### Installation Steps / 安裝步驟

1. **Download the project / 下載專案**
```bash
git clone <repository-url>
cd Carbon-Emissions-Trading-Experiment
```

2. **Create virtual environment / 建立虛擬環境**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

3. **Install dependencies / 安裝相依套件**
```bash
pip install -r requirements.txt
```

4. **Initialize and start / 初始化並啟動**
```bash
otree resetdb
otree devserver
```

After starting, visit `http://localhost:8000` to begin the experiment.

啟動後請造訪 `http://localhost:8000` 開始實驗。

## Configuration Settings / 配置設定

### Test Mode and Production Mode / 測試模式與正式模式

The platform supports two operating modes, which can be switched by editing `configs/experiment_config.yaml`:

平台支援兩種運行模式，可透過編輯 `configs/experiment_config.yaml` 進行切換：

```yaml
experiment_mode:
  test_mode_enabled: true  # true = test mode, false = production mode
                          # true = 測試模式, false = 正式模式
```

**Mode Comparison / 模式差異對比**

| Item / 項目 | Test Mode / 測試模式 | Production Mode / 正式模式 |
|-------------|---------------------|---------------------------|
| Players per group / 每組人數 | 2 players / 2 人 | 15 players / 15 人 |
| Number of rounds / 回合數 | 3 rounds / 3 回合 | 15 rounds / 15 回合 |
| Dominant firms / 主導廠商數量 | 1 firm / 1 個 | 3 firms / 3 個 |
| Trading time / 交易時間 | 60 seconds / 60 秒 | 120-180 seconds / 120-180 秒 |

### Main Parameter Settings / 主要參數設定

The configuration file contains complete experimental settings including firm role parameters, carbon tax settings, and trading parameters:

配置檔案包含廠商角色參數、碳稅設定、交易參數等完整實驗設定：

```yaml
general:
  dominant_firm:
    mc_range: [1, 5]        # Marginal cost coefficient range / 邊際成本係數範圍
    emission_per_unit: 2    # Carbon emission per unit / 每單位碳排放量
    max_production: 20      # Maximum production capacity / 最大生產能力
    
  non_dominant_firm:
    mc_range: [2, 7]
    emission_per_unit: 1
    max_production: 8

stages:
  carbon_tax:
    tax_random_selection:
      rates: [1, 2, 3]      # Carbon tax rate options / 碳稅率選項
      
  carbon_trading:
    trading_time: 120       # Trading time (seconds) / 交易時間（秒）
    carbon_allowance_per_player: 10  # Initial carbon allowance / 初始碳權配額
```

## Experimental Groups Description / 實驗組別說明

### Control Group / 對照組
**Experimental Flow / 實驗流程**: Introduction → Production Decision → Results Display / 介紹 → 生產決策 → 結果顯示  
**Features / 特點**: No carbon emission restrictions, establishing baseline data for pure market mechanisms / 無碳排放限制，建立純市場機制的基準數據

### Carbon Tax Group / 碳稅組
**Experimental Flow / 實驗流程**: Introduction → Production Decision → Results Display / 介紹 → 生產決策 → 結果顯示  
**Features / 特點**: Carbon tax levied based on emission levels, with tax calculation formula: Carbon Tax = Emission Level × Tax Rate / 根據碳排放量徵收稅金，稅額計算公式為：碳稅 = 碳排放量 × 稅率

### Carbon Trading Group / 碳交易組
**Experimental Flow / 實驗流程**: Introduction → Carbon Permit Trading → Production Decision → Results Display / 介紹 → 碳權交易 → 生產決策 → 結果顯示  
**Features / 特點**: Participants must first engage in carbon permit trading, production is limited by carbon permit holdings, using real-time matching trading mechanism / 參與者需先進行碳權交易，生產量受碳權持有量限制，採用即時撮合交易機制

### MUDA Practice Group / MUDA 練習組
**Experimental Flow / 實驗流程**: Introduction → Trading Practice → Results Display / 介紹 → 交易練習 → 結果顯示  
**Features / 特點**: Pure trading operation practice without production decisions, used for familiarizing with the trading interface / 純交易操作練習，不涉及生產決策，用於熟悉交易介面

## Core Technical Mechanisms / 核心技術機制

### Production Cost Calculation / 生產成本計算
Total cost uses an increasing marginal cost structure:

總成本採用遞增邊際成本結構：
```
Total Cost = Σ(Marginal Cost Coefficient × i + Random Disturbance) for i = 1 to Production Quantity
總成本 = Σ(邊際成本係數 × i + 隨機擾動) for i = 1 to 生產量
```

### Carbon Permit Trading Mechanism / 碳權交易機制
- **Order Types / 訂單類型**: Limit buy and sell orders / 限價買單和賣單
- **Matching Rules / 撮合規則**: Price priority, time priority / 價格優先、時間優先
- **Trading Restrictions / 交易限制**: Sell order quantity cannot exceed holdings / 賣單數量不得超過持有量
- **Real-time Updates / 即時更新**: Using WebSocket technology for real-time market status synchronization / 使用 WebSocket 技術實現即時市場狀態同步

### Data Collection Scope / 數據收集範圍
- **Production Decisions / 生產決策**: Output, cost, revenue, profit data / 產量、成本、收益、利潤數據
- **Trading Behavior / 交易行為**: Complete records of orders, transactions, cancellations / 掛單、成交、撤單完整記錄
- **Market Dynamics / 市場動態**: Price trends, trading volume, market depth changes / 價格走勢、成交量、市場深度變化

## Project Architecture / 專案架構

```
Carbon-Emissions-Trading-Experiment/
├── configs/                # Experimental configuration files / 實驗配置檔案
│   ├── experiment_config.yaml
│   └── config.py
├── utils/                  # Shared utility modules / 共用工具模組
│   └── shared_utils.py
├── Stage_Control/          # Control group experiment / 對照組實驗
├── Stage_CarbonTax/        # Carbon tax group experiment / 碳稅組實驗
├── Stage_MUDA/             # Practice group experiment / 練習組實驗
├── Stage_CarbonTrading/    # Carbon trading group experiment / 碳交易組實驗
├── docs/                   # Related documentation / 相關文檔
└── requirements.txt        # Dependency list / 相依套件清單
```

## Data Analysis Support / 數據分析支援

The platform automatically collects experimental data and supports export in multiple formats:

平台自動收集的實驗數據支援多種格式匯出：
- **CSV Format / CSV 格式**: Suitable for statistical software analysis / 適用於統計軟體分析
- **JSON Format / JSON 格式**: Suitable for programmatic processing / 適用於程式化處理
- **Excel Format / Excel 格式**: Suitable for manual inspection and preliminary analysis / 適用於人工檢視和初步分析

All data includes integrity checking mechanisms to ensure analysis-ready data quality.

所有數據均包含完整性檢查機制，確保分析就緒的數據品質。

## Deployment Instructions / 部署說明

### Environment Variables Setup / 環境變數設定
```bash
OTREE_ADMIN_PASSWORD=your_password
OTREE_SECRET_KEY=your_secret_key
DATABASE_URL=postgresql://user:pass@host:port/dbname
```

### Docker Containerized Deployment / Docker 容器化部署
```dockerfile
FROM python:3.9
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["otree", "prodserver", "0.0.0.0:8000"]
```

## Related Documentation / 相關文檔

- [System Functions and Operating Logic / 系統功能與運作邏輯說明](docs/系統功能與運作邏輯說明.md)
- [Test Mode Switching Instructions / 測試模式切換說明](docs/測試模式切換說明.md)
- [Development Work Log / 開發工作日誌](docs/工作日誌_碳排放交易實驗平台.md)
- [Data Codebook / 數據編碼簿](docs/codebook.md)
- [Database Cleaner Tool Instructions / 資料庫清理工具說明](docs/資料庫清理工具.md)

## Technical Support / 技術支援

For technical issues or research collaboration inquiries, please submit through GitHub Issues.

如有技術問題或研究合作需求，請透過 GitHub Issues 提出。

---

**Developer / 開發者**: Levi  
**Last Updated / 最後更新**: June 2025 / 2025 年 6 月  
**Version / 版本**: 3.0  
**License / 授權**: See [LICENSE](LICENSE) / 請見 [LICENSE](LICENSE)
