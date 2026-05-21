import os
import glob
import pandas as pd

# ==========================================
# 1. 경로 설정 (스크립트 위치 기준 자동 상대경로 계산)
# ==========================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR) 

# 입력 파일 경로
master_path = os.path.join(PROJECT_ROOT, 'Data_result', 'Classification', 'ETF_List_Final.xlsx')
time_series_dir = os.path.join(PROJECT_ROOT, 'Data', 'Raw_Data')
time_series_paths = sorted(glob.glob(os.path.join(time_series_dir, "[0-9]*.xlsx")))

# 출력 파일 경로 (Data_result 폴더 내에 저장)
output_dir = os.path.join(PROJECT_ROOT, 'Data_result')
output_path = os.path.join(output_dir, 'ETF_Time_Series_Merged.xlsx')

print("=" * 60)
print(f"마스터 파일 경로: {master_path}")
print(f"시계열 데이터 폴더: {time_series_dir}")
print(f"저장될 결과 파일 경로: {output_path}")
print("=" * 60)

# ==========================================
# 2. 마스터 파일에서 유효 코드 및 분류 정보 로드
# ==========================================
print("최종 ETF 마스터 파일 로드 중...")
df_master = pd.read_excel(master_path)
df_master.columns = df_master.columns.str.strip()

df_master['코드'] = df_master['코드'].astype(str).str.strip()
df_master['Category'] = df_master['Category'].astype(str).str.strip()

# 매칭을 위한 딕셔너리 및 유효 셋 생성
category_map = dict(zip(df_master['코드'], df_master['Category']))
valid_codes = set(category_map.keys())

# ==========================================
# 3. 4개 시계열 데이터 파일 로드, 필터링 및 병합
# ==========================================
merged_df = None

for path in time_series_paths:
    file_name = os.path.basename(path)
    print(f"시계열 파일 읽는 중 및 필터링 중: {file_name}")
    
    # FnGuide 구조 반영 (9번째 행이 헤더)
    df_ts = pd.read_excel(path, header=8)
    df_ts['코드'] = df_ts['코드'].astype(str).str.strip()
    
    # 마스터 파일에 존재하는 코드만 필터링
    df_filtered = df_ts[df_ts['코드'].isin(valid_codes)].copy()
    
    # 9행 이전의 메타 정보 컬럼들을 고정하고 날짜 컬럼만 추출하기 위함
    fixed_cols = ['코드', '코드명', '유형', '아이템코드', '아이템명', '집계주기']
    date_cols = [col for col in df_filtered.columns if col not in fixed_cols]
    
    # 해당 파일에서 고정 컬럼과 날짜 데이터만 깔끔하게 정돈
    df_filtered = df_filtered[fixed_cols + date_cols]
    
    if merged_df is None:
        # 첫 번째 파일은 기준 데이터프레임으로 설정
        merged_df = df_filtered
    else:
        # 두 번째 파일부터는 '고정 컬럼'들을 기준으로 가로(날짜) 방향으로 결합(Join/Merge)
        # 모든 파일에 종목과 아이템 행 구조가 동일하게 누적되므로 outer merge를 수행합니다.
        merged_df = pd.merge(merged_df, df_filtered, on=fixed_cols, how='outer')

print(f"시계열 날짜 병합 완료. 총 행수: {len(merged_df)}행")

# ==========================================
# 4. 분류 정보(Category) 컬럼 추가 및 저장
# ==========================================
print("마스터 파일의 Category 정보 매칭 중...")
# 고정 컬럼 바로 뒤나 맨 뒤에 Category 분별 컬럼 추가
merged_df['Category'] = merged_df['코드'].map(category_map)

# 분석하기 좋게 컬럼 순서 조정 (Category를 앞으로 이동)
cols = list(merged_df.columns)
# '집계주기' 바로 뒤(index=6)에 'Category' 컬럼 배치
cols.insert(6, cols.pop(cols.index('Category')))
merged_df = merged_df[cols]

# 엑셀 파일로 내보내기 (인덱스 제외)
print(f"최종 엑셀 파일 생성 중: {os.path.basename(output_path)}")
merged_df.to_excel(output_path, index=False)

print("=" * 60)
print(f"성공적으로 완료되었습니다!")
print(f"저장 위치: {output_path}")
print("=" * 60)