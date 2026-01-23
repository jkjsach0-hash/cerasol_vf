import streamlit as st
import pandas as pd

# 1. 페이지 설정
st.set_page_config(page_title="Factory Cost Analyzer", layout="wide")
st.title("🏭 Vacuum Furnace Cost Dashboard")

# 2. 시트 ID 설정
SHEET_ID = "사용자님의_시트_ID_입력" 

def load_sheet(sheet_name):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&sheet={sheet_name}"
    return pd.read_csv(url)

try:
    # 3. 탭 로드
    df_machines = load_sheet("Machines")
    df_water = load_sheet("Waterlogs")
    df_energy = load_sheet("MME")

    # --- 데이터 전처리 ---
    # 숫자가 들어갈 자리에 문자가 섞여있을 경우를 대비해 정제
    for df in [df_machines, df_energy, df_water]:
        for col in ['price', 'amount', 'fee', 'water(m3)']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].toString().replace(',', ''), errors='coerce').fillna(0)

    # 4. 비용 계산 로직
    # (1) 고정비 (Machines)
    monthly_fixed_cost = df_machines['price'].sum() / 120

    # (2) 월 선택 (MME)
    if 'date' in df_energy.columns:
        available_months = df_energy['date'].dropna().unique()
        selected_month = st.sidebar.selectbox("Select Month", available_months)
        
        energy_row = df_energy[df_energy['date'] == selected_month]
        total_kwh = energy_row['amount'].iloc[0] if not energy_row.empty else 0
        
        # --- 전기요금 결정 로직 ---
        # 시트에 fee가 없거나 0인 경우 추정치(kWh당 125원) 사용
        actual_fee = 0
        fee_method = ""
        
        if not energy_row.empty and 'fee' in energy_row.columns and energy_row['fee'].iloc[0] > 0:
            actual_fee = energy_row['fee'].iloc[0]
            fee_method = "Actual Bill"
        else:
            actual_fee = total_kwh * 125  # 단가 수정 가능
            fee_method = "Estimated (125\원/kWh)"

        # (3) 냉각수 비용 (Waterlogs)
        water_usage = 0
        if 'water(m3)' in df_water.columns:
            df_water['date'] = df_water['date'].astype(str)
            monthly_water = df_water[df_water['date'].str.contains(str(selected_month))]
            water_usage = monthly_water['water(m3)'].sum()
        
        water_cost = water_usage * 1200 

        # 5. 결과 출력
        st.info(f"📅 Analyzing **{selected_month}** | Fee Logic: **{fee_method}**")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Fixed Cost", f"{monthly_fixed_cost:,.0f} KRW")
        m2.metric("Power Usage", f"{total_kwh:,.1f} kWh")
        m3.metric("Electricity Fee", f"{actual_fee:,.0f} KRW")
        m4.metric("Total Cost", f"{(monthly_fixed_cost + actual_fee + water_cost):,.0f} KR
