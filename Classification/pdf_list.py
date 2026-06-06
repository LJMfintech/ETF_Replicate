import os
import glob
import pandas as pd
import warnings

# 엑셀 로드 시 발생하는 단순 서식 경고 무시
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

# ==========================================
# 1. 경로 설정 (스크립트 파일 위치 기준 상대경로)
# ==========================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

pdf_folder = os.path.join(PROJECT_ROOT, 'Data', 'ETF_PDF')
output_dir = os.path.join(PROJECT_ROOT, 'Data_result')
output_file_path = os.path.join(output_dir, 'Unique_Stock_List.csv')

print("=" * 60)
print(f"📂 탐색할 PDF 폴더 경로: {pdf_folder}")
print(f"💾 저장 예정 CSV 경로: {output_file_path}")
print("=" * 60)

# ==========================================
# 2. 엑셀 파일 탐색 및 종목명 + 최초 소스 코드 수집
# ==========================================
excel_files = glob.glob(os.path.join(pdf_folder, "*.xlsx"))
total_files = len(excel_files)
print(f"📊 총 {total_files}개의 ETF 엑셀 파일을 찾았습니다. 수집을 시작합니다...\n")

# 🛠️ [구조 변경] 중복 체크 및 최초 발견 ETF 코드를 기록하기 위한 딕셔너리
# 딕셔너리 구조 예시: { '삼성전자': '005930', 'KODEX 국고채3년 선물': '1039J0' }
stock_source_dict = {}

for idx, file_path in enumerate(excel_files, 1):
    file_name = os.path.basename(file_path)
    
    # 파일명에서 ETF 단축코드 추출 시도
    # 예: "KODEX_삼성그룹_005930.xlsx" 또는 "1039J0_국채선물.xlsx" 등 파일명에 포함된 코드 매칭용
    # 만약 파일명 규칙이 다르면 대문자화된 순수 파일명 핵심 키워드를 코드로 사용합니다.
    etf_code_src = file_name.split('.')[0].upper() 
    
    try:
        df_pdf = pd.read_excel(file_path, header=5)
        
        if df_pdf.empty:
            continue
            
        df_pdf.columns = df_pdf.columns.astype(str).str.strip()
        
        if '구성종목' in df_pdf.columns:
            stocks_series = df_pdf['구성종목'].dropna().astype(str).str.strip()
            
            for stock in stocks_series:
                # 공백 데이터 제외 및 기본적인 현금성 노이즈 1차 필터링
                if stock and '현금' not in stock and '예금' not in stock:
                    
                    # 🛠️ [핵심 조건] 이미 등록된 종목이라면 굳이 추가하거나 업데이트하지 않음 (최초 1회만 기록)
                    if stock not in stock_source_dict:
                        stock_source_dict[stock] = etf_code_src
                        
    except Exception as e:
        print(f" ❌ {file_name} 읽기 실패 오류 발생: {e}")

    # 50개 읽을 때마다 중간 현황 안내문 출력
    if idx % 50 == 0 or idx == total_files:
        progress_pct = (idx / total_files) * 100
        print(f" ⏳ [안내] 현재까지 {idx}개의 ETF 파일 분석을 완료했습니다! (진행률: {progress_pct:.1f}%)")
        print(f"    - 현재까지 찾아낸 누적 고유 종목 수: {len(stock_source_dict)}개")
        print("-" * 65)

# ==========================================
# 3. 고유 리스트 정렬 및 CSV 저장
# ==========================================
print("\n" + "="*60)
if stock_source_dict:
    # 종목명 가나다순으로 정렬하여 리스트 컴프리헨션으로 변환
    sorted_stocks = sorted(stock_source_dict.keys())
    
    # 정렬된 종목명에 매칭되는 최초 발견 ETF 코드를 맵핑하여 데이터프레임 생성
    result_data = {
        'Stock_Name': sorted_stocks,
        'First_Source_ETF': [stock_source_dict[s] for s in sorted_stocks]
    }
    df_result = pd.DataFrame(result_data)
    
    # 출력 디렉토리가 없을 경우 자동 생성
    os.makedirs(output_dir, exist_ok=True)
    
    # 한글 및 소스 코드 데이터 보존을 위해 utf-8-sig 인코딩 저장
    df_result.to_csv(output_file_path, index=False, encoding='utf-8-sig')
    
    print(f"🎉 추출 성공! 중복이 제거된 {len(df_result)}개의 고유 종목 리스트가 저장되었습니다.")
    print(f"👉 파일 위치: {output_file_path}")
else:
    print("⚠️ 엑셀 파일에서 '구성종목' 데이터를 추출하지 못했습니다. 파일 내부 컬럼명을 확인해 주세요.")
print("="*60)