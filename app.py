import streamlit as st
import pandas as pd

# 1. 페이지 설정
st.set_page_config(page_title="Factory Cost Analyzer", layout="wide")
st.title("🏭 Vacuum Furnace Cost Dashboard")

# 2. 시트 ID 설정 (사용자님의 시트 ID를 여기에 정확히 넣어주세요)
SHEET_ID = "사용자님의_시트_ID_입력" 

def load_sheet(sheet_name):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&sheet={sheet_name}"
    return pd.read_csv(url)

try:
    # 3. 데이터 로드
    df_machines = load_sheet("Machines")
    df_water = load_sheet("Waterlogs")
    df_energy = load_sheet("MME")

    # --- 데이터 전처리 (숫자 변환) ---
    def clean_val(df, col):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        return df

    df_machines = clean_val(df_machines, 'price')
    df_energy = clean_val(df_energy, 'amount')
    df_energy = clean_val(df_energy, 'fee')
    df_water = clean_val(df_water, 'water(m3)')

    # 4. 비용 계산
    # (1) 고정비 (Machines)
    monthly_fixed_cost = df_machines['price'].sum() / 120

    # (2) 월 선택 및 에너지 비용 (MME)
    if 'date' in df_energy.columns:
        available_months = df_energy['date'].dropna().unique()
        selected_month = st.sidebar.selectbox("Select Month", available_months)
        
        energy_row = df_energy[df_energy['date'] == selected_month]
        total_kwh = energy_row['amount'].iloc[0] if not energy_row.empty else 0
        
        # 전기요금 판별
        if not energy_row.empty and 'fee' in energy_row.columns and energy_row['fee'].iloc[0] > 0:
            actual_fee = energy_row['fee'].iloc[0]
            fee_method = "Actual Bill"
        else:
            actual_fee = total_kwh * 125 
            fee_method = "Estimated (125 KRW/kWh)"

        # (3) 냉각수 비용 (Waterlogs)
        water_usage = 0
        if 'water(m3)' in df_water.columns:
            df_water['date'] = df_water['date'].astype(str)
            monthly_water = df_water[df
