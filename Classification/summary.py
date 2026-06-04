import os
import glob
import pandas as pd
import numpy as np

# ==========================================
# 1. 깃허브 협업용 완전 자동 상대경로 설정
# ==========================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR) 

panel_data_path = os.path.join(PROJECT_ROOT, 'Data_result', 'Panel_change_Data', 'ETF_Data_panel.csv')
output_dir = os.path.join(PROJECT_ROOT, 'Data_result')
output_csv_path = os.path.join(output_dir, 'ETF_Table1_Summary_Statistics.csv')

print("=" * 70)
print(f"[Git Environment] 프로젝트 루트 감지 완료: {PROJECT_ROOT}")
print(f"입력 데이터 상대 경로 매칭 (패널 데이터): {panel_data_path}")
print(f"출력 통계량 상대 경로 매칭: {output_csv_path}")
print("=" * 70)

if not os.path.exists(panel_data_path):
    raise FileNotFoundError(
        f"패널 데이터를 찾을 수 없습니다. 깃허브 리포지토리에 데이터 파일이 "
        f"정확한 폴더 구조로 동기화되었는지 확인해주세요.\n경로: {panel_data_path}"
    )

# ==========================================
# 2. 패널 데이터 로드 및 날짜 표준화
# ==========================================
print("통합 ETF 패널 데이터 로드 및 전처리 시작...")

try:
    df_panel = pd.read_csv(panel_data_path, encoding='utf-8-sig')
except Exception:
    df_panel = pd.read_csv(panel_data_path, encoding='cp949')

# 컬럼명 양끝 공백 제거 (에러 방지 가드)
df_panel.columns = df_panel.columns.str.strip()

# 데이터 분석을 위한 필수 표준 지표 매핑 (영어 통계량 변수 매칭용 원본 이름 유지)
rename_dict = {
    'AUM(원)': 'AUM', 
    'TER 보수': 'TER', 
    '거래량(주)': 'Volume', 
    '상장주식수(주)': 'Shares',
    '수정주가(원)': 'Price',
    '구성종목수': 'Holdings'
}
df_panel = df_panel.rename(columns=rename_dict)

# 날짜 컬럼을 표준 시계열 객체로 변환 및 연도 추출
df_panel['날짜'] = pd.to_datetime(df_panel['날짜'])
df_panel['Year'] = df_panel['날짜'].dt.year

# 혹시 패널 데이터에 'Holdings'가 아예 없다면 연동 흐름을 위해 결측치 채움
if 'Holdings' not in df_panel.columns:
    df_panel['Holdings'] = np.nan

# ==========================================
# 3. 마스터 리스트 연동을 통한 Category 보완
# ==========================================
# 파일 내에 Category가 없다면 마스터 리스트의 '코드'와 패널의 'ETF코드'를 매핑하여 가져옵니다.
if 'Category' not in df_panel.columns:
    master_list_path = os.path.join(PROJECT_ROOT, "Data_result", "Classification", "ETF_List_Final.xlsx")
    if os.path.exists(master_list_path):
        df_m = pd.read_excel(master_list_path)
        df_m.columns = df_m.columns.str.strip()
        
        if '코드' in df_m.columns and 'Category' in df_m.columns:
            df_m['Clean_Code'] = df_m['코드'].astype(str).str.strip()
            df_panel['ETF코드'] = df_panel['ETF코드'].astype(str).str.strip()
            
            df_m_sub = df_m[['Clean_Code', 'Category']].drop_duplicates().rename(columns={'Clean_Code': 'ETF코드'})
            df_panel = pd.merge(df_panel, df_m_sub, on='ETF코드', how='left')

# ✨ [정렬 기준 변경] 개명하지 않고 원본 컬럼명인 'ETF코드'와 '날짜'를 기준으로 정렬합니다.
df_pivot = df_panel.sort_values(by=['ETF코드', '날짜']).reset_index(drop=True)

# ==========================================
# 4. [논문 정의] 상장일 추적 및 윈도우 필터링
# ==========================================
print("종목별 최초 상장일 추적 및 상장 후 특정 윈도우(6개월/60개월) 통계 계산 중...")
df_launch = df_pivot.groupby('ETF코드')['날짜'].min().reset_index().rename(columns={'날짜': 'Launch_Date'})
df_pivot = pd.merge(df_pivot, df_launch, on='ETF코드', how='left')
df_pivot['Days_Since_Launch'] = (df_pivot['날짜'] - df_pivot['Launch_Date']).dt.days

if 'Category' not in df_pivot.columns:
    df_pivot['Category'] = 'Broad-based'
df_pivot['Category'] = df_pivot['Category'].fillna('Broad-based')

# 마스터 프레임 준비 (ETF코드 기준)
df_etf_level = df_pivot.groupby(['ETF코드', 'Category']).agg({
    'Holdings': 'mean', 
    'TER': 'mean'      
}).reset_index().rename(columns={'Holdings': 'Number of holdings', 'TER': 'Fee (bps)'})

df_etf_level['Fee (bps)'] = df_etf_level['Fee (bps)'] * 100 

# [변수 3] 주식 회전율: 상장 후 딱 6개월(180일) 이내 데이터 제한 평균
df_turnover_window = df_pivot[df_pivot['Days_Since_Launch'] <= 180].copy()
if 'Volume' in df_turnover_window.columns and 'Shares' in df_turnover_window.columns:
    df_turnover_window['Daily_Turnover'] = (df_turnover_window['Volume'] / df_turnover_window['Shares']) * 100
    df_turnover_avg = df_turnover_window.groupby('ETF코드')['Daily_Turnover'].mean().reset_index().rename(columns={'Daily_Turnover': 'Share turnover (months 1-6; %)'})
    df_etf_level = pd.merge(df_etf_level, df_turnover_avg, on='ETF코드', how='left')

# [변수 4] 시장 조정 수익률: 상장 후 60개월 이내 월별 초과수익률
df_return_window = df_pivot[df_pivot['Days_Since_Launch'] <= 1825].copy()
if 'Price' in df_return_window.columns:
    df_return_window['Daily_Ret'] = df_return_window.groupby('ETF코드')['Price'].pct_change()
    df_monthly_ret = df_return_window.groupby(['ETF코드', df_return_window['날짜'].dt.to_period('M')])['Daily_Ret'].apply(lambda x: (1 + x).prod() - 1).reset_index()
    df_monthly_ret['Monthly_Ret_%'] = df_monthly_ret['Daily_Ret'] * 100

    mkt_monthly_ret = df_monthly_ret.groupby('날짜')['Monthly_Ret_%'].mean().reset_index().rename(columns={'Monthly_Ret_%': 'Mkt_Monthly_Ret'})
    df_monthly_ret = pd.merge(df_monthly_ret, mkt_monthly_ret, on='날짜', how='left')
    df_monthly_ret['Mkt_Adj_Ret'] = df_monthly_ret['Monthly_Ret_%'] - df_monthly_ret['Mkt_Monthly_Ret']

    df_ret_avg = df_monthly_ret.groupby('ETF코드')['Mkt_Adj_Ret'].mean().reset_index().rename(columns={'Mkt_Adj_Ret': 'Market-adjusted return (months 1-60; %)'})
    df_etf_level = pd.merge(df_etf_level, df_ret_avg, on='ETF코드', how='left')

# ==========================================
# 5. [논문 정의] 2025 Statistics (기말 AUM 및 연평균 기준 수수료 매출)
# ==========================================
df_2025 = df_pivot[df_pivot['Year'] == 2025].copy()

if not df_2025.empty:
    last_date_2025 = df_2025['날짜'].max()
    df_2025_last = df_2025[df_2025['날짜'] == last_date_2025].copy()
    if 'AUM' in df_2025_last.columns:
        df_2025_last['2025 Assets under management (tril KRW)'] = df_2025_last['AUM'] / 1e12
        df_etf_level = pd.merge(df_etf_level, df_2025_last[['ETF코드', '2025 Assets under management (tril KRW)']], on='ETF코드', how='left')
    
    if 'AUM' in df_2025.columns and 'TER' in df_2025.columns:
        df_2025_avg_aum = df_2025.groupby('ETF코드')['AUM'].mean().reset_index().rename(columns={'AUM': 'Avg_AUM_2025'})
        df_ter_2025 = df_2025.groupby('ETF코드')['TER'].mean().reset_index()
        
        df_rev_2025 = pd.merge(df_2025_avg_aum, df_ter_2025, on='ETF코드', how='left')
        df_rev_2025['2025 Implied revenues (bn KRW)'] = (df_rev_2025['Avg_AUM_2025'] * (df_rev_2025['TER'] / 100)) / 1e9
        df_etf_level = pd.merge(df_etf_level, df_rev_2025[['ETF코드', '2025 Implied revenues (bn KRW)']], on='ETF코드', how='left')

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

df_etf_level['Category'] = df_etf_level['Category'].astype(str).str.strip()
df_broad = df_etf_level[df_etf_level['Category'].str.lower() == 'broad-based']
df_spec = df_etf_level[df_etf_level['Category'].str.lower() == 'specialized']

table_broad = generate_table1_structure(df_broad, 'A. Broad-based ETFs')
table_spec = generate_table1_structure(df_spec, 'B. Specialized ETFs')

final_table = pd.concat([table_broad, table_spec], ignore_index=True)

if not final_table.empty:
    final_table = final_table.set_index(['Group', 'Variable'])
    print("\n" + "=" * 110)
    print(" [Table 1 학술 복제본] 최종 기초통계량 결과 (패널 데이터 원본 컬럼 유지)")
    print("=" * 110)
    print(final_table.round(2).to_string())
    print("=" * 110 + "\n")

    os.makedirs(output_dir, exist_ok=True)
    final_table.to_csv(output_csv_path, encoding='utf-8-sig')
    print(f"[Success] 깃허브 호환 파일 저장이 완료되었습니다.\n경로: {output_csv_path}")
else:
    print("❌ 요약 대조표(Table 1) 생성 조건이 충족되지 않았습니다. 데이터를 확인해 주세요.")