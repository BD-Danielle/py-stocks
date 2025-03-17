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
    """格式化股票代號為 Yahoo Finance 格式"""
    # 移除任何非数字字符
    code = ''.join(filter(str.isdigit, str(code)))
    
    # 确保代码至少为4位数
    code = code.zfill(4)
    
    # DR股票（如9103美德医疗-DR）使用.TW
    if code.startswith('91'):
        return f"{code}.TW"
    # ETF通常以00開頭
    elif code.startswith('00'):
        return f"{code}.TW"
    # 上櫃股票通常以6開頭
    elif code.startswith('6'):
        return f"{code}.TWO"
    # 其他情况（主要是上市股票）
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
    try:
        if os.path.exists("stock_trades-original.csv"):
            df = pd.read_csv("stock_trades-original.csv")
            # 確保日期格式正確
            df['交易日期'] = pd.to_datetime(df['交易日期']).dt.strftime('%Y/%m/%d')
            return df
    except Exception as e:
        print(f"讀取交易記錄時出錯：{e}")
    return pd.DataFrame()

def show_stock_history(stock_code):
    """顯示特定股票的歷史交易記錄"""
    df = load_original_trades()
    if df.empty:
        return "無歷史交易記錄"
    
    # 過濾指定股票的記錄並按日期排序（確保買賣順序正確）
    stock_records = df[df['代號'] == int(stock_code)].sort_values('交易日期')
    if stock_records.empty:
        return "該股票無歷史交易記錄"
    
    # 初始化變數
    total_investment = 0  # 總投資（含手續費）
    current_shares = 0   # 目前持股數
    total_cost = 0      # 當前持股成本（不含手續費和交易稅）
    total_profit = 0    # 總獲利
    
    # 添加表頭
    history_text = "═" * 120 + "\n"
    history_text += "📊 歷史交易記錄\n"
    history_text += "═" * 120 + "\n"
    
    # 新增列標題
    history_text += (
        f"{'交易日期':^9.99} | "
        f"{'交易':^5.5} | "
        f"{'價格':>6} | "
        f"{'股數':>9} | "
        f"{'金額':>11} | "
        f"{'手續費':>6.5} | "
        f"{'交易稅':>6.5} | "
        f"{'損益':>11}\n"
    )
    history_text += "─" * 120 + "\n"
    
    # 處理每筆交易
    for _, row in stock_records.iterrows():
        trade_type = row['買/賣/股利']
        profit = 0
        
        try:
            if trade_type == '買':
                # 處理買入交易
                price = float(row['買入價格'])
                shares = int(row['買入股數'])
                amount = price * shares
                fee = float(row['手續費']) if pd.notna(row.get('手續費')) else 20
                tax = 0
                
                # 更新持倉資訊
                current_shares += shares
                total_cost += amount
                total_investment += (amount + fee)
                
            elif trade_type == '賣':
                # 處理賣出交易
                price = float(row['賣出價格'])
                shares = int(row['賣出股數'])
                amount = price * shares
                fee = float(row['手續費']) if pd.notna(row.get('手續費')) else 20
                tax = float(row['交易稅']) if pd.notna(row.get('交易稅')) else round(amount * 0.003)
                
                if current_shares >= shares:
                    # 計算賣出部分的成本（使用平均成本）
                    avg_cost_per_share = total_cost / current_shares
                    sold_cost = avg_cost_per_share * shares
                    
                    # 計算本次交易獲利
                    # 卖賣出收入 = 賣出金額 - 手續費 - 交易稅
                    net_income = amount - fee - tax
                    # 賣出成本 = 買進成本 + 買進手續費
                    buy_fee = 20  # 買進手續費最低20元
                    buy_cost = sold_cost + buy_fee
                    # 實際獲利 = 賣出淨收入 - 買入成本
                    profit = net_income - buy_cost
                    total_profit += profit
                    
                    # 更新持倉資訊
                    current_shares -= shares
                    # 更新剩餘股票的成本
                    if current_shares > 0:
                        total_cost = avg_cost_per_share * current_shares
                    else:
                        total_cost = 0
            
            # 格式化每筆交易記錄
            history_text += (
                f"{str(row['交易日期']):^12} | "
                f"{trade_type:^6} | "
                f"{price:>7.2f} | "
                f"{shares:>10,d} | "
                f"{amount:>12,.0f} | "
                f"{fee:>8,.0f} | "
                f"{tax:>8,.0f} | "
                f"{profit:>12,.0f}\n"
            )
            
        except Exception as e:
            print(f"處理交易記錄時出錯：{e}")
            continue
    
    # 新增匯總資訊
    history_text += "═" * 120 + "\n"
    
    # 計算報酬率（保留兩位小數）
    if total_investment > 0:
        roi = (total_profit / total_investment) * 100
        history_text += (
            f"總投資金額：{total_investment:>7,.0f} 元   |   "
            f"總損益：{total_profit:>8,.0f} 元   |   "
            f"報酬率：{roi:>8.2f}%\n"
        )
    
    # 新增目前持股資訊
    history_text += f"目前持有：{current_shares:,d} 股"
    if current_shares > 0 and total_cost > 0:
        avg_cost = total_cost / current_shares
        history_text += f"   |   平均成本：{avg_cost:,.2f} 元"
    history_text += "\n"
    
    history_text += "═" * 120 + "\n"
    return history_text

def auto_update_price():
    """每分鐘自動更新股價"""
    if entry_code.get():  # 如果有輸入股票代碼
        get_stock_price()
    # 每60000毫秒（1分鐘）執行一次
    root.after(60000, auto_update_price)

def get_stock_price():
    stock_code = entry_code.get()
    if not stock_code:
        messagebox.showerror("错误", "請輸入股票代码")
        return
    
    try:
        # 首先尝试 .TWO 格式（上柜股票）
        formatted_code = format_stock_code(stock_code)
        stock = yf.Ticker(formatted_code)
        
        # 尝试获取数据
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
            raise Exception("无法获取股价数据")
        
        # 獲取最新的收盤價和日期
        price = data.iloc[-1]["Close"]
        trading_date = data.index[-1].strftime("%Y-%m-%d")
        
        # 取得股票名稱
        stock_name = get_stock_name(stock)
        if not stock_name:
            stock_name = f"股票 {stock_code}"
        
        # 显示当前价格和更新时间
        current_time = datetime.now().strftime("%H:%M:%S")
        current_price_text = f"{stock_name} 收盤價：{price:.2f} 元 ({trading_date}) - 更新時間：{current_time}"
        label_price.config(text=current_price_text)
        
        # 顯示歷史交易記錄
        history_text = show_stock_history(stock_code)
        text_history.delete("1.0", tk.END)
        text_history.insert(tk.END, history_text)
            
    except Exception as e:
        error_msg = str(e)
        print(f"取得股價時出錯：{error_msg}")  # 添加調試資訊
        if "HTTP 404 Not Found" in error_msg:
            messagebox.showerror("错误", f"找不到股票代碼 {stock_code}，請確認是否為有效的台股代碼")
        else:
            messagebox.showerror("错误", f"無法取得股價，請檢查網路連線或稍後再試\n錯誤訊息：{error_msg}")
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
        # 開始自動更新
        auto_update_price()

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
btn_price = tk.Button(stock_select_frame, text="獲取即時股價", command=lambda: [get_stock_price(), auto_update_price()])
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
