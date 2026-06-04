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
col_code = '코드'   
col_listing_date = '상장일'
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
# 2. 차별화 지수 산출 함수 (누락 추적 로직 추가)
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
    
    # 💥 누락 종목 분석을 위한 추적 백그라운드 리스트 생성
    missing_files_list = []
    empty_files_list = []

    for idx, etf_code in enumerate(active_etfs, 1):
        file_pattern = os.path.join(pdf_folder, f"*{etf_code}*.xlsx")
        matched_files = glob.glob(file_pattern)

        if matched_files:
            file_path = matched_files[0]
            try:
                df_pdf = pd.read_excel(file_path, header=5)
                
                if df_pdf.empty or len(df_pdf.columns) < 2:
                    empty_files_list.append(etf_code)
                    continue

                df_pdf.columns = df_pdf.columns.astype(str).str.strip()

                col_pdf_date = '날짜'
                if col_pdf_date in df_pdf.columns:
                    df_pdf['날짜_정제'] = df_pdf[col_pdf_date].astype(str).str.replace(r'[^0-9]', '', regex=True)
                    df_pdf = df_pdf[df_pdf['날짜_정제'] == target_date_num_str]

                if df_pdf.empty:
                    empty_files_list.append(etf_code)
                    continue

                col_pdf_name = '구성종목'
                col_pdf_weight = '금액기준 구성비중(%)'

                df_pdf[col_pdf_weight] = pd.to_numeric(
                    df_pdf[col_pdf_weight].astype(str).str.replace('%', '').str.replace(',', ''),
                    errors='coerce'
                )

                df_pdf = df_pdf.dropna(subset=[col_pdf_name, col_pdf_weight])
                
                if df_pdf.empty:
                    empty_files_list.append(etf_code)
                    continue

                weights = dict(zip(df_pdf[col_pdf_name], df_pdf[col_pdf_weight]))
                market_weights[etf_code] = weights

            except Exception:
                empty_files_list.append(etf_code)
        else:
            missing_files_list.append(etf_code)

        if idx % 50 == 0 or idx == total_etfs:
            progress_pct = (idx / total_etfs) * 100
            print(f"⏳ Progress: [{idx}/{total_etfs}] 완료 ({progress_pct:.1f}%)")

    print(f"\n=> 📂 수집 완료 (성공: {len(market_weights)}개 | 누락: {len(missing_files_list)}개 | 내용없음/날짜미매칭: {len(empty_files_list)}개)")

    # 💥 [추가 로직] 인간용 가독성 마스터 결합 처리 (엑셀 데이터 기준 매칭)
    name_col = '코드명' if '코드명' in df_list.columns else next((c for c in df_list.columns if '명' in c or '이름' in c), None)

    if len(missing_files_list) > 0:
        print("\n❌ [경고] PDF 파일 자체가 폴더에 존재하지 않는 종목 (누락):")
        for code in missing_files_list:
            etf_name = df_list[df_list[col_code] == code][name_col].values[0] if code in df_list[col_code].values and name_col else "이름 미확인"
            print(f"   - 코드: {code} | ETF명: {etf_name}")

    if len(empty_files_list) > 0:
        print("\n⚠️ [확인] 파일은 있으나 텅 비었거나 해당 날짜 데이터가 없는 종목 (내용없음):")
        for code in empty_files_list:
            etf_name = df_list[df_list[col_code] == code][name_col].values[0] if code in df_list[col_code].values and name_col else "이름 미확인"
            print(f"   - 코드: {code} | ETF명: {etf_name}")

    if not market_weights:
        print(f"⚠️ 연산 가능한 PDF 데이터가 없습니다.")
        return pd.DataFrame()

    print("\n🧮 코사인 유사도 마켓 매트릭스 연산 중...")
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

    if col_listing_date in df_list.columns:
        valid_by_listing = df_list[df_list[col_listing_date] <= target_dt][col_code].unique()
    else:
        valid_by_listing = df_list[col_code].unique()

    df_snapshot = df_data[
        (df_data[col_date] == target_dt) &
        (df_data[col_code].isin(valid_by_listing)) &
        (df_data[col_aum].notna()) &
        (df_data[col_fee].notna())
    ].copy()

    active_etfs = df_snapshot[col_code].unique()
    
    if len(active_etfs) == 0:
        return pd.DataFrame()

    df_diff = calculate_differentiation_at_date(target_dt, active_etfs)
    if df_diff.empty:
        return pd.DataFrame()

    df_merged = pd.merge(df_snapshot, df_diff, on=col_code, how='inner')
    df_merged = pd.merge(df_merged, df_list[[col_code, col_category]], on=col_code, how='left')

    if df_merged[col_fee].max() <= 1.0:
        df_merged['Fee_bps'] = df_merged[col_fee] * 10000
    else:
        df_merged['Fee_bps'] = df_merged[col_fee]

    return df_merged

data_15 = process_market_snapshot(date_15_str)
data_25 = process_market_snapshot(date_25_str)


# ==========================================
# 3-1. 시점별 전체 마스터 결과 데이터 CSV 저장
# ==========================================
print("\n" + "="*80)
print(" 💾 2015년 및 2025년 전체 결합 데이터(마스터) 파일 저장 시작")
print("=" * 80)

if '코드명' in df_list.columns:
    df_meta_names = df_list[[col_code, '코드명']].drop_duplicates(subset=[col_code])
else:
    df_meta_names = pd.DataFrame(columns=[col_code, '코드명'])

final_cols_layout = ['코드', '코드명', 'Category', col_aum, col_fee, 'Fee_bps', 'Product_Differentiation']

if not data_15.empty:
    if '코드명' in df_meta_names.columns:
        data_15 = pd.merge(data_15, df_meta_names, on=col_code, how='left')
    actual_cols_15 = [c for c in final_cols_layout if c in data_15.columns]
    df_save_15 = data_15[actual_cols_15].copy()
    path_csv_15 = os.path.join(base_dir, "Data_result", "ETF_Market_Data_2015.csv")
    df_save_15.to_csv(path_csv_15, index=False, encoding='utf-8-sig')
    print(f"✅ [2015년] 전체 데이터 ({len(df_save_15)}개 종목) 저장 완료 -> {path_csv_15}")
else:
    print("❌ [2015년] 대상 데이터가 없어 파일 저장을 건너뜁니다.")

if not data_25.empty:
    if '코드명' in df_meta_names.columns:
        data_25 = pd.merge(data_25, df_meta_names, on=col_code, how='left')
    actual_cols_25 = [c for c in final_cols_layout if c in data_25.columns]
    df_save_25 = data_25[actual_cols_25].copy()
    path_csv_25 = os.path.join(base_dir, "Data_result", "ETF_Market_Data_2025.csv")
    df_save_25.to_csv(path_csv_25, index=False, encoding='utf-8-sig')
    print(f"✅ [2025년] 전체 데이터 ({len(df_save_25)}개 종목) 저장 완료 -> {path_csv_25}")
else:
    print("❌ [2025년] 대상 데이터가 없어 파일 저장을 건너뜁니다.")

print("="*80)


# ==========================================
# 4. 버블 차트 시각화
# ==========================================
print("\n📊 버블 차트를 렌더링합니다...")
fig, axes = plt.subplots(1, 2, figsize=(15, 6), sharey=True)
aum_scale = 1e-9

def plot_panel(ax, data, title):
    ax.set_title(title, fontsize=14, pad=15)
    
    if not data.empty and col_category in data.columns:
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