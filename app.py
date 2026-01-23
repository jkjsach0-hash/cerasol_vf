import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. 페이지 설정
st.set_page_config(page_title="공장 소성 비용 분석기", layout="wide")
st.title("🏭 진공로 소성 비용 통합 대시보드")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # 3. 변경된 탭 이름으로 데이터 로드
    # 캐시를 사용하여 로딩 속도를 높이고 안정성을 확보합니다.
    @st.cache_data(ttl=300)
    def load_data():
        d1 = conn.read(worksheet="Machines")
        d2 = conn.read(worksheet="Waterlogs")
        d3 = conn.read(worksheet="MME")
        d4 = conn.read(worksheet="FEE")
        return d1, d2, d3, d4

    df_machines, df_water, df_energy, df_billing = load_data()

    # 데이터 로드 성공 메시지
    st.success("✅ 모든 데이터 시트(Machines, Waterlogs, MME, FEE) 연결 성공!")

    # --- 데이터 전처리 ---
    df_water['날짜'] = pd.to_datetime(df_water['날짜'], errors='coerce')
    df_machines['취득원가'] = pd.to_numeric(df_machines['취득원가'], errors='coerce')
    df_energy['전력량'] = pd.to_numeric(df_energy['전력량'], errors='coerce')
    df_billing['전기요금'] = pd.to_numeric(df_billing['전기요금'], errors='coerce')

    # 4. 사이드바: 분석 월 선택 (MME 시트의 '월' 열 기준)
    st.sidebar.header("🗓️ 기간 설정")
    available_months = df_energy['월'].dropna().unique()
    selected_month = st.sidebar.selectbox("조회할 월을 선택하세요", available_months)
    
    # 5. 비용 계산 로직
    # (1) 기계 고정비 (취득원가 합계 / 120개월)
    fixed_cost = (df_machines['취득원가'].sum() / 120)

    # (2) 전력량 및 전기요금 (MME와 FEE 시트 매칭)
    energy_row = df_energy[df_energy['월'] == selected_month]
    total_kwh = energy_row['전력량'].iloc[0] if not energy_row.empty else 0
    
    billing_row = df_billing[df_billing['월'] == selected_month]
    if not billing_row.empty and pd.notnull(billing_row['전기요금'].iloc[0]):
        actual_power_cost = billing_row['전기요금'].iloc[0]
        calc_note = "실제 청구 요금"
    else:
        actual_power_cost = total_kwh * 125 # 실제 요금 없을 시 추정 단가
        calc_note = "추정 요금 (단가 125원)"

    # (3) 냉각수 비용 (Waterlogs 기반 - 월 평균 추정)
    # 선택된 월 형식이 '2023.12' 등일 경우를 대비해 변환
    match_month = str(selected_month).replace('.', '-')
    df_water['월_match'] = df_water['날짜'].dt.to_period('M').astype(str)
    monthly_water = df_water[df_water['월_match'].str.contains(match_month, na=False)]
    
    if not monthly_water.empty:
        water_usage = monthly_water['냉각수사용량(m3)'].mean() * 30
    else:
        water_usage = 0
    water_cost = water_usage * 1200 # m3당 1,200원

    # 6. 메인 화면 대시보드
    st.info(f"💡 현재 **{selected_month}** 분석 중 | 전기료 적용 방식: **{calc_note}**")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("기계 감가상각", f"{fixed_cost:,.0f} 원")
    m2.metric("전력 사용량", f"{total_kwh:,.1f} kWh")
    m3.metric("전기 요금", f"{actual_power_cost:,.0f} 원")
    m4.metric("총 합계 비용", f"{(fixed_cost + actual_power_cost + water_cost):,.0f} 원")

    # 7. 그래프 시각화
    st.subheader("📊 비용 항목별 비중")
    chart_df = pd.DataFrame({
        "항목": ["기계비용", "전기료", "냉각수(추정)"],
        "금액": [fixed_cost, actual_power_cost, water_cost]
    })
    st.bar_chart(chart_df.set_index("항목"))

except Exception as e:
    st.error(f"❌ 에러 발생: {e}")
    st.info("시트 탭 이름(Machines, Waterlogs, MME, FEE)과 컬럼명이 정확한지 다시 확인해 주세요.")
