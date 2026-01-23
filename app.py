import streamlit as st
import pandas as pd
import urllib.parse

# 1. 페이지 설정
st.set_page_config(page_title="공장 소성 비용 분석기", layout="wide")
st.title("🏭 진공로 소성 비용 통합 대시보드")

# ---------------------------------------------------------
# [필수] 시트 ID 입력 (d/ 와 /edit 사이의 문자열)
SHEET_ID = "1AdDEm4r3lOpjCzzeksJMiTG5Z2kjmif-xvrKvE5BmSY" 
# ---------------------------------------------------------

def load_sheet(sheet_name):
    """특수문자/한글이 포함된 탭 이름을 안전하게 주소로 변환하여 로드"""
    safe_name = urllib.parse.quote(sheet_name)
    url = f"https://docs.google.com/spreadsheets/d/1AdDEm4r3lOpjCzzeksJMiTG5Z2kjmif-xvrKvE5BmSY/export?format=csv&sheet={safe_name}"
    return pd.read_csv(url)

# 2. 데이터 로드 (에러 발생 시 화면에 메시지 출력)
try:
    df_machines = load_sheet("설비")
    df_water = load_sheet("냉각수")
    df_energy = load_sheet("설비전력")
except Exception as e:
    st.error(f"❌ 데이터 로드 실패: {e}")
    st.stop() # 더 이상 진행하지 않고 멈춤

# 3. 데이터 전처리 (컬럼명 통일 및 숫자 변환)

# (1) 설비(Machines) 시트: '취득원가' -> 'price'
if '취득원가' in df_machines.columns:
    df_machines = df_machines.rename(columns={'취득원가': 'price'})
    # 쉼표 제거 후 숫자로 변환
    df_machines['price'] = pd.to_numeric(df_machines['price'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

# (2) 전력(MME) 시트: '날짜' -> 'date', '사용량' -> 'amount'
if '날짜' in df_energy.columns:
    df_energy = df_energy.rename(columns={'날짜': 'date', '사용량': 'amount'})
    df_energy['amount'] = pd.to_numeric(df_energy['amount'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    # 날짜 형식 변환 및 '월' 컬럼 생성 (YYYY-MM)
    df_energy['date'] = pd.to_datetime(df_energy['date'], errors='coerce')
    df_energy['month'] = df_energy['date'].dt.strftime('%Y-%m')

# (3) 냉각수(Waterlogs) 시트: 'water(m3)' 숫자 변환
if 'water(m3)' in df_water.columns:
    df_water['water(m3)'] = pd.to_numeric(df_water['water(m3)'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    # 날짜 형식 변환 및 '월' 컬럼 생성
    df_water['date'] = pd.to_datetime(df_water['date'], errors='coerce')
    df_water['month'] = df_water['date'].dt.strftime('%Y-%m')


# 4. 비용 계산 및 대시보드 출력

# (A) 기계 감가상각 (월 고정비)
monthly_fixed_cost = 0
if 'price' in df_machines.columns:
    monthly_fixed_cost = df_machines['price'].sum() / 120

# (B) 월별 변동비 계산
if 'month' in df_energy.columns:
    # 분석할 월 선택
    available_months = sorted(df_energy['month'].dropna().unique(), reverse=True)
    selected_month = st.sidebar.selectbox("분석할 월 선택", available_months)
    
    # 1. 전기요금 계산
    energy_row = df_energy[df_energy['month'] == selected_month]
    total_kwh = energy_row['amount'].iloc[0] if not energy_row.empty else 0
    electricity_cost = total_kwh * 125 # 단가 125원 가정
    
    # 2. 냉각수 비용 계산
    water_usage = 0
    if 'month' in df_water.columns:
        # 해당 월의 물 사용량 합계
        water_usage = df_water[df_water['month'] == selected_month]['water(m3)'].sum()
    water_cost = water_usage * 1200 # 톤당 1,200원

    # 5. 결과 표시
    st.divider()
    st.info(f"📅 분석 기간: **{selected_month}**")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("기계 감가상각 (월)", f"{monthly_fixed_cost:,.0f} 원")
    c2.metric("전력 사용량", f"{total_kwh:,.1f} kWh")
    c3.metric("전기 요금 (추정)", f"{electricity_cost:,.0f} 원")
    
    total_cost = monthly_fixed_cost + electricity_cost + water_cost
    c4.metric("💰 총 소성 비용", f"{total_cost:,.0f} 원")

    # 6. 차트
    st.subheader("📊 비용 구성 차트")
    chart_data = pd.DataFrame({
        "항목": ["기계비용", "전기요금", "냉각수비용"],
        "금액": [monthly_fixed_cost, electricity_cost, water_cost]
    })
    st.bar_chart(chart_data.set_index("항목"))

else:
    st.warning("전력 데이터(MME)를 불러올 수 없거나 날짜 형식이 올바르지 않습니다.")
