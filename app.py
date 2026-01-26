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
    eoy_book_value = max(cost - (
