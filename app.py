import streamlit as st
import pandas as pd

st.set_page_config(page_title="공장 소성 비용 분석기", layout="wide")
st.title("🏭 진공로 소성 비용 (강제 연결 모드)")

# 1. 시트 아이디 설정 (주소창의 d/ 와 /edit 사이의 문자열)
# 예: https://docs.google.com/spreadsheets/d/1ABCDEFG/edit -> ID는 1ABCDEFG
SHEET_ID = "여기에_사용자님의_시트_ID만_넣으세요" 

@st.cache_data
def load_data(sheet_name):
    # 구글 시트를 CSV로 강제 변환해서 읽어오는 주소입니다.
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    return pd.read_csv(url)

try:
    # 탭 이름 정확히 입력 (Machines, Waterlogs, MME, FEE)
    df_machines = load_data("Machines")
    df_water = load_data("Waterlogs")
    df_energy = load_data("MME")
    df_billing = load_data("FEE")

    st.success("✅ 강제 연결 성공!")
    
    # 데이터 확인용 (성공하면 나중에 지우셔도 됩니다)
    st.write("### 데이터 로드 확인")
    st.dataframe(df_machines.head(2))

    # --- 여기서부터는 이전과 동일한 계산 로직 ---
    # (코드가 너무 길어지면 헷갈리니 일단 로드 성공부터 확인합시다)

except Exception as e:
    st.error(f"❌ 마지막 시도 실패: {e}")
    st.info("구글 시트에서 [공유] -> [링크가 있는 모든 사용자]가 '뷰어' 이상인지 꼭 확인해주세요.")
