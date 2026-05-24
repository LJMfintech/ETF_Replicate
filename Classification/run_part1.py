import os
import sys
from pathlib import Path
import pandas as pd

# 실행 경로 이슈 방지를 위해 현재 폴더를 기준으로 프로젝트 루트 자동 추적 설정
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent

# 같은 디렉터리에 위치한 필터 및 분류 모듈 로드
from filter import run_filter
from classify import run_classification

def main():
    print("\n" + "="*50)
    print("  [ORCHESTRATOR] run_part1.py 가동 (Data_result/Classification 격리 저장)")
    print("="*50)
    
    # 인풋 소스 경로 지정 (상대경로 역산)
    raw_data_dir = PROJECT_ROOT / "Data" / "Raw_Data"
    
    # [핵심 변경] 모든 산출물이 저장될 하위 타깃 폴더 경로 설정
    target_result_dir = PROJECT_ROOT / "Data_result" / "Classification"
    
    # [방어 코드] 만약 Data_result/Classification 폴더 트리 구조가 없으면 파이썬이 스스로 자동 생성합니다.
    if not target_result_dir.exists():
        target_result_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 [안내] 결과 저장 전용 공간을 신규 생성했습니다: Data_result/Classification")
    
    input_path = raw_data_dir / "ETF_List.xlsx"
    output_xlsx_path = target_result_dir / "ETF_List_Final.xlsx"
    
    if not input_path.exists():
        print(f"🚨 [에러] 원본 엑셀 파일이 존재하지 않습니다.\n확인 필요 경로: {input_path}")
        return

    # 1. 원본 데이터 로드
    raw_df = pd.read_excel(input_path, engine='openpyxl')
    print(f"📁 원본 엑셀 로드 성공 (총 {len(raw_df)}개 행)")
    
    # 2. filter.py 가동
    print("\n[공정 1] filter.py 실행 - 주식형 선별 및 파생/배당 상품 탈락 공정...")
    cleaned_df = run_filter(raw_df, output_dir=target_result_dir)
    
    # 3. classify.py 가동
    print("\n[공정 2] classify.py 실행 - 논문 기준 테마/섹터(Specialized) 분류 공정...")
    final_df = run_classification(cleaned_df, output_dir=target_result_dir)
    
    # 4. 최종 통합본 마스터 엑셀 파일 저장
    final_df.to_excel(output_xlsx_path, index=False)
    
    print("\n" + "-"*50)
    print("📊 [Part 1 최종 분류 통계 요약]")
    print("-"*50)
    print(final_df["Category"].value_counts())
    print(f"\n✨ 모든 작업 완료! 산출물들은 아래 지정 폴더에서 확인하세요.\n📍 결과 보관소: {target_result_dir}\n")

if __name__ == "__main__":
    main()