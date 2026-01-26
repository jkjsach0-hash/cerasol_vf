import streamlit as st
import pandas as pd
from datetime import datetime
import time

# -----------------------------------------------------------------------------
# 1. 페이지 설정 (가장 먼저 실행되어야 함)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="공장 비용 관리", layout="wide")

# -----------------------------------------------------------------------------
# 2. 비밀번호 인증 함수
# -----------------------------------------------------------------------------
def check_password():
    """비밀번호가 맞는지 확인하는 함수"""
    
    # 세션에 인증 완료 기록이 없으면
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    # 인증이 완료된 상태라면 True 반환
    if st.session_state["password_correct"]:
        return True

    # 화면에 로그인 창 표시
    st.title("🔒 로그인")
    st.write("관계자 외 접근 금지 구역입니다.")
    
    password_input = st.text_input("비밀번호를 입력하세요", type="password")
    
    if st.button("접속"):
        # secrets.toml에 설정한 비밀번호와 비교
        if password_input == st.secrets["password"]:
            st.session_state["password_correct"] = True
            st.success("인증 성공! 시스템에 접속합니다...")
            time.sleep(1) # 잠시 대기 후 리로드
            st.rerun()
        else:
            st.error("비밀번호가 올바르지 않습니다.")
            
    return False

# -----------------------------------------------------------------------------
# 3. 메인 로직 실행 (로그인 통과 시에만 실행됨)
# -----------------------------------------------------------------------------
if not check_password():
    st.stop()  # 비밀번호가 틀리거나 입력 전이면 여기서 코드 실행 중단

# =============================================================================
# ▼ 여기서부터는 로그인 성공 시에만 보이는 화면입니다 ▼
# =============================================================================

st.title("🏭 공장 운영 관리 시스템")

# -----------------------------------------------------------------------------
# 4. 데이터 로드 설정 (⚠️ 본인 링크로 수정 필수)
# -----------------------------------------------------------------------------
# [시트1] 설비 시트
URL_EQUIPMENT = "https://docs.google.com/spreadsheets/d/1AdDEm4r3lOpjCzzeksJMiTG5Z2kjmif-xvrKvE5BmSY/export?format=csv&gid=0"

# [시트2] 냉각수 시트
URL_COOLING = "https://docs.google.com/spreadsheets/d/1AdDEm4r3lOpjCzzeksJMiTG5Z2kjmif-xvrKvE5BmSY/export?format=csv&gid=1052812012" 

# [시트3] 설비전력 시트
URL_POWER = "https://docs.google.com/spreadsheets/d/1AdDEm4r3lOpjCzzeksJMiTG5Z2kjmif-xvrKvE5BmSY/export?format=csv&gid=1442513579" 

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
tab1, tab2, tab3 = st.tabs(["🏭 설비 감가상각", "💧 냉각수 관리", "⚡ 설비 전력"])

# =============================================================================
# [탭 1] 설비 관리
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
# [탭 2] 냉각수 관리
# =============================================================================
with tab2:
    st.markdown("### 📊 연도별 냉각수 사용량 추이")
    df_cool = load_data(URL_COOLING)
    
    if df_cool is None:
        st.info("데이터 로드 실패. 링크와 GID를 확인하세요.")
    else:
        if '날짜' not in df_cool.columns or '사용량' not in df_cool.columns:
             st.error("컬럼 오류: '날짜', '사용량' 컬럼이 필요합니다.")
        else:
            df_cool['날짜'] = pd.to_datetime(df_cool['날짜'], errors='coerce')
            df_cool = df_cool.dropna(subset=['날짜'])
            df_cool['연도'] = df_cool['날짜'].dt.year
            df_cool['월'] = df_cool['날짜'].dt.month
            
            # 피벗 (차트용: 인덱스=월, 컬럼=연도)
            pivot_cool = df_cool.pivot_table(index='월', columns='연도', values='사용량', aggfunc='sum')
            pivot_cool = pivot_cool.reindex(range(1, 13), fill_value=0)
            
            # KPI
            years = pivot_cool.columns.tolist()
            if years:
                cols = st.columns(len(years))
                for i, year in enumerate(years):
                    with cols[i]:
                        st.metric(f"{year}년 총 사용량", f"{pivot_cool[year].sum():,.0f}")
            
            st.divider()
            st.subheader("📈 연도별 월간 그래프")
            st.line_chart(pivot_cool)
            st.markdown("---")
            
            st.subheader("📋 연도별 상세 비교표 (합계 포함)")
            # 행(연도), 열(월)로 변환
            table_cool = pivot_cool.T
            
            # [추가 기능] 합계 컬럼 생성
            table_cool['합계'] = table_cool.sum(axis=1)
            
            # 컬럼명 정리: 숫자 -> "1월", "합계" -> "합계"
            new_cols = []
            for c in table_cool.columns:
                if c == '합계': new_cols.append('합계')
                else: new_cols.append(f"{c}월")
            table_cool.columns = new_cols
            
            # 인덱스 정리
            table_cool.index = [f"{y}년" for y in table_cool.index]
            
            st.dataframe(table_cool.style.format("{:,.0f}").highlight_max(axis=0, color='#FFDDC1'), use_container_width=True)

# =============================================================================
# [탭 3] 설비 전력
# =============================================================================
with tab3:
    st.markdown("### ⚡ 연도별 전력 사용량 추이")
    
    df_power = load_data(URL_POWER)
    
    if df_power is None:
        st.info("설비 전력 데이터를 불러올 수 없습니다. 링크와 GID를 확인하세요.")
    else:
        if '날짜' not in df_power.columns or '사용량' not in df_power.columns:
             st.error("컬럼 오류: '날짜', '사용량' 컬럼이 있어야 합니다.")
        else:
            df_power['날짜'] = pd.to_datetime(df_power['날짜'], errors='coerce')
            df_power = df_power.dropna(subset=['날짜'])
            
            df_power['연도'] = df_power['날짜'].dt.year
            df_power['월'] = df_power['날짜'].dt.month
            
            # 피벗 (차트용)
            pivot_power = df_power.pivot_table(index='월', columns='연도', values='사용량', aggfunc='sum')
            pivot_power = pivot_power.reindex(range(1, 13), fill_value=0)
            
            # KPI
            years_p = pivot_power.columns.tolist()
            if years_p:
                cols_p = st.columns(len(years_p))
                for i, year in enumerate(years_p):
                    with cols_p[i]:
                        st.metric(f"{year}년 총 전력량", f"{pivot_power[year].sum():,.0f} kWh")
            
            st.divider()
            
            st.subheader("📈 전력 사용량 그래프")
            st.line_chart(pivot_power)
            
            st.markdown("---")
            
            st.subheader("📋 전력 상세 비교표 (합계 포함)")
            # 행(연도), 열(월)로 변환
            table_power = pivot_power.T
            
            # [추가 기능] 합계 컬럼 생성
            table_power['합계'] = table_power.sum(axis=1)
            
            # 컬럼명 정리
            new_cols_p = []
            for c in table_power.columns:
                if c == '합계': new_cols_p.append('합계')
                else: new_cols_p.append(f"{c}월")
            table_power.columns = new_cols_p
            
            table_power.index = [f"{y}년" for y in table_power.index]
            
            st.dataframe(
                table_power.style.format("{:,.0f}").highlight_max(axis=0, color='#D4F1F4'), 
                use_container_width=True
            )
