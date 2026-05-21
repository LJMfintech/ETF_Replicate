import os
import pandas as pd
import numpy as np

# ==========================================
# 1. 경로 설정 (스크립트 위치 기준 자동 상대경로 계산)
# ==========================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR) 

merged_path = os.path.join(PROJECT_ROOT, 'Data_result', 'ETF_Time_Series_Merged.xlsx')
output_dir = os.path.join(PROJECT_ROOT, 'Data_result')
output_csv_path = os.path.join(output_dir, 'ETF_Table1_Refined_2025.csv')

print("=" * 60)
print(f"통합 데이터 파일 로드 경로: {merged_path}")
print(f"수정본 Table 1 저장 경로: {output_csv_path}")
print("=" * 60)

if not os.path.exists(merged_path):
    raise FileNotFoundError(f"통합 데이터를 찾을 수 없습니다. 경로를 확인해주세요: {merged_path}")

# ==========================================
# 2. 데이터 통합 로드 및 시계열 녹이기 (Melt)
# ==========================================
print("통합 ETF 데이터 로드 중 (대용량 파일이므로 변환에 시간이 소요됩니다)...")
df_total = pd.read_excel(merged_path)

fixed_cols = ['코드', '코드명', '유형', '아이템코드', '아이템명', '집계주기', 'Category']
date_cols = [col for col in df_total.columns if col not in fixed_cols]

df_long = df_total.melt(
    id_vars=fixed_cols, 
    value_vars=date_cols, 
    var_name='Date', 
    value_name='Value'
)
df_long = df_long.dropna(subset=['Value'])
df_long['Date'] = pd.to_datetime(df_long['Date'])
df_long['Year'] = df_long['Date'].dt.year
df_long['Value'] = pd.to_numeric(df_long['Value'], errors='coerce')

# ==========================================
# 3. 데이터 피벗 및 엑셀 변수 정밀 매칭 (오류 해결)
# ==========================================
print("시계열 데이터 기반 핵심 변수 가공 중...")
df_pivot = df_long.pivot_table(
    index=['코드', '코드명', 'Category', 'Year', 'Date'], 
    columns='아이템명', 
    values='Value', 
    aggfunc='first'
).reset_index()

df_pivot.columns.name = None

# [오류 해결 포인트] 올려주신 이미지 속 변수명과 100% 일치하도록 매핑 명시
df_pivot = df_pivot.rename(columns={
    'AUM(원)': 'AUM', 
    'TER 보수': 'TER', 
    '구성종목수': 'Holdings',
    '거래량(주)': 'Volume', 
    '상장주식수(주)': 'Shares',   # '상장주식수(주)' 컬럼을 'Shares'로 정확히 인지하도록 수정
    '수정주가(원)': 'Price'
})

# 데이터 정렬 (수익률 연산용)
df_pivot = df_pivot.sort_values(by=['코드', 'Date']).reset_index(drop=True)

# --- [변수 1 & 2] 구성종목수 및 보수(bps) ---
df_pivot['Number of holdings'] = df_pivot['Holdings']
df_pivot['Fee (bps)'] = df_pivot['TER'] * 100

# --- [변수 3] 주식 회전율 (Share turnover %) ---
# 일별 회전율 = (거래량 / 상장주식수) * 100 -> 정밀 매핑 완료로 KeyError 제거됨
df_pivot['Share turnover (%)'] = (df_pivot['Volume'] / df_pivot['Shares']) * 100

# --- [변수 4] 시장 조정 수익률 (Market-adjusted return %) ---
df_pivot['Ret'] = df_pivot.groupby('코드')['Price'].pct_change() * 100
market_ret = df_pivot.groupby('Date')['Ret'].mean().reset_index().rename(columns={'Ret': 'Mkt_Ret'})
df_pivot = pd.merge(df_pivot, market_ret, on='Date', how='left')
df_pivot['Market-adjusted return (%)'] = df_pivot['Ret'] - df_pivot['Mkt_Ret']

# ==========================================
# 4. 횡단면 종목 레벨 집계 및 2025년 마지막 날 스냅샷 결합
# ==========================================
print("종목별 평균 통계 산출 및 2025년 최종일 데이터 결합 중...")

# 1) 4개 주요 변수에 대한 전체 기간 종목별 평균값 계산
df_etf_level = df_pivot.groupby(['코드', 'Category']).agg({
    'Number of holdings': 'mean',
    'Fee (bps)': 'mean',
    'Share turnover (%)': 'mean',
    'Market-adjusted return (%)': 'mean'
}).reset_index()

# 2) 2025년 데이터 필터링 후 '마지막 날' 추출
df_2025 = df_pivot[df_pivot['Year'] == 2025].copy()

if not df_2025.empty:
    last_date_2025 = df_2025['Date'].max()
    print(f"-> 확인된 2025년 마지막 거래일 기준시점: {last_date_2025.strftime('%Y-%m-%d')}")
    
    # 2025년 마지막 날의 데이터만 핀포인트 추출
    df_2025_last_day = df_2025[df_2025['Date'] == last_date_2025].copy()
    
    # [변수 5] 2025년 마지막 날 기준 AUM -> 조(Trillion) 원 단위
    df_2025_last_day['2025 End AUM (tril KRW)'] = df_2025_last_day['AUM'] / 1e12
    
    # [변수 6] 2025년 마지막 날 기준 수수료 매출 (당일 AUM * TER / 100) -> 십억(Billion) 원 단위
    df_2025_last_day['2025 End Implied revenues (bn KRW)'] = (df_2025_last_day['AUM'] * (df_2025_last_day['TER'] / 100)) / 1e9
    
    # 필요한 스냅샷 컬럼만 선택하여 메인 종목 데이터셋에 가로 결합(Merge)
    df_snapshot = df_2025_last_day[['코드', '2025 End AUM (tril KRW)', '2025 End Implied revenues (bn KRW)']]
    df_etf_level = pd.merge(df_etf_level, df_snapshot, on='코드', how='left')

# ==========================================
# 5. 논문 Table 1 표준 양식 생성 (8대 지표 프레임)
# ==========================================
def generate_table1_refined(df_sub, group_label):
    target_vars = [
        'Number of holdings',
        'Fee (bps)',
        'Share turnover (%)',
        'Market-adjusted return (%)',
        '2025 End AUM (tril KRW)',
        '2025 End Implied revenues (bn KRW)'
    ]
    
    records = []
    for var in target_vars:
        if var not in df_sub.columns:
            continue
        data_series = df_sub[var].dropna()
        n_count = len(data_series)
        
        if n_count == 0:
            continue
            
        records.append({
            'Variable': var,
            'N': n_count,
            'Mean': data_series.mean(),
            'SD': data_series.std(),
            'P5': np.percentile(data_series, 5),
            'P25': np.percentile(data_series, 25),
            'P50': np.percentile(data_series, 50),
            'P75': np.percentile(data_series, 75),
            'P95': np.percentile(data_series, 95)
        })
        
    res_df = pd.DataFrame(records)
    if not res_df.empty:
        res_df.insert(0, 'Group', group_label)
    return res_df

# 그룹화 및 결합
df_broad = df_etf_level[df_etf_level['Category'].str.lower() == 'broad-based']
df_spec = df_etf_level[df_etf_level['Category'].str.lower() == 'specialized']

table_broad = generate_table1_refined(df_broad, 'A. Broad-based ETFs')
table_spec = generate_table1_refined(df_spec, 'B. Specialized ETFs')

final_table = pd.concat([table_broad, table_spec], ignore_index=True)
final_table = final_table.set_index(['Group', 'Variable'])

# ==========================================
# 6. 결과 출력 및 CSV 파일 저장
# ==========================================
print("\n" + "=" * 105)
print(" [Table 1 완료본] ETF Summary Statistics (오류 수정 완료)")
print("=" * 105)
print(final_table.round(2).to_string())
print("=" * 105 + "\n")

os.makedirs(output_dir, exist_ok=True)
final_table.to_csv(output_csv_path, encoding='utf-8-sig')
print(f"최정 정제본 CSV 파일이 오류 없이 저장되었습니다:\n-> {output_csv_path}")