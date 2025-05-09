# 📈 股票追蹤與投資管理工具

## 介紹
這是一個 **Python 股票追蹤工具**，使用 `Tkinter` 建立 GUI，並透過 `yfinance` 獲取即時股價，讓使用者能夠：
- **輸入股票代碼** 並獲取即時股價 📊
- **記錄買入價格與股數**，自動計算總成本 💰
- **自動計算停損（-20%）、停利（+20%）價格** 📉📈
- **提醒是否應該賣出或買進** ⚠️
- **記錄交易歷史，供未來檢視與分析** 🗂️

## 功能特點
- **即時股價查詢**：支援台股上市、上櫃股票及 ETF
- **交易記錄管理**：
  - 自動記錄買入/賣出交易
  - 計算手續費（0.1425%）和證交稅（0.3%）
  - 追蹤每筆交易的損益
- **歷史記錄分析**：
  - 顯示特定股票的完整交易歷史
  - 計算總投資金額和總損益
  - 顯示平均成本
  - 計算投資報酬率（ROR）
- **使用者友善介面**：
  - 下拉式選單快速選擇已交易過的股票
  - 清晰的交易記錄顯示
  - 即時價格更新

## 🛠️ 安裝與環境設定

### 1️⃣ 創建虛擬環境（推薦）
#### 📌 Mac
### 手動設定

1. 建立虛擬環境：
```bash
python3 -m venv venv
```

2. 啟動虛擬環境：
```bash
source venv/bin/activate
```

3. 安裝依賴：
```bash
pip install -r requirements.txt
```

## 📦 依賴套件
- `tkinter`：GUI 介面
- `yfinance`：獲取股票數據
- `pandas`：數據處理與 CSV 檔案管理

## 💻 使用說明

### 1. 查詢股票價格
1. 在輸入框中輸入股票代碼（例如：2330）
2. 點擊「獲取即時股價」按鈕
3. 系統會顯示當前股價和交易日期

### 2. 記錄交易
1. 輸入買入價格
2. 輸入買入股數
3. 點擊「記錄交易」按鈕
4. 系統會自動：
   - 計算手續費和證交稅
   - 記錄交易日期和時間
   - 更新交易歷史

### 3. 查看交易歷史
- 系統會自動顯示：
  - 原始交易歷史
  - 當前交易記錄
  - 每筆交易的詳細資訊
  - 總投資金額和損益統計

## 📝 注意事項
- 股票代碼格式：
  - 上市股票：直接輸入代碼（如：2330）
  - 上櫃股票：以 6 開頭（如：6488）
  - ETF：以 00 開頭（如：0050）
- 手續費計算：
  - 買賣手續費：0.1425%（最低 20 元）
  - 賣出證交稅：0.3%
- 所有交易記錄會自動保存在 `stock_trades.csv` 檔案中

## 🔄 更新日誌
- 2024-03-21：初始版本發布
  - 基本股價查詢功能
  - 交易記錄管理
  - 歷史記錄分析

## 📄 授權
MIT License