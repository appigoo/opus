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


def calc_atr(df, period=14):
    """Average True Range for stop-loss calculation."""
    high = df['High']
    low = df['Low']
    close = df['Close']
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def check_multi_ema_array(df):
    """
    [Improvement #2] Multi-EMA alignment check.
    Returns: ('bullish_strong'|'bullish'|'neutral'|'bearish'|'bearish_strong', detail)
    """
    if len(df) < 60:
        return 'neutral', "數據不足"

    close = df['Close']
    ema5 = close.ewm(span=5, adjust=False).mean().iloc[-1]
    ema10 = close.ewm(span=10, adjust=False).mean().iloc[-1]
    ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
    ema60 = close.ewm(span=60, adjust=False).mean().iloc[-1]

    # Perfect bullish array: EMA5 > EMA10 > EMA20 > EMA60
    if ema5 > ema10 > ema20 > ema60:
        return 'bullish_strong', f"多頭排列 5>{ema5:.2f} 10>{ema10:.2f} 20>{ema20:.2f} 60>{ema60:.2f}"
    # Bullish: mostly aligned up
    if ema5 > ema20 and ema10 > ema20:
        return 'bullish', "偏多"
    # Perfect bearish array
    if ema5 < ema10 < ema20 < ema60:
        return 'bearish_strong', "空頭排列"
    if ema5 < ema20 and ema10 < ema20:
        return 'bearish', "偏空"
    return 'neutral', "混亂"


def check_macd_momentum(df, lookback=3):
    """
    [Improvement #1 & #3] MACD momentum grading.
    Detects histogram contraction even before a full cross.
    Returns: dict with momentum_state + score adjustment
    """
    if len(df) < lookback + 2:
        return {'state': 'unknown', 'score': 0, 'desc': '數據不足'}

    hist = df['Histogram'].iloc[-(lookback+1):].values
    latest = hist[-1]

    # Bullish momentum scenarios
    if latest > 0 and all(hist[i] >= hist[i-1] for i in range(1, len(hist))):
        return {'state': 'bull_accelerate', 'score': 1.5, 'desc': '多頭加速'}

    # Histogram negative but contracting (getting closer to 0) = momentum weakening bearish
    if latest < 0 and all(hist[i] > hist[i-1] for i in range(1, len(hist))):
        # abs value shrinking over lookback bars
        return {'state': 'bull_pending', 'score': 1.0, 'desc': '負值收縮中→多頭蓄勢'}

    # Bearish momentum
    if latest < 0 and all(hist[i] <= hist[i-1] for i in range(1, len(hist))):
        return {'state': 'bear_accelerate', 'score': -1.5, 'desc': '空頭加速'}

    if latest > 0 and all(hist[i] < hist[i-1] for i in range(1, len(hist))):
        return {'state': 'bear_pending', 'score': -1.0, 'desc': '正值收縮中→空頭蓄勢'}

    return {'state': 'neutral', 'score': 0, 'desc': '動能中性'}


def validate_breakout(df, level, direction='up', confirm_bars=2, vol_threshold=1.2):
    """
    [Improvement #4 & #5] Breakout validation + fake breakout filter.
    - Closing bar(s) must be above (below for bearish) level
    - Volume confirmation
    - Check if price retraced back within last 3 bars (= fake breakout)
    """
    if len(df) < confirm_bars + 3:
        return {'valid': False, 'reason': '數據不足', 'is_fake': False}

    recent = df.tail(5)
    closes = recent['Close'].values
    vol_sma = df['Volume'].rolling(20).mean().iloc[-1]
    recent_vol = recent['Volume'].values
    price = closes[-1]

    if direction == 'up':
        # Must close above level on latest bar
        if price <= level:
            return {'valid': False, 'reason': '未突破', 'is_fake': False}

        # Count confirm bars above level
        bars_above = sum(1 for c in closes[-confirm_bars:] if c > level)
        if bars_above < confirm_bars:
            # Single bar breakout — weak
            return {'valid': True, 'reason': '初次突破(未確認)', 'is_fake': False, 'strength': 'weak'}

        # Volume check at breakout bar
        # Find the breakout bar (first close above level in last 5)
        breakout_idx = None
        for i in range(len(closes)):
            if closes[i] > level and (i == 0 or closes[i-1] <= level):
                breakout_idx = i
                break

        vol_ok = True
        if breakout_idx is not None:
            vol_at_breakout = recent_vol[breakout_idx]
            vol_ok = vol_at_breakout >= vol_sma * vol_threshold

        # Fake breakout check: did price close back below level after breaking out?
        is_fake = False
        if breakout_idx is not None and breakout_idx < len(closes) - 1:
            post_bars = closes[breakout_idx+1:]
            if any(c < level for c in post_bars):
                is_fake = True

        if is_fake:
            return {'valid': False, 'reason': '假突破(回落)', 'is_fake': True}
        if not vol_ok:
            return {'valid': True, 'reason': '突破(量能不足)', 'is_fake': False, 'strength': 'medium'}

        return {'valid': True, 'reason': '有效突破', 'is_fake': False, 'strength': 'strong'}

    else:  # direction == 'down'
        if price >= level:
            return {'valid': False, 'reason': '未跌破', 'is_fake': False}

        bars_below = sum(1 for c in closes[-confirm_bars:] if c < level)
        if bars_below < confirm_bars:
            return {'valid': True, 'reason': '初次跌破(未確認)', 'is_fake': False, 'strength': 'weak'}

        breakout_idx = None
        for i in range(len(closes)):
            if closes[i] < level and (i == 0 or closes[i-1] >= level):
                breakout_idx = i
                break

        vol_ok = True
        if breakout_idx is not None:
            vol_ok = recent_vol[breakout_idx] >= vol_sma * vol_threshold

        is_fake = False
        if breakout_idx is not None and breakout_idx < len(closes) - 1:
            post_bars = closes[breakout_idx+1:]
            if any(c > level for c in post_bars):
                is_fake = True

        if is_fake:
            return {'valid': False, 'reason': '假跌破(回升)', 'is_fake': True}
        if not vol_ok:
            return {'valid': True, 'reason': '跌破(量能不足)', 'is_fake': False, 'strength': 'medium'}

        return {'valid': True, 'reason': '有效跌破', 'is_fake': False, 'strength': 'strong'}


def generate_trade_plan(price, signal_type, support_levels, resistance_levels, atr, confidence="MEDIUM"):
    """
    [Improvement #7] Generate complete trade plan.
    Position sizing now uses confidence tier (HIGH/MEDIUM/LOW).
    """
    plan = {
        'entry': price,
        'stop_loss': None,
        'tp1': None,
        'tp2': None,
        'risk_reward': None,
        'position_size_pct': 0,
        'notes': '',
    }

    if atr is None or np.isnan(atr):
        atr = price * 0.01  # fallback 1%

    # Size map: HIGH conf = full size, MEDIUM = 60%, LOW = 30%
    size_by_conf = {"HIGH": 100, "MEDIUM": 60, "LOW": 30, "NONE": 0}

    if signal_type in ('strong_buy', 'buy'):
        if support_levels:
            sup = support_levels[0][0]
            sl_by_sr = sup * 0.995
        else:
            sl_by_sr = price - 1.5 * atr
        sl_by_atr = price - 1.5 * atr
        plan['stop_loss'] = max(sl_by_sr, sl_by_atr)

        if resistance_levels:
            plan['tp1'] = resistance_levels[0][0]
            if len(resistance_levels) > 1:
                plan['tp2'] = resistance_levels[1][0]
            else:
                plan['tp2'] = price + (plan['tp1'] - price) * 1.618
        else:
            plan['tp1'] = price + 2 * atr
            plan['tp2'] = price + 3.5 * atr

        risk = price - plan['stop_loss']
        reward1 = plan['tp1'] - price
        if risk > 0:
            plan['risk_reward'] = reward1 / risk

        # Strong_buy gets 100% regardless; otherwise use confidence
        if signal_type == 'strong_buy':
            plan['position_size_pct'] = 100
        else:
            plan['position_size_pct'] = size_by_conf.get(confidence, 60)
        plan['notes'] = f"進場 ${price:.2f} | 止損 ${plan['stop_loss']:.2f} (-{(1-plan['stop_loss']/price)*100:.2f}%) | TP1 ${plan['tp1']:.2f} | TP2 ${plan['tp2']:.2f}"

    elif signal_type in ('strong_sell', 'sell'):
        if resistance_levels:
            res = resistance_levels[0][0]
            sl_by_sr = res * 1.005
        else:
            sl_by_sr = price + 1.5 * atr
        sl_by_atr = price + 1.5 * atr
        plan['stop_loss'] = min(sl_by_sr, sl_by_atr)

        if support_levels:
            plan['tp1'] = support_levels[0][0]
            if len(support_levels) > 1:
                plan['tp2'] = support_levels[1][0]
            else:
                plan['tp2'] = price - (price - plan['tp1']) * 1.618
        else:
            plan['tp1'] = price - 2 * atr
            plan['tp2'] = price - 3.5 * atr

        risk = plan['stop_loss'] - price
        reward1 = price - plan['tp1']
        if risk > 0:
            plan['risk_reward'] = reward1 / risk

        if signal_type == 'strong_sell':
            plan['position_size_pct'] = 100
        else:
            plan['position_size_pct'] = size_by_conf.get(confidence, 60)
        plan['notes'] = f"做空 ${price:.2f} | 止損 ${plan['stop_loss']:.2f} (+{(plan['stop_loss']/price-1)*100:.2f}%) | TP1 ${plan['tp1']:.2f} | TP2 ${plan['tp2']:.2f}"

    return plan


def analyze_signals(df, support_levels, resistance_levels):
    """
    Upgraded Triple Confirmation Logic v2 — incorporating 7 improvements:
    1. MACD momentum grading (not just golden/death cross)
    2. Multi-EMA array confirmation (5>10>20>60)
    3. Histogram contraction detection
    4. Breakout validity check (bars + volume)
    5. Fake breakout filter
    6. MTF resonance placeholder (filled by caller)
    7. Trade plan generation
    """
    if df.empty or len(df) < 30:
        return {
            'signal': '數據不足', 'signal_type': 'hold', 'trend': '未知',
            'macd_cross': '未知', 'histogram_momentum': 0, 'sr_status': '未知',
            'strength': 0, 'details': {}, 'trade_plan': None,
        }

    latest = df.iloc[-1]
    prev = df.iloc[-2]
    price = latest['Close']

    # ─── 1. Trend (EMA 12/26 — original) ───
    ema_fast = latest['EMA_fast']
    ema_slow = latest['EMA_slow']
    trend_bullish = ema_fast > ema_slow
    trend = "上升趨勢" if trend_bullish else "下降趨勢"
    trend_strength = abs(ema_fast - ema_slow) / price * 100

    # ─── [IMPROVEMENT #2] Multi-EMA array ───
    ema_array_state, ema_array_desc = check_multi_ema_array(df)

    # ─── 2. MACD (classic + momentum grading) ───
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

    # [IMPROVEMENT #1 & #3] MACD momentum grading
    macd_momentum = check_macd_momentum(df, lookback=3)

    if golden_cross:
        macd_cross = "金叉 ✦"
    elif death_cross:
        macd_cross = "死叉 ✦"
    elif macd_bullish:
        macd_cross = "DIF > DEA"
    else:
        macd_cross = "DIF < DEA"

    # ─── 3. Support/Resistance with validation ───
    closest_resistance = resistance_levels[0][0] if resistance_levels else None
    closest_support = support_levels[0][0] if support_levels else None

    # [IMPROVEMENT #4 & #5] Validate breakout
    breakout_bullish = False
    breakout_bearish = False
    breakout_quality = 'none'
    is_fake_breakout = False
    sr_status = "無突破"

    if closest_resistance and price > closest_resistance:
        val = validate_breakout(df, closest_resistance, direction='up')
        if val['valid']:
            breakout_bullish = True
            breakout_quality = val.get('strength', 'medium')
            sr_status = f"突破阻力 {closest_resistance:.2f} ({val['reason']})"
        elif val['is_fake']:
            is_fake_breakout = True
            sr_status = f"假突破 {closest_resistance:.2f} ⚠️"

    if closest_support and price < closest_support:
        val = validate_breakout(df, closest_support, direction='down')
        if val['valid']:
            breakout_bearish = True
            breakout_quality = val.get('strength', 'medium')
            sr_status = f"跌破支撐 {closest_support:.2f} ({val['reason']})"
        elif val['is_fake']:
            is_fake_breakout = True
            sr_status = f"假跌破 {closest_support:.2f} ⚠️"

    if not breakout_bullish and not breakout_bearish and not is_fake_breakout:
        if closest_resistance:
            dist_r = abs(price - closest_resistance) / price * 100
            if dist_r < 0.5:
                sr_status = f"接近阻力 {closest_resistance:.2f}"
        if closest_support:
            dist_s = abs(price - closest_support) / price * 100
            if dist_s < 0.5:
                sr_status = f"接近支撐 {closest_support:.2f}"

    # ─── Volume ───
    vol_sma = df['Volume'].rolling(20).mean().iloc[-1]
    vol_current = latest['Volume']
    vol_ratio = vol_current / vol_sma if vol_sma > 0 else 1
    vol_surge = vol_ratio > 1.5

    # ─── ATR for trade plan ───
    atr_series = calc_atr(df, 14)
    atr_val = atr_series.iloc[-1] if not atr_series.empty else price * 0.01

    # ═══ UPGRADED SIGNAL LOGIC ═══
    buy_score = 0
    sell_score = 0

    # Classic trend
    if trend_bullish:
        buy_score += 1
    else:
        sell_score += 1

    # [IMPROVEMENT #2] Multi-EMA weight
    if ema_array_state == 'bullish_strong':
        buy_score += 1.5
    elif ema_array_state == 'bullish':
        buy_score += 0.7
    elif ema_array_state == 'bearish_strong':
        sell_score += 1.5
    elif ema_array_state == 'bearish':
        sell_score += 0.7

    # Classic MACD cross
    if golden_cross:
        buy_score += 1.5
    elif macd_bullish:
        buy_score += 0.7
    if death_cross:
        sell_score += 1.5
    elif macd_bearish:
        sell_score += 0.7

    # [IMPROVEMENT #1 & #3] MACD momentum additions
    if macd_momentum['score'] > 0:
        buy_score += macd_momentum['score']
    elif macd_momentum['score'] < 0:
        sell_score += abs(macd_momentum['score'])

    # [IMPROVEMENT #4] Breakout quality weighting
    if breakout_bullish:
        if breakout_quality == 'strong':
            buy_score += 2.0
        elif breakout_quality == 'medium':
            buy_score += 1.2
        else:
            buy_score += 0.6
    if breakout_bearish:
        if breakout_quality == 'strong':
            sell_score += 2.0
        elif breakout_quality == 'medium':
            sell_score += 1.2
        else:
            sell_score += 0.6

    # [IMPROVEMENT #5] Fake breakout penalty
    if is_fake_breakout:
        buy_score -= 1.5
        sell_score -= 1.5

    # Volume boost
    if vol_surge:
        if buy_score > sell_score:
            buy_score += 0.8
        else:
            sell_score += 0.8

    # ─── Signal classification ───
    # Thresholds tuned for new scoring system
    signal_type = "hold"
    signal = "觀望"
    strength = 0

    net_score = buy_score - sell_score

    # ═══ DIRECT ACTION CLASSIFICATION ═══
    # Three explicit commands: 做多 / 做空 / 不動 (with confidence tier)
    # Lowered thresholds — user wants decisive calls, not cautious "watch" labels

    signal_type = "hold"
    signal = "不動"
    action = "HOLD"
    confidence = "LOW"
    strength = 0
    entry_trigger = ""  # concrete next-candle trigger

    # ─── BUY SIDE ───
    if buy_score >= 4.0 and net_score >= 2.0:
        # Decisive long
        if (breakout_bullish and breakout_quality == 'strong') or buy_score >= 5.5:
            signal = "強烈做多 🔥"
            action = "STRONG_BUY"
            confidence = "HIGH"
            signal_type = "strong_buy"
        else:
            signal = "做多"
            action = "BUY"
            confidence = "HIGH"
            signal_type = "buy"
        strength = min(100, int(buy_score * 14))
        entry_trigger = f"立即進場 ${price:.2f}"

    elif buy_score >= 2.5 and net_score >= 1.0:
        # Moderate long — still give a BUY command, not "watch"
        signal = "做多"
        action = "BUY"
        confidence = "MEDIUM"
        signal_type = "buy"
        strength = min(85, int(buy_score * 16))
        # Give concrete entry trigger
        if closest_support and price > closest_support:
            entry_trigger = f"立即進場 ${price:.2f}，或回測 ${closest_support:.2f} 加碼"
        elif closest_resistance:
            entry_trigger = f"立即進場 ${price:.2f}，突破 ${closest_resistance:.2f} 加碼"
        else:
            entry_trigger = f"立即進場 ${price:.2f}"

    # ─── SELL SIDE ───
    elif sell_score >= 4.0 and net_score <= -2.0:
        if (breakout_bearish and breakout_quality == 'strong') or sell_score >= 5.5:
            signal = "強烈做空 🔥"
            action = "STRONG_SELL"
            confidence = "HIGH"
            signal_type = "strong_sell"
        else:
            signal = "做空"
            action = "SELL"
            confidence = "HIGH"
            signal_type = "sell"
        strength = min(100, int(sell_score * 14))
        entry_trigger = f"立即進場 ${price:.2f}"

    elif sell_score >= 2.5 and net_score <= -1.0:
        signal = "做空"
        action = "SELL"
        confidence = "MEDIUM"
        signal_type = "sell"
        strength = min(85, int(sell_score * 16))
        if closest_resistance and price < closest_resistance:
            entry_trigger = f"立即做空 ${price:.2f}，或反彈至 ${closest_resistance:.2f} 加碼"
        else:
            entry_trigger = f"立即做空 ${price:.2f}"

    # ─── EDGE CASES: CONFLICTING SIGNALS → STILL GIVE DIRECTION ───
    elif abs(net_score) >= 0.5:
        # Mild directional bias — give a LOW confidence call, still actionable
        if net_score > 0:
            signal = "做多"
            action = "BUY"
            confidence = "LOW"
            signal_type = "buy"
            strength = max(25, int(buy_score * 12))
            # For low confidence, suggest waiting for trigger
            if closest_resistance:
                entry_trigger = f"等突破 ${closest_resistance:.2f} 進場（小倉位）"
            elif macd_momentum.get('state') == 'bull_pending':
                entry_trigger = f"等 MACD 金叉確認後進場"
            else:
                entry_trigger = f"小倉位試單 ${price:.2f}，止損收緊"
        else:
            signal = "做空"
            action = "SELL"
            confidence = "LOW"
            signal_type = "sell"
            strength = max(25, int(sell_score * 12))
            if closest_support:
                entry_trigger = f"等跌破 ${closest_support:.2f} 進場（小倉位）"
            elif macd_momentum.get('state') == 'bear_pending':
                entry_trigger = f"等 MACD 死叉確認後進場"
            else:
                entry_trigger = f"小倉位試空 ${price:.2f}，止損收緊"
    else:
        # Truly no signal — explicit "不動" with reason
        signal = "不動"
        action = "HOLD"
        confidence = "NONE"
        signal_type = "hold"
        strength = 0
        entry_trigger = "無明確方向，等待指標共振"

    # Reformat signal text to always include confidence tier
    if action in ("BUY", "STRONG_BUY"):
        display_signal = f"{signal} · {confidence}信心"
    elif action in ("SELL", "STRONG_SELL"):
        display_signal = f"{signal} · {confidence}信心"
    else:
        display_signal = signal

    signal = display_signal

    # [IMPROVEMENT #7] Generate trade plan
    trade_plan = generate_trade_plan(price, signal_type, support_levels, resistance_levels, atr_val, confidence)

    return {
        'signal': signal,
        'signal_type': signal_type,
        'trend': trend,
        'trend_bullish': trend_bullish,
        'trend_strength': trend_strength,
        'ema_array_state': ema_array_state,
        'ema_array_desc': ema_array_desc,
        'macd_cross': macd_cross,
        'macd_momentum': macd_momentum,
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
        'breakout_quality': breakout_quality,
        'is_fake_breakout': is_fake_breakout,
        'closest_support': closest_support,
        'closest_resistance': closest_resistance,
        'vol_ratio': vol_ratio,
        'vol_surge': vol_surge,
        'strength': strength,
        'buy_score': round(buy_score, 2),
        'sell_score': round(sell_score, 2),
        'net_score': round(net_score, 2),
        'action': action,
        'confidence': confidence,
        'entry_trigger': entry_trigger,
        'price': price,
        'ema_fast': ema_fast,
        'ema_slow': ema_slow,
        'atr': atr_val,
        'trade_plan': trade_plan,
        'mtf_resonance': None,  # filled by scan loop
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

def create_chart(df, ticker, support_levels, resistance_levels, signal_info, timeframe_key="1h"):
    """
    Create chart matching the screenshot style.
    Uses sequential integer x-axis to eliminate non-trading time gaps.
    """

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.55, 0.25, 0.20],
        subplot_titles=["K線 + 趨勢 + 支撐阻力", "MACD / DIF / DEA / Histogram", "成交量"]
    )

    # ── Sequential x-axis (removes non-trading gaps) ──
    x_seq = list(range(len(df)))
    timestamps = df.index.tolist()

    # Build tick labels: show date/time at sensible intervals
    n = len(df)
    if n <= 60:
        tick_step = max(1, n // 10)
    elif n <= 200:
        tick_step = max(1, n // 12)
    else:
        tick_step = max(1, n // 15)

    tickvals = list(range(0, n, tick_step))
    # Format based on timeframe
    intraday = timeframe_key in ("1m", "5m", "15m", "30m", "1h")
    ticktext = []
    prev_date = None
    for i in tickvals:
        ts = timestamps[i]
        if hasattr(ts, 'strftime'):
            if intraday:
                d = ts.strftime('%b %d')
                t = ts.strftime('%H:%M')
                if d != prev_date:
                    ticktext.append(f"{d}\n{t}")
                    prev_date = d
                else:
                    ticktext.append(t)
            else:
                ticktext.append(ts.strftime('%b %d\n%Y'))
        else:
            ticktext.append(str(i))

    # ─── Row 1: Candlestick + EMA + S/R ───
    fig.add_trace(go.Candlestick(
        x=x_seq,
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
        x=x_seq, y=df['EMA_fast'],
        line=dict(color='#2196f3', width=1.5),
        name=f'EMA{EMA_FAST}',
        opacity=0.8
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=x_seq, y=df['EMA_slow'],
        line=dict(color='#ff9800', width=1.5),
        name=f'EMA{EMA_SLOW}',
        opacity=0.8
    ), row=1, col=1)

    # Bollinger Bands
    bb_mid = df['Close'].rolling(20).mean()
    bb_std = df['Close'].rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std

    fig.add_trace(go.Scatter(
        x=x_seq, y=bb_upper,
        line=dict(color='#e53935', width=1, dash='dash'),
        name='BB Upper',
        opacity=0.4
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=x_seq, y=bb_lower,
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
        x=x_seq, y=df['Histogram'],
        marker_color=colors,
        name='Histogram',
        opacity=0.7
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=x_seq, y=df['DIF'],
        line=dict(color='#2196f3', width=1.5),
        name='DIF'
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=x_seq, y=df['DEA'],
        line=dict(color='#ff9800', width=1.5),
        name='DEA'
    ), row=2, col=1)

    # ─── Row 3: Volume ───
    vol_colors = ['#4caf50' if df['Close'].iloc[i] >= df['Open'].iloc[i]
                  else '#e53935' for i in range(len(df))]

    fig.add_trace(go.Bar(
        x=x_seq, y=df['Volume'],
        marker_color=vol_colors,
        name='成交量',
        opacity=0.7
    ), row=3, col=1)

    # Volume SMA
    vol_sma = df['Volume'].rolling(20).mean()
    fig.add_trace(go.Scatter(
        x=x_seq, y=vol_sma,
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
        margin=dict(l=50, r=20, t=30, b=30),
        xaxis_rangeslider_visible=False,
    )

    # Apply sequential tick labels to all x-axes
    for i in range(1, 4):
        fig.update_xaxes(
            gridcolor='#f0f0e8', showgrid=True,
            zeroline=False,
            tickvals=tickvals,
            ticktext=ticktext if i == 3 else [''] * len(tickvals),  # only show labels on bottom
            row=i, col=1
        )
        fig.update_yaxes(
            gridcolor='#f0f0e8', showgrid=True,
            zeroline=False, row=i, col=1
        )

    # Show tick labels on bottom chart only
    fig.update_xaxes(
        tickvals=tickvals,
        ticktext=ticktext,
        tickangle=0,
        tickfont=dict(size=10),
        row=3, col=1
    )

    # Hover: show actual timestamp
    fig.update_layout(
        hovermode='x unified',
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

        # ─── [IMPROVEMENT #6] Multi-Timeframe Resonance ───
        # Check the timeframe above and below current for directional agreement
        tf_order = ["1m", "5m", "15m", "30m", "1h", "1d", "1wk"]
        current_idx = tf_order.index(timeframe) if timeframe in tf_order else 3
        mtf_checks = []
        resonance_score = 0

        neighbor_tfs = []
        if current_idx > 0:
            neighbor_tfs.append(tf_order[current_idx - 1])  # lower TF
        if current_idx < len(tf_order) - 1:
            neighbor_tfs.append(tf_order[current_idx + 1])  # higher TF

        current_bullish = signal_info['signal_type'] in ('strong_buy', 'buy', 'watch_buy')
        current_bearish = signal_info['signal_type'] in ('strong_sell', 'sell', 'watch_sell')

        for ntf in neighbor_tfs:
            n_cfg = TIMEFRAME_MAP[ntf]
            n_df = fetch_data(ticker, n_cfg['interval'], n_cfg['period'])
            if n_df.empty or len(n_df) < 30:
                mtf_checks.append({'tf': ntf, 'agree': False, 'reason': '數據不足'})
                continue
            n_df['EMA_fast'] = calc_ema(n_df['Close'], ema_fast_input)
            n_df['EMA_slow'] = calc_ema(n_df['Close'], ema_slow_input)
            n_trend_bull = n_df['EMA_fast'].iloc[-1] > n_df['EMA_slow'].iloc[-1]

            if current_bullish and n_trend_bull:
                mtf_checks.append({'tf': ntf, 'agree': True, 'reason': '多頭一致'})
                resonance_score += 1
            elif current_bearish and not n_trend_bull:
                mtf_checks.append({'tf': ntf, 'agree': True, 'reason': '空頭一致'})
                resonance_score += 1
            else:
                mtf_checks.append({'tf': ntf, 'agree': False, 'reason': '方向分歧'})

        # Apply resonance bonus: +20% strength if all neighbors agree
        if len(mtf_checks) > 0 and all(c['agree'] for c in mtf_checks):
            signal_info['strength'] = min(100, int(signal_info['strength'] * 1.2))
            signal_info['mtf_resonance'] = {'state': 'strong', 'checks': mtf_checks, 'bonus': 20}
        elif resonance_score > 0:
            signal_info['mtf_resonance'] = {'state': 'partial', 'checks': mtf_checks, 'bonus': 0}
        else:
            signal_info['mtf_resonance'] = {'state': 'none', 'checks': mtf_checks, 'bonus': 0}

        results[ticker] = {
            'df': df,
            'support': support,
            'resistance': resistance,
            'signal': signal_info,
        }

        # Voice alert — direct command only
        if enable_voice and signal_info['signal_type'] in ('strong_buy', 'strong_sell', 'buy', 'sell'):
            if not voice_only_strong or signal_info['signal_type'] in ('strong_buy', 'strong_sell'):
                act = signal_info.get('action', 'HOLD')
                conf = signal_info.get('confidence', 'NONE')
                act_word = {"STRONG_BUY":"立即做多","BUY":"做多","STRONG_SELL":"立即做空","SELL":"做空"}.get(act, "")
                conf_word = {"HIGH":"高信心","MEDIUM":"中信心","LOW":"低信心"}.get(conf, "")
                voice_alerts.append(f"{ticker} {act_word} {conf_word}")

        # Telegram alert — direct action command format
        if enable_telegram and tg_bot_token and tg_chat_id:
            if signal_info['signal_type'] in ('strong_buy', 'strong_sell', 'buy', 'sell'):
                prev_signal = st.session_state.last_signals.get(ticker)
                if prev_signal != signal_info['signal_type']:
                    tp = signal_info.get('trade_plan') or {}
                    reso = signal_info.get('mtf_resonance') or {}
                    reso_txt = {"strong":"✅ 共振","partial":"⚠️ 部分","none":"❌ 分歧"}.get(reso.get('state','none'), '—')
                    ema_arr_txt = signal_info.get('ema_array_desc', '—')
                    mom_txt = signal_info.get('macd_momentum', {}).get('desc', '—')
                    action_cmd = signal_info.get('action', 'HOLD')
                    conf = signal_info.get('confidence', 'NONE')
                    trigger = signal_info.get('entry_trigger', '')

                    # Direct action line — MOST IMPORTANT
                    if action_cmd == "STRONG_BUY":
                        action_line = "🔥🟢 <b>立即做多 LONG</b>"
                    elif action_cmd == "BUY":
                        action_line = "🟢 <b>做多 LONG</b>"
                    elif action_cmd == "STRONG_SELL":
                        action_line = "🔥🔴 <b>立即做空 SHORT</b>"
                    elif action_cmd == "SELL":
                        action_line = "🔴 <b>做空 SHORT</b>"
                    else:
                        action_line = "⚪ 不動 HOLD"

                    conf_label = {"HIGH":"高信心","MEDIUM":"中信心","LOW":"低信心","NONE":"無訊號"}.get(conf, "—")

                    msg_lines = [
                        action_line,
                        f"━━━━━━━━━━━━━━",
                        f"🏷 <b>{ticker}</b> @ ${signal_info['price']:.2f} | {timeframe}",
                        f"💪 {conf_label} · 強度 {signal_info['strength']}%",
                        f"📌 {trigger}",
                    ]
                    if tp.get('stop_loss'):
                        msg_lines += [
                            f"━━━━━━━━━━━━━━",
                            f"<b>📋 交易計劃</b>",
                            f"🎯 進場: ${tp['entry']:.2f}",
                            f"🛑 止損: ${tp['stop_loss']:.2f}",
                            f"✅ TP1: ${tp['tp1']:.2f}",
                            f"🚀 TP2: ${tp['tp2']:.2f}",
                            f"⚖️ R:R = 1:{tp['risk_reward']:.2f}" if tp.get('risk_reward') else "",
                            f"📏 建議倉位: {tp['position_size_pct']}%",
                        ]
                    msg_lines += [
                        f"━━━━━━━━━━━━━━",
                        f"<i>依據: {ema_arr_txt} · MACD {signal_info['macd_cross']} · {mom_txt} · {signal_info['sr_status']} · 量{signal_info['vol_ratio']:.1f}x · MTF {reso_txt}</i>",
                        f"⏰ {datetime.now().strftime('%H:%M:%S')}",
                    ]
                    msg = "\n".join([l for l in msg_lines if l])
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
                action = sig.get('action', 'HOLD')
                confidence = sig.get('confidence', 'NONE')

                # Card class
                if sig_type == 'strong_buy':
                    card_class = "signal-card strong-buy"
                    price_color = "#4caf50"
                    action_text = "🔥 立即做多"
                    action_color = "#4caf50"
                elif sig_type == 'strong_sell':
                    card_class = "signal-card strong-sell"
                    price_color = "#e53935"
                    action_text = "🔥 立即做空"
                    action_color = "#e53935"
                elif sig_type == 'buy':
                    card_class = "signal-card normal-buy"
                    price_color = "#4caf50"
                    action_text = "▲ 做多"
                    action_color = "#4caf50"
                elif sig_type == 'sell':
                    card_class = "signal-card normal-sell"
                    price_color = "#e53935"
                    action_text = "▼ 做空"
                    action_color = "#e53935"
                else:
                    card_class = "signal-card hold-signal"
                    price_color = "#6b6b6b"
                    action_text = "● 不動"
                    action_color = "#6b6b6b"

                # Confidence badge
                conf_badge_color = {"HIGH": "#4caf50", "MEDIUM": "#ff9800", "LOW": "#9e9e9e", "NONE": "#cccccc"}.get(confidence, "#ccc")
                conf_label = {"HIGH": "高", "MEDIUM": "中", "LOW": "低", "NONE": "—"}.get(confidence, "—")

                st.markdown(f"""
                <div class="{card_class}">
                    <div class="ticker-header">{ticker}</div>
                    <div class="price-display" style="color:{price_color};">${price:.2f}</div>
                    <div style="font-size:20px;font-weight:800;margin:8px 0;color:{action_color};letter-spacing:1px;">
                        {action_text}
                    </div>
                    <div style="display:flex;gap:6px;justify-content:center;margin-bottom:6px;">
                        <span style="background:{conf_badge_color};color:white;padding:2px 10px;border-radius:10px;font-size:11px;font-weight:700;">
                            {conf_label}信心
                        </span>
                        <span style="background:#e8e8e0;color:#333;padding:2px 10px;border-radius:10px;font-size:11px;font-weight:600;">
                            {sig['strength']}%
                        </span>
                    </div>
                    <div style="font-size:11px;color:var(--text-secondary);">
                        量能 {sig['vol_ratio']:.1f}x
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

                # ═══ ACTION COMMAND BANNER (top of tab) ═══
                action = sig.get('action', 'HOLD')
                confidence = sig.get('confidence', 'NONE')
                entry_trigger = sig.get('entry_trigger', '')
                tp = sig.get('trade_plan') or {}

                if action in ("STRONG_BUY", "BUY"):
                    banner_bg = "linear-gradient(90deg, #4caf50 0%, #66bb6a 100%)"
                    big_text = "做多 LONG"
                    arrow = "▲"
                elif action in ("STRONG_SELL", "SELL"):
                    banner_bg = "linear-gradient(90deg, #e53935 0%, #ef5350 100%)"
                    big_text = "做空 SHORT"
                    arrow = "▼"
                else:
                    banner_bg = "linear-gradient(90deg, #9e9e9e 0%, #bdbdbd 100%)"
                    big_text = "不動 HOLD"
                    arrow = "●"

                conf_pill = {"HIGH": "高信心", "MEDIUM": "中信心", "LOW": "低信心", "NONE": "無訊號"}.get(confidence, "—")
                fire = " 🔥" if action in ("STRONG_BUY", "STRONG_SELL") else ""

                # Build action banner
                sl_txt = f"止損 ${tp['stop_loss']:.2f}" if tp.get('stop_loss') else ""
                tp1_txt = f"TP1 ${tp['tp1']:.2f}" if tp.get('tp1') else ""
                tp2_txt = f"TP2 ${tp['tp2']:.2f}" if tp.get('tp2') else ""
                rr_txt = f"R:R 1:{tp['risk_reward']:.2f}" if tp.get('risk_reward') else ""
                pos_txt = f"倉位 {tp['position_size_pct']}%" if tp.get('position_size_pct') else ""

                levels_line = " · ".join([x for x in [sl_txt, tp1_txt, tp2_txt, rr_txt, pos_txt] if x])

                st.markdown(f"""
                <div style="background:{banner_bg};color:white;padding:18px 24px;border-radius:14px;margin-bottom:14px;box-shadow:0 2px 8px rgba(0,0,0,0.12);">
                    <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;">
                        <div style="font-size:36px;font-weight:900;letter-spacing:2px;">
                            {arrow} {big_text}{fire}
                        </div>
                        <div style="background:rgba(255,255,255,0.25);padding:4px 12px;border-radius:8px;font-size:13px;font-weight:700;">
                            {conf_pill} · 強度 {sig['strength']}%
                        </div>
                    </div>
                    <div style="font-size:15px;margin-top:10px;opacity:0.95;font-weight:500;">
                        📌 {entry_trigger}
                    </div>
                    {f'<div style="font-size:13px;margin-top:6px;opacity:0.9;font-family:JetBrains Mono,monospace;">{levels_line}</div>' if levels_line else ''}
                </div>
                """, unsafe_allow_html=True)

                col_chart, col_info = st.columns([2.5, 1])

                with col_chart:
                    # Main chart
                    chart = create_chart(df, ticker, support, resistance, sig, timeframe)
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
                            <div style="margin-top:10px;font-size:11px;color:var(--text-secondary);font-family:'JetBrains Mono',monospace;">
                                買分 {sig.get('buy_score',0)} | 賣分 {sig.get('sell_score',0)} | 淨 {sig.get('net_score',0):+.1f}
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # [IMPROVEMENT #2] Multi-EMA array + [#1/#3] MACD momentum
                    ema_state = sig.get('ema_array_state', 'neutral')
                    ema_state_color = {
                        'bullish_strong': '#4caf50',
                        'bullish': '#66bb6a',
                        'bearish_strong': '#e53935',
                        'bearish': '#ef5350',
                        'neutral': '#9e9e9e'
                    }.get(ema_state, '#9e9e9e')
                    ema_state_label = {
                        'bullish_strong': '強多頭排列 🟢',
                        'bullish': '偏多',
                        'bearish_strong': '強空頭排列 🔴',
                        'bearish': '偏空',
                        'neutral': '混亂'
                    }.get(ema_state, '—')

                    mom = sig.get('macd_momentum', {})
                    mom_color = '#4caf50' if mom.get('score', 0) > 0 else ('#e53935' if mom.get('score', 0) < 0 else '#9e9e9e')

                    st.markdown(f"""
                    <div class="signal-card">
                        <div class="section-title">動能分析 (升級)</div>
                        <div class="signal-row">
                            <span class="dot" style="background-color:{ema_state_color};"></span>
                            <span class="label-text">EMA排列</span>
                            <span class="value-text" style="color:{ema_state_color};">{ema_state_label}</span>
                        </div>
                        <div class="signal-row">
                            <span class="dot" style="background-color:{mom_color};"></span>
                            <span class="label-text">MACD動能</span>
                            <span class="value-text" style="color:{mom_color};">{mom.get('desc', '—')}</span>
                        </div>
                        {f'<div class="signal-row"><span class="dot dot-red"></span><span class="label-text">假突破</span><span class="value-text" style="color:#e53935;">⚠️ 檢測到假突破</span></div>' if sig.get('is_fake_breakout') else ''}
                    </div>
                    """, unsafe_allow_html=True)

                    # [IMPROVEMENT #6] MTF Resonance card
                    reso = sig.get('mtf_resonance') or {}
                    if reso.get('checks'):
                        reso_state = reso.get('state', 'none')
                        reso_color = {'strong': '#4caf50', 'partial': '#ff9800', 'none': '#9e9e9e'}.get(reso_state)
                        reso_label = {'strong': '✅ 全部共振', 'partial': '⚠️ 部分共振', 'none': '❌ 無共振'}.get(reso_state)
                        bonus_txt = f" (+{reso['bonus']}%強度)" if reso.get('bonus', 0) > 0 else ""

                        checks_html = ""
                        for ck in reso['checks']:
                            icon = "✓" if ck['agree'] else "✗"
                            c_color = "#4caf50" if ck['agree'] else "#9e9e9e"
                            checks_html += f'<div class="trade-record" style="color:{c_color};">{icon} {ck["tf"]}: {ck["reason"]}</div>'

                        st.markdown(f"""
                        <div class="signal-card">
                            <div class="section-title">多時間框架共振</div>
                            <div style="text-align:center;font-size:14px;font-weight:600;color:{reso_color};margin-bottom:8px;">
                                {reso_label}{bonus_txt}
                            </div>
                            {checks_html}
                        </div>
                        """, unsafe_allow_html=True)

                    # [IMPROVEMENT #7] Trade Plan card
                    tp = sig.get('trade_plan') or {}
                    if tp.get('stop_loss') is not None and sig['signal_type'] != 'hold':
                        is_long = sig['signal_type'] in ('strong_buy', 'buy', 'watch_buy')
                        plan_color = '#4caf50' if is_long else '#e53935'
                        direction = "做多" if is_long else "做空"
                        rr = tp.get('risk_reward') or 0
                        rr_color = '#4caf50' if rr >= 2 else ('#ff9800' if rr >= 1 else '#e53935')

                        st.markdown(f"""
                        <div class="signal-card" style="border-left:4px solid {plan_color};">
                            <div class="section-title">📋 交易計劃</div>
                            <div style="text-align:center;margin-bottom:10px;">
                                <span style="font-size:16px;font-weight:700;color:{plan_color};">{direction}</span>
                                <span style="font-size:12px;color:var(--text-secondary);margin-left:8px;">建議倉位 {tp['position_size_pct']}%</span>
                            </div>
                            <div class="trade-record" style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f0f0e8;">
                                <span style="color:var(--text-secondary);">進場</span>
                                <span style="font-weight:700;">${tp['entry']:.2f}</span>
                            </div>
                            <div class="trade-record" style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f0f0e8;">
                                <span style="color:var(--text-secondary);">🛑 止損</span>
                                <span style="font-weight:700;color:#e53935;">${tp['stop_loss']:.2f}</span>
                            </div>
                            <div class="trade-record" style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f0f0e8;">
                                <span style="color:var(--text-secondary);">✅ TP1 (50%)</span>
                                <span style="font-weight:700;color:#4caf50;">${tp['tp1']:.2f}</span>
                            </div>
                            <div class="trade-record" style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f0f0e8;">
                                <span style="color:var(--text-secondary);">🚀 TP2 (剩餘)</span>
                                <span style="font-weight:700;color:#4caf50;">${tp['tp2']:.2f}</span>
                            </div>
                            <div class="trade-record" style="display:flex;justify-content:space-between;padding:6px 0;">
                                <span style="color:var(--text-secondary);">⚖️ R:R</span>
                                <span style="font-weight:700;color:{rr_color};">1:{rr:.2f}</span>
                            </div>
                            <div style="margin-top:8px;padding:6px;background:#f9f9f4;border-radius:6px;font-size:11px;color:var(--text-secondary);line-height:1.4;">
                                💡 TP1達標後移動止損至進場價，剩餘部位看向TP2。ATR: ${sig.get('atr', 0):.2f}
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

        # ═══ Multi-Timeframe Overview ═══
        st.markdown("---")
        st.markdown("### 🕐 多時間框架總覽")
        mtf_ticker = st.selectbox("選擇股票查看多時間框架", tickers, key="mtf_select")

        all_tfs = ["1m", "5m", "15m", "30m", "1h", "1d", "1wk"]
        tf_labels = {"1m":"1分鐘","5m":"5分鐘","15m":"15分鐘","30m":"30分鐘","1h":"1小時","1d":"日線","1wk":"週線"}

        mtf_cols = st.columns(len(all_tfs))
        for ci, tf_key in enumerate(all_tfs):
            with mtf_cols[ci]:
                tf_cfg = TIMEFRAME_MAP[tf_key]
                mtf_df = fetch_data(mtf_ticker, tf_cfg['interval'], tf_cfg['period'])
                if mtf_df.empty or len(mtf_df) < 30:
                    st.markdown(f"""
                    <div class="signal-card hold-signal" style="text-align:center;padding:10px;">
                        <div style="font-size:12px;font-weight:600;">{tf_labels[tf_key]}</div>
                        <div style="font-size:11px;color:var(--text-secondary);">數據不足</div>
                    </div>
                    """, unsafe_allow_html=True)
                    continue

                mtf_df['EMA_fast'] = calc_ema(mtf_df['Close'], ema_fast_input)
                mtf_df['EMA_slow'] = calc_ema(mtf_df['Close'], ema_slow_input)
                mtf_df['DIF'] = mtf_df['EMA_fast'] - mtf_df['EMA_slow']
                mtf_df['DEA'] = calc_ema(mtf_df['DIF'], macd_sig_input)
                mtf_df['Histogram'] = mtf_df['DIF'] - mtf_df['DEA']

                sr_df_mtf = fetch_data(mtf_ticker, tf_cfg['sr_interval'], tf_cfg['sr_period'])
                if sr_df_mtf.empty or len(sr_df_mtf) < 20:
                    sr_df_mtf = mtf_df
                sup_m, res_m = find_support_resistance(sr_df_mtf, min_touches=sr_min_touches, tolerance_pct=sr_tolerance/100)
                sig_m = analyze_signals(mtf_df, sup_m, res_m)

                sig_type_m = sig_m['signal_type']
                if sig_type_m in ('strong_buy', 'buy', 'watch_buy'):
                    card_cls = "normal-buy" if sig_type_m != 'strong_buy' else "strong-buy"
                    col_m = "#4caf50"
                    arrow = "▲"
                elif sig_type_m in ('strong_sell', 'sell', 'watch_sell'):
                    card_cls = "normal-sell" if sig_type_m != 'strong_sell' else "strong-sell"
                    col_m = "#e53935"
                    arrow = "▼"
                else:
                    card_cls = "hold-signal"
                    col_m = "#6b6b6b"
                    arrow = "●"

                trend_icon = "🟢" if sig_m.get('trend_bullish') else "🔴"
                macd_icon = "🟢" if sig_m['dif'] > sig_m['dea'] else "🔴"

                st.markdown(f"""
                <div class="signal-card {card_cls}" style="text-align:center;padding:10px;">
                    <div style="font-size:12px;font-weight:600;">{tf_labels[tf_key]}</div>
                    <div style="font-size:14px;font-weight:700;color:{col_m};margin:4px 0;">{arrow} {sig_m['signal']}</div>
                    <div style="font-size:11px;color:var(--text-secondary);">
                        趨勢{trend_icon} MACD{macd_icon}
                    </div>
                    <div style="font-size:11px;color:{col_m};font-family:'JetBrains Mono',monospace;">
                        {sig_m['strength']}%
                    </div>
                </div>
                """, unsafe_allow_html=True)

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
