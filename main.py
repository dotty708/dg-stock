import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# 페이지 기본 설정
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="주식 수익률 비교 분석",
    page_icon="📈",
    layout="wide"
)

st.title("📈 한국 · 미국 주식 수익률 비교 분석")
st.caption("yfinance + Plotly로 만든 주식 분석 웹앱")

# ─────────────────────────────────────────────
# 주요 종목 딕셔너리 (이름: 티커)
# 한국 주식은 코스피=.KS, 코스닥=.KQ 를 붙여야 함
# ─────────────────────────────────────────────
KR_STOCKS = {
    "삼성전자": "005930.KS",
    "SK하이닉스": "000660.KS",
    "LG에너지솔루션": "373220.KS",
    "현대차": "005380.KS",
    "NAVER": "035420.KS",
    "카카오": "035720.KS",
    "셀트리온": "068270.KS",
}

US_STOCKS = {
    "애플(Apple)": "AAPL",
    "마이크로소프트(Microsoft)": "MSFT",
    "엔비디아(NVIDIA)": "NVDA",
    "구글(Alphabet)": "GOOGL",
    "아마존(Amazon)": "AMZN",
    "테슬라(Tesla)": "TSLA",
    "메타(Meta)": "META",
}

# 전체 종목 합치기
ALL_STOCKS = {**KR_STOCKS, **US_STOCKS}

# ─────────────────────────────────────────────
# 사이드바: 사용자 입력
# ─────────────────────────────────────────────
st.sidebar.header("⚙️ 설정")

# 종목 선택 (여러 개 선택 가능)
selected_names = st.sidebar.multiselect(
    "비교할 종목을 선택하세요 (여러 개 가능)",
    options=list(ALL_STOCKS.keys()),
    default=["삼성전자", "애플(Apple)"]
)

# 기간 선택
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
# 데이터 불러오기 함수 (캐시 적용으로 속도 향상)
# ─────────────────────────────────────────────
@st.cache_data(ttl=600)  # 10분 동안 캐시 유지
def load_data(ticker, period):
    """yfinance로 주가 데이터를 불러옵니다."""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        return df
    except Exception as e:
        return pd.DataFrame()  # 오류 시 빈 데이터프레임 반환

# ─────────────────────────────────────────────
# 메인 로직
# ─────────────────────────────────────────────
if not selected_names:
    st.warning("👈 왼쪽 사이드바에서 비교할 종목을 1개 이상 선택해주세요!")
    st.stop()

# 데이터 수집
price_data = {}      # 종가 저장
return_data = {}     # 누적 수익률(%) 저장
summary_rows = []    # 요약 테이블용

with st.spinner("데이터를 불러오는 중입니다... ⏳"):
    for name in selected_names:
        ticker = ALL_STOCKS[name]
        df = load_data(ticker, selected_period)

        # 데이터가 비어있으면 건너뛰기
        if df.empty or "Close" not in df.columns:
            st.error(f"⚠️ '{name}' 데이터를 불러오지 못했습니다.")
            continue

        close = df["Close"].dropna()
        if len(close) < 2:
            st.error(f"⚠️ '{name}' 데이터가 충분하지 않습니다.")
            continue

        price_data[name] = close

        # 누적 수익률 계산: (현재가 / 시작가 - 1) * 100
        cumulative_return = (close / close.iloc[0] - 1) * 100
        return_data[name] = cumulative_return

        # 요약 정보 계산
        start_price = close.iloc[0]
        end_price = close.iloc[-1]
        total_return = (end_price / start_price - 1) * 100

        # 한국/미국 구분으로 통화 표시
        currency = "₩" if name in KR_STOCKS else "$"

        summary_rows.append({
            "종목": name,
            "시작가": f"{currency}{start_price:,.2f}",
            "현재가": f"{currency}{end_price:,.2f}",
            "수익률(%)": round(total_return, 2),
        })

# 유효한 데이터가 없으면 종료
if not return_data:
    st.error("표시할 데이터가 없습니다. 다른 종목이나 기간을 선택해보세요.")
    st.stop()

# ─────────────────────────────────────────────
# 1. 요약 테이블
# ─────────────────────────────────────────────
st.subheader(f"📊 수익률 요약 ({selected_period_label} 기준)")
summary_df = pd.DataFrame(summary_rows)
st.dataframe(summary_df, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────
# 2. 누적 수익률 비교 차트 (가장 중요!)
#    서로 다른 가격대의 종목을 공정하게 비교하기 위해
#    %수익률로 변환해서 한 그래프에 표시
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

# 0% 기준선 추가
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
# 3. 개별 종목 가격 차트 (탭으로 구성)
# ─────────────────────────────────────────────
st.subheader("💹 종목별 가격 차트")

tabs = st.tabs(list(price_data.keys()))
for tab, name in zip(tabs, price_data.keys()):
    with tab:
        close = price_data[name]
        currency = "₩" if name in KR_STOCKS else "$"

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

# ─────────────────────────────────────────────
# 안내 문구
# ─────────────────────────────────────────────
st.info("💡 데이터 출처: Yahoo Finance (yfinance) · 투자 판단의 참고용으로만 활용하세요.")
