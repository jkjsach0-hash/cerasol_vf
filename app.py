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
            time.sleep(1)
            st.rerun()
        else:
            st.error("비밀번호가 올바르지 않습니다.")
            
    return False

# -----------------------------------------------------------------------------
# 3. 메인 로직 실행 (로그인 통과 시에만 실행됨)
# -----------------------------------------------------------------------------
if not check_password():
    st.stop()

# =============================================================================
# ▼ 여기서부터는 로그인 성공 시에만 보이는 화면입니다 ▼
# =============================================================================

st.title("🏭 공장 운영 관리 시스템")

# -----------------------------------------------------------------------------
# 4. 데이터 로드 설정
# -----------------------------------------------------------------------------
URL_EQUIPMENT = "https://docs.google.com/spreadsheets/d/1AdDEm4r3lOpjCzzeksJMiTG5Z2kjmif-xvrKvE5BmSY/export?format=csv&gid=0"
URL_COOLING = "https://docs.google.com/spreadsheets/d/1AdDEm4r3lOpjCzzeksJMiTG5Z2kjmif-xvrKvE5BmSY/export?format=csv&gid=1052812012" 
URL_POWER = "https://docs.google.com/spreadsheets/d/1AdDEm4r3lOpjCzzeksJMiTG5Z2kjmif-xvrKvE5BmSY/export?format=csv&gid=1442513579" 

@st.cache_data(ttl=600)
def load_data(url):
    try:
        df = pd.read_csv(url, thousands=',')
        return df
    except Exception:
        return None

# -----------------------------------------------------------------------------
# 5. 탭 구성
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["💰 시간당 소성비용", "🏭 설비 감가상각", "💧 냉각수 관리", "⚡ 설비 전력"])

# =============================================================================
# [탭 1] 시간당 소성 비용 계산
# =============================================================================
with tab1:
    st.markdown("### 💰 전체 공장 시간당 소성 비용 산출")
    st.info("📌 현재 데이터(감가상각, 전력, 냉각수)를 기반으로 시간당 비용을 계산합니다. 가스비는 데이터 입력 후 추가됩니다.")
    
    st.divider()
    
    # 사이드바에 입력값 배치
    with st.sidebar:
        st.header("⚙️ 운영 파라미터 설정")
        
        st.subheader("📅 가동 시간")
        monthly_hours = st.number_input("월간 가동시간 (시간)", min_value=1, value=600, step=10, 
                                        help="예: 25일 × 24시간 = 600시간")
        
        st.subheader("💵 단가 설정")
        elec_price = st.number_input("전력 단가 (원/kWh)", min_value=0.0, value=120.0, step=1.0)
        water_price = st.number_input("수도 단가 (원/톤)", min_value=0.0, value=800.0, step=10.0)
        
        st.subheader("🔥 가스비 (추후 입력)")
        gas_cost_monthly = st.number_input("월간 가스비 (원)", min_value=0.0, value=0.0, step=10000.0,
                                          help="가스 데이터 입력 후 사용")
    
    # 데이터 로드
    df_eq = load_data(URL_EQUIPMENT)
    df_cool = load_data(URL_COOLING)
    df_power = load_data(URL_POWER)
    
    # 계산 로직
    cost_breakdown = {}
    
    # ① 감가상각비 (시간당)
    if df_eq is not None:
        req_cols_eq = ['설비코드', '설비명', '구입일자', '취득원가']
        if all(col in df_eq.columns for col in req_cols_eq):
            df_eq['구입일자'] = pd.to_datetime(df_eq['구입일자'], errors='coerce')
            today = datetime.now()
            FIXED_LIFE = 10
            
            def calc_yearly_dep(row):
                if pd.isna(row['구입일자']): return 0
                return row['취득원가'] / FIXED_LIFE
            
            df_eq['연간적립액'] = df_eq.apply(calc_yearly_dep, axis=1)
            total_yearly_dep = df_eq['연간적립액'].sum()
            monthly_dep = total_yearly_dep / 12
            hourly_dep = monthly_dep / monthly_hours
            cost_breakdown['감가상각비'] = hourly_dep
    
    # ② 전력비 (시간당)
    if df_power is not None:
        if '날짜' in df_power.columns and '사용량' in df_power.columns:
            df_power['날짜'] = pd.to_datetime(df_power['날짜'], errors='coerce')
            df_power = df_power.dropna(subset=['날짜'])
            df_power['실제전력소비량'] = df_power['사용량'] * 80
            
            # 최근 월 데이터 사용
            df_power['연월'] = df_power['날짜'].dt.to_period('M')
            latest_month = df_power['연월'].max()
            monthly_power = df_power[df_power['연월'] == latest_month]['실제전력소비량'].sum()
            
            monthly_power_cost = monthly_power * elec_price
            hourly_power_cost = monthly_power_cost / monthly_hours
            cost_breakdown['전력비'] = hourly_power_cost
    
    # ③ 냉각수비 (시간당)
    if df_cool is not None:
        if '날짜' in df_cool.columns and '사용량' in df_cool.columns:
            df_cool['날짜'] = pd.to_datetime(df_cool['날짜'], errors='coerce')
            df_cool = df_cool.dropna(subset=['날짜'])
            
            # 최근 월 데이터 사용
            df_cool['연월'] = df_cool['날짜'].dt.to_period('M')
            latest_month_cool = df_cool['연월'].max()
            monthly_water = df_cool[df_cool['연월'] == latest_month_cool]['사용량'].sum()
            
            monthly_water_cost = monthly_water * water_price
            hourly_water_cost = monthly_water_cost / monthly_hours
            cost_breakdown['냉각수비'] = hourly_water_cost
    
    # ④ 가스비 (시간당)
    hourly_gas_cost = gas_cost_monthly / monthly_hours
    if gas_cost_monthly > 0:
        cost_breakdown['가스비'] = hourly_gas_cost
    
    # 총 시간당 비용
    total_hourly_cost = sum(cost_breakdown.values())
    
    # 결과 표시
    st.markdown("---")
    st.subheader("📊 시간당 소성 비용 구성")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💎 감가상각비", 
                 f"{cost_breakdown.get('감가상각비', 0):,.0f} 원/시간",
                 help="설비 재구입을 위한 연간 적립액 기준")
    
    with col2:
        st.metric("⚡ 전력비", 
                 f"{cost_breakdown.get('전력비', 0):,.0f} 원/시간",
                 help=f"최근 월 전력소비량 × {elec_price}원/kWh")
    
    with col3:
        st.metric("💧 냉각수비", 
                 f"{cost_breakdown.get('냉각수비', 0):,.0f} 원/시간",
                 help=f"최근 월 냉각수사용량 × {water_price}원/톤")
    
    with col4:
        st.metric("🔥 가스비", 
                 f"{cost_breakdown.get('가스비', 0):,.0f} 원/시간",
                 help="월간 가스비 입력 필요" if gas_cost_monthly == 0 else "월간 가스비 기준")
    
    st.divider()
    
    # 총 비용 강조
    st.markdown("### 🎯 총 시간당 소성 비용")
    col_total1, col_total2, col_total3 = st.columns([1, 1, 1])
    
    with col_total1:
        st.metric("시간당", f"{total_hourly_cost:,.0f} 원", 
                 help="모든 비용 항목의 합계")
    
    with col_total2:
        st.metric("일일 (24시간)", f"{total_hourly_cost * 24:,.0f} 원")
    
    with col_total3:
        st.metric("월간 예상", f"{total_hourly_cost * monthly_hours:,.0f} 원",
                 help=f"시간당 비용 × {monthly_hours}시간")
    
    st.divider()
    
    # 비용 구성 차트
    st.subheader("📈 비용 구성 비율")
    if cost_breakdown:
        chart_data = pd.DataFrame({
            '항목': list(cost_breakdown.keys()),
            '비용': list(cost_breakdown.values())
        })
        chart_data = chart_data[chart_data['비용'] > 0]  # 0보다 큰 항목만
        st.bar_chart(chart_data.set_index('항목'))
    
    # 상세 테이블
    st.markdown("---")
    st.subheader("📋 상세 비용 분석표")
    
    if cost_breakdown:
        detail_data = []
        for item, cost in cost_breakdown.items():
            detail_data.append({
                '비용항목': item,
                '시간당 (원)': f"{cost:,.0f}",
                '일일 (원)': f"{cost * 24:,.0f}",
                f'월간 ({monthly_hours}h)': f"{cost * monthly_hours:,.0f}",
                '비율 (%)': f"{(cost/total_hourly_cost*100) if total_hourly_cost > 0 else 0:.1f}%"
            })
        
        # 합계 행 추가
        detail_data.append({
            '비용항목': '✅ 합계',
            '시간당 (원)': f"{total_hourly_cost:,.0f}",
            '일일 (원)': f"{total_hourly_cost * 24:,.0f}",
            f'월간 ({monthly_hours}h)': f"{total_hourly_cost * monthly_hours:,.0f}",
            '비율 (%)': "100.0%"
        })
        
        st.dataframe(pd.DataFrame(detail_data), use_container_width=True, hide_index=True)
    
    # 안내 메시지
    st.info("💡 **팁**: 왼쪽 사이드바에서 가동시간과 단가를 조정하여 시나리오별 비용을 시뮬레이션할 수 있습니다.")
    
    if gas_cost_monthly == 0:
        st.warning("⚠️ 가스비 데이터가 입력되지 않았습니다. 가스 사용량 데이터 입력 후 더 정확한 비용을 산출할 수 있습니다.")

# =============================================================================
# [탭 2] 설비 관리
# =============================================================================
with tab2:
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
# [탭 3] 냉각수 관리
# =============================================================================
with tab3:
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
            
            pivot_cool = df_cool.pivot_table(index='월', columns='연도', values='사용량', aggfunc='sum')
            pivot_cool = pivot_cool.reindex(range(1, 13), fill_value=0)
            
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
            table_cool = pivot_cool.T
            table_cool['합계'] = table_cool.sum(axis=1)
            
            new_cols = []
            for c in table_cool.columns:
                if c == '합계': new_cols.append('합계')
                else: new_cols.append(f"{c}월")
            table_cool.columns = new_cols
            table_cool.index = [f"{y}년" for y in table_cool.index]
            
            st.dataframe(table_cool.style.format("{:,.0f}").highlight_max(axis=0, color='#FFDDC1'), use_container_width=True)

# =============================================================================
# [탭 4] 설비 전력
# =============================================================================
with tab4:
    st.markdown("### ⚡ 연도별 전력 사용량 추이")
    st.info("💡 표시된 값은 기계 출력치에 단위값 80을 곱한 실제 전력소비량입니다.")
    
    df_power = load_data(URL_POWER)
    
    if df_power is None:
        st.info("설비 전력 데이터를 불러올 수 없습니다. 링크와 GID를 확인하세요.")
    else:
        if '날짜' not in df_power.columns or '사용량' not in df_power.columns:
             st.error("컬럼 오류: '날짜', '사용량' 컬럼이 있어야 합니다.")
        else:
            df_power['날짜'] = pd.to_datetime(df_power['날짜'], errors='coerce')
            df_power = df_power.dropna(subset=['날짜'])
            df_power['실제전력소비량'] = df_power['사용량'] * 80
            df_power['연도'] = df_power['날짜'].dt.year
            df_power['월'] = df_power['날짜'].dt.month
            
            pivot_power = df_power.pivot_table(index='월', columns='연도', values='실제전력소비량', aggfunc='sum')
            pivot_power = pivot_power.reindex(range(1, 13), fill_value=0)
            
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
            table_power = pivot_power.T
            table_power['합계'] = table_power.sum(axis=1)
            
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
