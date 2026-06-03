import os
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics.pairwise import cosine_similarity
import warnings

# 경고 무시
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

# ==========================================
# 1. 파일 경로 및 메인 데이터 로드 (상대경로)
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(current_dir)

pdf_folder = os.path.join(base_dir, "Data", "ETF_PDF")
data_path = os.path.join(base_dir, "Data_result", "Panel_change_Data", "ETF_Data_panel.csv")
list_path = os.path.join(base_dir, "Data_result", "Classification", "ETF_List_Final.xlsx") 

print("📌 정제된 패널 데이터(CSV) 및 리스트(Excel)를 로드하고 있습니다...")

try:
    df_data = pd.read_csv(data_path, encoding='utf-8-sig')
except UnicodeDecodeError:
    df_data = pd.read_csv(data_path, encoding='cp949')

df_list = pd.read_excel(list_path)

df_data.columns = df_data.columns.astype(str).str.strip()
df_list.columns = df_list.columns.astype(str).str.strip()

# 컬럼명 
col_date = '날짜'      
col_code = 'ETF코드'   
col_listing_date = '상장일'

# 🔥 [핵심 수정] 엑셀 J열에 있는 완벽한 분류 열 이름 사용!
col_category = 'Category' 

col_aum = next((c for c in df_data.columns if 'AUM' in c), None)
col_fee = next((c for c in df_data.columns if 'TER' in c or '보수' in c), None)

if not col_aum or not col_fee:
    raise KeyError("CSV 파일에서 AUM 또는 TER 보수 컬럼을 찾을 수 없습니다.")

# 날짜 데이터 정제
df_data[col_date] = pd.to_datetime(df_data[col_date], errors='coerce').dt.normalize()

if col_listing_date in df_list.columns:
    df_list[col_listing_date] = pd.to_datetime(df_list[col_listing_date], errors='coerce').dt.normalize()

# ETF 종목코드 통일 (CSV)
df_data[col_code] = df_data[col_code].astype(str).str.replace(r'[^0-9]', '', regex=True).str.zfill(6)

# ETF 종목코드 통일 (Excel - df_list)
if '종목코드' in df_list.columns:
    df_list['종목코드'] = df_list['종목코드'].astype(str).str.replace(r'[^0-9]', '', regex=True).str.zfill(6)
    df_list = df_list.rename(columns={'종목코드': col_code})
elif '코드' in df_list.columns:
    df_list['코드'] = df_list['코드'].astype(str).str.replace(r'[^0-9]', '', regex=True).str.zfill(6)
    df_list = df_list.rename(columns={'코드': col_code})
elif col_code in df_list.columns:
    df_list[col_code] = df_list[col_code].astype(str).str.replace(r'[^0-9]', '', regex=True).str.zfill(6)

# 값 데이터 숫자형 변환
df_data[col_aum] = pd.to_numeric(df_data[col_aum].astype(str).str.replace(',', ''), errors='coerce')
df_data[col_fee] = pd.to_numeric(df_data[col_fee].astype(str).str.replace(',', ''), errors='coerce')


# ==========================================
# 2. 차별화 지수 산출 함수 (동일)
# ==========================================
def calculate_differentiation_at_date(target_date_obj, active_etfs):
    target_date_str = target_date_obj.strftime('%Y-%m-%d')
    target_date_num_str = target_date_obj.strftime('%Y%m%d')

    print("\n" + "=" * 60)
    print(f"🔄 [{target_date_str}] 구성종목(PDF) 파일 연산 시작")
    print("=" * 60)

    total_etfs = len(active_etfs)
    print(f"📊 대상 ETF 총 개수: {total_etfs}개")

    if total_etfs == 0:
        return pd.DataFrame()

    market_weights = {}
    missing_files_count = 0
    empty_files_count = 0

    for idx, etf_code in enumerate(active_etfs, 1):
        file_pattern = os.path.join(pdf_folder, f"*{etf_code}*.xlsx")
        matched_files = glob.glob(file_pattern)

        if matched_files:
            file_path = matched_files[0]
            try:
                df_pdf = pd.read_excel(file_path, header=5)
                
                if df_pdf.empty or len(df_pdf.columns) < 2:
                    empty_files_count += 1
                    continue

                df_pdf.columns = df_pdf.columns.astype(str).str.strip()

                col_pdf_date = '날짜'
                if col_pdf_date in df_pdf.columns:
                    df_pdf['날짜_정제'] = df_pdf[col_pdf_date].astype(str).str.replace(r'[^0-9]', '', regex=True)
                    df_pdf = df_pdf[df_pdf['날짜_정제'] == target_date_num_str]

                if df_pdf.empty:
                    empty_files_count += 1
                    continue

                col_pdf_name = '구성종목'
                col_pdf_weight = '금액기준 구성비중(%)'

                df_pdf[col_pdf_weight] = pd.to_numeric(
                    df_pdf[col_pdf_weight].astype(str).str.replace('%', '').str.replace(',', ''),
                    errors='coerce'
                )

                df_pdf = df_pdf.dropna(subset=[col_pdf_name, col_pdf_weight])
                
                if df_pdf.empty:
                    empty_files_count += 1
                    continue

                weights = dict(zip(df_pdf[col_pdf_name], df_pdf[col_pdf_weight]))
                market_weights[etf_code] = weights

            except Exception:
                empty_files_count += 1
        else:
            missing_files_count += 1

        if idx % 50 == 0 or idx == total_etfs:
            progress_pct = (idx / total_etfs) * 100
            print(f"⏳ Progress: [{idx}/{total_etfs}] 완료 ({progress_pct:.1f}%)")

    print(f"\n=> 📂 수집 완료 (성공: {len(market_weights)}개 | 누락: {missing_files_count}개 | 내용없음: {empty_files_count}개)")

    if not market_weights:
        print(f"⚠️ 연산 가능한 PDF 데이터가 없습니다.")
        return pd.DataFrame()

    print("🧮 코사인 유사도 마켓 매트릭스 연산 중...")
    all_stocks = sorted(list(set(stock for w in market_weights.values() for stock in w.keys())))
    matrix_data = [[w.get(stock, 0.0) for stock in all_stocks] for w in market_weights.values()]
    df_matrix = pd.DataFrame(matrix_data, index=market_weights.keys(), columns=all_stocks)

    market_average_vector = df_matrix.mean(axis=0).values.reshape(1, -1)

    diff_results = {}
    for etf_code in df_matrix.index:
        etf_vector = df_matrix.loc[etf_code].values.reshape(1, -1)
        sim = cosine_similarity(etf_vector, market_average_vector)[0][0]
        diff_results[etf_code] = (1 - sim) * 100

    df_diff = pd.DataFrame(list(diff_results.items()), columns=[col_code, 'Product_Differentiation'])
    return df_diff


# ==========================================
# 3. 시점별 데이터 필터링 및 통합 
# ==========================================
date_15_str = '2015-12-30'
date_25_str = '2025-12-30'

def process_market_snapshot(date_str):
    target_dt = pd.to_datetime(date_str)

    # 1. 엑셀의 상장일 기준으로 유효한 종목만 뽑기
    if col_listing_date in df_list.columns:
        valid_by_listing = df_list[df_list[col_listing_date] <= target_dt][col_code].unique()
    else:
        valid_by_listing = df_list[col_code].unique()

    # 2. 패널 CSV 데이터 필터링
    df_snapshot = df_data[
        (df_data[col_date] == target_dt) &
        (df_data[col_code].isin(valid_by_listing)) &
        (df_data[col_aum].notna()) &
        (df_data[col_fee].notna())
    ].copy()

    active_etfs = df_snapshot[col_code].unique()
    
    if len(active_etfs) == 0:
        return pd.DataFrame()

    # 3. 차별화 지수(Product Differentiation) 연산
    df_diff = calculate_differentiation_at_date(target_dt, active_etfs)
    if df_diff.empty:
        return pd.DataFrame()

    # 4. 결합: 패널 데이터 + 차별화 지수 + 엑셀 리스트(Category 열 포함!)
    df_merged = pd.merge(df_snapshot, df_diff, on=col_code, how='inner')
    df_merged = pd.merge(df_merged, df_list[[col_code, col_category]], on=col_code, how='left')

    # 보수율 단위 통일
    if df_merged[col_fee].max() <= 1.0:
        df_merged['Fee_bps'] = df_merged[col_fee] * 10000
    else:
        df_merged['Fee_bps'] = df_merged[col_fee]

    return df_merged

data_15 = process_market_snapshot(date_15_str)
data_25 = process_market_snapshot(date_25_str)


# ==========================================
<<<<<<< HEAD
# [추가] 3-1. 좌측 상단 이상치(Fee > 2000bps) 종목 추적
# ==========================================
print("\n" + "="*80)
print(" 🔍 좌측 상단 이상치 영역 (수수료 > 2000bps) 종목 역추적 시작")
print("="*80)

# 2015년과 2025년 데이터 중에서 수수료가 2,000bps를 초과하는 종목 필터링
outliers_15 = data_15[data_15['Fee_bps'] > 2000].copy() if not data_15.empty else pd.DataFrame()
outliers_25 = data_25[data_25['Fee_bps'] > 2000].copy() if not data_25.empty else pd.DataFrame()

# 두 시점의 이상치 데이터에 연도 표기 추가 후 병합
if not outliers_15.empty: outliers_15['Snapshot_Year'] = 2015
if not outliers_25.empty: outliers_25['Snapshot_Year'] = 2025

df_outliers_all = pd.concat([outliers_15, outliers_25], ignore_index=True)

if not df_outliers_all.empty:
    # 엑셀 원본 리스트(df_list)에 '코드명'이나 '종목명' 컬럼이 있다면 함께 매칭해서 보여주기 위해 결합
    # df_list에 '코드명' 혹은 'ETF명' 등 텍스트 컬럼이 있다면 아래 리스트에 추가해 주세요.
    name_col = next((c for c in df_list.columns if '명' in c or '이름' in c or 'Name' in c), None)
    
    if name_col:
        df_outliers_all = pd.merge(df_outliers_all, df_list[[col_code, name_col]], on=col_code, how='left')
        display_cols = ['Snapshot_Year', col_code, name_col, col_category, col_aum, col_fee, 'Fee_bps', 'Product_Differentiation']
    else:
        display_cols = ['Snapshot_Year', col_code, col_category, col_aum, col_fee, 'Fee_bps', 'Product_Differentiation']
        
    print(f"🚨 총 {len(df_outliers_all)}개의 이상치 종목이 발견되었습니다:\n")
    print(df_outliers_all[display_cols].to_string(index=False))
    print("-" * 80)
    
    # 분석 편의를 위해 엑셀 파일로도 저장 처리
    outlier_file_path = os.path.join(base_dir, "Data_result", "ETF_Figure4_Outliers.xlsx")
    df_outliers_all[display_cols].to_excel(outlier_file_path, index=False)
    print(f"💾 이상치 종목 상세 리스트가 엑셀 파일로 저장되었습니다:\n-> {outlier_file_path}")
    
else:
    print("❌ 조건에 맞는 이상치 종목을 찾지 못했습니다. 필터링 조건을 확인해 주세요.")

print("="*80)






# ==========================================
=======
>>>>>>> 3881fa0318c96bad31cccd5846f314262862988e
# 4. 버블 차트 시각화 (J열 Category 기준)
# ==========================================
print("\n📊 버블 차트를 렌더링합니다...")
fig, axes = plt.subplots(1, 2, figsize=(15, 6), sharey=True)
aum_scale = 1e-9

def plot_panel(ax, data, title):
    ax.set_title(title, fontsize=14, pad=15)
    
    if not data.empty and col_category in data.columns:
        # 🔥 [핵심 반영] 엑셀 J열 'Category' 값을 그대로 사용하여 완벽하게 나눕니다!
        b_data = data[data[col_category] == 'Broad-based']
        s_data = data[data[col_category] == 'Specialized']
        
        if len(b_data) > 0:
            ax.scatter(b_data['Product_Differentiation'], b_data['Fee_bps'], s=b_data[col_aum] * aum_scale, 
                       facecolors='none', edgecolors='blue', linewidths=1.5, label='Broad-based ETFs')
        if len(s_data) > 0:
            ax.scatter(s_data['Product_Differentiation'], s_data['Fee_bps'], s=s_data[col_aum] * aum_scale, 
                       facecolors='none', edgecolors='red', linewidths=1.5, label='Specialized ETFs')
                       
        if len(b_data) > 0 or len(s_data) > 0:
            ax.legend(loc='upper left', frameon=True, edgecolor='black')
    else:
        ax.text(0.5, 0.5, 'No Data', ha='center', va='center', fontsize=12)

    ax.set_xlabel("Product differentiation", fontsize=12)
    if ax == axes[0]:
        ax.set_ylabel("Fee (bps)", fontsize=12)
    ax.set_xlim(-5, 105)
    ax.grid(True, linestyle=':', alpha=0.5)

plot_panel(axes[0], data_15, "A  Differentiation, fees, and AUM: 2015")
plot_panel(axes[1], data_25, "B  Differentiation, fees, and AUM: 2025")

max_y15 = data_15['Fee_bps'].max() if not data_15.empty and 'Fee_bps' in data_15.columns else 100
max_y25 = data_25['Fee_bps'].max() if not data_25.empty and 'Fee_bps' in data_25.columns else 100
axes[0].set_ylim(-5, max(max_y15, max_y25) + 10)

plt.tight_layout()
output_image_path = os.path.join(base_dir, "Data_result", "ETF_Market_Structure.png")
plt.savefig(output_image_path, dpi=300)
plt.show()

print(f"🎉 렌더링 완료! 드디어 완벽한 그래프가 생성되었습니다: {output_image_path}")