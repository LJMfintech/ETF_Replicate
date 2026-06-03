import os
import glob
import re
import pandas as pd
import numpy as np

# 1. 📌 회원님 컴퓨터에 맞춤 고정된 절대경로 설정
# (상대경로 계산 시 발생하는 꼬임 현상을 완벽하게 차단합니다.)
BASE_DIR = r"C:\Users\82104\Desktop\ETF_Replicate"

pdf_dir = os.path.join(BASE_DIR, "Data", "ETF_PDF")
master_list_path = os.path.join(BASE_DIR, "Data_result", "Classification", "ETF_List_Final.xlsx")
output_dir = os.path.join(BASE_DIR, "Data_result", "Classification")

# 2. 마스터 ETF 목록 불러오기
print(f"============================================================")
print(f"📋 마스터 리스트 로드 중...")
print(f"📂 로드 경로: {master_list_path}")

try:
    df_master = pd.read_excel(master_list_path)
except Exception as e:
    raise FileNotFoundError(f"❌ 마스터 리스트 파일을 찾을 수 없습니다. 경로를 확인해주세요.\n오류 내용: {e}")

df_master.columns = df_master.columns.str.strip()

# '종목명' 컬럼이 있으면 활용하기 위해 체크
name_col = '종목명' if '종목명' in df_master.columns else None

if '코드' in df_master.columns:
    # 인위적인 자릿수 변환 없이 원본 문자열 그대로 가져옵니다.
    df_master['Clean_Code'] = df_master['코드'].astype(str).str.strip()
else:
    raise KeyError(f"❌ 마스터 파일에 '코드' 컬럼이 없습니다. 현재 컬럼: {list(df_master.columns)}")

target_codes = df_master['Clean_Code'].unique()
print(f"✔ 분석 대상 ETF 개수: {len(target_codes)}개")

# 3. PDF 폴더 내의 모든 구성종목 파일 확보
all_pdf_files = glob.glob(os.path.join(pdf_dir, "*.xlsx")) + glob.glob(os.path.join(pdf_dir, "*.csv"))

# 4. 마스터 리스트와 PDF 파일 매핑 및 오류 발생 행(Line) 추적
matched_files = {}
unmatched_info = []  # 오류 정보를 (엑셀 줄번호, 원본코드, 종목명) 형태로 저장

# 엑셀의 index는 0부터 시작하므로 실제 엑셀 좌측 행 번호와 맞추기 위해 +2를 해줍니다.
for idx, row in df_master.iterrows():
    code = row['Clean_Code']
    name = row[name_col] if name_col else "종목명 없음"
    excel_line_num = idx + 2  # 엑셀 프로그램 좌측에 적힌 실제 행 번호
    
    # A가 붙어있든 안 붙어있든 원본 텍스트 그대로 매칭 시도
    code_no_A = code.replace('A', '')
    pattern = f"A{code_no_A}|_{code_no_A}|A{code}|_{code}"
    is_matched = False
    
    for file_path in all_pdf_files:
        file_name = os.path.basename(file_path)
        if re.search(pattern, file_name):
            matched_files[code] = file_path
            is_matched = True
            break
            
    if not is_matched:
        # 매칭 실패 시 원본 데이터 상태 그대로 기록
        unmatched_info.append({
            'line': excel_line_num,
            'code': code,
            'name': name
        })

print(f"✔ 파일 매칭 완료: 대상 {len(target_codes)}개 중 {len(matched_files)}개 파일 매칭 성공.")

# 🚨 매칭 실패한 파일들의 엑셀 행 번호 원본 그대로 출력
if unmatched_info:
    print(f"\n⚠️  [매칭 실패 알림] PDF 폴더에서 파일을 찾지 못한 ETF가 총 {len(unmatched_info)}개 있습니다.")
    print(f"📌 아래 적힌 엑셀 행 번호를 보고 마스터 리스트(ETF_List_Final.xlsx)를 직접 확인해 보세요:")
    print(f"------------------------------------------------------------")
    for item in unmatched_info:
        print(f" 📂 [엑셀 제 {item['line']}행]  코드 데이터: {item['code']}  |  종목명: {item['name']}")
    print(f"------------------------------------------------------------")
    print(f"💡 팁: 엑셀 내에 기재된 데이터가 온전한 6자리인지 눈으로 확인하기 가장 좋은 상태입니다.")
else:
    print(f"\n🎉 훌륭합니다! 모든 ETF 파일이 100% 완벽하게 매칭되었습니다.")

print(f"============================================================")

# =================================================================
# 5. 분석 기준 연도 설정 (원하는 연도로 변경 가능)
# =================================================================
TARGET_YEAR = "2025" 
print(f"\n🚀 {TARGET_YEAR}년도 구성종목 데이터 통합 작업을 시작합니다... (50개 단위 브리핑 적용)\n")

all_holdings = []
success_count = 0
fail_count = 0
total_matched = len(matched_files)

for idx, (code, file_path) in enumerate(matched_files.items(), 1):
    file_name = os.path.basename(file_path)
    
    try:
        if file_path.endswith('.xlsx'):
            df_header_check = pd.read_excel(file_path, nrows=10, header=None)
            header_row = 0
            for r_idx, row in df_header_check.iterrows():
                if '날짜' in row.values:
                    header_row = r_idx
                    break
            df_pdf = pd.read_excel(file_path, skiprows=header_row)
        else:
            df_header_check = pd.read_csv(file_path, nrows=10, header=None, encoding='cp949')
            header_row = 0
            for r_idx, row in df_header_check.iterrows():
                if '날짜' in row.values:
                    header_row = r_idx
                    break
            df_pdf = pd.read_csv(file_path, skiprows=header_row, encoding='cp949')
    except Exception as e:
        fail_count += 1
        continue
    
    df_pdf.columns = df_pdf.columns.str.strip()
    
    if '날짜' not in df_pdf.columns:
        fail_count += 1
        continue
        
    df_pdf['날짜_문자열'] = df_pdf['날짜'].astype(str).str.strip()
    
    df_year = df_pdf[df_pdf['날짜_문자열'].str.startswith(TARGET_YEAR)]
    if df_year.empty:
        fail_count += 1
        continue
        
    max_date = df_year['날짜_문자열'].max()
    df_filtered = df_year[df_year['날짜_문자열'] == max_date]
    
    target_weight_col = '금액기준 구성비중(%)'
    
    if '구성종목코드' not in df_filtered.columns or target_weight_col not in df_filtered.columns:
        fail_count += 1
        continue
        
    df_filtered = df_filtered[['구성종목코드', target_weight_col]].copy()
    df_filtered = df_filtered.dropna(subset=['구성종목코드'])
    df_filtered['구성종목코드'] = df_filtered['구성종목코드'].astype(str).str.strip()
    df_filtered = df_filtered[df_filtered['구성종목코드'] != '']
    
    df_filtered = df_filtered.rename(columns={target_weight_col: 'Raw_Weight'})
    df_filtered['ETF_Code'] = f"A{code}"
    
    all_holdings.append(df_filtered)
    success_count += 1

    # 50개 파일마다 진행 상황 출력
    if idx % 50 == 0 or idx == total_matched:
        print(f" ⏳ [중간 알림] 총 {total_matched}개 파일 중 {idx}개 분석 진행 완료...")
        print(f"    └ 현재까지 성공적으로 병합 대기 중: {success_count}개 / 조건 미달 및 제외: {fail_count}개")
        print(f"    └ 직전 처리된 파일: A{code} ({file_name})\n")

# 6. 하나의 거대한 매트릭스 행렬로 병합 및 변환
print(f"============================================================")
print(f"🔄 최종 데이터 수집 완료! {success_count}개 ETF 데이터를 기반으로 가로형 매트릭스 결합 중...")

if all_holdings:
    df_total = pd.concat(all_holdings, ignore_index=True)
    df_matrix = df_total.pivot_table(index='구성종목코드', columns='ETF_Code', values='Raw_Weight', aggfunc='first')
    df_matrix = df_matrix.fillna(0)
    df_matrix = df_matrix / 100.0
    df_matrix['Market_Average'] = df_matrix.mean(axis=1)
    df_matrix.index.name = "Stock_Code"
    
    # 7. 결과 CSV 파일 저장
    output_path = os.path.join(output_dir, f"ETF_Portfolio_Matrix_{TARGET_YEAR}.csv")
    
    os.makedirs(output_dir, exist_ok=True)
    df_matrix.to_csv(output_path, encoding='utf-8-sig', index=True)
    
    print("-" * 60)
    print(f"🎉 {TARGET_YEAR}년 포트폴리오 매트릭스 행렬 최종 빌드 성공!")
    print(f"💾 저장 위치: {output_path}")
    print(f"📊 최종 데이터 규모: 총 주식 {df_matrix.shape[0]}개  x  성공한 ETF {df_matrix.shape[1] - 1}개")
    print(f"📉 결산 요약: 정상 병합 {success_count}개 / 조건 미달 및 실패 {fail_count}개")
    print("-" * 60)
else:
    print(f"❌ {TARGET_YEAR}년에 정상적으로 추출된 ETF 데이터가 단 한 개도 없습니다.")