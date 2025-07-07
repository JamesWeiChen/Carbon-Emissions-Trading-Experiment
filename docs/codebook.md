# 碳排放交易實驗平台 - 編碼簿 (Codebook)

## 基本資訊
- **版本**: 4.0
- **更新日期**: 2025/7/7
- **平台**: oTree Framework
- **實驗類型**: 碳排放交易實驗

## 資料結構層級說明

本實驗平台使用三個主要的資料層級來記錄實驗資料：

### 1. Subsession 層級 (會話/回合層級)
記錄每回合的整體實驗參數和市場環境

### 2. Group 層級 (群組層級)
記錄群組內的互動資料，特別是交易相關資訊

### 3. Player 層級 (個人玩家層級)
記錄每位參與者的決策、行為和結果

---

## Stage_Control (控制組) 資料變數

### Subsession 層級變數
| 變數名稱 | 資料類型 | 說明 |
|---------|----------|------|
| `market_price` | CurrencyField | 市場商品價格 |

### Player 層級變數
| 變數名稱 | 資料類型 | 說明 |
|---------|----------|------|
| `marginal_cost_coefficient` | IntegerField | 邊際成本係數 |
| `carbon_emission_per_unit` | FloatField | 每單位產品碳排放量 |
| `is_dominant` | BooleanField | 是否為主導企業 |
| `max_production` | IntegerField | 最大生產能力 |
| `market_price` | CurrencyField | 市場價格 |
| `production` | IntegerField | 實際生產數量 (0-MAX_PRODUCTION) |
| `revenue` | CurrencyField | 營收 |
| `total_cost` | FloatField | 總成本 |
| `net_profit` | FloatField | 淨利潤 |
| `initial_capital` | CurrencyField | 初始資本 |
| `current_cash` | CurrencyField | 當前現金 |
| `final_cash` | CurrencyField | 最終現金 |
| `selected_round` | IntegerField | 隨機選中用於最終報酬的回合 |

---

## Stage_CarbonTax (碳稅組) 資料變數

### Subsession 層級變數
| 變數名稱 | 資料類型 | 說明 |
|---------|----------|------|
| `market_price` | CurrencyField | 市場商品價格 |
| `tax_rate` | FloatField | 碳稅稅率 |

### Player 層級變數
| 變數名稱 | 資料類型 | 說明 |
|---------|----------|------|
| `marginal_cost_coefficient` | IntegerField | 邊際成本係數 |
| `carbon_emission_per_unit` | FloatField | 每單位產品碳排放量 |
| `is_dominant` | BooleanField | 是否為主導企業 |
| `max_production` | IntegerField | 最大生產能力 |
| `market_price` | CurrencyField | 市場價格 |
| `production` | IntegerField | 實際生產數量 (0-MAX_PRODUCTION) |
| `revenue` | CurrencyField | 營收 |
| `total_cost` | FloatField | 總成本 |
| `carbon_tax_paid` | FloatField | 碳稅支付金額 |
| `net_profit` | FloatField | 淨利潤 |
| `initial_capital` | CurrencyField | 初始資本 |
| `current_cash` | CurrencyField | 當前現金 |
| `final_cash` | CurrencyField | 最終現金 |
| `selected_round` | IntegerField | 隨機選中用於最終報酬的回合 |

---

## Stage_CarbonTrading (碳交易組) 資料變數

### Subsession 層級變數
| 變數名稱 | 資料類型 | 說明 |
|---------|----------|------|
| `market_price` | CurrencyField | 市場商品價格 |
| `price_history` | LongStringField | 碳權價格歷史記錄 (JSON格式) |
| `start_time` | IntegerField | 回合開始時間 (Unix時間戳) |
| `total_optimal_emissions` | FloatField | 社會最適總排放量 |
| `cap_multiplier` | FloatField | 排放上限倍數 |
| `cap_total` | IntegerField | 總排放上限 |
| `allocation_details` | LongStringField | 配額分配詳細資訊 (JSON格式) |

### Group 層級變數
| 變數名稱 | 資料類型 | 說明 |
|---------|----------|------|
| `buy_orders` | LongStringField | 買單掛單記錄 (JSON格式) |
| `sell_orders` | LongStringField | 賣單掛單記錄 (JSON格式) |
| `trade_history` | LongStringField | 完整交易歷史記錄 (JSON格式) |

### Player 層級變數
| 變數名稱 | 資料類型 | 說明 |
|---------|----------|------|
| `is_dominant` | BooleanField | 是否為主導企業 |
| `marginal_cost_coefficient` | IntegerField | 邊際成本係數 |
| `carbon_emission_per_unit` | IntegerField | 每單位產品碳排放量 |
| `market_price` | CurrencyField | 市場價格 |
| `production` | IntegerField | 實際生產數量 (0-MAX_PRODUCTION) |
| `revenue` | CurrencyField | 營收 |
| `total_cost` | FloatField | 總成本 |
| `net_profit` | FloatField | 淨利潤 |
| `initial_capital` | CurrencyField | 初始資本 |
| `final_cash` | CurrencyField | 最終現金 |
| `max_production` | IntegerField | 最大生產能力 |
| `current_cash` | CurrencyField | 當前現金 |
| `permits` | IntegerField | 初始分配的碳權數量 |
| `current_permits` | IntegerField | 當前碳權餘額 |
| `submitted_offers` | LongStringField | 個人提交的交易訂單記錄 (JSON格式) |
| `total_bought` | IntegerField | 累計購買碳權數量 |
| `total_sold` | IntegerField | 累計出售碳權數量 |
| `total_spent` | CurrencyField | 累計購買花費 |
| `total_earned` | CurrencyField | 累計出售收入 |
| `selected_round` | IntegerField | 隨機選中用於最終報酬的回合 |
| `optimal_production` | FloatField | 個人最適產量 |
| `optimal_emissions` | FloatField | 個人最適排放量 |

---

## Stage_MUDA (修改版雙邊競價拍賣) 資料變數

### Subsession 層級變數
| 變數名稱 | 資料類型 | 說明 |
|---------|----------|------|
| `item_market_price` | CurrencyField | 物品市場參考價格 |
| `price_history` | LongStringField | 價格歷史記錄 (JSON格式) |
| `start_time` | IntegerField | 回合開始時間 (Unix時間戳) |

### Group 層級變數
| 變數名稱 | 資料類型 | 說明 |
|---------|----------|------|
| `buy_orders` | LongStringField | 買單掛單記錄 (JSON格式) |
| `sell_orders` | LongStringField | 賣單掛單記錄 (JSON格式) |
| `trade_history` | LongStringField | 完整交易歷史記錄 (JSON格式) |

### Player 層級變數
| 變數名稱 | 資料類型 | 說明 |
|---------|----------|------|
| `buy_quantity` | IntegerField | 提交的買單數量 |
| `buy_price` | FloatField | 提交的買單價格 |
| `sell_quantity` | IntegerField | 提交的賣單數量 |
| `sell_price` | FloatField | 提交的賣單價格 |
| `cash` | CurrencyField | 現金 |
| `items` | IntegerField | 物品數量 |
| `initial_capital` | CurrencyField | 初始資本 |
| `final_cash` | CurrencyField | 最終現金 |
| `current_cash` | CurrencyField | 當前現金 |
| `current_items` | IntegerField | 當前物品數量 |
| `personal_item_value` | CurrencyField | 個人物品價值 |
| `total_bought` | IntegerField | 累計購買數量 |
| `total_sold` | IntegerField | 累計出售數量 |
| `total_spent` | CurrencyField | 累計購買花費 |
| `total_earned` | CurrencyField | 累計出售收入 |
| `item_value` | CurrencyField | 物品總價值 |
| `total_value` | CurrencyField | 總資產價值 |
| `submitted_offers` | LongStringField | 個人提交的訂單記錄 (JSON格式) |
| `selected_round` | IntegerField | 隨機選中用於最終報酬的回合 |

---

## Stage_Survey (問卷調查) 資料變數

### Player 層級變數

#### 基本資料
| 變數名稱 | 資料類型 | 說明 |
|---------|----------|------|
| `name` | StringField | 姓名 |
| `student_id` | StringField | 學號 |
| `id_number` | StringField | 身份證字號 |
| `address` | StringField | 戶籍地址 |
| `address_code` | StringField | 戶籍地址郵遞區號 |

#### 背景資訊
| 變數名稱 | 資料類型 | 說明 |
|---------|----------|------|
| `gender` | StringField | 性別 ('M'/'F'/'N') |
| `grade` | StringField | 年級 |
| `major` | StringField | 主修學門 |
| `has_intro_econ` | BooleanField | 是否修過初級經濟學 |
| `has_env_econ` | BooleanField | 是否修過環境經濟學 |
| `has_pub_econ` | BooleanField | 是否修過公共經濟學 |
| `has_game_theory` | BooleanField | 是否修過博弈論 |

#### 制度理解與偏好
| 變數名稱 | 資料類型 | 說明 |
|---------|----------|------|
| `understand` | IntegerField | 制度理解程度 (1-5) |
| `prefer_mechanism` | StringField | 偏好的制度類型 |
| `real_world_choice` | StringField | 現實世界制度偏好 |

#### 決策行為
| 變數名稱 | 資料類型 | 說明 |
|---------|----------|------|
| `consider_market_power` | IntegerField | 是否考慮市場影響力 (1-5) |
| `adapt_to_others` | IntegerField | 是否根據他人行為調整策略 (1-4) |
| `attempt_manipulate` | StringField | 是否嘗試操控市場 |

#### 價值觀與偏好
| 變數名稱 | 資料類型 | 說明 |
|---------|----------|------|
| `main_goal` | StringField | 主要決策目標 |
| `free_rider_behavior` | StringField | 搭便車行為頻率 |
| `altruism` | StringField | 利他主義傾向 |

#### 制度公平與信任
| 變數名稱 | 資料類型 | 說明 |
|---------|----------|------|
| `fairness` | StringField | 制度公平性評價 |
| `institutional_effect` | IntegerField | 制度對行為的影響程度 (1-4) |

---

## JSON 格式資料結構說明

### 1. 交易歷史記錄 (trade_history)
```json
{
  "timestamp": "MM:SS",
  "buyer_id": 1,
  "seller_id": 2,
  "price": 25.0,
  "quantity": 3,
  "total_value": 75.0,
  "market_price": 30.0
}
```

### 2. 買賣掛單記錄 (buy_orders/sell_orders)
```json
[
  [player_id, price, quantity],
  [1, 25.0, 3],
  [2, 30.0, 2]
]
```

### 3. 個人訂單記錄 (submitted_offers)
```json
{
  "timestamp": 1705123456,
  "order_type": "buy",
  "price": 25.0,
  "quantity": 3,
  "status": "completed"
}
```

### 4. 價格歷史記錄 (price_history)
```json
{
  "timestamp": "01:23",
  "price": 25.0,
  "volume": 3
}
```

### 5. 配額分配詳細資訊 (allocation_details)
```json
{
  "player_id": 1,
  "allocated_permits": 50,
  "optimal_production": 45.2,
  "optimal_emissions": 67.8,
  "allocation_method": "proportional"
}
```

## 時間戳記格式說明

### 1. 相對時間戳記 (MM:SS)
- 格式：分鐘:秒鐘 (例如: "01:23")
- 用途：交易記錄、價格歷史
- 計算方式：當前時間 - 回合開始時間
- 範圍：00:00 - 03:00 (3分鐘交易時間)

### 2. 絕對時間戳記 (Unix timestamp)
- 格式：Unix時間戳 (例如: 1705123456)
- 用途：個人訂單記錄、系統記錄
- 計算方式：自1970年1月1日的秒數

## 重要計算公式

### 1. 生產成本計算
```
total_cost = marginal_cost_coefficient × production² / 2
```

### 2. 碳稅計算
```
carbon_tax_paid = tax_rate × production × carbon_emission_per_unit
```

### 3. 淨利潤計算
```
net_profit = revenue - total_cost - carbon_tax_paid
```

### 4. 交易利潤計算
```
trading_profit = total_earned - total_spent
```

### 5. 排放量計算
```
total_emissions = production × carbon_emission_per_unit
```

## 資料驗證規則

### 1. 數值範圍驗證
- `production`: 0 ≤ production ≤ MAX_PRODUCTION
- `price`: price > 0
- `quantity`: quantity > 0

### 2. 邏輯一致性驗證
- 現金餘額 = 初始資本 + 交易收入 - 交易支出 - 生產成本
- 碳權餘額 = 初始配額 + 購買數量 - 出售數量
- 總購買金額 = Σ(交易價格 × 交易數量)

### 3. 時間戳記驗證
- 相對時間戳記格式：`^[0-9]{2}:[0-9]{2}$`
- 時間序列遞增性檢查
- 時間範圍：0 ≤ 時間 ≤ 交易時間上限

## 資料匯出格式

### CSV 匯出主要欄位
1. **會話資訊**: session_code, participant_code, round_number
2. **時間資訊**: timestamp, start_time, elapsed_time
3. **生產決策**: production, revenue, total_cost, net_profit
4. **交易資訊**: total_bought, total_sold, total_spent, total_earned
5. **排放資訊**: emissions, permits, carbon_tax_paid
6. **市場資訊**: market_price, trade_history, price_history
7. **調查資料**: 所有問卷回答欄位

### JSON 匯出結構
完整的JSON匯出包含所有資料層級的完整資訊，適合進行深度分析和資料重現。

---

**注意**: 此編碼簿專注於後端資料記錄變數的詳細說明。所有變數都會自動保存至oTree的資料庫中，可透過管理介面或匯出功能取得完整資料。 