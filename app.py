import streamlit as st
import pandas as pd
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. 페이지 설정
# -----------------------------------------------------------------------------
st.set_page_config(page_title="소성 비용 및 설비 관리", layout="wide")
st.title("🏭 공장 운영 관리 시스템")

# -----------------------------------------------------------------------------
# 2. 데이터 로드 설정 (여기에 링크를 넣어주세요!)
# -----------------------------------------------------------------------------
# [시트1] 설비 시트 (gid=0 보통 첫번째 시트)
URL_EQUIPMENT = "https://docs.google.com/spreadsheets/d/1AdDEm4r3lOpjCzzeksJMiTG5Z2kjmif-xvrKvE5BmSY/export?format=csv&gid=0"

# [시트2] 냉각수 시트 (gid=숫자 확인 필수!)
# 시트 아래 탭에서 '냉각수' 시트를 누른 뒤, 주소창 끝에 있는 gid 숫자를 확인하세요.
URL_COOLING = "https://docs.google.com/spreadsheets/d/1AdDEm4r3lOpjCzzeksJMiTG5Z2kjmif-xvrKvE5BmSY/export?format=csv&gid=12345678" 


@st.cache_data(ttl=600)
def load_data(url):
    try:
        # thousands=',' : 숫자 쉼표 자동 제거 (천단위 구분자 처리)
        df = pd.read_csv(url, thousands=',')
        return df
    except Exception:
        return None

# -----------------------------------------------------------------------------
# 3. 탭 구성
# -----------------------------------------------------------------------------
tab1, tab2 = st.tabs(["🏭 설비 감가상각", "💧 냉각수 사용량"])


# =============================================================================
# [탭 1] 설비 관리
# =============================================================================
with tab1:
    st.markdown("### 설비별 감가상각 및 재구입 비용 (내용연수 10년)")
    
    df_eq = load_data(URL_EQUIPMENT)
    
    if df_eq is None:
        st.error("설비 데이터를 불러올 수 없습니다. 링크를 확인해주세요.")
    else:
        # 필수 컬럼 체크
        req_cols_eq = ['설비코드', '설비명', '구입일자', '취득원가']
        if not all(col in df_eq.columns for col in req_cols_eq):
            st.error(f"설비 시트 필수 컬럼 누락: {req_cols_eq}")
        else:
            # 날짜 변환 및 계산
            df_eq['구입일자'] = pd.to_datetime(df_eq['구입일자'], errors='coerce')
            
            today = datetime.now()
            end_of_year = datetime(today.year, 12, 31)
            FIXED_LIFE = 10
            
            def calc_metrics(row):
                if pd.isna(row['구입일자']): return pd.Series([0, 0, 0])
                
                cost = row['취득원가']
                dep_yearly = cost / FIXED_LIFE
                
                # 경과 연수
                days_passed = (today - row['구입일자']).days
                curr_val = max(cost - (dep_yearly * (days_passed / 365.0)), 0)
                
                # 올해 말 기준
                days_eoy = (end_of_year - row['구입일자']).days
                eoy_val = max(cost - (dep_yearly * (days_eoy / 365.0)), 0)
                
                return pd.Series([curr_val, eoy_val, dep_yearly])

            df_eq[['현재잔액', '올해말잔가', '연간적립액']] = df_eq.apply(calc_metrics, axis=1)
            
            # 요약 지표
            c1, c2, c3 = st.columns(3)
            c1.metric("총 취득 원가", f"{df_eq['취득원가'].sum():,.0f} 원")
            c2.metric("현재 장부가 총액", f"{df_eq['현재잔액'].sum():,.0f} 원")
            c3.metric("연간 총 적립 필요액", f"{df_eq['연간적립액'].sum():,.0f} 원")
            
            st.divider()
