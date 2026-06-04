import pandas as pd
import numpy as np
from pathlib import Path

# ==========================================
# 1. 상대경로 설정
# ==========================================
current_file = Path(__file__).resolve()
project_dir = next((parent for parent in current_file.parents if parent.name == "ETF_Replicate"), current_file.parent.parent)

labeled_panel_path = project_dir / "Data_result" / "Panel_change_Data" / "ETF_Data_panel_labeled.csv"
category_file_path = project_dir / "Data_result" / "Classification" / "ETF_List_Final.xlsx"
output_preprocessed_path = project_dir / "Data_result" / "Panel_change_Data" / "ETF_Data_panel_date0.csv"

print("=" * 60)
print("1단계: 한국 데이터 특성 반영 (2002~2025 전체 기간 전처리) 시작")
print("=" * 60)

# 데이터 로드
df_panel = pd.read_csv(labeled_panel_path, encoding="utf-8-sig")
df_meta = pd.read_excel(category_file_path, header=0)

# 코드 정제
df_panel["코드"] = df_panel["코드"].astype(str).str.replace(r'\s+', '', regex=True).str.strip().str.upper()
df_meta["코드"] = df_meta["코드"].astype(str).str.replace(r'\s+', '', regex=True).str.strip().str.upper()

# 날짜 추출 및 매칭
df_dates = df_meta[["코드", "상장일", "상장폐지일"]].copy()
df_dates["상장일"] = df_dates["상장일"].astype(str).str.split('.').str[0].str.strip()
df_dates["상장폐지일"] = df_dates["상장폐지일"].astype(str).str.split('.').str[0].str.strip()
df_dates["상장폐지일"] = df_dates["상장폐지일"].replace(["0", "00", "nan", ""], np.nan)
df_dates = df_dates.drop_duplicates(subset=["코드"])

df = pd.merge(df_panel, df_dates, on="코드", how="left")
df = df.dropna(subset=["Category", "날짜"])

# 날짜 포맷 강제 정렬 (2002-2025 기간 자동 수용)
df["날짜"] = pd.to_datetime(df["날짜"])
df["상장일"] = pd.to_datetime(df["상장일"], format="%Y%m%d", errors="coerce")
df["상장폐지일"] = pd.to_datetime(df["상장폐지일"], format="%Y%m%d", errors="coerce")

# 상장일 누락 방어
df["상장일"] = df["상장일"].fillna(df.groupby("코드")["날짜"].transform("min"))

# 상장일 기준 실제 경과 개월 수(Age) 정밀 연산
df["Age_month"] = (df["날짜"].dt.year - df["상장일"].dt.year) * 12 + (df["날짜"].dt.month - df["상장일"].dt.month) + 1

# 변수 정량화 및 단위 가공
df["Fee_bps"] = df["TER 보수"] * 100
df["상장주식수(주)"] = df["상장주식수(주)"].replace(0, np.nan)
df["daily_turnover"] = (df["거래량(주)"] / df["상장주식수(주)"]) * 100
df["daily_turnover"] = df["daily_turnover"].replace([np.inf, -np.inf], np.nan)
df["Return_pct"] = df["수정주가수익률(%)"]

# 상장폐지 더미 변수 (실제 폐지 날짜가 존재하는 경우만 1, 유지 중이면 0)
df["Is_Delisted"] = np.where(df["상장폐지일"].notna(), 1, 0)

# 한국 원화 기준 단위 정량화 (AUM은 십억원, 내재수입은 백만원 단위)
df["AUM_bn"] = df["AUM(원)"] / 1_000_000_000
df["Implied_rev_million"] = (df["TER 보수"] / 100) * df["AUM(원)"] / 1_000_000

# 생애주기별 플래그 설정 (존재하는 범위까지만 반영)
df["In_6_Months"] = np.where(df["Age_month"] <= 6, 1, 0)
df["In_60_Months"] = np.where(df["Age_month"] <= 60, 1, 0)

df.to_csv(output_preprocessed_path, index=False, encoding="utf-8-sig")
print("[성공] 1단계 전처리 완료! 결과가 'ETF_Data_panel_date0.csv'에 저장되었습니다.")