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
