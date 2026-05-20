import pandas as pd
from pathlib import Path

# 제외 키워드 목록
EXCLUDE_KEYWORDS = ['인버스', '레버리지', '액티브', '고배당', '배당', '커버드콜', '리츠', 'reits', '채권', '혼합', '선물']

def run_filter(df, output_dir: Path):
    """
    [Step 1-1] '국내주식형'만 선별 및 Data_result/Classification 폴더에 CSV 저장
    [Step 1-2] 제외 키워드 종목 탈락 처리 및 Data_result/Classification 폴더에 CSV 저장
    """
    df_working = df.copy()
    
    # 엑셀 헤더 이름 매핑
    col_c = "코드명" if "코드명" in df_working.columns else df_working.columns[2]
    col_e = "유형분류(대)" if "유형분류(대)" in df_working.columns else df_working.columns[4]
    
    # 1. 국내주식형 필터링 및 지정 폴더 저장
    df_step1 = df_working[df_working[col_e].astype(str).str.strip() == "국내주식형"].copy()
    df_step1.to_csv(output_dir / "etf_step1_korean_equity.csv", index=False, encoding="utf-8-sig")
    print(f"   [filter.py] 1단계 완료: '국내주식형' 선별 ({len(df_step1)}개) -> Data_result/Classification 저장 완료")
    
    # 2. 제외 키워드 필터링 및 지정 폴더 저장
    def has_exclude_keyword(name):
        return any(kw in str(name).lower() for kw in EXCLUDE_KEYWORDS)
        
    df_cleaned = df_step1[~df_step1[col_c].apply(has_exclude_keyword)].copy()
    df_cleaned.to_csv(output_dir / "etf_step2_filtered.csv", index=False, encoding="utf-8-sig")
    print(f"   [filter.py] 2단계 완료: 제외 키워드 탈락 ({len(df_cleaned)}개) -> Data_result/Classification 저장 완료")
    
    return df_cleaned