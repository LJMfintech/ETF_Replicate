import os
import glob
import pandas as pd
import warnings

# 엑셀 로드 시 발생하는 단순 서식 경고 무시
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

# ==========================================
# 1. 경로 설정 (스크립트 파일 위치 기준 상대경로)
# ==========================================
# 이 스크립트가 'C:\Users\james\Desktop\ETF_Replicate\Empirical' 폴더 등에 있다고 가정합니다.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()

# 한 단계 위로 올라가 프로젝트 루트인 'ETF_Replicate'를 잡습니다.
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# 입력 폴더(ETF_PDF) 및 출력 폴더(Data_result) 경로 구성
pdf_folder = os.path.join(PROJECT_ROOT, 'Data', 'ETF_PDF')
output_dir = os.path.join(PROJECT_ROOT, 'Data_result')
output_file_path = os.path.join(output_dir, 'Unique_Stock_List.csv')

print("=" * 60)
print(f"📂 탐색할 PDF 폴더 경로: {pdf_folder}")
print(f"💾 저장 예정 CSV 경로: {output_file_path}")
print("=" * 60)

# ==========================================
# 2. 엑셀 파일 탐색 및 종목명 수집
# ==========================================
# 폴더 내 모든 엑셀 파일(.xlsx) 리스트업
excel_files = glob.glob(os.path.join(pdf_folder, "*.xlsx"))
total_files = len(excel_files)
print(f"📊 총 {total_files}개의 ETF 엑셀 파일을 찾았습니다. 수집을 시작합니다...\n")

# 중복을 자동으로 제거하며 담기 위해 set(집합) 구조 사용
unique_stocks = set()

# 개별 ETF 엑셀 파일들을 하나씩 순회하며 읽어 들입니나.
for idx, file_path in enumerate(excel_files, 1):
    file_name = os.path.basename(file_path)
    try:
        # 보내주신 이미지 기준으로 6번째 행이 컬럼명(날짜, ETF코드 등)이므로 header=5 지정
        df_pdf = pd.read_excel(file_path, header=5)
        
        if df_pdf.empty:
            continue
            
        # 양 끝 공백 제거 및 문자열 처리
        df_pdf.columns = df_pdf.columns.astype(str).str.strip()
        
        # '구성종목' 열이 존재하는지 확인
        if '구성종목' in df_pdf.columns:
            # 결측치(NaN) 제거 및 문자열 전처리
            stocks_series = df_pdf['구성종목'].dropna().astype(str).str.strip()
            
            # 주식 리스트에 추가 (주식형 팩터 분석이므로 '현금' 성격의 데이터는 필터링)
            for stock in stocks_series:
                if stock and '현금' not in stock and '예금' not in stock:
                    unique_stocks.add(stock)
                    
        # 💡 [기존의 매치마다 출력하던 print문을 제거했습니다]
        
    except Exception as e:
        print(f" ❌ {file_name} 읽기 실패 오류 발생: {e}")

    # ------------------------------------------
    # [추가 변동 사항] ETF 엑셀 파일을 50개 읽을 때마다만 중간 현황 안내문 출력
    # ------------------------------------------
    if idx % 50 == 0 or idx == total_files:
        progress_pct = (idx / total_files) * 100
        print(f" ⏳ [안내] 현재까지 {idx}개의 ETF 파일 분석을 완료했습니다! (진행률: {progress_pct:.1f}%)")
        print(f"    - 현재까지 찾아낸 누적 고유 주식 종목 수: {len(unique_stocks)}개")
        print("-" * 65)

# ==========================================
# 3. 고유 리스트 정렬 및 CSV 저장
# ==========================================
print("\n" + "="*60)
if unique_stocks:
    # 가나다순 정렬 후 데이터프레임 변환
    sorted_stock_list = sorted(list(unique_stocks))
    df_result = pd.DataFrame(sorted_stock_list, columns=['Stock_Name'])
    
    # 출력 디렉토리가 없을 경우 자동 생성
    os.makedirs(output_dir, exist_ok=True)
    
    # 한글 깨짐 방지를 위해 utf-8-sig 인코딩으로 저장
    df_result.to_csv(output_file_path, index=False, encoding='utf-8-sig')
    
    print(f"🎉 추출 성공! 중복이 제거된 {len(df_result)}개의 고유 주식 종목 리스트가 저장되었습니다.")
    print(f"👉 파일 위치: {output_file_path}")
else:
    print("⚠️ 엑셀 파일에서 '구성종목' 데이터를 추출하지 못했습니다. 파일 내부 컬럼명을 확인해 주세요.")
print("="*60)