import streamlit as st
import pandas as pd

st.set_page_config(page_title="Factory Cost Analyzer", layout="wide")
st.title("🏭 Vacuum Furnace Cost Dashboard")

# 1. 시트 ID를 여기에 넣어주세요 (주소창 d/와 /edit 사이 문자열)
SHEET_ID = "사용자님의_시트_ID_입력" 

def load_sheet(sheet_name):
    # 가장 안정적인 export 주소 방식 사용
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&sheet={sheet_name}"
    return pd.read_csv(url)

try:
    # 탭 이름 로드
    df_machines = load_sheet("Machines")
    df_water = load_sheet("Waterlogs")
    df_energy = load_sheet("MME")
    df_billing = load_sheet("FEE")

    st.success("✅ Connection Successful! (English Headers Detected)")

    # --- 계산 로직 (영문 컬럼 기준) ---
    
    # 1. 고정비 (Machines 탭)
    # price 열 사용, 10년(120개월) 감가상각
    if 'price' in df_machines.columns:
        df_machines['price'] = pd.to_numeric(df_machines['price'], errors='coerce')
        monthly_fixed_cost = df_machines['price'].sum() / 120
    else:
        monthly_fixed_cost = 0

    # 2. 분석 월 선택 (MME 탭의 date 기준)
    # date 컬럼의 고유값 추출
    if 'date' in df_energy.columns:
        available_months = df_energy['date'].dropna().unique()
        selected_month = st.sidebar.selectbox("Select Month", available_months)
        
        # 해당 월 데이터 필터링
        energy_row = df_energy[df_energy['date'] == selected_month]
        total_kwh = energy_row['amount'].iloc[0] if not energy_row.empty else 0
        
        # 3. 전기 요금 (FEE 탭)
        billing_row = df_billing[df_billing['date'] == selected_month]
        if not billing_row.empty:
            actual_fee = billing_row['fee'].iloc[0]
        else:
            actual_fee = total_kwh * 125 # 요금 데이터 없을 시 추정치
            
        # 4. 화면 출력
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Fixed Cost (Monthly)", f"{monthly_fixed_cost:,.0f} KRW")
        m2.metric("Power Usage", f"{total_kwh:,.1f} kWh")
        m3.metric("Electricity Fee", f"{actual_fee:,.0f} KRW")

        # 5. 데이터 시각화
        chart_data = pd.DataFrame({
            "Category": ["Depreciation", "Electricity"],
            "Amount": [monthly_fixed_cost, actual_fee]
        })
        st.bar_chart(chart_data.set_index("Category"))
        
    else:
        st.warning("Could not find 'date' column in MME sheet.")

except Exception as e:
    st.error(f"❌ Connection Error: {e}")
    st.info("Check if your Sheet ID is correct and 'Anyone with the link' can View.")
