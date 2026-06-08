import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# ─────────────────────────────────────────────
# 페이지 기본 설정
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="게임 업계 주식 분석",
    page_icon="🎮",
    layout="wide"
)

st.title("🎮 게임 업계 주식 분석")
st.caption("국내외 게임 회사들의 수익률을 비교 분석해보세요!")

# ─────────────────────────────────────────────
# 게임 업계 종목 딕셔너리
# ⚠️ 아래 티커는 예시입니다. 여러분이 직접 조사해서
#    추가하거나 수정해보세요!
#    (한국: .KS 또는 .KQ / 미국: 그대로)
# ─────────────────────────────────────────────
GAME_STOCKS = {
    # ── 한국 게임사 ──
    "엔씨소프트": "036570.KS",
    "넷마블": "251270.KS",
    "크래프톤": "259960.KS",
    "펄어비스": "263750.KQ",
    "카카오게임즈": "293490.KQ",
    # ── 미국/해외 게임사 ──
    "EA(Electronic Arts)": "EA",
    "Take-Two": "TTWO",
    "Roblox": "RBLX",
    "닌텐도(Nintendo)": "NTDOY",
}

# 한국 종목과 해외 종목을 구분하기 위한 리스트
KR_GAME = ["엔씨소프트", "넷마블", "크래프톤", "펄어비스", "카카오게임즈"]

# ─────────────────────────────────────────────
# 사이드바: 사용자 입력
# ─────────────────────────────────────────────
st.sidebar.header("⚙️ 분석 설정")

selected_names = st.sidebar.multiselect(
    "비교할 게임 종목을 선택하세요 (여러 개 가능)",
    options=list(GAME_STOCKS.keys()),
    default=["엔씨소프트", "크래프톤"]
)

period_options = {
    "1개월": "1mo",
    "3개월": "3mo",
    "6개월": "6mo",
    "1년": "1y",
    "2년": "2y",
    "5년": "5y",
}
selected_period_label = st.sidebar.selectbox(
    "조회 기간을 선택하세요",
    options=list(period_options.keys()),
    index=3  # 기본값: 1년
)
selected_period = period_options[selected_period_label]

# ─────────────────────────────────────────────
# 데이터 불러오기 함수 (캐시 적용)
# ─────────────────────────────────────────────
@st.cache_data(ttl=600)
def load_data(ticker, period):
    """yfinance로 주가 데이터를 불러옵니다."""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        return df
    except Exception:
        return pd.DataFrame()

# ─────────────────────────────────────────────
# 메인 로직
# ─────────────────────────────────────────────
if not selected_names:
    st.warning("👈 왼쪽 사이드바에서 게임 종목을 1개 이상 선택해주세요!")
    st.stop()

price_data = {}
return_data = {}
summary_rows = []

with st.spinner("게임 종목 데이터를 불러오는 중... ⏳"):
    for name in selected_names:
        ticker = GAME_STOCKS[name]
        df = load_data(ticker, selected_period)

        if df.empty or "Close" not in df.columns:
            st.error(f"⚠️ '{name}' 데이터를 불러오지 못했습니다.")
            continue

        close = df["Close"].dropna()
        if len(close) < 2:
            st.error(f"⚠️ '{name}' 데이터가 충분하지 않습니다.")
            continue

        price_data[name] = close

        # 누적 수익률(%) 계산
        cumulative_return = (close / close.iloc[0] - 1) * 100
        return_data[name] = cumulative_return

        start_price = close.iloc[0]
        end_price = close.iloc[-1]
        total_return = (end_price / start_price - 1) * 100

        currency = "₩" if name in KR_GAME else "$"

        summary_rows.append({
            "종목": name,
            "시작가": f"{currency}{start_price:,.2f}",
            "현재가": f"{currency}{end_price:,.2f}",
            "수익률(%)": round(total_return, 2),
        })

if not return_data:
    st.error("표시할 데이터가 없습니다. 다른 종목이나 기간을 선택해보세요.")
    st.stop()

# ─────────────────────────────────────────────
# 1. 수익률 요약 테이블
# ─────────────────────────────────────────────
st.subheader(f"📊 게임 종목 수익률 요약 ({selected_period_label} 기준)")
summary_df = pd.DataFrame(summary_rows)
st.dataframe(summary_df, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────
# 2. 누적 수익률 비교 선 그래프
# ─────────────────────────────────────────────
st.subheader("📈 누적 수익률 비교 (%)")

fig_return = go.Figure()
for name, ret in return_data.items():
    fig_return.add_trace(go.Scatter(
        x=ret.index,
        y=ret.values,
        mode="lines",
        name=name,
        hovertemplate="%{x|%Y-%m-%d}<br>수익률: %{y:.2f}%<extra></extra>"
    ))

fig_return.add_hline(y=0, line_dash="dash", line_color="gray")
fig_return.update_layout(
    xaxis_title="날짜",
    yaxis_title="누적 수익률 (%)",
    hovermode="x unified",
    height=500,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
st.plotly_chart(fig_return, use_container_width=True)

# ─────────────────────────────────────────────
# 3. 기간 수익률 막대그래프 (종목 간 비교에 유용!)
# ─────────────────────────────────────────────
st.subheader("📊 기간 총수익률 비교 (막대그래프)")

bar_names = [row["종목"] for row in summary_rows]
bar_returns = [row["수익률(%)"] for row in summary_rows]
# 수익은 빨강, 손실은 파랑 (한국 증시 색 관습)
bar_colors = ["crimson" if r >= 0 else "royalblue" for r in bar_returns]

fig_bar = go.Figure(go.Bar(
    x=bar_names,
    y=bar_returns,
    marker_color=bar_colors,
    text=[f"{r}%" for r in bar_returns],
    textposition="outside"
))
fig_bar.update_layout(
    xaxis_title="종목",
    yaxis_title="총수익률 (%)",
    height=450
)
st.plotly_chart(fig_bar, use_container_width=True)

# ─────────────────────────────────────────────
# 4. 종목별 가격 차트 (탭)
# ─────────────────────────────────────────────
st.subheader("💹 종목별 가격 차트")

tabs = st.tabs(list(price_data.keys()))
for tab, name in zip(tabs, price_data.keys()):
    with tab:
        close = price_data[name]
        currency = "₩" if name in KR_GAME else "$"

        fig_price = go.Figure()
        fig_price.add_trace(go.Scatter(
            x=close.index,
            y=close.values,
            mode="lines",
            name=name,
            fill="tozeroy",
            line=dict(width=2)
        ))
        fig_price.update_layout(
            title=f"{name} 주가 추이",
            xaxis_title="날짜",
            yaxis_title=f"종가 ({currency})",
            height=400
        )
        st.plotly_chart(fig_price, use_container_width=True)

st.info("💡 데이터 출처: Yahoo Finance · 투자 판단의 참고용으로만 활용하세요.")
