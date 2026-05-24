import os
import glob
import pandas as pd
import numpy as np

# ==========================================
# 1. 깃허브 협업용 완전 자동 상대경로 설정
# ==========================================
# [중요] 이 스크립트 파일(summary.py)이 위치한 폴더의 절대 경로를 실시간으로 잡습니다.
# 터미널 실행 위치나 로컬 사용자명(james 등)에 구애받지 않고 항상 정확한 위치를 반환합니다.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()

# 스크립트 위치에서 딱 한 단계 부모 폴더로 올라가 프로젝트 루트인 'ETF_Replicate' 폴더를 계산합니다.
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR) 

# 프로젝트 루트를 기점으로 하위 폴더 시스템을 정밀 타겟팅합니다.
merged_path = os.path.join(PROJECT_ROOT, 'Data_result', 'ETF_Time_Series_Merged.xlsx')
output_dir = os.path.join(PROJECT_ROOT, 'Data_result')
output_csv_path = os.path.join(output_dir, 'ETF_Table1_Summary_Statistics.csv')

print("=" * 70)
print(f"[Git Environment] 프로젝트 루트 감지 완료: {PROJECT_ROOT}")
print(f"입력 데이터 상대 경로 매칭: {merged_path}")
print(f"출력 통계량 상대 경로 매칭: {output_csv_path}")
print("=" * 70)

if not os.path.exists(merged_path):
    raise FileNotFoundError(
        f"통합 데이터를 찾을 수 없습니다. 깃허브 리포지토리에 데이터 파일이 "
        f"정확한 폴더 구조로 동기화되었는지 확인해주세요.\n경로: {merged_path}"
    )

# ==========================================
# 2. 데이터 통합 로드 및 시계열 Melt
# ==========================================
print("통합 ETF 데이터 로드 및 전처리 시작...")
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
# 3. 데이터 피벗 및 엑셀 변수 정밀 매칭
# ==========================================
df_pivot = df_long.pivot_table(
    index=['코드', '코드명', 'Category', 'Year', 'Date'], 
    columns='아이템명', 
    values='Value', 
    aggfunc='first'
).reset_index()

df_pivot.columns.name = None

df_pivot = df_pivot.rename(columns={
    'AUM(원)': 'AUM', 
    'TER 보수': 'TER', 
    '구성종목수': 'Holdings',
    '거래량(주)': 'Volume', 
    '상장주식수(주)': 'Shares',
    '수정주가(원)': 'Price'
})

df_pivot = df_pivot.sort_values(by=['코드', 'Date']).reset_index(drop=True)

# ==========================================
# 4. [논문 정의] 상장일 추적 및 윈도우 필터링
# ==========================================
print("종목별 최초 상장일 추적 및 상장 후 특정 윈도우(6개월/60개월) 통계 계산 중...")
df_launch = df_pivot.groupby('코드')['Date'].min().reset_index().rename(columns={'Date': 'Launch_Date'})
df_pivot = pd.merge(df_pivot, df_launch, on='코드', how='left')
df_pivot['Days_Since_Launch'] = (df_pivot['Date'] - df_pivot['Launch_Date']).dt.days

# 마스터 프레임 준비
df_etf_level = df_pivot.groupby(['코드', 'Category']).agg({
    'Holdings': 'mean', 
    'TER': 'mean'      
}).reset_index().rename(columns={'Holdings': 'Number of holdings', 'TER': 'Fee (bps)'})

df_etf_level['Fee (bps)'] = df_etf_level['Fee (bps)'] * 100 

# [변수 3] 주식 회전율: 상장 후 딱 6개월(180일) 이내 데이터 제한 평균
df_turnover_window = df_pivot[df_pivot['Days_Since_Launch'] <= 180].copy()
df_turnover_window['Daily_Turnover'] = (df_turnover_window['Volume'] / df_turnover_window['Shares']) * 100
df_turnover_avg = df_turnover_window.groupby('코드')['Daily_Turnover'].mean().reset_index().rename(columns={'Daily_Turnover': 'Share turnover (months 1-6; %)'})
df_etf_level = pd.merge(df_etf_level, df_turnover_avg, on='코드', how='left')

# [변수 4] 시장 조정 수익률: 상장 후 60개월 이내 월별 초과수익률
df_return_window = df_pivot[df_pivot['Days_Since_Launch'] <= 1825].copy()
df_return_window['Daily_Ret'] = df_return_window.groupby('코드')['Price'].pct_change()
df_monthly_ret = df_return_window.groupby(['코드', df_return_window['Date'].dt.to_period('M')])['Daily_Ret'].apply(lambda x: (1 + x).prod() - 1).reset_index()
df_monthly_ret['Monthly_Ret_%'] = df_monthly_ret['Daily_Ret'] * 100

mkt_monthly_ret = df_monthly_ret.groupby('Date')['Monthly_Ret_%'].mean().reset_index().rename(columns={'Monthly_Ret_%': 'Mkt_Monthly_Ret'})
df_monthly_ret = pd.merge(df_monthly_ret, mkt_monthly_ret, on='Date', how='left')
df_monthly_ret['Mkt_Adj_Ret'] = df_monthly_ret['Monthly_Ret_%'] - df_monthly_ret['Mkt_Monthly_Ret']

df_ret_avg = df_monthly_ret.groupby('코드')['Mkt_Adj_Ret'].mean().reset_index().rename(columns={'Mkt_Adj_Ret': 'Market-adjusted return (months 1-60; %)'})
df_etf_level = pd.merge(df_etf_level, df_ret_avg, on='코드', how='left')

# ==========================================
# 5. [논문 정의] 2025 Statistics (기말 AUM 및 연평균 기준 수수료 매출)
# ==========================================
df_2025 = df_pivot[df_pivot['Year'] == 2025].copy()

if not df_2025.empty:
    last_date_2025 = df_2025['Date'].max()
    df_2025_last = df_2025[df_2025['Date'] == last_date_2025].copy()
    df_2025_last['2025 Assets under management (tril KRW)'] = df_2025_last['AUM'] / 1e12
    
    df_2025_avg_aum = df_2025.groupby('코드')['AUM'].mean().reset_index().rename(columns={'AUM': 'Avg_AUM_2025'})
    df_ter_2025 = df_2025.groupby('코드')['TER'].mean().reset_index()
    
    df_rev_2025 = pd.merge(df_2025_avg_aum, df_ter_2025, on='코드', how='left')
    df_rev_2025['2025 Implied revenues (bn KRW)'] = (df_rev_2025['Avg_AUM_2025'] * (df_rev_2025['TER'] / 100)) / 1e9
    
    df_etf_level = pd.merge(df_etf_level, df_2025_last[['코드', '2025 Assets under management (tril KRW)']], on='코드', how='left')
    df_etf_level = pd.merge(df_etf_level, df_rev_2025[['코드', '2025 Implied revenues (bn KRW)']], on='코드', how='left')

# ==========================================
# 6. 논문 표준 통계량 구조화 및 CSV 저장
# ==========================================
def generate_table1_structure(df_sub, group_label):
    target_vars = [
        'Number of holdings',
        'Fee (bps)',
        'Share turnover (months 1-6; %)',
        'Market-adjusted return (months 1-60; %)',
        '2025 Assets under management (tril KRW)',
        '2025 Implied revenues (bn KRW)'
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

df_broad = df_etf_level[df_etf_level['Category'].str.lower() == 'broad-based']
df_spec = df_etf_level[df_etf_level['Category'].str.lower() == 'specialized']

table_broad = generate_table1_structure(df_broad, 'A. Broad-based ETFs')
table_spec = generate_table1_structure(df_spec, 'B. Specialized ETFs')

final_table = pd.concat([table_broad, table_spec], ignore_index=True)
final_table = final_table.set_index(['Group', 'Variable'])

print("\n" + "=" * 110)
print(" [Table 1 학술 복제본] 최종 기초통계량 결과")
print("=" * 110)
print(final_table.round(2).to_string())
print("=" * 110 + "\n")

# 출력 디렉토리 확인 및 저장
os.makedirs(output_dir, exist_ok=True)
final_table.to_csv(output_csv_path, encoding='utf-8-sig')
print(f"[Success] 깃허브 호환 파일 저장이 완료되었습니다.\n경로: {output_csv_path}")