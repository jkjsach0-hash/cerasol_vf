import streamlit as st
import pandas as pd
import urllib.parse

st.set_page_config(page_title="공장 소성 비용 분석기", layout="wide")
st.title("🏭 진공로 소성 비용 통합 대시보드")

# 1. 시트 ID 설정 (여기에 본인의 시트 ID를 넣어주세요)
SHEET_ID = "1AdDEm4r3lOpjCzzeksJMiTG5Z2kjmif-xvrKvE5BmSY" 

def load_sheet(sheet_name):
    # 한글 탭 이름도 안전하게 가져오는 주소 생성
    safe_name = urllib.parse.quote(sheet_name)
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&sheet={safe_name}"
    return pd.read_csv(url)

try:
    # 2. 데이터 로드 (시트의 탭 이름과 일치해야 합니다)
    # 업로드하신 파일명 기반으로 추측한 탭 이름: Machines, Waterlogs, MME
    df_machines = load_sheet("Machines")
    df_water = load_sheet("Waterlogs")
    df_energy = load_sheet("MME")

    # 3. 컬럼 이름 표준화 (한글/영어 섞인 것을 통일)
    # 설비 시트: '취득원가' -> 'price'
    df_machines = df_machines.rename(columns={'취득원가': 'price'})
    
    # 전력 시트: '날짜' -> 'date', '사용량' -> 'amount'
    df_energy = df_energy.rename(columns={'날짜': 'date', '사용량': 'amount'})
    
    # 냉각수 시트: 'date'와 'water(m3)'는 그대로 사용

    # 4. 데이터 전처리 (콤마 제거 및 숫자 변환)
    def clean_numeric(df, col_name):
        if col_name in df.columns:
            df[col_name] = pd.to_numeric(df[col_name].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        return df

    df_machines = clean_numeric(df_machines, 'price')
    df_energy = clean_numeric(df_energy, 'amount')
    df_water = clean_numeric(df_water, 'water(m3)')

    # 5. 비용 계산 로직
    
    # (1) 설비 고정비 (취득원가 합계 / 120개월)
    monthly_fixed_cost = df_machines['price'].sum() / 120

    # (2) 월별 변동비 계산
    if 'date' in df_energy.columns:
        # 날짜 목록 추출
        available_months = df_energy['date'].dropna().unique()
        selected_month = st.sidebar.selectbox("분석할 월 선택", available_months)
        
        # 선택된 월의 전력량 가져오기
        energy_row = df_energy[df_energy['date'] == selected_month]
        total_kwh = energy_row['amount'].iloc[0] if not energy_row.empty else 0
        
        # 전기요금 계산 (전력량 * 125원)
        electricity_cost = total_kwh * 125
        
        # 냉각수 비용 계산
        water_usage = 0
        if 'date' in df_water.columns and 'water(m3)' in df_water.columns:
            # 날짜 형식을 문자로 변환하여 매칭
            df_water['date'] = df_water['date'].astype(str)
            monthly_water = df_water[df_water['date'].str.contains(str(selected_month), na=False)]
            water_usage = monthly_water['water(m3)'].sum()
        
        water_cost = water_usage * 1200 # 톤당 1200원

        # 6. 결과 화면 출력
        st.info(f"📅 분석 기간: **{selected_month}** | 전기료 단가: **125원/kWh** (추정)")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("기계 감가상각 (월)", f"{monthly_fixed_cost:,.0f} 원")
        col2.metric("전력 사용량", f"{total_kwh:,.1f} kWh")
        col3.metric("전기 요금 (추정)", f"{electricity_cost:,.0f} 원")
        
        total_cost = monthly_fixed_cost + electricity_cost + water_cost
        col4.metric("💰 총 소성 비용", f"{total_cost:,.0f} 원")

        # 7. 차트 시각화
        st.divider()
        st.subheader("📊 비용 구성 차트")
        chart_data = pd.DataFrame({
            "항목": ["기계감가상각", "전기요금", "냉각수비용"],
            "금액": [monthly_fixed_cost, electricity_cost, water_cost]
        })
        st.bar_chart(chart_data.set_index("항목"))

        # (옵션) 상세 데이터 보기
        with st.expander("데이터 원본 보기"):
            st.write("설비 목록", df_machines[['설비명', 'price']].head())
            st.write("선택된 월 전력 데이터", energy_row)
            
    else:
        st.warning("전력 시트(MME)에서 '날짜' 컬럼을 찾을 수 없습니다.")

except Exception as e:
    st.error(f"❌ 데이터 연결 오류: {e}")
    st.info("Tip: 시트 ID가 정확한지, 탭 이름(Machines, Waterlogs, MME)이 시트와 일치하는지 확인해주세요.")
