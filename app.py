import streamlit as st
import pandas as pd
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="소성 비용 계산기", layout="wide")
st.title("🏭 설비 관리 및 비용 산출")

# -----------------------------------------------------------------------------
# 2. 데이터 로드 (공유 링크 방식 - CSV 변환)
# -----------------------------------------------------------------------------
# 여기에 변환한 URL을 넣으세요
SHEET_URL = "https://docs.google.com/spreadsheets/d/1AdDEm4r3lOpjCzzeksJMiTG5Z2kjmif-xvrKvE5BmSY/export?format=csv"

@st.cache_data(ttl=600)
def load_data():
    # thousands=',' 옵션: "5,000,000" 같은 문자를 자동으로 숫자 5000000으로 변환해 줌 (에러 방지 핵심)
    df = pd.read_csv(SHEET_URL, thousands=',') 
    return df

try:
    df = load_data()
    
    # 필수 컬럼 확인
    required_cols = ['설비코드', '설비명', '구입일자', '취득원가']
    if not all(col in df.columns for col in required_cols):
        st.error(f"시트에서 다음 컬럼을 찾을 수 없습니다: {required_cols}")
        st.stop()
        
    # 날짜 변환
    df['구입일자'] = pd.to_datetime(df['구입일자'])
    
except Exception as e:
    st.error("데이터를 불러오는 데 실패했습니다.")
    st.warning("팁: 구글 시트 공유 설정이 '링크가 있는 모든 사용자'로 되어 있는지 확인하세요.")
    st.code(SHEET_URL, language='text') # 어떤 링크를 시도했는지 보여줌
    st.stop()

# -----------------------------------------------------------------------------
# 3. 핵심 계산 로직 & 4. UI 구성 (이전과 동일)
# -----------------------------------------------------------------------------
# (이 아래 코드는 이전에 작성해드린 것과 완전히 똑같습니다. 복사해서 쓰시면 됩니다.)

today = datetime.now()
end_of_year = datetime(today.year, 12, 31)

def calculate_metrics(row):
    cost = row['취득원가']
    life_years = row['내용연수']
    buy_date = row['구입일자']
    
    if pd.isna(life_years) or life_years == 0:
        return pd.Series([0, 0, 0])

    depreciation_per_year = cost / life_years
    days_passed = (today - buy_date).days
    years_passed = days_passed / 365.0
    current_book_value = max(cost - (depreciation_per_year * years_passed), 0)
    
    days_until_eoy = (end_of_year - buy_date).days
    years_until_eoy = days_until_eoy / 365.0
    eoy_book_value = max(cost - (depreciation_per_year * years_until_eoy), 0)
    
    replacement_fund_yearly = depreciation_per_year

    return pd.Series([current_book_value, eoy_book_value, replacement_fund_yearly])

df[['현재잔액', '올해말잔가', '연간적립필요액']] = df.apply(calculate_metrics, axis=1)

# --- UI 표시 ---
st.subheader("📊 전체 설비 요약")
col1, col2, col3 = st.columns(3)

total_acquisition = df['취득원가'].sum()
total_current_value = df['현재잔액'].sum()
total_yearly_fund = df['연간적립필요액'].sum()

with col1:
    st.metric("총 취득 원가", f"{total_acquisition:,.0f} 원")
with col2:
    st.metric("현재 설비 총 잔액", f"{total_current_value:,.0f} 원", f"-{total_acquisition - total_current_value:,.0f}")
with col3:
    st.metric("올해 적립 필요 총액", f"{total_yearly_fund:,.0f} 원")

st.divider()

st.subheader("📋 설비별 상세 현황")
display_df = df.copy()
display_df['구입일자'] = display_df['구입일자'].dt.strftime('%Y-%m-%d')
def format_currency(x): return f"{x:,.0f} 원"

st.dataframe(
    display_df[['설비명', '구입일자', '내용연수', '취득원가', '현재잔액', '올해말잔가', '연간적립필요액']].style.format({
        '취득원가': format_currency,
        '현재잔액': format_currency,
        '올해말잔가': format_currency,
        '연간적립필요액': format_currency,
        '내용연수': '{} 년'
    }),
    use_container_width=True,
    hide_index=True
)
