import pandas as pd
from pathlib import Path

# ==========================================
# 1. 상대경로 설정
# ==========================================
current_dir = Path(__file__).parent
project_dir = current_dir.parent

data_path = (
    project_dir
    / "Data"
    / "Raw_Data"
    / "ETF_Data.xlsx"
)

output_folder = (
    project_dir
    / "Data_result"
    / "Panel_change_Data"
)

output_folder.mkdir(
    parents=True,
    exist_ok=True
)

# ==========================================
# 2. 원자료 로드
# ==========================================
raw = pd.read_excel(
    data_path,
    header=None
)

row_code = 8
row_name = 9
row_type = 10
row_itemcode = 11
row_itemname = 12
row_freq = 13
row_data_start = 14
date_col = 0

print("=" * 60)
print("ETF 데이터 정제를 시작합니다")
print("=" * 60)
print("읽는 파일:", data_path)
print("원자료 크기:", raw.shape)

# ==========================================
# 3. wide → long 변환
# ==========================================
records = []

total_cols = raw.shape[1] - 1
processed_cols = 0
skipped_cols = 0
progress_step = 50

print("\nWide → Long 변환 시작")

for j in range(1, raw.shape[1]):

    etf_code = raw.iloc[row_code, j]
    etf_name = raw.iloc[row_name, j]
    etf_type = raw.iloc[row_type, j]
    item_code = raw.iloc[row_itemcode, j]
    item_name = raw.iloc[row_itemname, j]
    freq = raw.iloc[row_freq, j]

    processed_cols += 1

    if pd.isna(etf_code) or pd.isna(item_name):
        skipped_cols += 1
        continue

    temp = pd.DataFrame({
        "날짜": pd.to_datetime(
            raw.iloc[row_data_start:, date_col],
            errors="coerce"
        ),
        "ETF코드": str(etf_code).strip().zfill(6),  # [수정됨] 코드 -> ETF코드
        "ETF명": etf_name,                          # [수정됨] 코드명 -> ETF명
        "유형": etf_type,
        "아이템코드": item_code,
        "아이템명": item_name,
        "집계주기": freq,
        "값": pd.to_numeric(
            raw.iloc[row_data_start:, j],
            errors="coerce"
        ),
    })

    # [수정됨] Date -> 날짜
    temp = temp.dropna(subset=["날짜"])
    records.append(temp)

    if (
        processed_cols % progress_step == 0
        or processed_cols == total_cols
    ):
        progress_pct = processed_cols / total_cols * 100

        print(
            f"진행률: {processed_cols}/{total_cols} "
            f"({progress_pct:.1f}%) | "
            f"유효열: {len(records)} | "
            f"스킵열: {skipped_cols}"
        )

print("Long 변환 완료")

if len(records) == 0:
    raise ValueError("변환 가능한 데이터 열이 없습니다. 행 번호 설정을 확인하세요.")

df_long = pd.concat(
    records,
    ignore_index=True
)

df_long = df_long.dropna(
    subset=["값"],
    how="all"
)

print("Long 데이터 크기:", df_long.shape)

# ==========================================
# 4. long → panel 변환
# ==========================================
print("\nPanel 변환 시작")

df_panel = df_long.pivot_table(
    index=[
        "날짜", 
        "ETF코드",  # [수정됨] 코드 -> ETF코드
        "ETF명",    # [수정됨] 코드명 -> ETF명
        "유형"
    ],
    columns="아이템명",
    values="값",
    aggfunc="first"
).reset_index()

df_panel.columns.name = None

print("Panel 데이터 크기:", df_panel.shape)

# ==========================================
# 5. Panel CSV만 저장
# ==========================================
panel_path_csv = output_folder / "ETF_Data_panel.csv"

print("\nPanel CSV 파일 저장 중")

df_panel.to_csv(
    panel_path_csv,
    index=False,
    encoding="utf-8-sig"
)

print("=" * 60)
print("정제 완료")
print("=" * 60)
print("저장된 파일:")
print(panel_path_csv)