import streamlit as st
import pandas as pd

# 1. 페이지 설정
st.set_page_config(page_title="Factory Cost Analyzer", layout="wide")
st.title("🏭 Vacuum Furnace Cost Dashboard")

# 2. 시트 ID 설정 (사용자님의 시트 ID를 입력하세요)
SHEET_ID = "사용자님의_시트_ID_입력" 

def load_sheet(sheet_name):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&sheet={sheet_name}"
    return pd.read_csv(url)

try:
    # 3. 데이터 로드
    df_machines = load_sheet("Machines")
    df_water = load_sheet("Waterlogs")
    df_energy = load_sheet("MME")

    # --- 데이터 전처리 (숫자 변환 및 콤마 제거) ---
    def clean_numeric(series):
        return pd.to_numeric(series.astype(str).str.replace(',', ''), errors='coerce').fillna(0)

    if 'price' in df_machines.columns:
        df_machines['price'] = clean_numeric(df_machines['price'])
    if 'amount' in df_energy.columns:
        df_energy['amount'] = clean_numeric(df_energy['amount'])
    if 'fee' in df_energy.columns:
        df_energy['fee'] = clean_numeric(df_energy['fee'])
    if 'water(m3)' in df_water.columns:
        df_water['water(m3)'] = clean_numeric(df_water['water(m3)'])

    # 4. 비용 계산
    # (1) 고정비
    monthly_fixed_cost = df_machines['price'].sum() / 120

    # (2) 월 선택 및 에너지 비용
    if 'date' in df_energy.columns:
        available_months = df_energy['date'].dropna().unique()
        selected_month = st.sidebar.selectbox("Select Month", available_months)
        
        energy_row = df_energy[df_energy['date'] == selected_month]
        total_kwh = energy_row['amount'].iloc[0] if not energy_row.empty else 0
        
        # 전기요금: fee가 0보다 크면 실제 금액, 아니면 추정치
        if not energy_row.empty and 'fee' in energy_row.columns and energy_row['fee'].iloc[0] > 0:
            actual_fee = energy_row['fee'].iloc[0]
            fee_method = "Actual Bill"
        else:
            actual_fee = total_kwh * 125 
            fee_method = "Estimated (125 KRW/kWh)"

        # (3) 냉각수 비용
        water_usage = 0
        if 'water(m3)' in df_water.columns:
            df_water['date'] = df_water['date'].astype(str)
            monthly_water = df_water[df_water['date'].str.contains(str(selected_month), na=False)]
            water_usage = monthly_water['water(m3)'].sum()
        
        water_cost = water_usage * 1200 

        # 5. 결과 대시보드 출력
        st.info(f"📅 Analyzing **{selected_month}** | Fee Logic: **{fee_method}**")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Fixed Cost", f"{monthly_fixed_cost:,.0f} KRW")
        m2.metric("Power Usage", f"{total_kwh:,.1f} kWh")
        m3.metric("Electricity Fee", f"{actual_fee:,.0f} KRW")
        m4.
