import pandas as pd
from pathlib import Path

# =========================================================================
# [필독] 필터링 키워드 관리 구역
# =========================================================================

# 1-A. 일반적인 자산 유형/특성 제외 키워드 (소문자 기준, 공백 없이 작성)
EXCLUDE_KEYWORDS = [
    '인버스', '레버리지', '액티브', '고배당', '배당', '커버드콜', '리츠', 'reits', '채권', 
    '혼합', '선물', '대만', '합성', '장기채'
]

# 1-B. [추가] 이름엔 특징이 없으나 해외 종목이 섞여 있어 '수동 탈락'시킬 ETF 목록
# 💡 띄어쓰기나 대소문자를 신경 쓰지 않고 실제 이름과 유사하게 편하게 적으시면 됩니다.
# 💡 앞으로 빼고 싶은 ETF가 더 발견되면 이 리스트에 콤마(,)로 구분해서 계속 추가하세요!
SPECIFIC_ETF_KEYWORDS = [
    'PLUS 한화그룹주',       # 👈 요청하신 한화그룹주 ETF 실제 반영
    'ACE 200TR',         # (예시) 이런 식으로 계속 추가 가능
    'SOL 200TR',
    'KODEX 최소변동성',
    '마이티 코스피100',
    'KODEX 모멘텀주',
    'ACE 코스피'
]


def run_filter(df, output_dir: Path):
    """
    [Step 1-1] '국내주식형'만 선별 및 Data_result/Classification 폴더에 CSV 저장
    [Step 1-1.5] 8자리 숫자(YYYYMMDD) 비교를 통한 2026년 이후 상장 종목 차단
    [Step 1-2] 제외 키워드 및 수동 지정 종목 탈락 처리 후 최종 CSV 저장
    """
    df_working = df.copy()
    
    # 엑셀 헤더 이름 양끝 공백 제거
    df_working.columns = df_working.columns.str.strip()
    
    # 변수명 매핑
    col_c = "코드명"
    col_e = "유형분류(대)"
    col_date = "상장일"
    
    # -------------------------------------------------------------
    # 1. 국내주식형 필터링
    # -------------------------------------------------------------
    df_step1 = df_working[df_working[col_e].astype(str).str.strip() == "국내주식형"].copy()
    print(f"   [filter.py] 1단계 완료: '국내주식형' 선별 ({len(df_step1)}개)")
    
    # -------------------------------------------------------------
    # [정밀 반영] 20260101 이후 상장 종목 제거
    # -------------------------------------------------------------
    df_step1[col_date] = pd.to_numeric(df_step1[col_date], errors='coerce')
    df_before_2026 = df_step1[df_step1[col_date] < 20260101].copy()
    
    dropped_future_count = len(df_step1) - len(df_before_2026)
    print(f"   [filter.py] 상장일 필터 완료: 2026년 이후 상장 종목 {dropped_future_count}개 탈락 완료")
    
    df_before_2026[col_date] = df_before_2026[col_date].astype(int)
    
    # 1단계 파일 저장
    df_before_2026.to_csv(output_dir / "etf_step1_korean_equity.csv", index=False, encoding="utf-8-sig")
    
    # -------------------------------------------------------------
    # 2. 제외 키워드 및 특정 지정 단어 필터링 (최종 진화형 로직)
    # -------------------------------------------------------------
    
    # 마스터 마스킹 리스트 결합 및 전처리 (공백 제거 + 소문자화 일괄 적용)
    # 두 리스트를 하나로 합쳐서 컴퓨터가 읽기 좋은 형태로 변환합니다.
    ALL_DROP_KEYWORDS = [kw.replace(" ", "").lower() for kw in (EXCLUDE_KEYWORDS + SPECIFIC_ETF_KEYWORDS)]
    
    def has_exclude_keyword(name):
        # 대상 ETF 코드명의 모든 공백을 제거하고 소문자로 통일 (예: "PLUS  한화그룹주 " -> "plus한화그룹주")
        clean_name = str(name).replace(" ", "").lower()
        
        # 합쳐진 마스터 탈락 리스트를 순회하며 하나라도 포함되어 있는지 검사
        for clean_kw in ALL_DROP_KEYWORDS:
            if clean_kw in clean_name:
                return True
        return False
        
    # 필터 적용 (has_exclude_keyword가 False인 정상 국내 종목만 남김)
    df_cleaned = df_before_2026[~df_before_2026[col_c].apply(has_exclude_keyword)].copy()
    
    # 최종 결과 저장
    df_cleaned.to_csv(output_dir / "etf_step2_filtered.csv", index=False, encoding="utf-8-sig")
    print(f"   [filter.py] 2단계 완료: 총 {len(df_before_2026) - len(df_cleaned)}개 종목 필터링 탈락 완료")
    print(f"   📊 [최종 생존 샘플 수]: {len(df_cleaned)}개 ETF가 연구 데이터셋으로 확정되었습니다.")
    print(f"   👉 결과 파일이 'Data_result/Classification' 폴더에 저장되었습니다.")
    
    return df_cleaned