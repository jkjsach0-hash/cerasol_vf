import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. 앱 페이지 설정
st.set_page_config(page_title="공장 소성 비용 분석기", layout="wide")
st.title("🏭 진공로 소성 비용 통합 대시보드")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # 3. 데이터 시트 읽기 (탭 이름 대소문자 정확히 일치시킴)
    # machines -> Machines 로 수정됨
    df_machines = conn.read(worksheet="Machines")
    df_water = conn.read(worksheet="waterlogs")
    df_energy = conn.read(worksheet="MachinesMonthlyEnergy")
    df_billing = conn.read(worksheet="FactoryEnergyExpenses")

    # --- 데이터 전처리 ---
    # 날짜 형식을 안전하게 변환
    df_water['날짜'] = pd.to_datetime(df_water['날짜'], errors='coerce')
    
    # 숫자로 변환 (문자가 섞여있을 경우를 대비)
    df_machines['취득원가'] = pd.to_numeric(df_machines['취득원가'], errors='coerce')
    df_energy['전력량'] = pd.to_numeric(df_energy['전력량'], errors='coerce')
    df_billing['전기요금'] = pd.to_numeric(df_billing['전기요금'], errors='coerce')

    # 4. 사이드바: 분석 월 선택
    st.sidebar.header("🗓️ 기간 설정")
    # MachinesMonthlyEnergy 탭의 '월' 열 기준
    available_months = df_energy['월'].dropna().unique()
    selected_month = st.sidebar.selectbox("조회할 월을 선택하세요", available_months)
    
    # 5. 비용 계산 로직
    # (1) 기계 고정비: 120개월 분할
    monthly_fixed_cost = (df_machines['취득원가'].sum() / 120)

    # (2) 전력량 및 전기요금
    energy_row = df_energy[df_energy['월'] == selected_month]
    total_kwh = energy_row['전력량'].iloc[0] if not energy_row.empty else 0
    
    billing_row = df_billing[df_billing['월'] == selected_month]
    if not billing_row.empty and pd.notnull(billing_row['전기요금'].iloc[0]):
        actual_power_cost = billing_row['전기요금'].iloc[0]
    else:
        actual_power_cost = total_kwh * 125 # 실제 요금 없을 때 기본 단가 적용

    # (3) 냉각수 비용 (월 단위 매칭)
    selected_month_str = str(selected_month).replace('.', '-')
    df_water['월_match'] = df_water['날짜'].dt.to_period('M').astype(str)
    monthly_water = df_water[df_water['월_match'].str.contains(selected_month_str, na=False)]
    
    if not monthly_water.empty:
        total_water_usage = monthly_water['냉각수사용량(m3)'].mean() * 30
    else:
        total_water_usage = 0
    water_cost = total_water_usage * 1200

    # 6. 결과 화면
    st.success(f"✅ {selected_month} 데이터 로드 완료")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("기계 감가상각", f"{monthly_fixed_cost:,.0f} 원")
    m2.metric("전력 사용량", f"{total_kwh:,.1f} kWh")
    m3.metric("전기 요금", f"{actual_power_cost:,.0f} 원")
    m4.metric("총 소성 비용", f"{(monthly_fixed_cost + actual_power_cost + water_cost):,.0f} 원")

    # 7. 시각화
    st.subheader("📊 항목별 비용 비중")
    chart_data = pd.DataFrame({
        "항목": ["기계비용", "전기료", "냉각수"],
        "금액": [monthly_fixed_cost, actual_power_cost, water_cost]
    })
    st.bar_chart(chart_data.set_index("항목"))

except Exception as e:
    st.error(f"⚠️ 에러 발생: {e}")
    st.info("Secrets에 주소가 잘 입력되었는지, 시트 공유가 '전체 공개'인지 다시 확인해 주세요.")
