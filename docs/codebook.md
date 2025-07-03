# 碳排放交易實驗平台 - 數據編碼簿

**版本**：3.2
**最後更新**：2025 年 7 月 3 日  
**實驗平台**：oTree 5.10.0+  

---

## 目錄

1. [總覽](#總覽)
2. [通用變數](#通用變數)
3. [對照組變數](#對照組變數)
4. [碳稅組變數](#碳稅組變數)
5. [MUDA 訓練組變數](#muda訓練組變數)
6. [碳交易組變數](#碳交易組變數)
7. [計算變數](#計算變數)
8. [數據匯出格式](#數據匯出格式)

---

## 總覽

### 實驗設計
- **處理組數**：4 組（對照組、碳稅組、MUDA 訓練組、碳交易組）
- **參與者**：
  - 正式模式：每組 15 人
  - 測試模式：每組 2 人
- **回合數**：
  - 正式模式：15 回合
  - 測試模式：3 回合
- **貨幣單位**：實驗幣（oTree Points）
- **數據收集**：全自動化，包含決策、交易、結果數據

### 資料表結構
實驗數據儲存在以下主要資料表中：
- `Stage_Control_Player` - 對照組玩家數據
- `Stage_CarbonTax_Player` - 碳稅組玩家數據  
- `Stage_MUDA_Player` - MUDA 訓練組玩家數據
- `Stage_CarbonTrading_Player` - 碳交易組玩家數據
- `Stage_*_Subsession` - 各組會話層級數據
- `Stage_*_Group` - 各組群組層級數據

---

## 通用變數

### 基本識別變數

| 變數名 | 類型 | 說明 | 取值範圍 | 備註 |
|--------|------|------|----------|------|
| `participant_id` | Integer | 參與者唯一識別碼 | 1-N | 跨組別唯一 |
| `session_id` | Integer | 會話識別碼 | 1-N | 實驗場次 |
| `group_id` | Integer | 群組識別碼 | 1-N | 正式：每組 15 人；測試：每組 2 人 |
| `id_in_group` | Integer | 組內玩家編號 | 1-15 | 正式：1-15；測試：1-2 |
| `round_number` | Integer | 回合數 | 1-15 | 正式：1-15；測試：1-3 |

### 角色與能力變數

| 變數名 | 類型 | 說明 | 取值範圍 | 備註 |
|--------|------|------|----------|------|
| `is_dominant` | Boolean | 是否為主導廠商 | 0/1 | 1 = 主導廠商, 0 = 非主導廠商 |
| `marginal_cost_coefficient` | Integer | 邊際成本係數 | 1-7 | 主導廠商：1-5, 非主導：2-7 |
| `carbon_emission_per_unit` | Float/Integer | 每單位碳排放量 | 1/2 | 主導廠商：2, 非主導：1（碳交易組為 Integer） |
| `max_production` | Integer | 最大生產能力 | 8/20 | 主導廠商：20, 非主導：8 |
| `market_price` | Currency | 市場價格 | 23-42 | 隨機分配，基礎價格 ± 變動 |

### 財務變數

| 變數名 | 類型 | 說明 | 取值範圍 | 備註 |
|--------|------|------|----------|------|
| `initial_capital` | Currency | 初始資金 | 300/10000 | 對照組/碳稅組：300, 交易組：10000 |
| `current_cash` | Currency | 當前現金 | -∞ to +∞ | 可為負數（碳交易組） |
| `final_cash` | Currency | 最終現金 | -∞ to +∞ | 包含收益後的現金 |

### 決策變數

| 變數名 | 類型 | 說明 | 取值範圍 | 備註 |
|--------|------|------|----------|------|
| `production` | Integer | 生產量決策 | 0-50 | 受最大生產能力限制 |

### 結果變數

| 變數名 | 類型 | 說明 | 取值範圍 | 備註 |
|--------|------|------|----------|------|
| `revenue` | Currency | 生產收益 | 0-2100 | production × market_price |
| `total_cost` | Float | 總生產成本 | 0-∞ | 包含隨機擾動 |
| `net_profit` | Float | 淨利潤 | -∞ to +∞ | 收益 - 成本 - 稅收（如有） |
| `payoff` | Float | 實驗報酬 | -∞ to +∞ | 等於 net_profit |

### 最終報酬變數

| 變數名 | 類型 | 說明 | 取值範圍 | 備註 |
|--------|------|------|----------|------|
| `selected_round` | Integer | 選中回合 | 1-15 | 隨機選擇用於最終報酬（正式：1-15；測試：1-3） |

---

## 對照組變數

### 資料表：`Stage_Control_Player`

對照組為基準組，不受碳排放政策限制。

#### 會話層級變數（`Stage_Control_Subsession`）

| 變數名 | 類型 | 說明 | 取值範圍 | 備註 |
|--------|------|------|----------|------|
| `market_price` | Currency | 市場價格 | 23-42 | 隨機分配，基礎價格 ± 變動 |

#### 玩家層級特有變數
*對照組玩家使用通用變數，無特有變數*

#### 成本計算公式
```
總成本 = Σ(i=1 to production) [marginal_cost_coefficient × i + random_disturbance_i]
```
其中 `random_disturbance_i ~ Uniform(-1, 1)`，使用固定種子確保一致性。

#### 利潤計算公式
```
淨利潤 = 收益 - 總成本
收益 = 生產量 × 市場價格
```

---

## 碳稅組變數

### 資料表：`Stage_CarbonTax_Player`

碳稅組需要為碳排放繳納稅金。

#### 會話層級變數（`Stage_CarbonTax_Subsession`）

| 變數名 | 類型 | 說明 | 取值範圍 | 備註 |
|--------|------|------|----------|------|
| `market_price` | Currency | 市場價格 | 23-42 | 隨機分配，基礎價格 ± 變動 |
| `tax_rate` | Currency | 碳稅率 | 1-3 | 每回合隨機選擇 |

#### 玩家層級特有變數

| 變數名 | 類型 | 說明 | 取值範圍 | 備註 |
|--------|------|------|----------|------|
| `carbon_tax_paid` | Float | 已繳碳稅 | 0-∞ | total_emissions × tax_rate |

#### 計算公式
```
總碳排放 = 生產量 × 每單位碳排放量
碳稅總額 = 總碳排放 × 碳稅率
淨利潤 = 收益 - 總成本 - 碳稅總額
```

---

## MUDA 訓練組變數

### 資料表：`Stage_MUDA_Player`

MUDA 組為純交易練習，不涉及生產決策。

#### 會話層級變數（`Stage_MUDA_Subsession`）

| 變數名 | 類型 | 說明 | 取值範圍 | 備註 |
|--------|------|------|----------|------|
| `item_market_price` | Currency | 碳權市場價格 | 25-40 | 隨機選擇 |
| `price_history` | LongString | 價格歷史 | JSON 格式 | 記錄價格變動 |
| `start_time` | Integer | 交易開始時間 | Unix 時間戳 | 用於計算交易時間 |

#### 群組層級變數（`Stage_MUDA_Group`）

| 變數名 | 類型 | 說明 | 取值範圍 | 備註 |
|--------|------|------|----------|------|
| `buy_orders` | LongString | 買單列表 | JSON 格式 | 即時買單 |
| `sell_orders` | LongString | 賣單列表 | JSON 格式 | 即時賣單 |
| `trade_history` | LongString | 交易歷史 | JSON 格式 | 所有成交記錄 |

#### 玩家層級變數

| 變數名 | 類型 | 說明 | 取值範圍 | 備註 |
|--------|------|------|----------|------|
| `buy_quantity` | Integer | 買單數量 | 0-∞ | 玩家提交的買單 |
| `buy_price` | Float | 買單價格 | 0-∞ | 玩家提交的買單價格 |
| `sell_quantity` | Integer | 賣單數量 | 0-∞ | 玩家提交的賣單 |
| `sell_price` | Float | 賣單價格 | 0-∞ | 玩家提交的賣單價格 |
| `cash` | Currency | 現金餘額 | -∞ to +∞ | 交易後現金 |
| `items` | Integer | 碳權持有量 | 0-∞ | 交易後碳權數量 |
| `current_cash` | Currency | 當前現金 | -∞ to +∞ | 即時現金餘額 |
| `current_items` | Integer | 當前碳權 | 0-∞ | 即時碳權持有量 |
| `personal_item_value` | Currency | 個人碳權價值 | 25-40 | 個人對碳權的估值 |
| `total_bought` | Integer | 累計購買量 | 0-∞ | 總購買碳權數量 |
| `total_sold` | Integer | 累計賣出量 | 0-∞ | 總賣出碳權數量 |
| `total_spent` | Currency | 累計支出 | 0-∞ | 總購買支出 |
| `total_earned` | Currency | 累計收入 | 0-∞ | 總賣出收入 |
| `item_value` | Currency | 碳權總價值 | 0-∞ | current_items × personal_item_value |
| `total_value` | Currency | 總資產價值 | -∞ to +∞ | current_cash + item_value |
| `submitted_offers` | LongString | 提交訂單記錄 | JSON 格式 | 所有提交的買賣單 |

#### 交易數據結構

##### `submitted_offers` JSON 格式
```json
[
  {
    "timestamp": 1703925600,
    "direction": "buy",
    "price": 30,
    "quantity": 5,
    "round": 1
  }
]
```

##### `price_history` JSON 格式
```json
[
  {
    "timestamp": "02:30",
    "price": 28.5,
    "event": "trade",
    "market_price": 30,
    "round": 1
  }
]
```

---

## 碳交易組變數

### 資料表：`Stage_CarbonTrading_Player`

碳交易組結合交易和生產決策，最為複雜。

#### 會話層級變數（`Stage_CarbonTrading_Subsession`）

| 變數名 | 類型 | 說明 | 取值範圍 | 備註 |
|--------|------|------|----------|------|
| `market_price` | Currency | 市場價格 | 23-42 | 隨機分配，基礎價格 ± 變動 |
| `price_history` | LongString | 價格歷史 | JSON 格式 | 記錄價格變動 |
| `start_time` | Integer | 交易開始時間 | Unix 時間戳 | 用於計算交易時間 |
| `total_optimal_emissions` | Float | 社會最適排放總量 | 0-∞ | 理論最適值 |
| `cap_multiplier` | Float | 配額倍率 | 0.8/1.0/1.2 | 隨機選擇 |
| `cap_total` | Integer | 總配額 | 0-∞ | 四捨五入後的整數 |
| `allocation_details` | LongString | 分配詳情 | JSON 格式 | 配額分配過程 |

#### 群組層級變數（`Stage_CarbonTrading_Group`）

| 變數名 | 類型 | 說明 | 取值範圍 | 備註 |
|--------|------|------|----------|------|
| `buy_orders` | LongString | 買單列表 | JSON 格式 | 即時買單 |
| `sell_orders` | LongString | 賣單列表 | JSON 格式 | 即時賣單 |
| `trade_history` | LongString | 交易歷史 | JSON 格式 | 所有成交記錄 |

#### 玩家層級變數

##### 碳權相關
| 變數名 | 類型 | 說明 | 取值範圍 | 備註 |
|--------|------|------|----------|------|
| `permits` | Integer | 初始碳權分配 | 0-∞ | 實驗開始時分配 |
| `current_permits` | Integer | 當前碳權餘額 | 0-∞ | 交易後餘額 |
| `optimal_production` | Float | 個人最適產量 | 0-∞ | 理論計算值 |
| `optimal_emissions` | Float | 個人最適排放量 | 0-∞ | 理論計算值 |

##### 交易統計
| 變數名 | 類型 | 說明 | 取值範圍 | 備註 |
|--------|------|------|----------|------|
| `total_bought` | Integer | 累計購買碳權 | 0-∞ | 總購買量 |
| `total_sold` | Integer | 累計賣出碳權 | 0-∞ | 總賣出量 |
| `total_spent` | Currency | 累計購買支出 | 0-∞ | 總支出金額 |
| `total_earned` | Currency | 累計賣出收入 | 0-∞ | 總收入金額 |
| `submitted_offers` | LongString | 提交訂單記錄 | JSON 格式 | 所有買賣單 |

#### 交易數據結構

##### `trade_history` JSON 格式
```json
[
  {
    "timestamp": "01:45",
    "buyer_id": 1,
    "seller_id": 2,
    "price": 25.0,
    "quantity": 3,
    "total_value": 75.0,
    "market_price": 30.0
  }
]
```

##### `buy_orders` / `sell_orders` JSON 格式
```json
[
  [player_id, price, quantity],
  [1, 28.0, 5],
  [2, 26.5, 3]
]
```

#### 生產約束
```
最大可生產量 = min(max_production, current_permits ÷ carbon_emission_per_unit)
```

#### 利潤計算公式
```
最終資產價值 = current_cash + revenue - production_cost
淨利潤 = 最終資產價值 - initial_capital
```

---

## 計算變數

### 衍生變數說明

以下變數在數據分析時可計算得出：

#### 效率指標
| 變數名 | 計算公式 | 說明 |
|--------|----------|------|
| `total_emissions` | `production × carbon_emission_per_unit` | 總碳排放量 |
| `group_emissions` | `Σ(total_emissions)` | 群組總排放 |
| `avg_cost_per_unit` | `total_cost ÷ production` | 平均單位成本 |
| `profit_margin` | `net_profit ÷ revenue` | 利潤率 |

#### 交易效率（僅交易組）
| 變數名 | 計算公式 | 說明 |
|--------|----------|------|
| `avg_buy_price` | `total_spent ÷ total_bought` | 平均購買價格 |
| `avg_sell_price` | `total_earned ÷ total_sold` | 平均賣出價格 |
| `trading_profit` | `total_earned - total_spent` | 交易利潤 |
| `permits_utilization` | `total_emissions ÷ current_permits` | 碳權使用率 |

#### 時間變數
| 變數名 | 說明 | 格式 |
|--------|------|------|
| `trade_timestamp` | 交易時間戳 | "MM:SS" |
| `decision_time` | 決策用時 | 秒數 |
| `trading_duration` | 交易持續時間 | MUDA：180秒（測試：60秒）；碳交易：120秒（測試：60秒） |

---

## 數據匯出格式

### CSV 匯出結構

#### 主要數據文件
1. **All apps - wide.csv**：所有應用程式的寬格式數據
2. **All apps - long.csv**：所有應用程式的長格式數據  
3. **[AppName] - all data.csv**：各別應用程式的完整數據
4. **Time stamps.csv**：頁面造訪時間戳

#### 寬格式 vs 長格式
- **寬格式**：每行一個參與者，所有回合數據在同一行
- **長格式**：每行一個觀察值（參與者 × 回合）

### 數據清理建議

#### 缺失值處理
- `None` 值：表示該變數不適用於當前處理組
- `0` 值：表示實際的零值（如未生產）

#### 異常值檢查
- 負現金值：在碳交易組中為正常現象
- 極高生產量：檢查是否超過最大生產能力
- 交易價格：檢查是否在合理範圍內

#### 數據驗證
```python
# 檢查生產約束
assert production <= max_production

# 檢查碳權約束（僅碳交易組）
if stage == 'carbon_trading':
    assert production * carbon_emission_per_unit <= current_permits

# 檢查收益計算
assert abs(revenue - production * market_price) < 0.01
```

---

## 統計分析建議

### 描述性統計
- 各組別的生產量、利潤分佈
- 碳排放量的組間比較
- 交易活躍度分析（交易組）

### 推論統計
- 處理組效果檢驗（ANOVA/t-test）
- 回合間學習效應
- 廠商類型對決策的影響

### 高級分析
- 交易策略分類（交易組）
- 市場效率分析
- 政策工具比較效果

---

## 附錄

### 變數命名規則
- 小寫字母 + 底線：`variable_name`
- 布林變數以 `is_` 開頭：`is_dominant`
- 累計變數以 `total_` 開頭：`total_cost`
- 當前狀態變數以 `current_` 開頭：`current_cash`

### 單位說明
- **Currency**：oTree 內建貨幣類型，精確到小數點後 2 位
- **Float**：浮點數，用於精確計算
- **Integer**：整數，用於計數變數
- **LongString**：長字串，用於 JSON 數據

### 數據完整性
- 所有金額變數使用一致的精度
- 時間戳使用統一格式
- JSON 數據結構標準化
- 缺失值編碼統一

---

**編制者**：Levi  
**聯絡方式**：請參考專案 README  
**版權**：MIT License  
**最後更新**：2025 年 6 月 30 日
