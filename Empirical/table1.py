import pandas as pd
import numpy as np
from pathlib import Path

# ==========================================
# 1. 경로 설정 (최상위 프로젝트 폴더 자동 추적)
# ==========================================
current_file = Path(__file__).resolve()
project_dir = next((parent for parent in current_file.parents if parent.name == "ETF_Replicate"), current_file.parent.parent)

# 입력 파일 및 출력 파일 경로 정의
preprocessed_path = project_dir / "Data_result" / "Panel_change_Data" / "ETF_Data_panel_date0.csv"
mkf500_path = project_dir / "Data_result" / "Portfolio" / "MKF500.csv"  # ★ 요청하신 MKF500 경로 반영
output_table1_path = project_dir / "Data_result" / "Empirical" / "table1.csv"

# 출력 폴더 자동 생성
output_table1_path.parent.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("2단계: MKF500 시장 지수 반영 최종 Table 1 산출을 시작합니다.")
print("=" * 60)

# ==========================================
# 2. 데이터 로드 및 시장 수익률 결합 (Merge)
# ==========================================
df = pd.read_csv(preprocessed_path, encoding="utf-8-sig")
df_mkf = pd.read_csv(mkf500_path, encoding="utf-8-sig")

df["날짜"] = pd.to_datetime(df["날짜"])
df_mkf["날짜"] = pd.to_datetime(df_mkf["날짜"])

# [정밀 매칭] 두 데이터셋 모두에 연월 키를 생성하여 휴장일 오차 차단
df["연월_key"] = df["날짜"].dt.to_period("M")
df_mkf["연월_key"] = df_mkf["날짜"].dt.to_period("M")

# MKF500은 전체 시장 지수이므로, 필요한 '연월'과 '월별수익률(%)' 컬럼만 중복 없이 추출
df_mkf_clean = df_mkf[["연월_key", "월별수익률(%)"]].drop_duplicates(subset=["연월_key"]).copy()
df_mkf_clean.rename(columns={"월별수익률(%)": "Mkt_Return_pct"}, inplace=True)

# ETF 데이터에 시장 수익률 결합
df = pd.merge(df, df_mkf_clean, on="연월_key", how="left")

# ==========================================
# 3. 수정주가 기반 자산 수익률 및 시장조정수익률 산출
# ==========================================
df = df.sort_values(by=["코드", "날짜"]).reset_index(drop=True)
df["ETF_Return_pct"] = df.groupby("코드")["수정주가(원)"].pct_change(periods=1) * 100

# 시장 수익률 결측치는 0으로 방어 처리 후, 정석 [ETF 수익률 - 시장 수익률] 계산
df["Mkt_Return_pct"] = df["Mkt_Return_pct"].fillna(0)
df["Ex_Return_pct"] = df["ETF_Return_pct"] - df["Mkt_Return_pct"]

# ==========================================
# 4. 통계량 산출 함수 정의
# ==========================================
def get_stats_row(series, var_name, panel_name):
    data = series.dropna()
    return {
        "Panel": panel_name, "Variable": var_name, "N": len(data),
        "Mean": data.mean(), "SD": data.std(),
        "P5": np.percentile(data, 5) if len(data) > 0 else np.nan,
        "P25": np.percentile(data, 25) if len(data) > 0 else np.nan,
        "P50": np.median(data) if len(data) > 0 else np.nan,
        "P75": np.percentile(data, 75) if len(data) > 0 else np.nan,
        "P95": np.percentile(data, 95) if len(data) > 0 else np.nan
    }

def build_panel_statistics(sub_df, panel_label):
    rows = []
    
    # 1. Number of holdings (평균 구성종목수)
    holdings_sample = sub_df.groupby("코드")["구성종목수"].mean()
    rows.append(get_stats_row(holdings_sample, "Number of holdings", panel_label))
    
    # 2. Fee (bps) (연간 운용보수 총액)
    fund_fees = sub_df.groupby("코드")["Fee_bps"].mean()
    rows.append(get_stats_row(fund_fees, "Fee (bps)", panel_label))
    
    # 3. Share turnover (상장 첫 6개월 동안의 일별 회전율 평균)
    turnover_sample = sub_df[sub_df["In_6_Months"] == 1].groupby("코드")["daily_turnover"].mean()
    rows.append(get_stats_row(turnover_sample, "Share turnover (months 1-6; %)", panel_label))
    
    # 4. ★ [정정 완료] Market-adjusted return (상장 첫 60개월 동안의 진짜 시장조정수익률)
    mkt_adj_return = sub_df[sub_df["In_60_Months"] == 1].groupby("코드")["Ex_Return_pct"].mean()
    rows.append(get_stats_row(mkt_adj_return, "Market-adjusted return (months 1-60; %)", panel_label))
    
    # 5. Delisted (2025년 말 기준 청산 여부)
    fund_delisted = sub_df.groupby("코드")["Is_Delisted"].last()
    rows.append(get_stats_row(fund_delisted, "Delisted", panel_label))
    
    # --- 2025년 기준 서브셋 단면 추출 ---
    df_2025 = sub_df[sub_df["날짜"].dt.year == 2025]
    
    # 6. Assets under management (AUM) (2025년 말 잔액)
    if len(df_2025) > 0:
        last_idx_2025 = df_2025.groupby("코드")["날짜"].idxmax()
        aum_last_2025 = df_2025.loc[last_idx_2025].set_index("코드")["AUM_bn"]
    else:
        last_idx_all = sub_df.groupby("코드")["날짜"].idxmax()
        aum_last_2025 = sub_df.loc[last_idx_all].set_index("코드")["AUM_bn"]
    rows.append(get_stats_row(aum_last_2025, "Assets under management (bn KRW)", panel_label))
    
    # 7. Implied revenues (2025년 평균 AUM 기반 내재수입)
    if len(df_2025) > 0:
        rev_avg_2025 = df_2025.groupby("코드")["Implied_rev_million"].mean()
    else:
        rev_avg_2025 = sub_df.groupby("코드")["Implied_rev_million"].mean()
    rows.append(get_stats_row(rev_avg_2025, "Implied revenues (m KRW)", panel_label))
    
    return pd.DataFrame(rows)

# ==========================================
# 5. 그룹별 통계량 연산 및 결합
# ==========================================
df["Category_clean"] = df["Category"].str.lower().str.strip()
table1_a = build_panel_statistics(df[df["Category_clean"] == "broad-based"], "A. Broad-based ETFs")
table1_b = build_panel_statistics(df[df["Category_clean"] == "specialized"], "B. Specialized ETFs")

table1_final = pd.concat([table1_a, table1_b], ignore_index=True)

# 반올림 및 컬럼 배치 고정
numeric_cols = ["Mean", "SD", "P5", "P25", "P50", "P75", "P95"]
table1_final[numeric_cols] = table1_final[numeric_cols].round(2)
table1_final = table1_final[["Panel", "Variable", "N", "Mean", "SD", "P5", "P25", "P50", "P75", "P95"]]

# 화면 출력 및 저장
print("\n" + "=" * 45 + " [ MKF500 지수 반영 Table 1 최종 결과 ] " + "=" * 45)
print(table1_final.to_string(index=False))
print("=" * 120 + "\n")

table1_final.to_csv(output_table1_path, index=False, encoding="utf-8-sig")
print(f"[완료] 시장조정수익률 연산이 포함된 최종 요약표가 저장되었습니다.\n 경로: {output_table1_path}\n")