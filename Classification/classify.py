import pandas as pd
from pathlib import Path

# Specialized(테마/섹터 특화형) 판정을 위한 핵심 단어 목록
SPECIALIZED_KEYWORDS = [
    '반도체', '2차전지', '바이오', '헬스케어', '정보기술', ' it', 'it ', ' it ', '300it', '200it', 
    '150it', '테마', '섹터', '자동차', '화학', '철강', '에너지', '게임', '미디어', '엔터', 
    '인프라', 'esg', '친환경', '소부장', '건설', '증권', '금융', '은행', '중공업', '그룹', 
    '조선', '방산', 'ai', '우주', '원자력', '로봇', '전력', '지주회사', '항공', '화장품', 
    '배터리', 'k-pop', 'kpop', '수소', '설비', 'bbig', '메타버스', '여행', '태양광', '중국',
    '테크', '탄소효율', 'e커머스', '뷰티', '우선주', '기자재', '뉴딜', '디지털', '소버린',
    '기후변화', '전기', '웹툰', '드라마', '동학개미', '의료', '내수주', '소비',
    '농업', '혁신', '그린', '창업', 'top10', 'top5', '포커스', '상위', '기계', '수출', '플랫폼',
    '경기방어', '경기주도', '소프트웨어', '보험', '콘텐츠', '푸드', '5g', '서비스', 'banks',
    '방송', '통신', 'green', '생활', '대만', '산업재'

]

def run_classification(df, output_dir: Path):
    """
    [Step 1-3] 논문 기준 Broad-based vs Specialized 그룹 이분 분류 및 Data_result/Classification 폴더 저장
    """
    df_working = df.copy()
    
    col_c = "코드명" if "코드명" in df_working.columns else df_working.columns[2]
    col_f = "유형분류(소)" if "유형분류(소)" in df_working.columns else df_working.columns[5]
    
    def check_category(row):
        combined_text = str(row[col_c]).lower()
        
        if any(kw in combined_text for kw in SPECIALIZED_KEYWORDS):
            return "Specialized"
        return "Broad-based"
        
    df_working["Category"] = df_working.apply(check_category, axis=1)
    
    # 분류 완료 파일 CSV 저장
    df_working.to_csv(output_dir / "etf_step3_classified.csv", index=False, encoding="utf-8-sig")
    print(f"   [classify.py] 3단계 완료: Broad vs Specialized 분류 -> Data_result/Classification 저장 완료")
    
    return df_working