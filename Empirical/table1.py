import pandas as pd
import numpy as np
from pathlib import Path

current_file = Path(__file__).resolve()
project_dir = next((parent for parent in current_file.parents if parent.name == "ETF_Replicate"), current_file.parent.parent)

preprocessed_path = project_dir / "Data_result" / "Panel_change_Data" / "ETF_Data_panel_date0.csv"
output_table1_path = project_dir / "Data_result" / "Panel_change_Data" / "table1.csv"

print("=" * 60)
print("2단계: 2002~2025 전체 시계열 기반 최종 Table 1 산출을 시작합니다.")
print("=" * 60)

df = pd.read_csv(preprocessed_path, encoding="utf-8-sig")

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
    
    # 1. 수수료 (Fee bps)
    fund_fees = sub_df.groupby("코드")["Fee_bps"].mean()
    rows.append(get_stats_row(fund_fees, "Fee (bps)", panel_label))
    
    # 2. 주식 회전율 (상장 첫 6개월 데이터)
    turnover_sample = sub_df[sub_df["In_6_Months"] == 1].groupby("코드")["daily_turnover"].mean()
    rows.append(get_stats_row(turnover_sample, "Share turnover (months 1-6; %)", panel_label))
    
    # 3. 시장 조정 수익률 (상장 첫 60개월 데이터)
    return_sample = sub_df[sub_df["In_60_Months"] == 1].groupby("코드")["Return_pct"].mean()
    rows.append(get_stats_row(return_sample, "Market-adjusted return (months 1-60; %)", panel_label))
    
    # 4. 상장폐지 (Delisted)
    fund_delisted = sub_df.groupby("코드")["Is_Delisted"].last()
    rows.append(get_stats_row(fund_delisted, "Delisted", panel_label))
    
    # 5 & 6. 자산규모 및 내재수입 (★연도 고정 탈피: 각 펀드가 가진 시계열의 가장 최근 날짜 단면 추출)
    last_idx = sub_df.groupby("코드")["날짜"].idxmax()
    df_last = sub_df.loc[last_idx]
    
    aum_last = df_last.set_index("코드")["AUM_bn"]
    rev_last = df_last.set_index("코드")["Implied_rev_million"]
        
    rows.append(get_stats_row(aum_last, "Assets under management (bn KRW)", panel_label))
    rows.append(get_stats_row(rev_last, "Implied revenues (m KRW)", panel_label))
    
    return pd.DataFrame(rows)

df["Category_clean"] = df["Category"].str.lower().str.strip()
table1_a = build_panel_statistics(df[df["Category_clean"] == "broad-based"], "A. Broad-based ETFs")
table1_b = build_panel_statistics(df[df["Category_clean"] == "specialized"], "B. Specialized ETFs")

table1_final = pd.concat([table1_a, table1_b], ignore_index=True)
numeric_cols = ["Mean", "SD", "P5", "P25", "P50", "P75", "P95"]
table1_final[numeric_cols] = table1_final[numeric_cols].round(2)

print("\n" + "=" * 42 + " [ 한국 데이터 기준 Table 1 결과 ] " + "=" * 42)
print(table1_final.to_string(index=False))
print("=" * 115 + "\n")

table1_final.to_csv(output_table1_path, index=False, encoding="utf-8-sig")
print("[완료] 한국 ETF 시장 특성이 반영된 결과 요약표가 'table1.csv'로 저장되었습니다.")