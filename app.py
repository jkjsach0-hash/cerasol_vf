import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. 앱 제목 및 설정
st.set_page_config(page_title="월간 소성 비용 계산기", layout="wide")
st.title("🔥 진공로 월간 소성 비용 분석")

# 2. 구글 시트 연결 (비밀번호 설정은 .streamlit/secrets.toml에 필요)
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 데이터 불러오기 (시트 이름은 실제와 맞춰주세요)
df_machines = conn.read(worksheet="기계구입비용")
df_water = conn.read(worksheet="냉각수 일일 사용량")
df_power = conn.read(worksheet="전기로 전력량")

# 4. 비용 계산 로직
st.sidebar.header("📅 분석 기간 설정")
target_month = st.sidebar.selectbox("대상 월 선택", ["2024-01", "2024-02", "2024-03"]) # 예시

# --- (1) 고정비: 기계 감가상각비 ---
# 월별 감가상각 = 구매가 / (수명 * 12)
df_machines['월감가상각'] = df_machines['구매가'] / (df_machines['기대수명'] * 12)
total_depreciation = df_machines['월감가상각'].sum() + df_machines['월유지보수비'].sum()

# --- (2) 변동비: 냉각수 (누락값 처리) ---
df_water['날짜'] = pd.to_datetime(df_water['날짜'])
# 선택한 달의 데이터만 필터링 후 평균값으로 한 달치 추정
avg_water = df_water['사용량'].mean() 
total_water_usage = avg_water * 30 # 한 달 30일 기준 추정

# --- (3) 변동비: 전력료 ---
# API 연결 전까지는 사용자가 단가를 입력하거나 시트값을 사용
power_usage = df_power['총전력량'].sum()
power_rate = st.sidebar.number_input("전기 단가 (원/kWh)", value=120)
total_power_cost = power_usage * power_rate

# 5. 결과 대시보드
col1, col2, col3 = st.columns(3)
col1.metric("고정비 (감가상각/유지비)", f"{total_depreciation:,.0f} 원")
col2.metric("전력 요금 (추정)", f"{total_power_cost:,.0f} 원")
col3.metric("총 소성 비용", f"{(total_depreciation + total_power_cost):,.0f} 원")

# 6. 비용 구조 시각화 (차트)
st.subheader("📊 비용 구성 비율")
cost_data = {
    "항목": ["기계 감가상각", "전기료", "냉각수료(추정)"],
    "금액": [total_depreciation, total_power_cost, total_water_usage * 1000] # 수도세 단가 1000원 가정
}
st.bar_chart(pd.DataFrame(cost_data).set_index("항목"))

st.success("구글 시트로부터 데이터를 성공적으로 불러왔습니다.")
