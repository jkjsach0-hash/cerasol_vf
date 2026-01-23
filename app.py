import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. 앱 페이지 설정
st.set_page_config(page_title="소성 비용 계산기", layout="wide")
st.title("🔥 진공로 소성 비용 통합 분석기")

# 2. 구글 시트 연결
# .streamlit/secrets.toml에 등록된 주소를 자동으로 읽어옵니다.
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # 3. 데이터 시트별로 불러오기
    # worksheet 이름이 실제 구글 시트 탭 이름과 정확히 일치해야 합니다.
    df_machines = conn.read(worksheet="Machines")
    df_water = conn.read(worksheet="Waterlogs")
    df_power = conn.read(worksheet="MachinesMonthlyEnergy")
    df_billing = conn.read(worksheet="FactoryEnergyExpenses")

    # --- 데이터 전처리 ---
    # 날짜 컬럼을 시트에서 정리한 대로 변환
    df_water['날짜'] = pd.to_datetime(df_water['날짜'])
    df_power['날짜'] = pd.to_datetime(df_power['날짜'])

    # 4. 사이드바: 분석 기간 및 단가 설정
    st.sidebar.header("⚙️ 설정 및 입력")
    # 분석하고 싶은 월 선택 (데이터 내의 고유한 년-월 리스트)
    available_months = df_power['날짜'].dt.to_period('M').unique().astype(str)
    selected_month = st.sidebar.selectbox("분석 대상 월 선택", available_months)

    # 한전 API 미연결 시 사용할 기본 단가
    default_rate = st.sidebar.number_input("전기 기본 단가 (원/kWh)", value=120)

    # 5. 비용 계산 로직
    # (1) 고정비: 기계 감가상각 (구매가 / (수명*12))
    df_machines['월감가상각'] = df_machines['구매가'] / (df_machines['기대수명'] * 12)
    fixed_cost = df_machines['월감가상각'].sum() + df_machines['월유지보수비'].sum()

    # (2) 변동비: 전력량 계산 (선택 월 필터링)
    monthly_power = df_power[df_power['날짜'].dt.to_period('M') == selected_month]
    total_kwh = monthly_power['총전력량'].sum()
    
    # 공장 전기 요금 시트가 비어있으면 수동 단가 사용
    if df_billing.empty or '단가' not in df_billing.columns:
        power_cost = total_kwh * default_rate
    else:
        # 시트 데이터가 있다면 해당 월의 단가 사용 (없으면 기본값)
        power_cost = total_kwh * df_billing['단가'].iloc[0]

    # (3) 변동비: 냉각수 (데이터 누락 처리)
    monthly_water = df_water[df_water['날짜'].dt.to_period('M') == selected_month]
    if len(monthly_water) < 25: # 한 달 데이터가 부족할 경우
        avg_water = monthly_water['사용량'].mean() if not monthly_water.empty else 0
        total_water = avg_water * 30 # 한 달치로 추정
        st.warning(f"⚠️ {selected_month} 냉각수 데이터가 부족하여 평균값으로 추정합니다.")
    else:
        total_water = monthly_water['사용량'].sum()
    
    water_cost = total_water * 1000 # 톤당 1000원 가정 (수정 가능)

    # 6. 결과 화면 출력 (대시보드)
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("기계 고정비", f"{fixed_cost:,.0f} 원")
    m2.metric("전력 사용량", f"{total_kwh:,.1f} kWh")
    m3.metric("전기 요금", f"{power_cost:,.0f} 원")
    m4.metric("총 소성 비용", f"{(fixed_cost + power_cost + water_cost):,.0f} 원")

    # 7. 시각화 (막대 그래프)
    st.subheader(f"📊 {selected_month} 비용 구성 비율")
    chart_data = pd.DataFrame({
        "항목": ["고정비(기계)", "전기요금", "냉각수"],
        "금액": [fixed_cost, power_cost, water_cost]
    })
    st.bar_chart(chart_data.set_index("항목"))

except Exception as e:
    st.error(f"데이터를 불러오는 중 에러가 발생했습니다: {e}")
    st.info("구글 시트의 탭 이름과 컬럼명이 코드와 일치하는지 확인해 주세요.")
