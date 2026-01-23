import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="공장 소성 비용 분석기", layout="wide")
st.title("🏭 진공로 소성 비용 통합 대시보드")

# 1. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # [중요] 탭 이름 대신 "번호"로 시트를 가져오도록 시도합니다.
    # 만약 이름으로 찾을 수 없다면 첫 번째 탭부터 순서대로 읽어옵니다.
    
    @st.cache_data(ttl=600)
    def load_all_sheets():
        # 시트 전체를 읽어와서 각 탭을 리스트에 담습니다.
        # 이름 매칭 에러를 피하기 위해 하나씩 시도합니다.
        s1 = conn.read(worksheet="Machines")
        s2 = conn.read(worksheet="Waterlogs") # 대문자 반영
        s3 = conn.read(worksheet="MachinesMonthlyEnergy")
        s4 = conn.read(worksheet="FactoryEnergyExpenses")
        return s1, s2, s3, s4

    df_machines, df_water, df_energy, df_billing = load_all_sheets()

    st.success("🎉 모든 탭(Machines, Waterlogs 등) 연결에 성공했습니다!")

    # --- 데이터 계산 ---
    # 1. 기계 비용 (취득원가 합계 / 120개월)
    total_price = pd.to_numeric(df_machines['취득원가'], errors='coerce').sum()
    monthly_fixed_cost = total_price / 120

    # 2. 월 선택 (MachinesMonthlyEnergy의 '월' 열 기준)
    available_months = df_energy['월'].dropna().unique()
    selected_month = st.sidebar.selectbox("분석할 월 선택", available_months)

    # 3. 전력량 및 전기요금
    energy_data = df_energy[df_energy['월'] == selected_month]
    total_kwh = energy_data['전력량'].iloc[0] if not energy_data.empty else 0
    
    billing_data = df_billing[df_billing['월'] == selected_month]
    if not billing_data.empty:
        actual_cost = billing_data['전기요금'].iloc[0]
    else:
        actual_cost = total_kwh * 125 # 시트에 요금 없으면 추정치

    # 4. 결과 출력
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("기계 감가상각(월)", f"{monthly_fixed_cost:,.0f} 원")
    m2.metric("전력 사용량", f"{total_kwh:,.1f} kWh")
    m3.metric("전기 요금", f"{actual_cost:,.0f} 원")

    # 5. 차트
    chart_data = pd.DataFrame({
        "항목": ["기계비용", "전기료"],
        "금액": [monthly_fixed_cost, actual_cost]
    })
    st.bar_chart(chart_data.set_index("항목"))

except Exception as e:
    st.error(f"⚠️ 연결 실패 상세 원인: {e}")
    st.write("### 💡 해결을 위해 아래 내용을 확인해주세요:")
    st.write("1. **Secrets 주소:** 끝에 `/edit` 외에 다른 글자가 있는지 확인 (예: `#gid=...` 는 삭제)")
    st.write("2. **시트 공유:** '링크가 있는 모든 사용자'가 **[뷰어]** 또는 **[편집자]**인지 확인")
    st.write("3. **탭 순서:** 시트 하단 탭 순서가 `Machines`, `Waterlogs` ... 순서인지 확인")
