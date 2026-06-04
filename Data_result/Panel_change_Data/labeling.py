import pandas as pd
from pathlib import Path

# ==========================================
# 1. 상대경로 설정 (최상위 프로젝트 폴더 자동 추적)
# ==========================================
current_file = Path(__file__).resolve()

project_dir = None
for parent in current_file.parents:
    if parent.name == "ETF_Replicate":
        project_dir = parent
        break

if project_dir is None:
    project_dir = current_file.parent.parent

# 이미지에 나타난 대소문자 폴더 구조 맞춤
category_file_path = project_dir / "Data_result" / "Classification" / "ETF_List_Final.xlsx"
panel_file_path = project_dir / "Data_result" / "Panel_change_Data" / "ETF_Data_panel.csv"
output_file_path = project_dir / "Data_result" / "Panel_change_Data" / "ETF_Data_panel_labeled.csv"

print("=" * 60)
print("ETF 카테고리(Labeling) 최종 정밀 병합을 시작합니다.")
print("=" * 60)

# ==========================================
# 2. 데이터 로드 (header=0 설정으로 2번째 행부터 데이터 시작)
# ==========================================
df_panel = pd.read_csv(panel_file_path, encoding="utf-8-sig")
df_meta = pd.read_excel(category_file_path, header=0)

# ==========================================
# 3. 데이터 정제 및 코드 뒤 숨은 공백 완전 박멸
# ==========================================
# 스크린샷에 확인된 정확한 컬럼명 지정 ('코드', 'Category')
df_map = df_meta[["코드", "Category"]].copy()

# [핵심 보정] 문자열 변환 후, 눈에 안 보이는 뒤쪽 공백(\s)과 줄바꿈을 완벽히 지웁니다.
df_panel["코드"] = df_panel["코드"].astype(str).str.replace(r'\s+', '', regex=True).str.strip().str.upper()
df_map["코드"] = df_map["코드"].astype(str).str.replace(r'\s+', '', regex=True).str.strip().str.upper()

# 엑셀 매핑 테이블 내 중복 코드 제거
df_map = df_map.drop_duplicates(subset=["코드"])

# ==========================================
# 4. 데이터 정밀 병합 (Left Join)
# ==========================================
print("\n[진행] '코드'를 기준으로 두 파일을 결합하는 중...")
df_final = pd.merge(df_panel, df_map, on="코드", how="left")

match_count = df_final['Category'].notna().sum()
print(f"   - 패널 데이터 전체 행 수: {len(df_final)}개")
print(f"   - 카테고리 매칭 성공 행 수: {match_count}개")

# ==========================================
# 5. 결과 저장
# ==========================================
print("\n[완료] 최종 결과를 안전하게 저장합니다...")
df_final.to_csv(
    output_file_path,
    index=False,
    encoding="utf-8-sig"
)

print("=" * 60)
print("병합 완료! 저장된 파일 위치:")
print(output_file_path)
print("=" * 60)