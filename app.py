"""
三重確認交易系統 — Triple Confirmation Trading System
趨勢形成 + MACD訊號 + 成交量增多 + 支撐阻力突破
Multi-stock, Multi-timeframe, Telegram + Voice Alerts
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import requests
import json
import threading
from io import BytesIO

# ─── Page Config ───
st.set_page_config(
    page_title="三重確認交易系統",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS matching screenshot style ───
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

:root {
    --bg-main: #f5f5f0;
    --bg-card: #ffffff;
    --border: #e8e8e0;
    --text-primary: #2d2d2d;
    --text-secondary: #6b6b6b;
    --green: #4caf50;
    --red: #e53935;
    --orange: #ff9800;
    --green-light: #e8f5e9;
    --red-light: #ffebee;
    --orange-light: #fff3e0;
    --gray-dot: #9e9e9e;
}

.stApp {
    background-color: var(--bg-main) !important;
    font-family: 'Noto Sans TC', 'JetBrains Mono', sans-serif !important;
}

.block-container {
    padding-top: 1rem !important;
    max-width: 100% !important;
}

h1, h2, h3, h4, h5, h6, p, span, div, label {
    font-family: 'Noto Sans TC', 'JetBrains Mono', sans-serif !important;
    color: var(--text-primary) !important;
}

/* Card styling */
.signal-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.signal-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
    font-size: 15px;
}

.dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
    flex-shrink: 0;
}

.dot-green { background-color: var(--green); }
.dot-red { background-color: var(--red); }
.dot-orange { background-color: var(--orange); }
.dot-gray { background-color: var(--gray-dot); }

.label-text {
    color: var(--text-secondary);
    min-width: 80px;
    font-size: 14px;
}

.value-text {
    font-weight: 500;
    font-size: 14px;
}

.metric-box {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px;
    text-align: center;
}

.metric-value {
    font-size: 28px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace !important;
}

.metric-label {
    font-size: 12px;
    color: var(--text-secondary);
    margin-top: 4px;
}

.strong-buy {
    background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
    border: 2px solid var(--green);
}

.strong-sell {
    background: linear-gradient(135deg, #ffebee, #ffcdd2);
    border: 2px solid var(--red);
}

.normal-buy {
    border-left: 4px solid var(--green);
}

.normal-sell {
    border-left: 4px solid var(--red);
}

.hold-signal {
    border-left: 4px solid var(--gray-dot);
}

.section-title {
    font-size: 15px;
    font-weight: 500;
    color: var(--text-primary);
    margin-bottom: 12px;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--border);
}

.trade-record {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13px;
    padding: 4px 0;
}

.ticker-header {
    font-size: 22px;
    font-weight: 700;
    margin-bottom: 4px;
}

.price-display {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 32px;
    font-weight: 700;
}

/* Hide streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

div[data-testid="stMetric"] {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 12px 16px;
}

div[data-testid="stMetric"] label {
    font-size: 12px !important;
    color: var(--text-secondary) !important;
}

div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 20px !important;
}

.stSelectbox label, .stMultiSelect label, .stSlider label {
    font-size: 13px !important;
    font-weight: 500 !important;
}

div[data-testid="stSidebar"] {
    background-color: #fafaf5 !important;
}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
}

.stTabs [data-baseweb="tab"] {
    font-family: 'Noto Sans TC', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    border-radius: 8px 8px 0 0 !important;
    padding: 8px 16px !important;
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# CORE ENGINE
# ═══════════════════════════════════════════════════════

TIMEFRAME_MAP = {
    "1m": {"interval": "1m", "period": "7d", "sr_interval": "1h", "sr_period": "1mo"},
    "5m": {"interval": "5m", "period": "60d", "sr_interval": "1d", "sr_period": "6mo"},
    "15m": {"interval": "15m", "period": "60d", "sr_interval": "1d", "sr_period": "6mo"},
    "30m": {"interval": "30m", "period": "60d", "sr_interval": "1d", "sr_period": "1y"},
    "1h": {"interval": "1h", "period": "730d", "sr_interval": "1d", "sr_period": "2y"},
    "1d": {"interval": "1d", "period": "2y", "sr_interval": "1wk", "sr_period": "5y"},
    "1wk": {"interval": "1wk", "period": "5y", "sr_interval": "1mo", "sr_period": "10y"},
}

EMA_FAST = 12
EMA_SLOW = 26
MACD_SIGNAL = 9


@st.cache_data(ttl=30)
def fetch_data(ticker, interval, period):
    """Fetch OHLCV data from yfinance."""
    try:
        df = yf.download(ticker, interval=interval, period=period, progress=False, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        # Flatten multi-level columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index = pd.to_datetime(df.index)
        return df
    except Exception as e:
        st.error(f"數據獲取失敗 {ticker}: {e}")
        return pd.DataFrame()


def calc_ema(series, span):
    return series.ewm(span=span, adjust=False).mean()


def calc_macd(df):
    """Calculate MACD, Signal, Histogram."""
    df = df.copy()
    df['EMA_fast'] = calc_ema(df['Close'], EMA_FAST)
    df['EMA_slow'] = calc_ema(df['Close'], EMA_SLOW)
    df['DIF'] = df['EMA_fast'] - df['EMA_slow']
    df['DEA'] = calc_ema(df['DIF'], MACD_SIGNAL)
    df['Histogram'] = df['DIF'] - df['DEA']
    return df


def find_support_resistance(df, min_touches=2, tolerance_pct=0.003):
    """
    Find support/resistance levels based on:
    1. Multi-touch validation (most important)
    2. Historical highs/lows and turning points
    3. Price congestion zones / volume accumulation areas
    4. Gap / long candle origins (institutional intervention)
    """
    if df.empty or len(df) < 20:
        return [], []

    highs = df['High'].values
    lows = df['Low'].values
    closes = df['Close'].values
    volumes = df['Volume'].values if 'Volume' in df.columns else np.ones(len(df))

    current_price = closes[-1]
    price_range = max(highs) - min(lows)
    if price_range == 0:
        return [], []
    tol = current_price * tolerance_pct

    # Collect candidate levels from swing highs/lows
    candidates = []

    # Local highs and lows (window=5)
    for w in [3, 5, 8]:
        for i in range(w, len(df) - w):
            # Swing high
            if highs[i] == max(highs[i-w:i+w+1]):
                candidates.append(highs[i])
            # Swing low
            if lows[i] == min(lows[i-w:i+w+1]):
                candidates.append(lows[i])

    # Add gap origins (large candle bodies)
    for i in range(1, len(df)):
        body = abs(closes[i] - closes[i-1])
        avg_body = np.mean(np.abs(np.diff(closes[max(0,i-20):i+1]))) if i > 1 else body
        if body > avg_body * 2.0:
            candidates.append(min(closes[i], closes[i-1]))  # gap origin
            candidates.append(max(closes[i], closes[i-1]))

    if not candidates:
        return [], []

    # Cluster nearby levels
    candidates = sorted(candidates)
    clusters = []
    current_cluster = [candidates[0]]

    for c in candidates[1:]:
        if abs(c - np.mean(current_cluster)) <= tol:
            current_cluster.append(c)
        else:
            clusters.append(current_cluster)
            current_cluster = [c]
    clusters.append(current_cluster)

    # Filter by minimum touches
    levels = []
    for cluster in clusters:
        if len(cluster) >= min_touches:
            level = np.mean(cluster)
            touches = len(cluster)
            # Count actual price interactions (close within tolerance)
            interactions = sum(1 for c in closes if abs(c - level) <= tol)
            strength = touches + interactions
            levels.append((level, strength, touches))

    # Separate into support and resistance
    support = [(lvl, s, t) for lvl, s, t in levels if lvl < current_price]
    resistance = [(lvl, s, t) for lvl, s, t in levels if lvl >= current_price]

    # Sort: support descending (closest first), resistance ascending
    support = sorted(support, key=lambda x: -x[0])[:5]
    resistance = sorted(resistance, key=lambda x: x[0])[:5]

    return support, resistance


def analyze_signals(df, support_levels, resistance_levels):
    """
    Triple Confirmation Logic:
    1. Trend: EMA fast vs slow
    2. MACD: Golden/Death cross + Histogram flip
    3. S/R Breakout: Price vs key levels
    """
    if df.empty or len(df) < 30:
        return {
            'signal': '數據不足',
            'signal_type': 'hold',
            'trend': '未知',
            'macd_cross': '未知',
            'histogram_momentum': 0,
            'sr_status': '未知',
            'strength': 0,
            'details': {}
        }

    latest = df.iloc[-1]
    prev = df.iloc[-2]
    price = latest['Close']

    # 1. Trend Confirmation
    ema_fast = latest['EMA_fast']
    ema_slow = latest['EMA_slow']
    trend_bullish = ema_fast > ema_slow
    trend = "上升趨勢" if trend_bullish else "下降趨勢"
    trend_strength = abs(ema_fast - ema_slow) / price * 100

    # 2. MACD Confirmation
    dif = latest['DIF']
    dea = latest['DEA']
    prev_dif = prev['DIF']
    prev_dea = prev['DEA']
    hist = latest['Histogram']
    prev_hist = prev['Histogram']

    golden_cross = prev_dif <= prev_dea and dif > dea
    death_cross = prev_dif >= prev_dea and dif < dea
    hist_flip_positive = prev_hist <= 0 and hist > 0
    hist_flip_negative = prev_hist >= 0 and hist < 0

    macd_bullish = dif > dea
    macd_bearish = dif < dea

    if golden_cross:
        macd_cross = "金叉 ✦"
    elif death_cross:
        macd_cross = "死叉 ✦"
    elif macd_bullish:
        macd_cross = "DIF > DEA"
    else:
        macd_cross = "DIF < DEA"

    # 3. Support/Resistance Breakout
    sr_status = "無突破"
    breakout_bullish = False
    breakout_bearish = False
    closest_resistance = resistance_levels[0][0] if resistance_levels else None
    closest_support = support_levels[0][0] if support_levels else None

    # Check resistance breakout
    if closest_resistance and price > closest_resistance:
        tol = price * 0.001
        if price > closest_resistance + tol:
            breakout_bullish = True
            sr_status = f"突破阻力 {closest_resistance:.2f}"

    # Check support breakdown
    if closest_support and price < closest_support:
        tol = price * 0.001
        if price < closest_support - tol:
            breakout_bearish = True
            sr_status = f"跌破支撐 {closest_support:.2f}"

    if not breakout_bullish and not breakout_bearish:
        if closest_resistance:
            dist_r = abs(price - closest_resistance) / price * 100
            if dist_r < 0.5:
                sr_status = f"接近阻力 {closest_resistance:.2f}"
        if closest_support:
            dist_s = abs(price - closest_support) / price * 100
            if dist_s < 0.5:
                sr_status = f"接近支撐 {closest_support:.2f}"

    # Volume confirmation
    vol_sma = df['Volume'].rolling(20).mean().iloc[-1]
    vol_current = latest['Volume']
    vol_ratio = vol_current / vol_sma if vol_sma > 0 else 1
    vol_surge = vol_ratio > 1.5

    # ═══ Triple Confirmation Signal Logic ═══
    signal_type = "hold"
    signal = "觀望"
    strength = 0

    # Count confirmations for BUY
    buy_confirms = 0
    if trend_bullish:
        buy_confirms += 1
    if macd_bullish or golden_cross:
        buy_confirms += 1
    if golden_cross:
        buy_confirms += 0.5  # extra weight for fresh cross

    # Count confirmations for SELL
    sell_confirms = 0
    if not trend_bullish:
        sell_confirms += 1
    if macd_bearish or death_cross:
        sell_confirms += 1
    if death_cross:
        sell_confirms += 0.5

    # Apply triple confirmation
    if buy_confirms >= 2:
        if breakout_bullish or (vol_surge and buy_confirms >= 2.5):
            signal = "強烈買入 🔥"
            signal_type = "strong_buy"
            strength = min(100, int(buy_confirms * 25 + (30 if breakout_bullish else 0) + (20 if vol_surge else 0)))
        else:
            signal = "普通買入"
            signal_type = "buy"
            strength = min(80, int(buy_confirms * 20 + (15 if vol_surge else 0)))
    elif sell_confirms >= 2:
        if breakout_bearish or (vol_surge and sell_confirms >= 2.5):
            signal = "強烈賣出 🔥"
            signal_type = "strong_sell"
            strength = min(100, int(sell_confirms * 25 + (30 if breakout_bearish else 0) + (20 if vol_surge else 0)))
        else:
            signal = "普通賣出"
            signal_type = "sell"
            strength = min(80, int(sell_confirms * 20 + (15 if vol_surge else 0)))
    else:
        # Partial signals
        if hist_flip_positive:
            signal = "動能轉多（待確認）"
            signal_type = "watch_buy"
            strength = 30
        elif hist_flip_negative:
            signal = "動能轉空（待確認）"
            signal_type = "watch_sell"
            strength = 30
        else:
            signal = "觀望"
            signal_type = "hold"
            strength = 0

    return {
        'signal': signal,
        'signal_type': signal_type,
        'trend': trend,
        'trend_bullish': trend_bullish,
        'trend_strength': trend_strength,
        'macd_cross': macd_cross,
        'golden_cross': golden_cross,
        'death_cross': death_cross,
        'dif': dif,
        'dea': dea,
        'histogram': hist,
        'hist_flip_positive': hist_flip_positive,
        'hist_flip_negative': hist_flip_negative,
        'histogram_momentum': hist,
        'sr_status': sr_status,
        'breakout_bullish': breakout_bullish,
        'breakout_bearish': breakout_bearish,
        'closest_support': closest_support,
        'closest_resistance': closest_resistance,
        'vol_ratio': vol_ratio,
        'vol_surge': vol_surge,
        'strength': strength,
        'price': price,
        'ema_fast': ema_fast,
        'ema_slow': ema_slow,
    }


def send_telegram(bot_token, chat_id, message):
    """Send signal via Telegram."""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=10)
        return True
    except Exception:
        return False


def generate_voice_html(text):
    """Generate HTML for browser-based speech synthesis."""
    return f"""
    <script>
    (function() {{
        const msg = new SpeechSynthesisUtterance("{text}");
        msg.lang = 'zh-TW';
        msg.rate = 1.0;
        msg.pitch = 1.0;
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(msg);
    }})();
    </script>
    """


# ═══════════════════════════════════════════════════════
# CHARTING
# ═══════════════════════════════════════════════════════

def create_chart(df, ticker, support_levels, resistance_levels, signal_info):
    """Create chart matching the screenshot style."""

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.55, 0.25, 0.20],
        subplot_titles=["K線 + 趨勢 + 支撐阻力", "MACD / DIF / DEA / Histogram", "成交量"]
    )

    # ─── Row 1: Candlestick + EMA + S/R ───
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'],
        increasing_line_color='#4caf50',
        decreasing_line_color='#e53935',
        increasing_fillcolor='#4caf50',
        decreasing_fillcolor='#e53935',
        name='K線',
        line=dict(width=1),
    ), row=1, col=1)

    # EMA lines
    fig.add_trace(go.Scatter(
        x=df.index, y=df['EMA_fast'],
        line=dict(color='#2196f3', width=1.5),
        name=f'EMA{EMA_FAST}',
        opacity=0.8
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=df['EMA_slow'],
        line=dict(color='#ff9800', width=1.5),
        name=f'EMA{EMA_SLOW}',
        opacity=0.8
    ), row=1, col=1)

    # Bollinger Bands (for reference envelope)
    bb_mid = df['Close'].rolling(20).mean()
    bb_std = df['Close'].rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std

    fig.add_trace(go.Scatter(
        x=df.index, y=bb_upper,
        line=dict(color='#e53935', width=1, dash='dash'),
        name='BB Upper',
        opacity=0.4
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=bb_lower,
        line=dict(color='#4caf50', width=1, dash='dash'),
        name='BB Lower',
        opacity=0.4
    ), row=1, col=1)

    # Support/Resistance lines
    for lvl, strength, touches in resistance_levels[:3]:
        fig.add_hline(
            y=lvl, line_dash="dot", line_color="#e53935",
            opacity=min(0.8, 0.3 + touches * 0.1),
            annotation_text=f"R {lvl:.2f} ({touches}t)",
            annotation_position="right",
            annotation_font_size=10,
            annotation_font_color="#e53935",
            row=1, col=1
        )

    for lvl, strength, touches in support_levels[:3]:
        fig.add_hline(
            y=lvl, line_dash="dot", line_color="#4caf50",
            opacity=min(0.8, 0.3 + touches * 0.1),
            annotation_text=f"S {lvl:.2f} ({touches}t)",
            annotation_position="right",
            annotation_font_size=10,
            annotation_font_color="#4caf50",
            row=1, col=1
        )

    # ─── Row 2: MACD ───
    colors = ['#4caf50' if v >= 0 else '#e53935' for v in df['Histogram']]

    fig.add_trace(go.Bar(
        x=df.index, y=df['Histogram'],
        marker_color=colors,
        name='Histogram',
        opacity=0.7
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=df['DIF'],
        line=dict(color='#2196f3', width=1.5),
        name='DIF'
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=df['DEA'],
        line=dict(color='#ff9800', width=1.5),
        name='DEA'
    ), row=2, col=1)

    # ─── Row 3: Volume ───
    vol_colors = ['#4caf50' if df['Close'].iloc[i] >= df['Open'].iloc[i]
                  else '#e53935' for i in range(len(df))]

    fig.add_trace(go.Bar(
        x=df.index, y=df['Volume'],
        marker_color=vol_colors,
        name='成交量',
        opacity=0.7
    ), row=3, col=1)

    # Volume SMA
    vol_sma = df['Volume'].rolling(20).mean()
    fig.add_trace(go.Scatter(
        x=df.index, y=vol_sma,
        line=dict(color='#ff9800', width=1),
        name='Vol SMA20',
        opacity=0.6
    ), row=3, col=1)

    # ─── Layout ───
    fig.update_layout(
        height=700,
        paper_bgcolor='#ffffff',
        plot_bgcolor='#ffffff',
        font=dict(family="Noto Sans TC, JetBrains Mono, sans-serif", size=12, color='#2d2d2d'),
        showlegend=False,
        margin=dict(l=50, r=20, t=30, b=20),
        xaxis_rangeslider_visible=False,
    )

    for i in range(1, 4):
        fig.update_xaxes(
            gridcolor='#f0f0e8', showgrid=True,
            zeroline=False, row=i, col=1
        )
        fig.update_yaxes(
            gridcolor='#f0f0e8', showgrid=True,
            zeroline=False, row=i, col=1
        )

    return fig


# ═══════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### ⚙️ 系統設定")

    # Watchlist
    default_tickers = "TSLA,AMZN,AAPL,NVDA,GOOGL,META"
    tickers_input = st.text_input(
        "監控股票（逗號分隔）",
        value=default_tickers,
        help="輸入股票代碼，用逗號分隔"
    )
    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

    # Timeframe
    timeframe = st.selectbox(
        "時間框架",
        options=list(TIMEFRAME_MAP.keys()),
        index=3,  # default 30m
        format_func=lambda x: {"1m":"1分鐘","5m":"5分鐘","15m":"15分鐘","30m":"30分鐘","1h":"1小時","1d":"日線","1wk":"週線"}[x]
    )

    st.markdown("---")

    # Auto refresh
    auto_refresh = st.checkbox("自動掃描刷新", value=False)
    refresh_interval = st.slider(
        "刷新間隔（秒）",
        min_value=30, max_value=500, value=60, step=10,
        disabled=not auto_refresh
    )

    st.markdown("---")

    # Telegram
    st.markdown("### 📱 Telegram 推送")
    enable_telegram = st.checkbox("啟用 Telegram 訊號", value=False)
    tg_bot_token = st.text_input("Bot Token", type="password", disabled=not enable_telegram)
    tg_chat_id = st.text_input("Chat ID", disabled=not enable_telegram)

    st.markdown("---")

    # Voice
    st.markdown("### 🔊 語音播報")
    enable_voice = st.checkbox("啟用語音播報", value=False)
    voice_only_strong = st.checkbox("僅強烈訊號時播報", value=True, disabled=not enable_voice)

    st.markdown("---")

    # EMA Settings
    with st.expander("📐 指標參數"):
        ema_fast_input = st.number_input("EMA 快線", value=EMA_FAST, min_value=3, max_value=50)
        ema_slow_input = st.number_input("EMA 慢線", value=EMA_SLOW, min_value=10, max_value=200)
        macd_sig_input = st.number_input("MACD Signal", value=MACD_SIGNAL, min_value=3, max_value=30)
        sr_min_touches = st.number_input("S/R 最少觸碰次數", value=2, min_value=1, max_value=10)
        sr_tolerance = st.slider("S/R 容差 %", min_value=0.1, max_value=1.0, value=0.3, step=0.1)

    # Scan button
    scan_btn = st.button("🔍 立即掃描", use_container_width=True, type="primary")


# ═══════════════════════════════════════════════════════
# MAIN CONTENT
# ═══════════════════════════════════════════════════════

# Title
st.markdown("""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
    <span style="font-size:28px;font-weight:700;font-family:'Noto Sans TC',sans-serif;">三重確認交易系統</span>
    <span style="font-size:13px;color:#6b6b6b;padding:4px 10px;background:#f0f0e8;border-radius:6px;">
        趨勢 + MACD + 支撐阻力突破
    </span>
</div>
""", unsafe_allow_html=True)

# Initialize session state
if 'last_signals' not in st.session_state:
    st.session_state.last_signals = {}
if 'scan_count' not in st.session_state:
    st.session_state.scan_count = 0
if 'trade_log' not in st.session_state:
    st.session_state.trade_log = []


def run_scan():
    """Main scanning function."""
    st.session_state.scan_count += 1
    tf_config = TIMEFRAME_MAP[timeframe]
    results = {}
    voice_alerts = []

    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, ticker in enumerate(tickers):
        status_text.text(f"掃描中... {ticker} ({idx+1}/{len(tickers)})")
        progress_bar.progress((idx + 1) / len(tickers))

        # Fetch main timeframe data
        df = fetch_data(ticker, tf_config['interval'], tf_config['period'])
        if df.empty or len(df) < 30:
            results[ticker] = None
            continue

        # Calculate indicators
        EMA_FAST_VAL = ema_fast_input if 'ema_fast_input' in dir() else EMA_FAST
        EMA_SLOW_VAL = ema_slow_input if 'ema_slow_input' in dir() else EMA_SLOW

        df['EMA_fast'] = calc_ema(df['Close'], ema_fast_input)
        df['EMA_slow'] = calc_ema(df['Close'], ema_slow_input)
        df['DIF'] = df['EMA_fast'] - df['EMA_slow']
        df['DEA'] = calc_ema(df['DIF'], macd_sig_input)
        df['Histogram'] = df['DIF'] - df['DEA']

        # Fetch higher timeframe for S/R
        sr_df = fetch_data(ticker, tf_config['sr_interval'], tf_config['sr_period'])

        if sr_df.empty or len(sr_df) < 20:
            # Fallback to current timeframe
            sr_df = df

        support, resistance = find_support_resistance(
            sr_df,
            min_touches=sr_min_touches,
            tolerance_pct=sr_tolerance / 100
        )

        # Analyze signals
        signal_info = analyze_signals(df, support, resistance)

        results[ticker] = {
            'df': df,
            'support': support,
            'resistance': resistance,
            'signal': signal_info,
        }

        # Voice alert collection
        if enable_voice and signal_info['signal_type'] in ('strong_buy', 'strong_sell', 'buy', 'sell'):
            if not voice_only_strong or signal_info['signal_type'] in ('strong_buy', 'strong_sell'):
                voice_alerts.append(f"{ticker} {signal_info['signal']}")

        # Telegram alert
        if enable_telegram and tg_bot_token and tg_chat_id:
            if signal_info['signal_type'] in ('strong_buy', 'strong_sell', 'buy', 'sell'):
                prev_signal = st.session_state.last_signals.get(ticker)
                if prev_signal != signal_info['signal_type']:
                    msg = (
                        f"📊 <b>三重確認訊號</b>\n"
                        f"━━━━━━━━━━━━━━\n"
                        f"🏷 {ticker} | {timeframe}\n"
                        f"💰 ${signal_info['price']:.2f}\n"
                        f"📌 {signal_info['signal']}\n"
                        f"━━━━━━━━━━━━━━\n"
                        f"趨勢: {signal_info['trend']}\n"
                        f"MACD: {signal_info['macd_cross']}\n"
                        f"S/R: {signal_info['sr_status']}\n"
                        f"量能: {'放量' if signal_info['vol_surge'] else '正常'} ({signal_info['vol_ratio']:.1f}x)\n"
                        f"強度: {signal_info['strength']}%\n"
                        f"━━━━━━━━━━━━━━\n"
                        f"⏰ {datetime.now().strftime('%H:%M:%S')}"
                    )
                    send_telegram(tg_bot_token, tg_chat_id, msg)

        st.session_state.last_signals[ticker] = signal_info.get('signal_type')

    progress_bar.empty()
    status_text.empty()

    # Voice playback
    if voice_alerts:
        voice_text = "。".join(voice_alerts)
        st.components.v1.html(generate_voice_html(voice_text), height=0)

    return results


# ─── Run scan ───
if scan_btn or auto_refresh:
    results = run_scan()

    if not results:
        st.warning("沒有獲取到數據，請檢查股票代碼")
    else:
        # ─── Signal Overview Dashboard ───
        st.markdown("### 📡 訊號總覽")

        # Summary cards row
        signal_cols = st.columns(len(tickers))
        for i, ticker in enumerate(tickers):
            with signal_cols[i]:
                r = results.get(ticker)
                if r is None:
                    st.markdown(f"""
                    <div class="signal-card hold-signal">
                        <div class="ticker-header">{ticker}</div>
                        <div style="color:var(--text-secondary);font-size:13px;">數據不足</div>
                    </div>
                    """, unsafe_allow_html=True)
                    continue

                sig = r['signal']
                price = sig['price']
                signal_text = sig['signal']
                sig_type = sig['signal_type']

                # Card class
                if sig_type == 'strong_buy':
                    card_class = "signal-card strong-buy"
                    price_color = "#4caf50"
                elif sig_type == 'strong_sell':
                    card_class = "signal-card strong-sell"
                    price_color = "#e53935"
                elif sig_type in ('buy', 'watch_buy'):
                    card_class = "signal-card normal-buy"
                    price_color = "#4caf50"
                elif sig_type in ('sell', 'watch_sell'):
                    card_class = "signal-card normal-sell"
                    price_color = "#e53935"
                else:
                    card_class = "signal-card hold-signal"
                    price_color = "#6b6b6b"

                st.markdown(f"""
                <div class="{card_class}">
                    <div class="ticker-header">{ticker}</div>
                    <div class="price-display" style="color:{price_color};">${price:.2f}</div>
                    <div style="font-size:15px;font-weight:600;margin:6px 0;color:{price_color};">{signal_text}</div>
                    <div style="font-size:12px;color:var(--text-secondary);">
                        強度 {sig['strength']}% | 量能 {sig['vol_ratio']:.1f}x
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")

        # ─── Detailed tabs per ticker ───
        tabs = st.tabs(tickers)

        for tab, ticker in zip(tabs, tickers):
            with tab:
                r = results.get(ticker)
                if r is None:
                    st.info(f"{ticker} 數據不足，無法分析")
                    continue

                df = r['df']
                sig = r['signal']
                support = r['support']
                resistance = r['resistance']

                col_chart, col_info = st.columns([2.5, 1])

                with col_chart:
                    # Main chart
                    chart = create_chart(df, ticker, support, resistance, sig)
                    st.plotly_chart(chart, use_container_width=True, config={'displayModeBar': False})

                with col_info:
                    # ─── Signal Analysis Card ───
                    trend_dot = "dot-green" if sig.get('trend_bullish') else "dot-red"
                    macd_dot = "dot-green" if sig['dif'] > sig['dea'] else "dot-red"
                    hist_dot = "dot-green" if sig['histogram'] > 0 else "dot-red"

                    # S/R status
                    if sig.get('breakout_bullish'):
                        sr_dot = "dot-green"
                        sr_text = f"突破 {sig['closest_resistance']:.2f}"
                    elif sig.get('breakout_bearish'):
                        sr_dot = "dot-red"
                        sr_text = f"跌破 {sig['closest_support']:.2f}"
                    else:
                        sr_dot = "dot-gray"
                        if sig['closest_resistance']:
                            sr_text = f"未突破 {sig['closest_resistance']:.2f}"
                        else:
                            sr_text = "無明確水平"

                    # Support status
                    if sig['closest_support']:
                        sup_text = f"守住 {sig['closest_support']:.2f}"
                        sup_dot = "dot-gray"
                    else:
                        sup_text = "無明確支撐"
                        sup_dot = "dot-gray"

                    st.markdown(f"""
                    <div class="signal-card">
                        <div class="section-title">當前訊號分析</div>
                        <div class="signal-row">
                            <span class="dot {trend_dot}"></span>
                            <span class="label-text">趨勢方向</span>
                            <span class="value-text">{sig['trend']}</span>
                        </div>
                        <div class="signal-row">
                            <span class="dot {macd_dot}"></span>
                            <span class="label-text">MACD位置</span>
                            <span class="value-text">DIF {sig['dif']:.3f} / DEA {sig['dea']:.3f}</span>
                        </div>
                        <div class="signal-row">
                            <span class="dot {hist_dot}"></span>
                            <span class="label-text">柱量動能</span>
                            <span class="value-text">{"正向" if sig['histogram']>0 else "負向"} {sig['histogram']:.3f}</span>
                        </div>
                        <div class="signal-row">
                            <span class="dot {sr_dot}"></span>
                            <span class="label-text">阻力突破</span>
                            <span class="value-text">{sr_text}</span>
                        </div>
                        <div class="signal-row">
                            <span class="dot {sup_dot}"></span>
                            <span class="label-text">支撐跌破</span>
                            <span class="value-text">{sup_text}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Volume info
                    vol_color = "#4caf50" if sig['vol_surge'] else "#6b6b6b"
                    st.markdown(f"""
                    <div class="signal-card">
                        <div class="section-title">成交量分析</div>
                        <div class="signal-row">
                            <span class="dot {"dot-green" if sig["vol_surge"] else "dot-gray"}"></span>
                            <span class="label-text">量比</span>
                            <span class="value-text" style="color:{vol_color};">{sig['vol_ratio']:.2f}x {"🔥 放量" if sig['vol_surge'] else "正常"}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Signal strength
                    sig_color = "#4caf50" if sig['signal_type'] in ('strong_buy','buy','watch_buy') else (
                        "#e53935" if sig['signal_type'] in ('strong_sell','sell','watch_sell') else "#6b6b6b")
                    st.markdown(f"""
                    <div class="signal-card">
                        <div class="section-title">綜合訊號</div>
                        <div style="text-align:center;">
                            <div class="metric-value" style="color:{sig_color};font-size:22px;">{sig['signal']}</div>
                            <div style="margin-top:8px;">
                                <span style="font-family:'JetBrains Mono',monospace;font-size:24px;font-weight:700;color:{sig_color};">{sig['strength']}%</span>
                                <span class="metric-label" style="display:block;">訊號強度</span>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # S/R levels table
                    if support or resistance:
                        st.markdown("""
                        <div class="signal-card">
                            <div class="section-title">關鍵價位</div>
                        """, unsafe_allow_html=True)

                        if resistance:
                            for lvl, strength, touches in resistance[:3]:
                                st.markdown(f"""
                                <div class="trade-record" style="color:#e53935;">
                                    ▲ R {lvl:.2f} ({touches}次觸碰)
                                </div>
                                """, unsafe_allow_html=True)

                        st.markdown(f"""
                        <div class="trade-record" style="color:#2196f3;font-weight:700;">
                            ● 現價 {sig['price']:.2f}
                        </div>
                        """, unsafe_allow_html=True)

                        if support:
                            for lvl, strength, touches in support[:3]:
                                st.markdown(f"""
                                <div class="trade-record" style="color:#4caf50;">
                                    ▼ S {lvl:.2f} ({touches}次觸碰)
                                </div>
                                """, unsafe_allow_html=True)

                        st.markdown("</div>", unsafe_allow_html=True)

        # ─── Scan info footer ───
        st.markdown(f"""
        <div style="text-align:center;color:var(--text-secondary);font-size:12px;padding:16px 0;border-top:1px solid var(--border);margin-top:20px;">
            掃描次數: {st.session_state.scan_count} | 時間框架: {timeframe} |
            最後更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
            {'🔄 自動刷新 ' + str(refresh_interval) + '秒' if auto_refresh else '手動模式'}
        </div>
        """, unsafe_allow_html=True)

    # Auto-refresh logic
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()

else:
    # Landing state
    st.markdown("""
    <div style="text-align:center;padding:60px 20px;">
        <div style="font-size:48px;margin-bottom:16px;">📊</div>
        <div style="font-size:20px;font-weight:600;margin-bottom:8px;">三重確認交易系統</div>
        <div style="color:#6b6b6b;font-size:14px;max-width:500px;margin:0 auto;">
            趨勢確認 + MACD觸發 + 支撐阻力突破<br>
            三重確認才開倉，缺一不可<br><br>
            點擊左側「🔍 立即掃描」或啟用自動掃描開始監控
        </div>
    </div>
    """, unsafe_allow_html=True)
