import streamlit as st
import pandas as pd
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. 페이지 설정
# -----------------------------------------------------------------------------
st.set_page_config(page_title="공장 비용 관리", layout="wide")
st.title("🏭 공장 운영 관리 시스템")

# -----------------------------------------------------------------------------
# 2. 데이터 로드 설정 (링크 입력 필요)
# -----------------------------------------------------------------------------
# [시트1] 설비 시트 (gid=0)
URL_EQUIPMENT = "https://docs.google.com/spreadsheets/d/1AdDEm4r3lOpjCzzeksJMiTG5Z2kjmif-xvrKvE5BmSY/export?format=csv&gid=0"

# [시트2] 냉각수 시트 (gid 확인 필수)
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
# [탭 1] 설비 관리 (기존 유지)
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
# [탭 2] 냉각수 관리 (업그레이드: 전년 vs 금년 비교)
# =============================================================================
with tab2:
    st.markdown("### 📊 연도별 냉각수 사용량 비교")
    
    df_cool = load_data(URL_COOLING)
    
    if df_cool is None:
        st.info("데이터 로드 실패. 링크와 GID를 확인하세요.")
    else:
        req_cols_cool = ['날짜', '사용량']
        if not all(col in df_cool.columns for col in req_cols_cool):
             st.error("컬럼 오류: '날짜', '사용량' 컬럼이 필요합니다.")
        else:
            # 1. 데이터 전처리
            df_cool['날짜'] = pd.to_datetime(df_cool['날짜'], errors='coerce')
            df_cool = df_cool.dropna(subset=['날짜'])
            
            # 연도와 월 추출
            df_cool['연도'] = df_cool['날짜'].dt.year
            df_cool['월'] = df_cool['날짜'].dt.month
            
            # 2. 현재 연도와 전년도 설정
            current_year = datetime.now().year
            prev_year = current_year - 1
            
            # 3. 데이터 분리 및 집계
            df_yearly = df_cool.groupby('연도')['사용량'].sum()
            
            usage_this_year = df_yearly.get(current_year, 0)
            usage_prev_year = df_yearly.get(prev_year, 0)
            
            # 증감 계산
            delta = usage_this_year - usage_prev_year
            
            # --- 상단 지표 (Metrics) ---
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric(label=f"{current_year}년 총 사용량 (현재까지)", 
                          value=f"{usage_this_year:,.0f}", 
                          delta=f"{delta:,.0f} (전년 총합 대비)", delta_color="off")
            with m2:
                st.metric(label=f"{prev_year}년 총 사용량", 
                          value=f"{usage_prev_year:,.0f}")
            with m3:
                # 전년 동기간 대비 비교 (데이터가 충분할 경우 더 정확하겠지만 여기선 단순 비교)
                if usage_prev_year > 0:
                    ratio = (usage_this_year / usage_prev_year) * 100
                    st.metric(label="전년 대비 비율", value=f"{ratio:.1f}%")

            st.divider()

            # 4. 차트용 데이터 가공 (Pivot)
            # 인덱스: 1~12월, 컬럼: 연도, 값: 사용량 합계
            pivot_df = df_cool.pivot_table(index='월', columns='연도', values='사용량', aggfunc='sum')
            
            # 차트에 모든 월(1~12)이 표시되도록 빈 데이터 채우기
            all_months = pd.DataFrame({'월': range(1, 13)}).set_index('월')
            chart_data = all_months.join(pivot_df).fillna(0)
            
            # 필요한 연도만 선택 (전년, 금년) - 데이터가 없어도 에러 안 나게 처리
            cols_to_show = []
            if prev_year in chart_data.columns: cols_to_show.append(prev_year)
            if current_year in chart_data.columns: cols_to_show.append(current_year)
            
            final_chart_data = chart_data[cols_to_show]

            # --- 메인 화면 분할 (왼쪽: 차트, 오른쪽: 상세표) ---
            col_chart, col_table = st.columns([2, 1])
            
            with col_chart:
                st.subheader(f"📈 {prev_year}년 vs {current_year}년 월별 비교")
                # 스트림릿 내장 라인 차트 (색상으로 연도 구분)
                st.line_chart(final_chart_data)
                st.caption("💡 팁: 차트 위에 마우스를 올리면 상세 수치를 볼 수 있습니다.")

            with col_table:
                st.subheader("📋 월별 상세 데이터")
                # 보기 좋게 포맷팅
                display_table = final_chart_data.copy()
                # 컬럼 이름을 문자열로 변환 (2024 -> "2024년")
                display_table.columns = [f"{c}년" for c in display_table.columns]
                
                st.dataframe(
                    display_table.style.format("{:,.0f}"),
                    use_container_width=True
                )
