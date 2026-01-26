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

# =============================================================================
# [탭 2] 냉각수 관리 (3개년 비교 업그레이드)
# =============================================================================
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
            
            # 2. 피벗 테이블 생성 (행: 월, 열: 연도, 값: 사용량)
            # 23, 24, 25년 데이터가 자동으로 각각의 열이 됩니다.
            pivot_df = df_cool.pivot_table(index='월', columns='연도', values='사용량', aggfunc='sum')
            
            # 1월~12월이 모두 표시되도록 강제 설정 (데이터 없는 달은 0 처리)
            pivot_df = pivot_df.reindex(range(1, 13), fill_value=0)
            
            # 3. 연간 총 사용량 요약 (상단 KPI)
            # 존재하는 모든 연도에 대해 메트릭 표시
            years = pivot_df.columns.tolist() # [2023, 2024, 2025] 등
            cols = st.columns(len(years)) # 연도 개수만큼 컬럼 생성
            
            for i, year in enumerate(years):
                total_usage = pivot_df[year].sum()
                with cols[i]:
                    st.metric(label=f"{year}년 총 사용량", value=f"{total_usage:,.0f}")
            
            st.divider()

            # 4. 비교 그래프 (Line Chart)
            st.subheader("📈 연도별 월간 추이 그래프")
            st.line_chart(pivot_df)
            st.caption("색상별로 다른 연도를 나타냅니다. 마우스를 올리면 상세 수치를 볼 수 있습니다.")
            
            st.markdown("---")

            # 5. 상세 비교표 (아래 배치)
            st.subheader("📋 월별 상세 비교표")
            
            # 표를 예쁘게 보여주기 위해 컬럼명 변경 (2023 -> "2023년")
            display_df = pivot_df.copy()
            display_df.columns = [f"{y}년" for y in display_df.columns]
            
            # 인덱스 이름(월)에 '월' 글자 붙이기
            display_df.index = [f"{m}월" for m in display_df.index]
            
            # 월별 사용량이 가장 많은 셀에 하이라이트 (시각적 효과)
            st.dataframe(
                display_df.style.format("{:,.0f}").highlight_max(axis=1, color='#FFDDC1'),
                use_container_width=True
            )
