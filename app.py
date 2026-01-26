import streamlit as st
import pandas as pd
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. 페이지 설정
# -----------------------------------------------------------------------------
st.set_page_config(page_title="소성 비용 계산기", layout="wide")
st.title("🏭 설비 관리 및 비용 산출")
st.markdown("모든 설비의 내용연수는 **10년**을 기준으로 계산합니다.")

# -----------------------------------------------------------------------------
# 2. 데이터 로드 (공유 링크 방식)
# -----------------------------------------------------------------------------
# 👇 여기에 본인의 구글 시트 링크(CSV 변환된 것)를 넣어주세요
SHEET_URL = "https://docs.google.com/spreadsheets/d/1AdDEm4r3lOpjCzzeksJMiTG5Z2kjmif-xvrKvE5BmSY/export?format=csv"

@st.cache_data(ttl=600)
def load_data():
    # thousands=',' : 숫자 쉼표 자동 처리
    try:
        df = pd.read_csv(SHEET_URL, thousands=',')
        return df
    except Exception:
        return None

df = load_data()

# 데이터 로드 실패 혹은 필수 컬럼 확인
if df is None:
    st.error("데이터를 불러올 수 없습니다. 구글 시트 링크와 공유 설정(링크가 있는 모든 사용자 뷰어)을 확인해주세요.")
    st.stop()

# 시트의 컬럼 순서: 설비코드, 설비명, 구입일자, 취득원가
required_cols = ['설비코드', '설비명', '구입일자', '취득원가']
if not all(col in df.columns for col in required_cols):
    st.error(f"시트에서 다음 필수 컬럼을 찾을 수 없습니다: {required_cols}")
    st.write("현재 시트의 컬럼:", df.columns.tolist())
    st.stop()

# 날짜 변환
try:
    df['구입일자'] = pd.to_datetime(df['구입일자'])
except Exception as e:
    st.error("구입일자 형식이 올바르지 않은 데이터가 있습니다. (YYYY-MM-DD 형식 권장)")
    st.stop()

# -----------------------------------------------------------------------------
# 3. 핵심 계산 로직 (내용연수 10년 고정)
# -----------------------------------------------------------------------------
today = datetime.now()
end_of_year = datetime(today.year, 12, 31)
FIXED_LIFE_YEARS = 10  # 내용연수 10년 고정

def calculate_metrics(row):
    cost = row['취득원가']
    buy_date = row['구입일자']
    
    # 1. 연간 감가상각비 (10년 정액법)
    depreciation_per_year = cost / FIXED_LIFE_YEARS
    
    # 2. 경과 연수 계산
    days_passed = (today - buy_date).days
    years_passed = days_passed / 365.0
    
    # 3. 현재 감가상각 잔액 (0원 미만 불가)
    current_book_value = max(cost - (depreciation_per_year * years_passed), 0)
    
    # 4. 올해 말 기준 예상 잔가
    days_until_eoy = (end_of_year - buy_date).days
    years_until_eoy = days_until_eoy / 365.0
    eoy_book_value = max(cost - (depreciation_per_year * years_until_eoy), 0)
    
    # 5. 재구입 적립 필요 비용 (연간 감가상각비와 동일)
    replacement_fund_yearly = depreciation_per_year

    return pd.Series([current_book_value, eoy_book_value, replacement_fund_yearly])

# 계산 실행
df[['현재잔액', '올해말잔가', '연간적립필요액']] = df.apply(calculate_metrics, axis=1)

# -----------------------------------------------------------------------------
# 4. 화면 UI 구성
# -----------------------------------------------------------------------------

# [섹션 1] 요약 지표
st.subheader("📊 전체 설비 요약")
col1, col2, col3 = st.columns(3)

total_acquisition = df['취득원가'].sum()
total_current_value = df['현재잔액'].sum()
total_yearly_fund = df['연간적립필요액'].sum()

with col1:
    st.metric("총 취득 원가", f"{total_acquisition:,.0f} 원")
with col2:
    st.metric("현재 설비 총 잔액", f"{total_current_value:,.0f} 원", 
              delta=f"-{total_acquisition - total_current_value:,.0f} (감가상각 누계)")
with col3:
    st.metric("올해 적립 필요 총액", f"{total_yearly_fund:,.0f} 원",
              help="10년 교체 주기를 가정했을 때 올해 적립해야 할 금액의 합계")

st.divider()

# [섹션 2] 상세 리스트
st.subheader("📋 설비별 상세 현황")

# 표시용 데이터 복사 및 포맷팅
display_df = df.copy()
display_df['구입일자'] = display_df['구입일자'].dt.strftime('%Y-%m-%d')

def format_currency(x):
    return f"{x:,.0f} 원"

# 보여줄 컬럼 순서 지정
cols_to_show = ['설비코드', '설비명', '구입일자', '취득원가', '현재잔액', '올해말잔가', '연간적립필요액']

st.dataframe(
    display_df[cols_to_show].style.format({
        '취득원가': format_currency,
        '현재잔액': format_currency,
        '올해말잔가': format_currency,
        '연간적립필요액': format_currency
    }),
    use_container_width=True,
    hide_index=True
)
