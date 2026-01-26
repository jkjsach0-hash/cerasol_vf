import streamlit as st
import pandas as pd
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. 페이지 설정
# -----------------------------------------------------------------------------
st.set_page_config(page_title="공장 비용 관리", layout="wide")
st.title("🏭 공장 운영 관리 시스템")

# -----------------------------------------------------------------------------
# 2. 데이터 로드 설정 (⚠️ 본인 링크로 수정 필수)
# -----------------------------------------------------------------------------
# [시트1] 설비 시트
URL_EQUIPMENT = "https://docs.google.com/spreadsheets/d/1AdDEm4r3lOpjCzzeksJMiTG5Z2kjmif-xvrKvE5BmSY/export?format=csv&gid=0"

# [시트2] 냉각수 시트
URL_COOLING = "https://docs.google.com/spreadsheets/d/1AdDEm4r3lOpjCzzeksJMiTG5Z2kjmif-xvrKvE5BmSY/export?format=csv&gid=1052812012" 

@st.cache_data(ttl=600)
def load_data(url):
    try:
        df = pd.read_csv(url, thousands=',')
        return df
    except Exception:
        return None

# -----------------------------------------------------------------------------
# 3. 탭 구성
# -----------------------------------------------------------------------------
tab1, tab2 = st.tabs(["🏭 설비 감가상각", "💧 냉각수 관리"])

# =============================================================================
# [탭 1] 설비 관리 (기존 내용 유지)
# =============================================================================
with tab1:
    st.markdown("### 설비별 감가상각 및 재구입 비용")
    df_eq = load_data(URL_EQUIPMENT)
    
    if df_eq is None:
        st.error("설비 데이터를 불러올 수 없습니다.")
    else:
        req_cols_eq = ['설비코드', '설비명', '구입일자', '취득원가']
        if not all(col in df_eq.columns for col in req_cols_eq):
            st.error(f"필수 컬럼 누락: {req_cols_eq}")
        else:
            df_eq['구입일자'] = pd.to_datetime(df_eq['구입일자'], errors='coerce')
            today = datetime.now()
            end_of_year = datetime(today.year, 12, 31)
            FIXED_LIFE = 10
            
            def calc_metrics(row):
                if pd.isna(row['구입일자']): return pd.Series([0, 0, 0])
                cost = row['취득원가']
                dep_yearly = cost / FIXED_LIFE
                days_passed = (today - row['구입일자']).days
                curr_val = max(cost - (dep_yearly * (days_passed / 365.0)), 0)
                days_eoy = (end_of_year - row['구입일자']).days
                eoy_val = max(cost - (dep_yearly * (days_eoy / 365.0)), 0)
                return pd.Series([curr_val, eoy_val, dep_yearly])

            df_eq[['현재잔액', '올해말잔가', '연간적립액']] = df_eq.apply(calc_metrics, axis=1)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("총 취득 원가", f"{df_eq['취득원가'].sum():,.0f} 원")
            c2.metric("현재 장부가 총액", f"{df_eq['현재잔액'].sum():,.0f} 원")
            c3.metric("올해 적립 필요액", f"{df_eq['연간적립액'].sum():,.0f} 원")
            
            st.divider()
            
            show_df = df_eq.copy()
            show_df['구입일자'] = show_df['구입일자'].dt.strftime('%Y-%m-%d')
            st.dataframe(
                show_df[['설비명', '구입일자', '취득원가', '현재잔액', '올해말잔가', '연간적립액']].style.format("{:,.0f}", subset=['취득원가', '현재잔액', '올해말잔가', '연간적립액']),
                use_container_width=True, hide_index=True
            )

with tab2:
    st.markdown("### 📊 연도별 냉각수 사용량 추이 및 비교")
    
    df_cool = load_data(URL_COOLING)
    
    if df_cool is None:
        st.info("데이터 로드 실패. 링크와 GID를 확인하세요.")
    else:
        if '날짜' not in df_cool.columns or '사용량' not in df_cool.columns:
             st.error("컬럼 오류: '날짜', '사용량' 컬럼이 필요합니다.")
        else:
            # 1. 데이터 전처리
            df_cool['날짜'] = pd.to_datetime(df_cool['날짜'], errors='coerce')
            df_cool = df_cool.dropna(subset=['날짜'])
            
            df_cool['연도'] = df_cool['날짜'].dt.year
            df_cool['월'] = df_cool['날짜'].dt.month
            
            # 2. 피벗 데이터 생성 (차트용: 인덱스=월, 컬럼=연도)
            pivot_data = df_cool.pivot_table(index='월', columns='연도', values='사용량', aggfunc='sum')
            pivot_data = pivot_data.reindex(range(1, 13), fill_value=0) # 1~12월 강제 고정
            
            # 3. KPI (연간 총 사용량)
            years = pivot_data.columns.tolist()
            cols = st.columns(len(years))
            for i, year in enumerate(years):
                total_usage = pivot_data[year].sum()
                with cols[i]:
                    st.metric(label=f"{year}년 총 사용량", value=f"{total_usage:,.0f}")
            
            st.divider()

            # 4. 비교 그래프 (차트는 월별 흐름을 봐야 하므로 기존 축 유지)
            st.subheader("📈 연도별 월간 추이 그래프")
            st.line_chart(pivot_data)
            
            st.markdown("---")

            # 5. 상세 비교표 (✨요청사항 적용: 행=연도, 열=월)
            st.subheader("📋 연도별 월간 상세 비교표")
            
            # 행과 열을 뒤집습니다 (.T : Transpose)
            table_df = pivot_data.T
            
            # 컬럼명 (1, 2, 3...) -> (1월, 2월, 3월...)
            table_df.columns = [f"{m}월" for m in table_df.columns]
            
            # 행 인덱스 (2023, 2024...) -> (2023년, 2024년...)
            table_df.index = [f"{y}년" for y in table_df.index]
            
            # 테이블 표시 (highlight_max(axis=0) : 세로로 비교했을 때(같은 월끼리) 가장 큰 값 강조)
            st.dataframe(
                table_df.style.format("{:,.0f}").highlight_max(axis=0, color='#FFDDC1'),
                use_container_width=True
            )
