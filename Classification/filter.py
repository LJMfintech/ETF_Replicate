import pandas as pd
from pathlib import Path

# 제외 키워드 목록
EXCLUDE_KEYWORDS = ['인버스', '레버리지', '액티브', '고배당', '배당', '커버드콜', '리츠', 'reits', '채권', '혼합', '선물']

def run_filter(df, output_dir: Path):
    """
    [Step 1-1] '국내주식형'만 선별 및 Data_result/Classification 폴더에 CSV 저장
    [Step 1-1.5] 8자리 숫자(YYYYMMDD) 비교를 통한 2026년 이후 상장 종목 차단 (오류 정정 완료)
    [Step 1-2] 제외 키워드 종목 탈락 처리 및 Data_result/Classification 폴더에 CSV 저장
    """
    df_working = df.copy()
    
    # 엑셀 헤더 이름 양끝 공백 제거
    df_working.columns = df_working.columns.str.strip()
    
    # 이미지에서 확인된 변수명 매핑
    col_c = "코드명"
    col_e = "유형분류(대)"
    col_date = "상장일"
    
    # -------------------------------------------------------------
    # 1. 국내주식형 필터링
    # -------------------------------------------------------------
    df_step1 = df_working[df_working[col_e].astype(str).str.strip() == "국내주식형"].copy()
    print(f"   [filter.py] 1단계 완료: '국내주식형' 선별 ({len(df_step1)}개)")
    
    # -------------------------------------------------------------
    # [정밀 반영] 20260101 이후 상장 종목 제거 (8자리 숫자 포맷 대응)
    # -------------------------------------------------------------
    # 상장일 데이터를 정수/숫자형으로 안전 변환 ('20210720' -> 20210720)
    df_step1[col_date] = pd.to_numeric(df_step1[col_date], errors='coerce')
    
    # 20260101 미만(즉, 2025년 12월 31일 상장 종목까지)만 데이터셋에 남김
    df_before_2026 = df_step1[df_step1[col_date] < 20260101].copy()
    
    # 탈락한 미래 종목 개수 계산 및 로그 출력
    dropped_future_count = len(df_step1) - len(df_before_2026)
    print(f"   [filter.py] 상장일 필터 완료: 2026년 이후 상장 종목 {dropped_future_count}개 탈락 완료")
    
    # 원본 형태인 깔끔한 정수형(Int) 구조로 복원하여 저장
    df_before_2026[col_date] = df_before_2026[col_date].astype(int)
    
    # 1단계 파일 저장 (2026년 이후 미래 종목이 완벽히 제거된 버전)
    df_before_2026.to_csv(output_dir / "etf_step1_korean_equity.csv", index=False, encoding="utf-8-sig")
    
    # -------------------------------------------------------------
    # 2. 제외 키워드 필터링
    # -------------------------------------------------------------
    def has_exclude_keyword(name):
        return any(kw in str(name).lower() for kw in EXCLUDE_KEYWORDS)
        
    df_cleaned = df_before_2026[~df_before_2026[col_c].apply(has_exclude_keyword)].copy()
    df_cleaned.to_csv(output_dir / "etf_step2_filtered.csv", index=False, encoding="utf-8-sig")
    print(f"   [filter.py] 2단계 완료: 제외 키워드 탈락 ({len(df_cleaned)}개) -> Data_result/Classification 저장 완료")
    
    return df_cleaned