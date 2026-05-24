import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'Hiragino Sans'
from datetime import datetime

# === ページ設定 ===
st.set_page_config(
    page_title="投資システム",
    page_icon="📈",
    layout="wide",
)

# === ウォッチリスト ===
WATCHLIST = {
    # 日本株
    "7203.T": "トヨタ自動車",
    "6758.T": "ソニーG",
    "9984.T": "ソフトバンクG",
    "8306.T": "三菱UFJ",
    "9432.T": "NTT",
    "9433.T": "KDDI",
    "6098.T": "リクルートHD",
    "8035.T": "東京エレクトロン",
    "7974.T": "任天堂",
    "9983.T": "ファーストリテイリング",
    "6861.T": "キーエンス",
    "8316.T": "三井住友FG",
    "8058.T": "三菱商事",
    "6501.T": "日立製作所",
    "8001.T": "伊藤忠商事",
    # 米株
    "AAPL":  "Apple",
    "MSFT":  "Microsoft",
    "GOOGL": "Alphabet",
    "AMZN":  "Amazon",
    "NVDA":  "NVIDIA",
    "TSLA":  "Tesla",
    "META":  "Meta",
    "JPM":   "JPMorgan",
    "V":     "Visa",
    "WMT":   "Walmart",
}


# === 共通関数: データ取得とシグナル計算 ===
@st.cache_data(ttl=600)  # 10分キャッシュ(同じデータを連続取得しない)
def get_data_with_signals(ticker, period="6mo", rsi_threshold=70):
    """データ取得 + 指標計算 + シグナル検出"""
    data = yf.download(ticker, period=period, progress=False)
    if data.empty:
        return None
    df = data[["Close"]].copy()
    df.columns = ["Close"]

    df["MA5"]  = df["Close"].rolling(5).mean()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA60"] = df["Close"].rolling(60).mean()

    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    df["Signal"] = ""
    for i in range(1, len(df)):
        prev, curr = df.iloc[i - 1], df.iloc[i]
        if prev["MA5"] <= prev["MA20"] and curr["MA5"] > curr["MA20"]:
            if curr["Close"] > curr["MA60"] and curr["RSI"] < rsi_threshold:
                df.iloc[i, df.columns.get_loc("Signal")] = "BUY"
        elif prev["MA5"] >= prev["MA20"] and curr["MA5"] < curr["MA20"]:
            df.iloc[i, df.columns.get_loc("Signal")] = "SELL"
    return df


# === ヘッダー ===
st.title("📈 投資システム ダッシュボード")
st.caption(f"最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# === タブ ===
tab1, tab2, tab3 = st.tabs(["🔍 銘柄分析", "📡 スキャナ", "🧪 バックテスト"])


# ========================================
# タブ1: 銘柄分析
# ========================================
with tab1:
    st.header("銘柄分析")

    col1, col2 = st.columns([1, 3])

    with col1:
        # 銘柄選択
        ticker_label = st.selectbox(
            "銘柄を選択",
            options=list(WATCHLIST.keys()),
            format_func=lambda x: f"{WATCHLIST[x]} ({x})",
        )
        period_label = st.selectbox(
            "期間",
            options=["3mo", "6mo", "1y", "2y", "5y"],
            index=1,
        )

    with col2:
        if ticker_label:
            with st.spinner(f"{WATCHLIST[ticker_label]} のデータを取得中..."):
                df = get_data_with_signals(ticker_label, period=period_label)

            if df is None or df.empty:
                st.error("データを取得できませんでした")
            else:
                # サマリー情報
                latest = df.iloc[-1]
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("現在価格", f"{float(latest['Close']):,.2f}")
                c2.metric("RSI", f"{float(latest['RSI']):.1f}")
                ret_20d = (float(latest['Close']) / float(df['Close'].iloc[-20]) - 1) * 100
                c3.metric("20日リターン", f"{ret_20d:+.2f}%")
                signals_count = (df["Signal"] != "").sum()
                c4.metric(f"期間内シグナル", f"{signals_count} 件")

                # チャート
                fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True,
                                                gridspec_kw={"height_ratios": [3, 1]})

                ax1.plot(df.index, df["Close"], label="Close", color="gray", linewidth=1)
                ax1.plot(df.index, df["MA5"],  label="MA5",  linewidth=1.2)
                ax1.plot(df.index, df["MA20"], label="MA20", linewidth=1.2)
                ax1.plot(df.index, df["MA60"], label="MA60", linewidth=1.2, color="green")
                buys  = df[df["Signal"] == "BUY"]
                sells = df[df["Signal"] == "SELL"]
                ax1.scatter(buys.index,  buys["Close"],  marker="^", color="red",  s=100, label="BUY",  zorder=5)
                ax1.scatter(sells.index, sells["Close"], marker="v", color="blue", s=100, label="SELL", zorder=5)
                ax1.set_title(f"{WATCHLIST[ticker_label]} ({ticker_label})")
                ax1.legend()
                ax1.grid(alpha=0.3)

                ax2.plot(df.index, df["RSI"], color="purple", linewidth=1)
                ax2.axhline(70, color="red", linewidth=0.5, linestyle="--")
                ax2.axhline(30, color="green", linewidth=0.5, linestyle="--")
                ax2.set_ylabel("RSI")
                ax2.grid(alpha=0.3)

                plt.tight_layout()
                st.pyplot(fig)
                plt.close(fig)

                # シグナル履歴
                signals_df = df[df["Signal"] != ""][["Close", "RSI", "Signal"]].copy()
                signals_df.index = signals_df.index.strftime("%Y-%m-%d")
                if not signals_df.empty:
                    st.subheader("シグナル履歴")
                    st.dataframe(signals_df, use_container_width=True)


# ========================================
# タブ2: スキャナ
# ========================================
with tab2:
    st.header("スキャナ - 全銘柄を一気にチェック")

    if st.button("🔄 スキャン実行", type="primary"):
        results = []
        progress = st.progress(0)
        status = st.empty()

        for i, (ticker, name) in enumerate(WATCHLIST.items()):
            status.text(f"処理中: {name} ({ticker}) ... [{i+1}/{len(WATCHLIST)}]")
            df = get_data_with_signals(ticker, period="6mo")
            if df is not None and not df.empty and len(df) >= 60:
                latest = df.iloc[-1]
                close = float(latest["Close"])
                rsi = float(latest["RSI"])
                ma5, ma20, ma60 = float(latest["MA5"]), float(latest["MA20"]), float(latest["MA60"])

                if close > ma20 > ma60:
                    trend = "↑ 強い上昇"
                elif close > ma20 and ma20 < ma60:
                    trend = "↗ 上昇転換中"
                elif close < ma20 < ma60:
                    trend = "↓ 強い下落"
                elif close < ma20 and ma20 > ma60:
                    trend = "↘ 下落転換中"
                else:
                    trend = "→ 横ばい"

                return_20d = (close / float(df["Close"].iloc[-20]) - 1) * 100

                recent_signals = df["Signal"].tail(5)
                recent_buy  = "BUY"  in recent_signals.values
                recent_sell = "SELL" in recent_signals.values

                results.append({
                    "銘柄": name,
                    "コード": ticker,
                    "価格": close,
                    "RSI": rsi,
                    "20日%": return_20d,
                    "トレンド": trend,
                    "🟢BUY直近": "✅" if recent_buy else "",
                    "🔴SELL直近": "✅" if recent_sell else "",
                })
            progress.progress((i + 1) / len(WATCHLIST))

        progress.empty()
        status.empty()
        st.success(f"完了: {len(results)} 銘柄をスキャンしました")

        result_df = pd.DataFrame(results)

        # BUYシグナル
        buy_df = result_df[result_df["🟢BUY直近"] == "✅"]
        st.subheader(f"🟢 直近5日以内に BUY シグナル ({len(buy_df)} 件)")
        if not buy_df.empty:
            st.dataframe(buy_df[["銘柄", "コード", "価格", "RSI", "20日%", "トレンド"]], use_container_width=True)
        else:
            st.info("該当なし")

        # SELLシグナル
        sell_df = result_df[result_df["🔴SELL直近"] == "✅"]
        st.subheader(f"🔴 直近5日以内に SELL シグナル ({len(sell_df)} 件)")
        if not sell_df.empty:
            st.dataframe(sell_df[["銘柄", "コード", "価格", "RSI", "20日%", "トレンド"]], use_container_width=True)
        else:
            st.info("該当なし")

        # 強い上昇トレンド
        st.subheader("📈 強い上昇トレンド TOP10(20日リターン順)")
        strong_up = result_df[result_df["トレンド"] == "↑ 強い上昇"].sort_values("20日%", ascending=False).head(10)
        st.dataframe(strong_up[["銘柄", "コード", "価格", "RSI", "20日%"]], use_container_width=True)

        # 過熱・売られすぎ
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("⚠️ 過熱(RSI > 70)")
            overbought = result_df[result_df["RSI"] > 70].sort_values("RSI", ascending=False)
            if not overbought.empty:
                st.dataframe(overbought[["銘柄", "RSI", "トレンド"]], use_container_width=True)
            else:
                st.info("該当なし")
        with c2:
            st.subheader("💡 売られすぎ(RSI < 30)")
            oversold = result_df[result_df["RSI"] < 30].sort_values("RSI")
            if not oversold.empty:
                st.dataframe(oversold[["銘柄", "RSI", "トレンド"]], use_container_width=True)
            else:
                st.info("該当なし")
    else:
        st.info("「スキャン実行」ボタンを押して全銘柄をチェックします")


# ========================================
# タブ3: バックテスト
# ========================================
with tab3:
    st.header("バックテスト")

    col1, col2 = st.columns([1, 3])

    with col1:
        bt_ticker = st.selectbox(
            "銘柄",
            options=list(WATCHLIST.keys()),
            format_func=lambda x: f"{WATCHLIST[x]} ({x})",
            key="bt_ticker",
        )
        bt_period = st.selectbox(
            "期間",
            options=["6mo", "1y", "2y", "5y"],
            index=2,
            key="bt_period",
        )
        bt_capital = st.number_input("初期資金", value=1_000_000, step=100_000)
        bt_stop_loss = st.slider("損切り (%)", 1, 20, 5) / 100

    with col2:
        if st.button("🧪 バックテスト実行", type="primary"):
            with st.spinner("実行中..."):
                df = get_data_with_signals(bt_ticker, period=bt_period)

            if df is None or df.empty:
                st.error("データなし")
            else:
                # シミュレーション
                cash, shares, last_buy = bt_capital, 0, 0
                fee = 0.001
                trades, equity_curve = [], []

                for i in range(len(df)):
                    price = float(df["Close"].iloc[i])
                    signal = df["Signal"].iloc[i]
                    date = df.index[i]

                    if signal == "BUY" and cash > 0:
                        shares = (cash * (1 - fee)) / price
                        cash, last_buy = 0, price
                        trades.append({"type": "BUY", "price": price})
                    elif signal == "SELL" and shares > 0:
                        cash = shares * price * (1 - fee)
                        profit = (price - last_buy) / last_buy * 100
                        trades.append({"type": "SELL", "profit_pct": profit})
                        shares = 0
                    elif shares > 0 and price < last_buy * (1 - bt_stop_loss):
                        cash = shares * price * (1 - fee)
                        profit = (price - last_buy) / last_buy * 100
                        trades.append({"type": "STOP", "profit_pct": profit})
                        shares = 0

                    equity_curve.append({"date": date, "equity": cash + shares * price})

                final = cash + shares * float(df["Close"].iloc[-1])
                ret_pct = (final - bt_capital) / bt_capital * 100
                sell_t = [t for t in trades if t["type"] in ("SELL", "STOP")]
                wins = [t for t in sell_t if t["profit_pct"] > 0]
                win_rate = len(wins) / len(sell_t) * 100 if sell_t else 0

                bh = bt_capital * (1 - fee) * float(df["Close"].iloc[-1]) / float(df["Close"].iloc[0])
                bh_pct = (bh - bt_capital) / bt_capital * 100

                eq = pd.DataFrame(equity_curve).set_index("date")
                eq["peak"] = eq["equity"].cummax()
                eq["dd"] = (eq["equity"] - eq["peak"]) / eq["peak"] * 100
                max_dd = eq["dd"].min()

                # 結果サマリー
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("戦略リターン", f"{ret_pct:+.2f}%")
                c2.metric("B&H", f"{bh_pct:+.2f}%", delta=f"{ret_pct - bh_pct:+.2f}%")
                c3.metric("勝率", f"{win_rate:.1f}%", delta=f"{len(sell_t)}回")
                c4.metric("最大DD", f"{max_dd:.2f}%")

                # 資産推移グラフ
                fig, ax = plt.subplots(figsize=(12, 5))
                ax.plot(eq.index, eq["equity"], label="Strategy", linewidth=1.5, color="blue")
                bh_curve = bt_capital * (1 - fee) * df["Close"] / float(df["Close"].iloc[0])
                ax.plot(df.index, bh_curve, label="Buy & Hold", linewidth=1.5, linestyle="--", color="orange")
                ax.axhline(bt_capital, color="gray", linewidth=0.5, linestyle=":")
                ax.set_title(f"{WATCHLIST[bt_ticker]} - Backtest")
                ax.legend()
                ax.grid(alpha=0.3)
                plt.tight_layout()
                st.pyplot(fig)
                plt.close(fig)