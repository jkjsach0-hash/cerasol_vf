import streamlit as st
import pandas as pd

st.set_page_config(page_title="진공로 비용 분석", layout="wide")

# 1. 시트 ID를 여기에 넣어주세요 (주소창의 d/ 와 /edit 사이 문자열)
# 예: 1abc123...
SHEET_ID = "사용자님의_시트_ID_입력" 

def load_sheet(sheet_name):
    # 가장 에러가 적은 'export' 주소 방식을 사용합니다.
    # 한글 탭 이름을 파이썬이 안전하게 읽도록 처리합니다.
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&sheet={sheet_name}"
    return pd.read_csv(url)

try:
    st.write("🔄 데이터 연결 시도 중...")
    
    # 탭 이름 매칭 (Machines, Waterlogs, MME, FEE)
    df_machines = load_sheet("Machines")
    df_water = load_sheet("Waterlogs")
    df_energy = load_sheet("MME")
    df_billing = load_sheet("FEE")

    st.success("✅ 드디어 연결되었습니다!")

    # --- 화면 구성 ---
    tab1, tab2 = st.tabs(["📊 비용 분석", "📋 원본 데이터"])

    with tab1:
        # 감가상각 계산
        if '취득원가' in df_machines.columns:
            price_sum = pd.to_numeric(df_machines['취득원가'], errors='coerce').sum()
            monthly_depreciation = price_sum / 120
            st.metric("월 고정비 (감가상각)", f"{monthly_depreciation:,.0f} 원")
        
        # MME(전력량) 데이터 확인
        if not df_energy.empty:
            st.write("### 월별 전력량 추이")
            st.line_chart(df_energy.set_index('월')['전력량'])

    with tab2:
        st.write("### Machines 시트 내용")
        st.dataframe(df_machines)

except Exception as e:
    st.error(f"❌ 연결 실패 메시지: {e}")
    st.info("시트 ID가 정확한지, 그리고 시트가 '링크가 있는 모든 사용자에게 뷰어'로 공개되었는지 다시 확인해주세요.")
