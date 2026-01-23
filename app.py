import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. 앱 페이지 설정
st.set_page_config(page_title="공장 소성 비용 분석기", layout="wide")
st.title("🏭 진공로 소성 비용 통합 대시보드")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # 3. 데이터 시트 읽기
    df_machines = conn.read(worksheet="Machines")
    df_water = conn.read(worksheet="Waterlogs")
    df_energy = conn.read(worksheet="MachinesMonthlyEnergy")
    df_billing = conn.read(worksheet="FactoryEnergyExpenses")

    # --- 데이터 전처리 ---
    df_water['날짜'] = pd.to_datetime(df_water['날짜'])
    df_machines['취득원가'] = pd.to_numeric(df_machines['취득원가'], errors='coerce')
    df_energy['전력량'] = pd.to_numeric(df_energy['전력량'], errors='coerce')
    df_billing['전기요금'] = pd.to_numeric(df_billing['전기요금'], errors='coerce')

    # 4. 사이드바: 분석 월 선택
    st.sidebar.header("🗓️ 기간 설정")
    available_months = df_energy['월'].unique()
    selected_month = st.sidebar.selectbox("조회할 월을 선택하세요", available_months)
    
    # 5. 비용 계산 로직
    # (1) 기계 고정비: 취득원가 합계 / 120개월(10년)
    monthly_fixed_cost = (df_machines['취득원가'].sum() / 120)

    # (2) 전력량 및 전기요금 결정
    # MachinesMonthlyEnergy에서 해당 월 전력량 가져오기
    energy_row = df_energy[df_energy['월'] == selected_month]
    total_kwh = energy_row['전력량'].iloc[0] if not energy_row.empty else 0
    
    # FactoryEnergyExpenses에서 실제 요금 확인
    billing_row = df_billing[df_billing['월'] == selected_month]
    if not billing_row.empty and pd.notnull(billing_row['전기요금'].iloc[0]):
        actual_power_cost = billing_row['전기요금'].iloc[0]
        calc_method = "실제 청구 요금 기반"
    else:
        # 실제 요금이 없으면 전력량 기반 추정 (기본 단가 125원 가정)
        actual_power_cost = total_kwh * 125
        calc_method = "전력량 기반 추정치 (단가 125원 적용)"

    # (3) 냉각수 비용 (waterlogs 기반 추정)
    match_month = str(selected_month).replace('.', '-')
    df_water['월_temp'] = df_water['날짜'].dt.to_period('M').astype(str)
    monthly_water = df_water[df_water['월_temp'].str.contains(match_month)]
    
    if not monthly_water.empty:
        total_water_usage = monthly_water['냉각수사용량(m3)'].mean() * 30
    else:
        total_water_usage = 0
    water_cost = total_water_usage * 1200 # m3당 1,200원

    # 6. 결과 화면 (대시보드)
    st.info(f"💡 현재 **{selected_month}** 데이터를 분석 중입니다. ({calc_method})")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("기계 감가상각", f"{monthly_fixed_cost:,.0f} 원")
    m2.metric("전력 사용량", f"{total_kwh:,.1f} kWh")
    m3.metric("전기 요금", f"{actual_power_cost:,.0f} 원")
    m4.metric("총 소성 비용", f"{(monthly_fixed_cost + actual_power_cost + water_cost):,.0f} 원")

    # 7. 시각화
    col_chart, col_table = st.columns([2, 1])
    with col_chart:
        st.subheader("📊 비용 구성 비율")
        chart_data = pd.DataFrame({
            "항목": ["고정비(기계)", "전기요금", "냉각수"],
            "금액": [monthly_fixed_cost, actual_power_cost, water_cost]
        })
        st.bar_chart(chart_data.set_index("항목"))

    with col_table:
        st.subheader("📋 설비 리스트")
        st.dataframe(df_machines[['기계명', '취득원가']], hide_index=True)

except Exception as e:
    st.error(f"⚠️ 시트 연결 에러: {e}")
    st.warning("구글 시트의 탭 이름(machines, waterlogs, MachinesMonthlyEnergy, FactoryEnergyExpenses)을 다시 확인해주세요.")
