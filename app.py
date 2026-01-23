import streamlit as st
import pandas as pd

st.set_page_config(page_title="Factory Cost Analyzer", layout="wide")
st.title("🏭 Vacuum Furnace Cost Dashboard")

# 1. 시트 ID 설정
SHEET_ID = "사용자님의_시트_ID_입력" 

def load_sheet(name):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&sheet={name}"
    return pd.read_csv(url)

try:
    # 2. 데이터 로드
    df_m = load_sheet("Machines")
    df_w = load_sheet("Waterlogs")
    df_e = load_sheet("MME")

    # 3. 데이터 전처리 (숫자 변환)
    for df, col in [(df_m, 'price'), (df_e, 'amount'), (df_e, 'fee'), (df_w, 'water(m3)')]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

    # 4. 비용 계산
    fixed_cost = df_m['price'].sum() / 120

    if 'date' in df_e.columns:
        months = df_e['date'].dropna().unique()
        sel_month = st.sidebar.selectbox("Select Month", months)
        
        e_row = df_e[df_e['date'] == sel_month]
        kwh = e_row['amount'].iloc[0] if not e_row.empty else 0
        
        # 전기요금 (fee가 0이면 추정치 사용)
        if not e_row.empty and 'fee' in e_row.columns and e_row['fee'].iloc[0] > 0:
            fee = e_row['fee'].iloc[0]
            method = "Actual"
        else:
            fee = kwh * 125 
            method = "Estimated"

        # 냉각수 비용
        w_val = 0
        if 'water(m3)' in df_w.columns:
            df_w['date'] = df_w['date'].astype(str)
            w_match = df_w[df_w['date'].str.contains(str(sel_month), na=False)]
            w_val = w_match['water(m3)'].sum()
        
        w_cost = w_val * 1200 

        # 5. 대시보드 출력
        st.info(f"📅 Month: {sel_month} | Fee: {method}")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Fixed Cost", f"{fixed_cost:,.0f} KRW")
        c2.metric("Power", f"{kwh:,.1f} kWh")
        c3.metric("Electric Fee", f"{fee:,.0f} KRW")
        total = fixed_cost + fee + w_cost
        c4.metric("Total Cost", f"{total:,.0f} KRW")

        # 6. 차트
        st.subheader("Cost Breakdown")
        chart_df = pd.DataFrame({
            "Category": ["Fixed", "Electric", "Water"],
            "Amount": [fixed_cost, fee, w_cost]
        })
        st.bar_chart(chart_df.set_index("Category"))
        
except Exception as e:
    st.error(f"❌ Connection Error: {e}")
