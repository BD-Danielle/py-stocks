import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import yfinance as yf
import pandas as pd
import os
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = ['WenQuanYi Micro Hei']
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import requests
from bs4 import BeautifulSoup
import time

# 設定 matplotlib 中文字型
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']  # Mac OS 的中文字型
plt.rcParams['axes.unicode_minus'] = False  # 讓負號正確顯示

# 全局變量
root = None
entry_code = None
stock_combo = None
label_price = None
text_history = None
text_trades = None
summary_frame = None
chart_frame = None
notebook = None  # 添加 notebook 作為全局變量

# 設定交易紀錄檔案
FILE_NAME = "stock_trades.csv"

# 若檔案不存在，建立檔案
if not os.path.exists(FILE_NAME):
    df = pd.DataFrame(columns=[
        "交易日期", "買/賣/股利", "代號", "股票", "交易類別",
                             "買入股數", "買入價格", "賣出股數", "賣出價格", "現價",
                             "手續費", "交易稅", "交易成本", "支出", "收入", 
        "價差", "ROR", "持有時間"
    ])
    df.to_csv(FILE_NAME, index=False)

# 讀取歷史交易紀錄


def load_trades():
    """讀取交易記錄"""
    if os.path.exists(FILE_NAME):
        return pd.read_csv(FILE_NAME)
    return pd.DataFrame(columns=[
        "交易日期", "買/賣/股利", "代號", "股票", "交易類別",
                              "買入股數", "買入價格", "賣出股數", "賣出價格", "現價",
                              "手續費", "交易稅", "交易成本", "支出", "收入", 
        "價差", "ROR", "持有時間"
    ])


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
            # 讀取 CSV 文件
            df = pd.read_csv("stock_trades-original.csv")

            # 確保必要的列存在
            required_columns = [
                "交易日期", "買/賣/股利", "代號", "股票", "交易類別",
                "買入股數", "買入價格", "賣出股數", "賣出價格", "現價",
                "手續費", "交易稅", "交易成本", "支出", "收入"
            ]

            for col in required_columns:
                if col not in df.columns:
                    print(f"警告：缺少必要欄位 {col}")
                    return pd.DataFrame()

            # 處理日期格式
            df['交易日期'] = pd.to_datetime(df['交易日期']).dt.strftime('%Y/%m/%d')

            # 處理數值欄位，將非數值填充為 0
            numeric_columns = ['買入股數', '買入價格', '賣出股數', '賣出價格',
                               '現價', '手續費', '交易稅', '交易成本']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            # 處理金額欄位中的逗號和引號
            for col in ['支出', '收入']:
                df[col] = pd.to_numeric(df[col].str.replace(',', '').str.replace('"', ''), errors='coerce').fillna(0)

            return df

    except Exception as e:
        print(f"讀取交易記錄時出錯：{str(e)}")
        return pd.DataFrame()

    return pd.DataFrame()


def get_stock_holdings():
    """獲取當前所有股票持股狀況"""
    df = load_original_trades()
    if df.empty:
        return {}

    holdings = {}

    # 按股票代號分組處理
    for code in df['代號'].unique():
        stock_df = df[df['代號'] == code]

        # 計算總買入和賣出股數
        total_bought = stock_df[stock_df['買/賣/股利'] == '買']['買入股數'].sum()
        total_sold = stock_df[stock_df['買/賣/股利'] == '賣']['賣出股數'].sum()

        # 計算當前持股
        current_shares = total_bought - total_sold

        if current_shares > 0:
            # 獲取最新的股票名稱
            stock_name = stock_df.iloc[-1]['股票']

            # 計算平均成本
            buy_records = stock_df[stock_df['買/賣/股利'] == '買']
            total_cost = (buy_records['買入價格'] * buy_records['買入股數']).sum()
            avg_cost = total_cost / total_bought if total_bought > 0 else 0

            holdings[code] = {
                'name': stock_name,
                'shares': current_shares,
                'avg_cost': avg_cost
            }

    return holdings


def update_stock_list(*args):
    """更新股票清單下拉選單"""
    holdings = get_stock_holdings()

    # 清空當前選項
    stock_combo['values'] = []

    # 添加持有的股票到下拉選單
    stock_options = []
    for code, info in holdings.items():
        stock_options.append(f"{code} - {info['name']} ({info['shares']}股)")

    if stock_options:
        stock_combo['values'] = stock_options
        stock_combo.set(stock_options[0])  # 設置預設選項
    else:
        stock_combo['values'] = ['無持股紀錄']
        stock_combo.set('無持股紀錄')


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
                tax = float(row['交易稅']) if pd.notna(
                    row.get('交易稅')) else round(amount * 0.003)

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
    """自動更新股價"""
    if hasattr(root, 'status_label'):
        root.status_label.config(text="更新中...")

    result = get_stock_price()

    if hasattr(root, 'status_label'):
        root.status_label.config(text="就緒")
        if hasattr(root, 'update_time_label'):
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            root.update_time_label.config(text=f"最後更新：{current_time}")

    # 每分鐘更新一次
    root.after(60000, auto_update_price)


def update_stock_chart(stock_code):
    """更新股票技術走勢圖"""
    global chart_frame

    if not chart_frame:
        print("圖表區域尚未初始化")
        return

    try:
        # 獲取股票數據
        formatted_code = format_stock_code(stock_code)
        stock = yf.Ticker(formatted_code)
        df = stock.history(period="6mo")  # 獲取6個月的數據

        if df.empty:
            return

        # 清除原有圖表
        for widget in chart_frame.winfo_children():
            widget.destroy()

        # 創建新圖表
        fig = Figure(figsize=(10, 6))

        # 設置全局字型大小
        plt.rcParams['font.size'] = 10  # 基本字型大小
        plt.rcParams['axes.titlesize'] = 10  # 標題字型大小
        plt.rcParams['axes.labelsize'] = 10  # 軸標籤字型大小
        plt.rcParams['xtick.labelsize'] = 10  # X軸刻度字型大小
        plt.rcParams['ytick.labelsize'] = 10  # Y軸刻度字型大小
        plt.rcParams['legend.fontsize'] = 10  # 圖例字型大小

        # 主圖：K線圖
        ax1 = fig.add_subplot(211)

        # 繪製K線圖
        candlestick_data = []
        for date, row in df.iterrows():
            candlestick_data.append((date, row['Open'],
                                     row['High'],
                                     row['Low'],
                                     row['Close']))

        # 設置x軸為日期
        dates = [x[0] for x in candlestick_data]
        ax1.set_xticks(range(0, len(dates), 20))
        # 修改日期格式和方向
        ax1.set_xticklabels([d.strftime('%m/%d') for d in dates[::20]],
                            rotation=0,  # 水平顯示
                            ha='center')  # 水平置中對齊

        # 繪製蠟燭圖
        for i, (date, open_price, high, low, close) in enumerate(candlestick_data):
            if close >= open_price:
                color = 'red'
                alpha = 1.0
            else:
                color = 'green'
                alpha = 1.0

            # 繪製實體
            ax1.add_patch(plt.Rectangle(
                (i-0.3, min(open_price, close)),
                0.6,
                abs(open_price-close),
                fill=True,
                color=color,
                alpha=alpha
            ))
            # 繪製上下影線
            ax1.plot([i, i], [low, high], color=color, alpha=alpha)

        # 計算並繪製均線
        ma5 = df['Close'].rolling(window=5).mean()
        ma20 = df['Close'].rolling(window=20).mean()
        ma60 = df['Close'].rolling(window=60).mean()

        ax1.plot(ma5.values, label='MA5', color='blue', linewidth=1)
        ax1.plot(ma20.values, label='MA20', color='orange', linewidth=1)
        ax1.plot(ma60.values, label='MA60', color='purple', linewidth=1)

        ax1.set_title(f'{stock_code} 技術分析圖', pad=15, fontsize=14)
        ax1.set_ylabel('股價', fontsize=12)
        ax1.grid(True)
        ax1.legend(loc='upper left', fontsize=10)

        # 下方子圖：成交量
        ax2 = fig.add_subplot(212, sharex=ax1)
        volume_data = df['Volume'].values

        # 根據漲跌繪製不同顏色的成交量柱狀圖
        colors = ['red' if close >= open_price else 'green'
                  for open_price, close
                  in zip(df['Open'], df['Close'])]

        ax2.bar(range(len(volume_data)),
                volume_data,
                color=colors,
                alpha=0.7)
        ax2.set_title('成交量', pad=15, fontsize=14)
        ax2.set_ylabel('股數', fontsize=12)
        ax2.grid(True)

        # 設置成交量圖的 X 軸標籤
        ax2.set_xticks(range(0, len(dates), 20))
        ax2.set_xticklabels([d.strftime('%m/%d') for d in dates[::20]],
                            rotation=0,  # 水平顯示
                            ha='center')  # 水平置中對齊

        # 調整布局，增加子圖之間的間距
        fig.subplots_adjust(hspace=0.3)  # 增加垂直間距

        # 創建畫布並顯示
        canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    except Exception as e:
        print(f"更新走勢圖時出錯：{str(e)}")


def get_stock_price():
    """獲取股票價格"""
    if not entry_code or not label_price:
        return

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
        current_price_text = (
            f"{stock_name} 收盤價：{price:.2f} 元 "
            f"({trading_date}) - 更新時間：{current_time}"
        )
        label_price.config(text=current_price_text)

        # 更新技術走勢圖
        update_stock_chart(stock_code)
        
        # 顯示歷史交易記錄
        if text_history:
            history_text = show_stock_history(stock_code)
            text_history.delete("1.0", tk.END)
            text_history.insert(tk.END, history_text)
            
    except Exception as e:
        error_msg = str(e)
        print(f"取得股價時出錯：{error_msg}")  # 添加調試資訊
        if "HTTP 404 Not Found" in error_msg:
            messagebox.showerror(
                "错误",
                f"找不到股票代碼 {stock_code}，請確認是否為有效的台股代碼"
            )
        else:
            messagebox.showerror(
                "错误",
                f"無法取得股價，請檢查網路連線或稍後再試\n錯誤訊息：{error_msg}"
            )
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


def on_stock_selected(event):
    """當選擇股票時觸發"""
    global notebook  # 添加全局引用
    selected = stock_combo.get()
    if selected and selected != '無持股紀錄':
        # 從選擇的項目中提取股票代碼
        stock_code = selected.split(' - ')[0].strip()
        # 設置輸入框的值
        entry_code.delete(0, tk.END)
        entry_code.insert(0, stock_code)
        # 觸發獲取股價
        get_stock_price()
        # 開始自動更新
        auto_update_price()
        # 更新籌碼資料
        if notebook:  # 添加檢查
            for frame in notebook.winfo_children():
                if hasattr(frame, 'update_chip_data'):
                    frame.update_chip_data(stock_code)


def create_professional_gui(root_window):
    """建立專業版投資工具介面"""
    global root, entry_code, stock_combo, label_price
    global text_history, text_trades, summary_frame, chart_frame, notebook  # 添加 notebook

    root = root_window

    # 使用 ttk.Notebook 創建分頁式介面
    notebook = ttk.Notebook(root)
    notebook.pack(fill='both', expand=True, padx=5, pady=5)

    # 1. 主要交易頁面
    main_frame = create_main_trading_frame(notebook)
    notebook.add(main_frame, text="📊 即時交易")

    # 2. 技術分析頁面
    technical_frame = create_technical_analysis_frame(notebook)
    notebook.add(technical_frame, text="📈 技術分析")

    # 3. 籌碼分析頁面
    chip_frame = create_chip_analysis_frame(notebook)
    notebook.add(chip_frame, text="🔄 籌碼分析")

    # 4. 績效報告頁面
    performance_frame = create_performance_frame(notebook)
    notebook.add(performance_frame, text="📋 績效報告")

    # 5. 風險控管頁面
    risk_frame = create_risk_management_frame(notebook)
    notebook.add(risk_frame, text="⚠️ 風險控管")


def create_main_trading_frame(notebook):
    """創建主要交易頁面"""
    global entry_code, stock_combo, label_price, text_history, chart_frame

    frame = ttk.Frame(notebook)

    # 上方區域：股票資訊和即時報價
    top_frame = ttk.LabelFrame(frame, text="股票資訊")
    top_frame.pack(fill='x', padx=5, pady=5)

    # 股票選擇和即時報價區
    stock_info_frame = ttk.Frame(top_frame)
    stock_info_frame.pack(fill='x', padx=5, pady=5)

    # 左側：股票選擇
    stock_select_frame = ttk.Frame(stock_info_frame)
    stock_select_frame.pack(side='left', padx=5)

    ttk.Label(stock_select_frame, text="股票代碼:").pack(side='left')
    entry_code = ttk.Entry(stock_select_frame, width=10)
    entry_code.pack(side='left', padx=5)

    stock_combo = ttk.Combobox(stock_select_frame, width=30)
    stock_combo.pack(side='left', padx=5)

    # 建立價格標籤
    label_price = ttk.Label(stock_select_frame, text="")
    label_price.pack(side='left', padx=5)

    # 綁定選擇事件
    stock_combo.bind('<<ComboboxSelected>>', on_stock_selected)

    # 更新股票列表
    root.after(100, update_stock_list)  # 延遲 100ms 後更新股票列表

    # 右側：即時報價資訊
    quote_frame = ttk.Frame(stock_info_frame)
    quote_frame.pack(side='right', padx=5)

    # 即時股價資訊（使用Grid布局）
    price_info = {
        "現價": "0.00",
        "漲跌": "+0.00",
        "漲跌幅": "0.00%",
        "成交量": "0",
        "最高": "0.00",
        "最低": "0.00"
    }

    row = 0
    for label, value in price_info.items():
        ttk.Label(quote_frame, text=label).grid(row=row, column=0, padx=5)
        ttk.Label(quote_frame, text=value).grid(row=row, column=1, padx=5)
        row += 1

    # 中間區域：技術走勢圖
    chart_frame = ttk.LabelFrame(frame, text="技術走勢")
    chart_frame.pack(fill='both', expand=True, padx=5, pady=5)

    # 下方區域：歷史交易記錄
    history_frame = ttk.LabelFrame(frame, text="歷史交易記錄")
    history_frame.pack(fill='both', expand=True, padx=5, pady=5)

    # 創建文本框來顯示歷史交易記錄
    text_history = tk.Text(history_frame, height=10, wrap=tk.WORD)
    text_history.pack(fill='both', expand=True, padx=5, pady=5)

    # 添加滾動條
    scrollbar = ttk.Scrollbar(history_frame,
                              orient="vertical",
                              command=text_history.yview)
    scrollbar.pack(side='right', fill='y')
    text_history.configure(yscrollcommand=scrollbar.set)

    return frame


def create_technical_analysis_frame(notebook):
    """創建技術分析頁面"""
    frame = ttk.Frame(notebook)

    # 左側：技術指標選擇
    indicators_frame = ttk.LabelFrame(frame, text="技術指標")
    indicators_frame.pack(side='left', fill='y', padx=5, pady=5)

    # 創建技術指標的變量
    indicator_vars = {}
    indicators = {
        "KD指標": "kd",
        "RSI": "rsi",
        "MACD": "macd",
        "布林通道": "bollinger",
        "移動平均線": "ma",
        "成交量": "volume",
        "OBV": "obv",
        "威廉指標": "williams"
    }

    # 右側：指標圖表顯示
    chart_container = ttk.LabelFrame(frame, text="技術指標圖表")
    chart_container.pack(side='right', fill='both',
                         expand=True, padx=5, pady=5)

    def on_indicator_change():
        """當指標選擇改變時更新圖表"""
        stock_code = entry_code.get() if entry_code else None
        if stock_code:
            update_technical_charts(stock_code)

    # 創建 Checkbutton
    for indicator_name, indicator_code in indicators.items():
        var = tk.BooleanVar(value=False)  # 預設不選中
        indicator_vars[indicator_code] = var
        cb = ttk.Checkbutton(
            indicators_frame,
            text=indicator_name,
            variable=var,
            command=on_indicator_change
        )
        cb.pack(anchor='w', padx=5, pady=2)

    def update_technical_charts(stock_code):
        """更新技術指標圖表"""
        try:
            # 清除現有圖表
            for widget in chart_container.winfo_children():
                widget.destroy()

            # 獲取股票數據
            formatted_code = format_stock_code(stock_code)
            stock = yf.Ticker(formatted_code)
            df = stock.history(period="6mo")

            if df.empty:
                return

            # 計算需要的子圖數量
            active_indicators = sum(var.get()
                                    for var in indicator_vars.values())
            if active_indicators == 0:
                return

            # 創建圖表
            fig = Figure(figsize=(12, 2 * active_indicators))
            current_subplot = 1

            # KD 指標
            if indicator_vars['kd'].get():
                ax = fig.add_subplot(active_indicators, 1, current_subplot)
                # 計算 KD 值
                df['K'], df['D'] = calculate_kd(df)
                ax.plot(df.index, df['K'], label='K值', color='blue')
                ax.plot(df.index, df['D'], label='D值', color='orange')
                ax.set_title('KD指標')
                ax.grid(True)
                ax.legend()
                current_subplot += 1

            # RSI 指標
            if indicator_vars['rsi'].get():
                ax = fig.add_subplot(active_indicators, 1, current_subplot)
                # 計算 RSI
                df['RSI'] = calculate_rsi(df)
                ax.plot(df.index, df['RSI'], label='RSI', color='purple')
                ax.axhline(y=70, color='r', linestyle='--')
                ax.axhline(y=30, color='g', linestyle='--')
                ax.set_title('RSI指標')
                ax.grid(True)
                ax.legend()
                current_subplot += 1

            # MACD 指標
            if indicator_vars['macd'].get():
                ax = fig.add_subplot(active_indicators, 1, current_subplot)
                # 計算 MACD
                df['MACD'], df['Signal'], df['Hist'] = calculate_macd(df)
                ax.plot(df.index, df['MACD'], label='MACD', color='blue')
                ax.plot(df.index, df['Signal'], label='Signal', color='orange')
                ax.bar(df.index, df['Hist'],
                       label='Histogram', color='gray', alpha=0.3)
                ax.set_title('MACD指標')
                ax.grid(True)
                ax.legend()
                current_subplot += 1

            # 布林通道
            if indicator_vars['bollinger'].get():
                ax = fig.add_subplot(active_indicators, 1, current_subplot)
                # 計算布林通道
                df['Middle'], df['Upper'], df['Lower'] = calculate_bollinger_bands(
                    df)
                ax.plot(df.index, df['Close'], label='收盤價', color='black')
                ax.plot(df.index, df['Upper'], label='上軌', color='red')
                ax.plot(df.index, df['Middle'], label='中軌', color='blue')
                ax.plot(df.index, df['Lower'], label='下軌', color='green')
                ax.set_title('布林通道')
                ax.grid(True)
                ax.legend()
                current_subplot += 1

            # 移動平均線
            if indicator_vars['ma'].get():
                ax = fig.add_subplot(active_indicators, 1, current_subplot)
                # 計算移動平均線
                df['MA5'] = df['Close'].rolling(window=5).mean()
                df['MA20'] = df['Close'].rolling(window=20).mean()
                df['MA60'] = df['Close'].rolling(window=60).mean()
                ax.plot(df.index, df['Close'], label='收盤價',
                        color='black', alpha=0.5)
                ax.plot(df.index, df['MA5'], label='MA5', color='blue')
                ax.plot(df.index, df['MA20'], label='MA20', color='orange')
                ax.plot(df.index, df['MA60'], label='MA60', color='red')
                ax.set_title('移動平均線')
                ax.grid(True)
                ax.legend()
                current_subplot += 1

            # 成交量
            if indicator_vars['volume'].get():
                ax = fig.add_subplot(active_indicators, 1, current_subplot)
                ax.bar(df.index, df['Volume'], label='成交量',
                       color='gray', alpha=0.5)
                ax.set_title('成交量')
                ax.grid(True)
                ax.legend()
                current_subplot += 1

            # OBV
            if indicator_vars['obv'].get():
                ax = fig.add_subplot(active_indicators, 1, current_subplot)
                # 計算 OBV
                df['OBV'] = calculate_obv(df)
                ax.plot(df.index, df['OBV'], label='OBV', color='purple')
                ax.set_title('OBV指標')
                ax.grid(True)
                ax.legend()
                current_subplot += 1

            # 威廉指標
            if indicator_vars['williams'].get():
                ax = fig.add_subplot(active_indicators, 1, current_subplot)
                # 計算威廉指標
                df['Williams %R'] = calculate_williams_r(df)
                ax.plot(df.index, df['Williams %R'],
                        label='Williams %R', color='blue')
                ax.axhline(y=-20, color='r', linestyle='--')
                ax.axhline(y=-80, color='g', linestyle='--')
                ax.set_title('威廉指標')
                ax.grid(True)
                ax.legend()

            # 調整布局
            fig.tight_layout()

            # 創建畫布並顯示
            canvas = FigureCanvasTkAgg(fig, master=chart_container)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)

        except Exception as e:
            print(f"更新技術指標圖表時出錯：{str(e)}")

    # 將更新函數保存為全局變量
    frame.update_technical_charts = update_technical_charts

    return frame


def calculate_kd(df, n=9, m1=3, m2=3):
    """計算KD指標"""
    high_n = df['High'].rolling(n).max()
    low_n = df['Low'].rolling(n).min()
    rsv = (df['Close'] - low_n) / (high_n - low_n) * 100
    k = rsv.rolling(m1).mean()
    d = k.rolling(m2).mean()
    return k, d


def calculate_rsi(df, period=14):
    """計算RSI指標"""
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_macd(df, fast=12, slow=26, signal=9):
    """計算MACD指標"""
    exp1 = df['Close'].ewm(span=fast, adjust=False).mean()
    exp2 = df['Close'].ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    histogram = macd - signal_line
    return macd, signal_line, histogram


def calculate_bollinger_bands(df, period=20, std_dev=2):
    """計算布林通道"""
    middle = df['Close'].rolling(window=period).mean()
    std = df['Close'].rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    return middle, upper, lower


def calculate_obv(df):
    """計算OBV指標"""
    obv = pd.Series(index=df.index, dtype='float64')
    obv.iloc[0] = 0
    for i in range(1, len(df)):
        if df['Close'].iloc[i] > df['Close'].iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] + df['Volume'].iloc[i]
        elif df['Close'].iloc[i] < df['Close'].iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] - df['Volume'].iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i-1]
    return obv


def calculate_williams_r(df, period=14):
    """計算威廉指標"""
    highest_high = df['High'].rolling(window=period).max()
    lowest_low = df['Low'].rolling(window=period).min()
    wr = -100 * ((highest_high - df['Close']) / (highest_high - lowest_low))
    return wr


def create_chip_analysis_frame(notebook):
    """創建籌碼分析頁面"""
    frame = ttk.Frame(notebook)

    # 左側：籌碼資訊
    info_frame = ttk.LabelFrame(frame, text="籌碼資訊")
    info_frame.pack(side='left', fill='both', padx=5, pady=5)

    # 建立籌碼資訊標籤
    labels = {}
    info_items = [
        ("外資持股", "foreign_holding"),
        ("投信持股", "trust_holding"),
        ("自營商持股", "dealer_holding"),
        ("融資餘額", "margin_balance"),
        ("融券餘額", "short_balance"),
        ("當沖比率", "day_trade_ratio")
    ]

    for i, (label, key) in enumerate(info_items):
        labels[key] = ttk.Label(info_frame, text="0.00%")
        ttk.Label(info_frame, text=label).grid(row=i, column=0, padx=5, pady=2, sticky='e')
        labels[key].grid(row=i, column=1, padx=5, pady=2, sticky='w')

    # 右側：籌碼變化圖表
    chart_frame = ttk.LabelFrame(frame, text="籌碼變化")
    chart_frame.pack(side='right', fill='both', expand=True, padx=5, pady=5)

    def update_chip_data(stock_code):
        """更新籌碼資料"""
        try:
            # 獲取股票數據
            formatted_code = format_stock_code(stock_code)
            stock = yf.Ticker(formatted_code)
            
            # 獲取大戶持股資料（最近5個交易日）
            df = stock.history(period="5d")
            
            if df.empty:
                return
            
            # 清除現有圖表
            for widget in chart_frame.winfo_children():
                widget.destroy()

            # 創建圖表
            fig = Figure(figsize=(10, 8))
            
            # 設置全局字型
            plt.rcParams['font.size'] = 10
            
            # 三大法人買賣超圖
            ax1 = fig.add_subplot(311)
            dates = df.index
            
            # 模擬三大法人買賣超數據（實際應從其他數據源獲取）
            foreign_buy = df['Volume'] * 0.4  # 外資買超
            trust_buy = df['Volume'] * 0.1    # 投信買超
            dealer_buy = df['Volume'] * 0.05   # 自營商買超
            
            ax1.bar(dates, foreign_buy, label='外資', color='red', alpha=0.7)
            ax1.bar(dates, trust_buy, bottom=foreign_buy, label='投信', color='green', alpha=0.7)
            ax1.bar(dates, dealer_buy, bottom=foreign_buy+trust_buy, label='自營商', color='blue', alpha=0.7)
            
            ax1.set_title('三大法人買賣超')
            ax1.legend()
            ax1.grid(True)
            
            # 融資融券圖
            ax2 = fig.add_subplot(312)
            margin_data = df['High'] * 1000  # 模擬融資餘額
            short_data = df['Low'] * 1000    # 模擬融券餘額
            
            ax2.plot(dates, margin_data, label='融資餘額', color='red', marker='o')
            ax2.plot(dates, short_data, label='融券餘額', color='green', marker='o')
            ax2.set_title('融資融券餘額')
            ax2.legend()
            ax2.grid(True)
            
            # 股權分散圖
            ax3 = fig.add_subplot(313)
            holding_data = {
                '外資': 40,
                '投信': 10,
                '自營商': 5,
                '其他': 45
            }
            
            ax3.pie(holding_data.values(), 
                   labels=holding_data.keys(),
                   autopct='%1.1f%%',
                   colors=['red', 'green', 'blue', 'gray'])
            ax3.set_title('股權分散')
            
            # 更新左側籌碼資訊
            labels['foreign_holding'].config(text=f"{holding_data['外資']:.2f}%")
            labels['trust_holding'].config(text=f"{holding_data['投信']:.2f}%")
            labels['dealer_holding'].config(text=f"{holding_data['自營商']:.2f}%")
            labels['margin_balance'].config(text=f"{margin_data[-1]:,.0f}")
            labels['short_balance'].config(text=f"{short_data[-1]:,.0f}")
            labels['day_trade_ratio'].config(text="5.23%")  # 模擬當沖比率
            
            # 調整布局
            fig.tight_layout()
            
            # 創建畫布並顯示
            canvas = FigureCanvasTkAgg(fig, master=chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
            
        except Exception as e:
            print(f"更新籌碼資料時出錯：{str(e)}")
    
    # 將更新函數保存為 frame 的屬性
    frame.update_chip_data = update_chip_data
    
    return frame


def create_performance_frame(notebook):
    """創建績效報告頁面"""
    frame = ttk.Frame(notebook)

    # 上方：總體績效摘要
    summary_frame = ttk.LabelFrame(frame, text="績效摘要")
    summary_frame.pack(fill='x', padx=5, pady=5)

    # 使用Grid布局顯示績效指標
    performance_metrics = [
        ("總投資報酬率", "+15.2%"),
        ("年化報酬率", "+12.8%"),
        ("夏普比率", "1.25"),
        ("最大回撤", "-8.5%"),
        ("勝率", "65.2%"),
        ("獲利因子", "1.85")
    ]

    for i, (metric, value) in enumerate(performance_metrics):
        col = i % 3
        row = i // 3
        ttk.Label(summary_frame, text=metric).grid(
            row=row, column=col*2, padx=5, pady=2, sticky='e')
        ttk.Label(summary_frame, text=value).grid(
            row=row, column=col*2+1, padx=5, pady=2, sticky='w')

    # 下方：詳細績效分析
    details_frame = ttk.Notebook(frame)
    details_frame.pack(fill='both', expand=True, padx=5, pady=5)

    # 1. 報酬分析頁面
    returns_frame = ttk.Frame(details_frame)
    details_frame.add(returns_frame, text="報酬分析")
    
    # 創建報酬分析子頁面的內容
    returns_left = ttk.Frame(returns_frame)
    returns_left.pack(side='left', fill='both', expand=True)
    
    # 月度報酬表格
    monthly_returns = ttk.LabelFrame(returns_left, text="月度報酬率")
    monthly_returns.pack(fill='both', expand=True, padx=5, pady=5)
    
    # 創建表格
    tree = ttk.Treeview(monthly_returns, columns=('年月', '報酬率', '累計報酬'), show='headings')
    tree.heading('年月', text='年月')
    tree.heading('報酬率', text='報酬率')
    tree.heading('累計報酬', text='累計報酬')
    tree.pack(fill='both', expand=True)
    
    # 添加滾動條
    scrollbar = ttk.Scrollbar(monthly_returns, orient="vertical", command=tree.yview)
    scrollbar.pack(side='right', fill='y')
    tree.configure(yscrollcommand=scrollbar.set)
    
    # 報酬分析圖表
    returns_right = ttk.Frame(returns_frame)
    returns_right.pack(side='right', fill='both', expand=True)
    
    fig = Figure(figsize=(6, 4))
    ax = fig.add_subplot(111)
    ax.set_title('累計報酬走勢')
    canvas = FigureCanvasTkAgg(fig, master=returns_right)
    canvas.draw()
    canvas.get_tk_widget().pack(fill='both', expand=True)

    # 2. 風險分析頁面
    risk_frame = ttk.Frame(details_frame)
    details_frame.add(risk_frame, text="風險分析")
    
    # 創建風險分析子頁面的內容
    risk_left = ttk.Frame(risk_frame)
    risk_left.pack(side='left', fill='both', expand=True)
    
    # 風險指標
    risk_metrics = ttk.LabelFrame(risk_left, text="風險指標")
    risk_metrics.pack(fill='both', expand=True, padx=5, pady=5)
    
    risk_items = [
        ("波動率", "15.2%"),
        ("最大回撤", "-8.5%"),
        ("Beta係數", "0.85"),
        ("夏普比率", "1.25"),
        ("索提諾比率", "1.15"),
        ("資訊比率", "0.95")
    ]
    
    for i, (metric, value) in enumerate(risk_items):
        ttk.Label(risk_metrics, text=metric).grid(row=i, column=0, padx=5, pady=2, sticky='e')
        ttk.Label(risk_metrics, text=value).grid(row=i, column=1, padx=5, pady=2, sticky='w')
    
    # 風險分析圖表
    risk_right = ttk.Frame(risk_frame)
    risk_right.pack(side='right', fill='both', expand=True)
    
    fig2 = Figure(figsize=(6, 4))
    ax2 = fig2.add_subplot(111)
    ax2.set_title('回撤分析')
    canvas2 = FigureCanvasTkAgg(fig2, master=risk_right)
    canvas2.draw()
    canvas2.get_tk_widget().pack(fill='both', expand=True)

    # 3. 交易記錄頁面
    trades_frame = ttk.Frame(details_frame)
    details_frame.add(trades_frame, text="交易記錄")
    
    # 創建交易記錄表格
    trades_tree = ttk.Treeview(trades_frame, 
                              columns=('日期', '代碼', '股票名稱', '交易', '價格', '數量', '金額', '手續費', '交易稅', '損益'),
                              show='headings')
    
    # 設置列標題
    column_headers = [
        ('日期', 100),
        ('代碼', 80),
        ('股票名稱', 120),
        ('交易', 60),
        ('價格', 80),
        ('數量', 80),
        ('金額', 100),
        ('手續費', 80),
        ('交易稅', 80),
        ('損益', 100)
    ]
    
    for header, width in column_headers:
        trades_tree.heading(header, text=header)
        trades_tree.column(header, width=width)
    
    # 添加滾動條
    trades_scrollbar = ttk.Scrollbar(trades_frame, orient="vertical", command=trades_tree.yview)
    trades_scrollbar.pack(side='right', fill='y')
    trades_tree.configure(yscrollcommand=trades_scrollbar.set)
    trades_tree.pack(fill='both', expand=True)
    
    # 更新交易記錄
    df = load_original_trades()
    if not df.empty:
        for _, row in df.iterrows():
            trade_type = row['買/賣/股利']
            if trade_type == '買':
                price = row['買入價格']
                shares = row['買入股數']
                amount = price * shares
            else:
                price = row['賣出價格']
                shares = row['賣出股數']
                amount = price * shares if not pd.isna(price) and not pd.isna(shares) else 0
            
            trades_tree.insert('', 'end', values=(
                row['交易日期'],
                row['代號'],
                row['股票'],  # 新增股票名稱
                trade_type,
                f"{float(price):.2f}" if not pd.isna(price) else "",
                f"{int(shares):,}" if not pd.isna(shares) else "",
                f"{amount:,.0f}",
                row['手續費'],
                row['交易稅'],
                row.get('價差', '')
            ))
    
    # 更新圖表數據
    if not df.empty:
        # 計算累計報酬
        cumulative_returns = []
        current_return = 0
        dates = []
        
        for _, row in df.sort_values('交易日期').iterrows():
            if row['買/賣/股利'] == '買':
                current_return -= (float(row['買入價格']) * float(row['買入股數']) +
                                 float(row['手續費']) if pd.notna(row['手續費']) else 20)
            elif row['買/賣/股利'] == '賣':
                current_return += (float(row['賣出價格']) * float(row['賣出股數']) -
                                 float(row['手續費']) if pd.notna(row['手續費']) else 20 -
                                 float(row['交易稅']) if pd.notna(row['交易稅']) else 0)
            
            cumulative_returns.append(current_return)
            dates.append(pd.to_datetime(row['交易日期']))
        
        # 更新報酬分析圖表
        ax.clear()
        ax.plot(dates, cumulative_returns, marker='o')
        ax.set_title('累計報酬走勢')
        ax.grid(True)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        fig.tight_layout()
        canvas.draw()
        
        # 更新風險分析圖表
        ax2.clear()
        # 計算回撤
        peak = 0
        drawdowns = []
        for ret in cumulative_returns:
            if ret > peak:
                peak = ret
            drawdown = (ret - peak) / peak * 100 if peak != 0 else 0
            drawdowns.append(drawdown)
        
        ax2.plot(dates, drawdowns, color='red')
        ax2.set_title('回撤分析')
        ax2.grid(True)
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        fig2.tight_layout()
        canvas2.draw()

    # 更新月度報酬率表格
    df = load_original_trades()
    if not df.empty:
        # 計算每月的報酬率
        df['交易日期'] = pd.to_datetime(df['交易日期'])
        df.set_index('交易日期', inplace=True)
        monthly_returns = df.resample('ME').apply(lambda x: (x['收入'].sum() - x['支出'].sum()) / x['支出'].sum() if x['支出'].sum() != 0 else 0)

        # 清空表格
        for item in tree.get_children():
            tree.delete(item)

        # 插入新數據
        for date, value in monthly_returns.items():
            tree.insert('', 'end', values=(date.strftime('%Y-%m'), f'{value:.2%}', f'{value:.2f}'))

    return frame


def create_risk_management_frame(notebook):
    """創建風險控管頁面"""
    frame = ttk.Frame(notebook)

    # 左側：風險參數設定
    settings_frame = ttk.LabelFrame(frame, text="風險參數設定")
    settings_frame.pack(side='left', fill='y', padx=5, pady=5)

    risk_params = [
        ("單筆交易上限", "entry"),
        ("停損比例", "entry"),
        ("停利比例", "entry"),
        ("資金使用率上限", "entry"),
        ("單一標的部位上限", "entry"),
        ("風險警告等級", "combo")
    ]

    for param, widget_type in risk_params:
        param_frame = ttk.Frame(settings_frame)
        param_frame.pack(fill='x', padx=5, pady=2)

        ttk.Label(param_frame, text=param).pack(side='left')
        if widget_type == "entry":
            ttk.Entry(param_frame, width=10).pack(side='right')
        else:
            ttk.Combobox(param_frame, width=10).pack(side='right')

    # 右側：風險監控儀表板
    dashboard_frame = ttk.LabelFrame(frame, text="風險監控儀表板")
    dashboard_frame.pack(side='right', fill='both',
                         expand=True, padx=5, pady=5)

    # 可以使用 matplotlib 來繪製風險監控圖表
    canvas = tk.Canvas(dashboard_frame, bg='white')
    canvas.pack(fill='both', expand=True, padx=5, pady=5)

    return frame


def setup_styles():
    """設定自定義樣式"""
    style = ttk.Style()

    # 買入按鈕樣式
    style.configure('Buy.TButton',
                    background='#4CAF50',
                    foreground='white')

    # 賣出按鈕樣式
    style.configure('Sell.TButton',
                    background='#f44336',
                    foreground='white')

    # 取消按鈕樣式
    style.configure('Cancel.TButton',
                    background='#9E9E9E',
                    foreground='white')


def create_status_bar(root_window):
    """創建狀態欄"""
    status_frame = ttk.Frame(root_window)
    status_frame.pack(side=tk.BOTTOM, fill=tk.X)

    status_label = ttk.Label(status_frame, text="就緒")
    status_label.pack(side=tk.LEFT, padx=5)

    update_time_label = ttk.Label(status_frame, text="")
    update_time_label.pack(side=tk.RIGHT, padx=5)

    return status_label, update_time_label


def export_trading_records():
    """匯出交易記錄"""
    try:
        df = load_original_trades()
        if df.empty:
            messagebox.showwarning("警告", "沒有可匯出的交易記錄")
            return

        # 讓使用者選擇保存位置和格式
        file_types = [
            ('Excel 檔案', '*.xlsx'),
            ('CSV 檔案', '*.csv'),
            ('JSON 檔案', '*.json')
        ]
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=file_types,
            title="選擇匯出位置"
        )

        if not file_path:
            return

        try:
            if file_path.endswith('.xlsx'):
                # 使用 openpyxl 引擎
                df.to_excel(file_path, index=False, engine='openpyxl')
            elif file_path.endswith('.csv'):
                df.to_csv(file_path, index=False)
            elif file_path.endswith('.json'):
                df.to_json(file_path, orient='records', force_ascii=False)

            messagebox.showinfo("成功", f"交易記錄已成功匯出到：\n{file_path}")
        except PermissionError:
            messagebox.showerror("錯誤", "無法存取選擇的位置，請確認是否有寫入權限")
        except Exception as e:
            messagebox.showerror("錯誤", f"匯出失敗：{str(e)}\n請確認檔案未被其他程式開啟")
            
    except Exception as e:
        messagebox.showerror("錯誤", f"準備匯出資料時發生錯誤：{str(e)}")


def create_menu(root_window):
    """創建選單"""
    menubar = tk.Menu(root_window)
    root_window.config(menu=menubar)

    # 檔案選單
    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="檔案", menu=file_menu)
    file_menu.add_command(label="匯出交易記錄", command=export_trading_records)
    file_menu.add_separator()
    file_menu.add_command(label="離開", command=root_window.quit)

    # 幫助選單
    help_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="幫助", menu=help_menu)
    help_menu.add_command(
        label="關於", command=lambda: messagebox.showinfo("關於", "專業股票交易系統 v1.0"))


def initialize_gui():
    """初始化圖形界面"""
    root_window = tk.Tk()
    root_window.title("專業股票交易系統")

    # 設置視窗大小和位置
    window_width = 1200
    window_height = 800
    screen_width = root_window.winfo_screenwidth()
    screen_height = root_window.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    root_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    # 設置樣式
    setup_styles()

    # 創建選單
    create_menu(root_window)

    # 創建專業界面
    create_professional_gui(root_window)

    # 創建狀態欄
    status_label, update_time_label = create_status_bar(root_window)

    # 將標籤保存為全局變量
    root_window.status_label = status_label
    root_window.update_time_label = update_time_label

    # 啟動主循環
    root_window.mainloop()


def calculate_performance_metrics(stock_code=None):
    """計算交易績效指標"""
    df = load_original_trades()
    if df.empty:
        return {}

    # 如果指定了股票代碼，只分析該股票
    if stock_code:
        df = df[df['代號'] == stock_code]

    metrics = {
        'total_investment': 0,  # 總投資金額
        'total_return': 0,      # 總報酬
        'win_rate': 0,         # 勝率
        'profit_factor': 0,    # 獲利因子
        'max_drawdown': 0,     # 最大回撤
        'total_trades': 0,     # 總交易次數
        'win_trades': 0,       # 獲利次數
        'loss_trades': 0       # 虧損次數
    }

    # 計算交易統計
    total_profit = 0
    total_loss = 0

    # 按股票分組計算
    for code in df['代號'].unique():
        stock_df = df[df['代號'] == code]

        # 計算買入成本
        buy_cost = 0
        buy_shares = 0
        sell_profit = 0

        for _, row in stock_df.iterrows():
            if row['買/賣/股利'] == '買':
                cost = row['買入價格'] * row['買入股數']
                fee = float(row['手續費']) if pd.notna(row['手續費']) else 20
                buy_cost += cost + fee
                buy_shares += row['買入股數']
                metrics['total_investment'] += cost + fee

            elif row['買/賣/股利'] == '賣':
                revenue = row['賣出價格'] * row['賣出股數']
                fee = float(row['手續費']) if pd.notna(row['手續費']) else 20
                tax = float(row['交易稅']) if pd.notna(
                    row['交易稅']) else revenue * 0.003

                # 計算此次賣出的成本
                avg_cost = buy_cost / buy_shares if buy_shares > 0 else 0
                sell_cost = avg_cost * row['賣出股數']

                profit = revenue - sell_cost - fee - tax
                if profit > 0:
                    total_profit += profit
                    metrics['win_trades'] += 1
                else:
                    total_loss += abs(profit)
                    metrics['loss_trades'] += 1

                metrics['total_trades'] += 1

    # 計算績效指標
    metrics['total_return'] = total_profit - total_loss
    metrics['win_rate'] = (metrics['win_trades'] / metrics['total_trades']
                           * 100) if metrics['total_trades'] > 0 else 0
    metrics['profit_factor'] = total_profit / \
        total_loss if total_loss > 0 else float('inf')

    # 計算報酬率
    if metrics['total_investment'] > 0:
        metrics['roi'] = (metrics['total_return'] /
                          metrics['total_investment']) * 100
    else:
        metrics['roi'] = 0

    return metrics


def update_performance_display():
    """更新績效顯示"""
    metrics = calculate_performance_metrics()

    # 更新績效摘要標籤
    performance_labels = {
        'total_investment': f"總投資金額: {metrics['total_investment']:,.0f} 元",
        'total_return': f"總報酬: {metrics['total_return']:,.0f} 元",
        'roi': f"報酬率: {metrics['roi']:.2f}%",
        'win_rate': f"勝率: {metrics['win_rate']:.1f}%",
        'profit_factor': f"獲利因子: {metrics['profit_factor']:.2f}",
        'total_trades': f"總交易次數: {metrics['total_trades']}"
    }

    # 更新績效顯示
    row = 0
    col = 0
    for label, value in performance_labels.items():
        ttk.Label(summary_frame, text=value).grid(
            row=row, column=col, padx=5, pady=2, sticky='w'
        )
        col += 1
        if col >= 3:
            col = 0
            row += 1


def create_charts(frame):
    """創建圖表顯示"""
    # 創建圖表容器
    fig = Figure(figsize=(12, 6))

    # 添加子圖
    ax1 = fig.add_subplot(221)  # 股價走勢
    ax2 = fig.add_subplot(222)  # 獲利分布
    ax3 = fig.add_subplot(223)  # 交易量
    ax4 = fig.add_subplot(224)  # 累計報酬

    # 獲取數據
    df = load_original_trades()
    if not df.empty:
        # 轉換日期格式
        df['交易日期'] = pd.to_datetime(df['交易日期'])

        # 1. 繪製股價走勢
        ax1.set_title('股價走勢')
        for code in df['代號'].unique():
            stock_df = df[df['代號'] == code]
            ax1.plot(stock_df['交易日期'], stock_df['現價'],
                     label=f"{code}", marker='o')
        ax1.legend()
        ax1.grid(True)

        # 2. 繪製獲利分布
        profits = []
        for code in df['代號'].unique():
            stock_df = df[df['代號'] == code]
            metrics = calculate_performance_metrics(code)
            profits.append((code, metrics['total_return']))

        profits.sort(key=lambda x: x[1], reverse=True)
        codes, values = zip(*profits)
        ax2.bar(codes, values)
        ax2.set_title('各股獲利分布')
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)

        # 3. 繪製交易量
        monthly_trades = df.groupby(
            df['交易日期'].dt.strftime('%Y-%m'))['代號'].count()
        ax3.bar(range(len(monthly_trades)), monthly_trades.values)
        ax3.set_title('月度交易量')
        ax3.set_xticks(range(len(monthly_trades)))
        ax3.set_xticklabels(monthly_trades.index, rotation=45)

        # 4. 繪製累計報酬
        cumulative_return = []
        current_return = 0
        for _, row in df.sort_values('交易日期').iterrows():
            if row['買/賣/股利'] == '買':
                current_return -= (row['買入價格'] * row['買入股數'] +
                                   float(row['手續費'] if pd.notna(row['手續費']) else 20))
            elif row['買/賣/股利'] == '賣':
                current_return += (row['賣出價格'] * row['賣出股數'] -
                                   float(row['手續費'] if pd.notna(row['手續費']) else 20) -
                                   float(row['交易稅'] if pd.notna(row['交易稅']) else 0))
            cumulative_return.append((row['交易日期'], current_return))

        dates, returns = zip(*cumulative_return)
        ax4.plot(dates, returns, marker='o')
        ax4.set_title('累計報酬')
        ax4.grid(True)
        plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45)

    # 調整布局
    fig.tight_layout()

    # 創建畫布
    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()

    # 將畫布放置到框架中
    canvas.get_tk_widget().pack(fill='both', expand=True)

    return canvas


def update_charts():
    """更新圖表顯示"""
    # 清除原有圖表
    for widget in chart_frame.winfo_children():
        widget.destroy()

    # 創建新圖表
    create_charts(chart_frame)


def get_institutional_data(stock_code):
    """獲取三大法人買賣超資料"""
    try:
        # 移除股票代碼中的 .TW 或 .TWO
        stock_code = ''.join(filter(str.isdigit, stock_code))
        
        # 設定日期範圍（最近5個交易日）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=10)  # 多取幾天以確保有5個交易日
        
        # 證交所API網址
        url = "https://www.twse.com.tw/rwd/zh/fund/T86?date={}&selectType=ALL&response=json"
        
        data = {
            'dates': [],
            'foreign': [],
            'trust': [],
            'dealer': []
        }
        
        # 獲取每日資料
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y%m%d')
            response = requests.get(url.format(date_str))
            
            if response.status_code == 200:
                json_data = response.json()
                if json_data.get('data'):
                    for row in json_data['data']:
                        if row[0] == stock_code:
                            data['dates'].append(current_date)
                            data['foreign'].append(int(row[4].replace(',', '')))  # 外資買賣超
                            data['trust'].append(int(row[7].replace(',', '')))    # 投信買賣超
                            data['dealer'].append(int(row[10].replace(',', '')))  # 自營商買賣超
            
            current_date += timedelta(days=1)
            time.sleep(0.5)  # 避免請求過於頻繁
            
        return data
    except Exception as e:
        print(f"獲取三大法人資料時出錯：{str(e)}")
        return None

def get_margin_trading_data(stock_code):
    """獲取融資融券餘額資料"""
    try:
        # 移除股票代碼中的 .TW 或 .TWO
        stock_code = ''.join(filter(str.isdigit, stock_code))
        
        # 證交所融資融券API
        url = "https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date={}&selectType=ALL&response=json"
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=10)
        
        data = {
            'dates': [],
            'margin_balance': [],
            'short_balance': []
        }
        
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y%m%d')
            response = requests.get(url.format(date_str))
            
            if response.status_code == 200:
                json_data = response.json()
                if json_data.get('data'):
                    for row in json_data['data']:
                        if row[0] == stock_code:
                            data['dates'].append(current_date)
                            data['margin_balance'].append(int(row[5].replace(',', '')))  # 融資餘額
                            data['short_balance'].append(int(row[8].replace(',', '')))   # 融券餘額
            
            current_date += timedelta(days=1)
            time.sleep(0.5)
            
        return data
    except Exception as e:
        print(f"獲取融資融券資料時出錯：{str(e)}")
        return None

def get_shareholding_distribution(stock_code):
    """獲取股權分散資料"""
    try:
        # 移除股票代碼中的 .TW 或 .TWO
        stock_code = ''.join(filter(str.isdigit, stock_code))
        
        # 證交所股權分散表API
        url = f"https://www.tdcc.com.tw/smWeb/QryStockAjax.do"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        
        # 取得最近一週的資料
        today = datetime.now()
        friday = today - timedelta(days=(today.weekday() - 4) % 7)
        date_str = friday.strftime('%Y%m%d')
        
        data = {
            'scaDates': date_str,
            'scaDate': date_str,
            'SqlMethod': 'StockNo',
            'StockNo': stock_code,
            'radioStockNo': stock_code
        }
        
        response = requests.post(url, data=data, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'class': 'table_2'})
            
            if table:
                rows = table.find_all('tr')[1:]  # 跳過表頭
                total_shares = 0
                distribution = {
                    '1-999': 0,
                    '1,000-5,000': 0,
                    '5,001-10,000': 0,
                    '10,001-50,000': 0,
                    '50,001-100,000': 0,
                    '100,001-500,000': 0,
                    '500,001-1,000,000': 0,
                    '1,000,001以上': 0
                }
                
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 4:
                        shares = int(cols[3].text.replace(',', ''))
                        total_shares += shares
                        
                        # 根據持股數量分類
                        level = cols[1].text.strip()
                        distribution[level] = shares
                
                return distribution
            
        return None
    except Exception as e:
        print(f"獲取股權分散資料時出錯：{str(e)}")
        return None

def update_chip_data(stock_code):
    """更新籌碼資料"""
    try:
        # 獲取三大法人資料
        inst_data = get_institutional_data(stock_code)
        # 獲取融資融券資料
        margin_data = get_margin_trading_data(stock_code)
        # 獲取股權分散資料
        dist_data = get_shareholding_distribution(stock_code)
        
        if not any([inst_data, margin_data, dist_data]):
            print("無法獲取籌碼資料")
            return
            
        # 清除現有圖表
        for widget in chart_frame.winfo_children():
            widget.destroy()
            
        # 創建新圖表
        fig = Figure(figsize=(10, 8))
        
        # 設置全局字型
        plt.rcParams['font.size'] = 10
        
        # 三大法人買賣超圖
        ax1 = fig.add_subplot(311)
        if inst_data:
            dates = inst_data['dates']
            ax1.bar(dates, inst_data['foreign'], label='外資', color='red', alpha=0.7)
            ax1.bar(dates, inst_data['trust'], bottom=inst_data['foreign'], 
                   label='投信', color='green', alpha=0.7)
            ax1.bar(dates, inst_data['dealer'], 
                   bottom=[f+t for f,t in zip(inst_data['foreign'], inst_data['trust'])],
                   label='自營商', color='blue', alpha=0.7)
            
        ax1.set_title('三大法人買賣超')
        ax1.legend()
        ax1.grid(True)
        
        # 融資融券圖
        ax2 = fig.add_subplot(312)
        if margin_data:
            dates = margin_data['dates']
            ax2.plot(dates, margin_data['margin_balance'], 
                    label='融資餘額', color='red', marker='o')
            ax2.plot(dates, margin_data['short_balance'], 
                    label='融券餘額', color='green', marker='o')
            
        ax2.set_title('融資融券餘額')
        ax2.legend()
        ax2.grid(True)
        
        # 股權分散圖
        ax3 = fig.add_subplot(313)
        if dist_data:
            labels = list(dist_data.keys())
            sizes = list(dist_data.values())
            ax3.pie(sizes, labels=labels, autopct='%1.1f%%', 
                   colors=['red', 'green', 'blue', 'gray', 'orange', 'purple', 'yellow', 'pink'])
            ax3.set_title('股權分散')
        
        # 調整布局
        fig.tight_layout()
        
        # 創建畫布並顯示
        canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # 更新左側籌碼資訊
        if inst_data and margin_data:
            # 計算三大法人最新持股比例
            total_inst = sum([inst_data['foreign'][-1], 
                            inst_data['trust'][-1], 
                            inst_data['dealer'][-1]])
            
            labels['foreign_holding'].config(
                text=f"{inst_data['foreign'][-1]/total_inst*100:.2f}%")
            labels['trust_holding'].config(
                text=f"{inst_data['trust'][-1]/total_inst*100:.2f}%")
            labels['dealer_holding'].config(
                text=f"{inst_data['dealer'][-1]/total_inst*100:.2f}%")
            labels['margin_balance'].config(
                text=f"{margin_data['margin_balance'][-1]:,}")
            labels['short_balance'].config(
                text=f"{margin_data['short_balance'][-1]:,}")
            
            # 計算當沖比率（假設值）
            labels['day_trade_ratio'].config(text="5.23%")
            
    except Exception as e:
        print(f"更新籌碼資料時出錯：{str(e)}")

# 啟動應用程序
if __name__ == "__main__":
    initialize_gui()
