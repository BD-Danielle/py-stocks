import tkinter as tk
from tkinter import messagebox, ttk
import yfinance as yf
import pandas as pd
import os
from datetime import datetime

# 設定交易紀錄檔案
FILE_NAME = "stock_trades.csv"

# 若檔案不存在，建立檔案
if not os.path.exists(FILE_NAME):
    df = pd.DataFrame(columns=["交易日期", "買/賣/股利", "代號", "股票", "交易類別", 
                             "買入股數", "買入價格", "賣出股數", "賣出價格", "現價",
                             "手續費", "交易稅", "交易成本", "支出", "收入", 
                             "價差", "ROR", "持有時間"])
    df.to_csv(FILE_NAME, index=False)

# 讀取歷史交易紀錄
def load_trades():
    if os.path.exists(FILE_NAME):
        return pd.read_csv(FILE_NAME)
    return pd.DataFrame(columns=["交易日期", "買/賣/股利", "代號", "股票", "交易類別", 
                               "買入股數", "買入價格", "賣出股數", "賣出價格", "現價",
                               "手續費", "交易稅", "交易成本", "支出", "收入", 
                               "價差", "ROR", "持有時間"])

def format_stock_code(code):
    """格式化股票代碼為 Yahoo Finance 格式"""
    # 移除任何非數字字符
    code = ''.join(filter(str.isdigit, str(code)))
    
    # 確保代碼至少為4位數
    code = code.zfill(4)
    
    # ETF通常以00開頭
    if code.startswith('00'):
        return f"{code}.TW"
    # 上櫃股票通常以6開頭
    elif code.startswith('6'):
        return f"{code}.TWO"
    # 其他情況（主要是上市股票）
    else:
        return f"{code}.TW"

def calculate_fees(price, shares, is_buy=True):
    """計算手續費和交易稅"""
    fee = round(max(20, price * shares * 0.001425))  # 手續費 0.1425%，最低20元
    tax = 0 if is_buy else round(price * shares * 0.003)  # 賣出時收取 0.3% 證交稅
    return fee, tax

def get_stock_name(stock):
    """獲取股票名稱"""
    try:
        info = stock.info
        return info.get('longName', '') or info.get('shortName', '')
    except:
        return ''

def load_original_trades():
    """讀取原始交易記錄檔案"""
    if os.path.exists("stock_trades-original.csv"):
        return pd.read_csv("stock_trades-original.csv")
    return pd.DataFrame()

def show_stock_history(stock_code):
    """顯示特定股票的歷史交易記錄"""
    df = load_original_trades()
    if df.empty:
        return "無歷史交易記錄"
    
    # 過濾指定股票的記錄
    stock_records = df[df['代號'] == int(stock_code)]
    if stock_records.empty:
        return "該股票無歷史交易記錄"
    
    # 計算總投資金額和總收益
    total_investment = 0
    total_profit = 0
    
    # 添加表頭
    history_text = "═" * 120 + "\n"
    history_text += "📊 歷史交易記錄\n"
    history_text += "═" * 120 + "\n"
    
    # 添加欄位標題，增加欄位寬度
    history_text += (
        f"{'交易日期':^12} | {'交易':^6} | {'價格':>10} | {'股數':>8} | "
        f"{'金額':>12} | {'手續費':>10} | {'交易稅':>10} | {'損益':>12}\n"
    )
    history_text += "─" * 120 + "\n"
    
    # 依照日期排序
    stock_records = stock_records.sort_values('交易日期', ascending=True)
    
    # 計算累計持有股數和成本
    current_shares = 0
    total_cost = 0
    
    for _, row in stock_records.iterrows():
        trade_type = row['買/賣/股利']
        
        try:
            if trade_type == '買':
                price = float(row['買入價格'])
                shares = int(row['買入股數'])
                amount = -1 * price * shares
                total_investment += abs(amount)
                current_shares += shares
                total_cost += abs(amount)
            else:
                price = float(row['賣出價格'])
                shares = int(row['賣出股數'])
                amount = price * shares
                current_shares -= shares
                # 計算賣出部分的成本比例
                if current_shares + shares > 0:  # 防止除以零
                    cost_per_share = total_cost / (current_shares + shares)
                    sold_cost = cost_per_share * shares
                    total_cost -= sold_cost
                else:
                    sold_cost = total_cost
                    total_cost = 0
            
            fee = float(row['手續費']) if '手續費' in row and pd.notna(row['手續費']) else 0
            tax = float(row['交易稅']) if '交易稅' in row and pd.notna(row['交易稅']) else 0
            
            # 計算損益
            if trade_type == '買':
                profit = 0  # 買入時不計算損益
            else:
                profit = amount - sold_cost - fee - tax  # 賣出時計算實際損益
                total_profit += profit
            
            # 格式化每一行交易記錄，增加間距和對齊
            history_text += (
                f"{str(row['交易日期']):^12} | "
                f"{trade_type:^6} | "
                f"{price:>10,.2f} | "
                f"{shares:>8,d} | "
                f"{amount:>12,.0f} | "
                f"{fee:>10,.0f} | "
                f"{tax:>10,.0f} | "
                f"{profit:>12,.0f}\n"
            )
        except (ValueError, TypeError) as e:
            continue
    
    # 添加匯總資訊
    history_text += "═" * 120 + "\n"
    
    # 計算報酬率
    if total_investment > 0:
        roi = (total_profit / total_investment) * 100
        roi_text = f"盈利" if roi > 0 else "虧損"
        history_text += (
            f"總投資金額：{total_investment:>15,.0f} 元   |   "
            f"總損益：{total_profit:>15,.0f} 元   |   "
            f"{roi_text}：{abs(roi):>8,.2f}%\n"
        )
    else:
        history_text += "尚無投資損益資訊\n"
    
    # 添加目前持股資訊
    if current_shares > 0 and total_cost > 0:  # 確保不會除以零
        avg_cost = total_cost / current_shares
        history_text += f"目前持有：{current_shares:,d} 股   |   平均成本：{avg_cost:,.2f} 元\n"
    elif current_shares > 0:
        history_text += f"目前持有：{current_shares:,d} 股   |   平均成本：無法計算\n"
    
    history_text += "═" * 120 + "\n"
    
    return history_text

def get_stock_price():
    stock_code = entry_code.get()
    if not stock_code:
        messagebox.showerror("錯誤", "請輸入股票代碼")
        return
    
    try:
        # 首先嘗試 .TWO 格式（上櫃股票）
        formatted_code = format_stock_code(stock_code)
        stock = yf.Ticker(formatted_code)
        
        # 嘗試獲取數據
        data = stock.history(period="5d")
        if len(data) == 0:
            # 如果獲取失敗，嘗試切換交易所後綴
            if formatted_code.endswith('.TWO'):
                formatted_code = f"{stock_code}.TW"
            else:
                formatted_code = f"{stock_code}.TWO"
            stock = yf.Ticker(formatted_code)
            data = stock.history(period="5d")
            
        if len(data) == 0:
            raise Exception("無法獲取股價數據")
        
        # 獲取最新的收盤價和日期
        price = data.iloc[-1]["Close"]
        trading_date = data.index[-1].strftime("%Y-%m-%d")
        
        # 獲取股票名稱
        stock_name = get_stock_name(stock)
        if not stock_name:
            stock_name = f"股票 {stock_code}"
        
        # 顯示當前價格
        current_price_text = f"{stock_name} 收盤價：{price:.2f} 元 ({trading_date})"
        label_price.config(text=current_price_text)
        
        # 顯示歷史交易記錄
        history_text = show_stock_history(stock_code)
        text_history.delete("1.0", tk.END)
        text_history.insert(tk.END, history_text)
            
    except Exception as e:
        error_msg = str(e)
        if "HTTP 404 Not Found" in error_msg:
            messagebox.showerror("錯誤", f"找不到股票代碼 {stock_code}，請確認是否為有效的台股代碼")
        else:
            messagebox.showerror("錯誤", f"無法獲取股價，請檢查網路連接或稍後再試\n錯誤信息：{error_msg}")
        return

# 記錄交易紀錄
def record_trade():
    stock_code = entry_code.get()
    buy_price = entry_buy_price.get()
    shares = entry_shares.get()
    
    if not stock_code or not buy_price or not shares:
        messagebox.showerror("錯誤", "請填寫所有欄位")
        return

    try:
        buy_price = float(buy_price)
        shares = int(shares)
    except ValueError:
        messagebox.showerror("錯誤", "請輸入有效數值")
        return

    # 獲取股價和股票資訊
    try:
        formatted_code = format_stock_code(stock_code)
        stock = yf.Ticker(formatted_code)
        
        data = stock.history(period="1mo")
        if len(data) == 0:
            raise Exception("無法獲取股價數據")
            
        current_price = data.iloc[-1]["Close"]
        stock_name = get_stock_name(stock)
            
    except Exception as e:
        messagebox.showerror("錯誤", f"無法獲取當前股價\n錯誤信息：{str(e)}")
        return

    # 計算相關費用和金額
    fee, tax = calculate_fees(buy_price, shares, True)
    total_cost = fee + tax
    total_expense = buy_price * shares + total_cost
    
    # 準備新的交易記錄
    today = datetime.now().strftime("%Y/%m/%d")
    new_trade = pd.DataFrame([{
        "交易日期": today,
        "買/賣/股利": "買",
        "代號": stock_code,
        "股票": stock_name,
        "交易類別": "一般",
        "買入股數": shares,
        "買入價格": buy_price,
        "賣出股數": "",
        "賣出價格": "",
        "現價": current_price,
        "手續費": fee,
        "交易稅": tax,
        "交易成本": total_cost,
        "支出": f"-{total_expense:,.0f}",
        "收入": "",
        "價差": current_price - buy_price,
        "ROR": "",
        "持有時間": 0
    }])

    # 存入 CSV
    df = load_trades()
    df = pd.concat([df, new_trade], ignore_index=True)
    df.to_csv(FILE_NAME, index=False)

    messagebox.showinfo("成功", "交易已記錄！")
    update_trades_list()

# 更新交易紀錄視窗
def update_trades_list():
    df = load_trades()
    text_trades.delete("1.0", tk.END)
    
    if df.empty:
        text_trades.insert(tk.END, "無交易紀錄")
        return
    
    for _, row in df.iterrows():
        # 格式化顯示內容
        trade_type = row['買/賣/股利']
        if trade_type == '買':
            price = row['買入價格']
            shares = row['買入股數']
        else:
            price = row['賣出價格']
            shares = row['賣出股數']
            
        text_trades.insert(tk.END, (
            f"日期: {row['交易日期']} | "
            f"交易: {trade_type} | "
            f"代號: {row['代號']} | "
            f"名稱: {row['股票']} | "
            f"價格: {price} | "
            f"股數: {shares} | "
            f"現價: {row['現價']} | "
            f"成本: {row['交易成本']} | "
            f"價差: {row['價差']}\n"
        ))
        text_trades.insert(tk.END, "-"*100 + "\n")

def update_stock_list(*args):
    """更新股票清單下拉選單"""
    df = load_original_trades()
    if not df.empty:
        # 獲取唯一的股票代碼和名稱
        stocks = df[['代號', '股票']].drop_duplicates()
        # 清空當前選項
        stock_combo['values'] = []
        # 添加新選項
        stock_options = [f"{row['代號']} - {row['股票']}" for _, row in stocks.iterrows()]
        stock_combo['values'] = stock_options

def on_stock_selected(event):
    """當選擇股票時觸發"""
    if stock_combo.get():
        # 從選擇的項目中提取股票代碼
        stock_code = stock_combo.get().split(' - ')[0]
        # 設置輸入框的值
        entry_code.delete(0, tk.END)
        entry_code.insert(0, stock_code)
        # 觸發獲取股價
        get_stock_price()

# 介面設計
root = tk.Tk()
root.title("📈 股票交易記錄工具")
root.geometry("1200x900")  # 加寬視窗寬度

# 股票選擇區域
stock_select_frame = tk.Frame(root)
stock_select_frame.pack(pady=10)

# 股票代碼輸入框和下拉選單並排
tk.Label(stock_select_frame, text="輸入股票代碼:").pack(side=tk.LEFT, padx=5)
entry_code = tk.Entry(stock_select_frame)
entry_code.pack(side=tk.LEFT, padx=5)

# 下拉式選單
stock_combo = ttk.Combobox(stock_select_frame, width=30)
stock_combo.pack(side=tk.LEFT, padx=5)
stock_combo.bind('<<ComboboxSelected>>', on_stock_selected)

# 取得股價按鈕
btn_price = tk.Button(stock_select_frame, text="獲取即時股價", command=get_stock_price)
btn_price.pack(side=tk.LEFT, padx=5)

# 當前價格標籤
label_price = tk.Label(root, text="當前價格：N/A")
label_price.pack(pady=5)

# 交易紀錄輸入區域
input_frame = tk.Frame(root)
input_frame.pack(pady=10)

tk.Label(input_frame, text="輸入買入價格:").pack(side=tk.LEFT, padx=5)
entry_buy_price = tk.Entry(input_frame)
entry_buy_price.pack(side=tk.LEFT, padx=5)

tk.Label(input_frame, text="輸入買入股數:").pack(side=tk.LEFT, padx=5)
entry_shares = tk.Entry(input_frame)
entry_shares.pack(side=tk.LEFT, padx=5)

# 紀錄交易按鈕
btn_record = tk.Button(input_frame, text="記錄交易", command=record_trade)
btn_record.pack(side=tk.LEFT, padx=5)

# 歷史交易記錄顯示區域
tk.Label(root, text="📊 原始交易歷史:").pack()
text_history = tk.Text(root, height=12, width=120)
text_history.pack(padx=20, pady=5)

# 交易紀錄
tk.Label(root, text="📜 當前交易紀錄:").pack()
text_trades = tk.Text(root, height=25, width=120)
text_trades.pack(padx=20, pady=5)

# 初始化下拉選單
update_stock_list()

# 更新交易紀錄
update_trades_list()

# 介面啟動
root.mainloop()
