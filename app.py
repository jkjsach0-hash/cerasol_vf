import streamlit as st
import pandas as pd
import urllib.parse

# 1. 페이지 설정
st.set_page_config(page_title="공장 소성 비용 분석기", layout="wide")
st.title("🏭 진공로 소성 비용 통합 대시보드")

# ---------------------------------------------------------
# [중요] 시트 ID 설정
# 본인의 구글 시트 주소에서 d/ 와 /edit 사이에 있는 ID만 입력하세요.
SHEET_ID = "1AdDEm4r3lOpjCzzeksJMiTG5Z2kjmif-xvrKvE5BmSY" 
# ---------------------------------------------------------

def load_sheet(sheet_name):
    """구글 시트의 특정 탭을 CSV로 가져오는 함수"""
    # 탭 이름에 공백이나 특수문자가 있어도 처리 가능하도록 인코딩
    safe_name = urllib.parse.quote(sheet_name)
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&sheet={safe_name}"
    return pd.read_csv(url)

try:
    # 2. 데이터 로드 (업로드한 파일 구조 반영)
    # 탭 이름: Machines, Waterlogs, MME
    df_machines = load_sheet("설비")
    df_water = load_sheet("냉각수")
    df_energy = load_sheet("설비전력")

    # 3. 데이터 전처리 (콤마 제거 및 숫자 변환 함수)
    def clean_numeric(df, col_name):
        if col_name in df.columns:
            # 문자열로 변환 후 콤마 제거 -> 숫자로 변환 (에러 발생 시 0 처리)
            df[col_name] = pd.to_numeric(df[col_name].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        return df

    # 각 시트의 실제 열 이름에 맞춰 숫자 변환 적용
    df_machines = clean_numeric(df_machines, '취득원가')   # 설비.csv
    df_energy = clean_numeric(df_energy, '사용량')        # 설비전력.csv
    df_water = clean_numeric(df_water, '사용량')       # 냉각수.csv

    # 4. 비용 계산 로직

    # (1) 기계 감가상각비 (Machines 탭)
    # 로직: '취득원가' 총합 나누기 120개월
    if '취득원가' in df_machines.columns:
        monthly_fixed_cost = df_machines['취득원가'].sum() / 120
    else:
        monthly_fixed_cost = 0

    # (2) 전력비 및 냉각수비 (월별 계산)
    # MME 탭의 '날짜' 컬럼을 기준으로 월을 선택
    if '날짜' in df_energy.columns:
        # 날짜 형식 통일 (YYYY-MM-DD -> YYYY-MM)
        df_energy['날짜'] = pd.to_datetime(df_energy['날짜'], errors='coerce')
        df_energy['월'] = df_energy['날짜'].dt.strftime('%Y-%m')
        
        # 사이드바에서 월 선택
        available_months = df_energy['날짜'].dropna().unique()
        selected_month = st.sidebar.selectbox("분석할 월 선택", available_months)
        
        # 선택된 월의 데이터 필터링
        energy_row = df_energy[df_energy['월'] == selected_month]
        
        # 전력 사용량 가져오기
        total_kwh = energy_row['사용량'].iloc[0] if not energy_row.empty else 0
        
        # 전기요금 계산 (별도 요금 컬럼이 없으므로 단가 125원 적용)
        electricity_cost = total_kwh * 125

        # (3) 냉각수 비용 계산 (Waterlogs 탭)
        # Waterlogs 탭은 '날짜' 컬럼 사용 (영문)
        water_cost = 0
        water_usage = 0
        
        if 'date' in df_water.columns and 'water(m3)' in df_water.columns:
            # 날짜를 문자열로 변환하여 'YYYY-MM' 매칭 확인
            # 예: 2024-01-15 데이터에서 '2024-01'이 포함되어 있는지 확인
            df_water['date_str'] = df_water['date'].astype(str)
            monthly_water_data = df_water[df_water['date_str'].str.contains(selected_month, na=False)]
            
            # 해당 월의 사용량 합계
            water_usage = monthly_water_data['water(m3)'].sum()
            water_cost = water_usage * 1200 # 톤당 1,200원
