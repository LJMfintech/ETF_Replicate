import pandas as pd
import numpy as np
import os

def main():
    # 1. 파일 경로 설정 (기존 구조 유지)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(current_dir, 'ETF_Data_panel.csv')
    output_path = os.path.join(current_dir, 'ETF_Data_panel_monthly.csv')

    print(f"입력 파일을 찾는 위치: {input_path}")
    
    if not os.path.exists(input_path):
        print(f"❌ 에러: {input_path} 파일을 찾을 수 없습니다.")
        return

    print("데이터를 불러오는 중입니다...")
    df = pd.read_csv(input_path)

    # 컬럼명 전후 공백 제거 및 코드 6자리 패딩
    df.columns = df.columns.str.strip()
    df['코드'] = df['코드'].astype(str).str.strip().str.zfill(6)

    # 2. 날짜 데이터 타입 변환 및 정렬
    df['날짜'] = pd.to_datetime(df['날짜'])
    df = df.sort_values(by=['코드', '날짜'])

    # 3. 변경된 변수 스펙에 맞춘 결측치(Missing Values) 사전 처리
    # 저량 변수들 (직전 영업일의 값으로 채움)
    df['AUM(원)'] = df.groupby('코드')['AUM(원)'].ffill()
    df['TER 보수'] = df.groupby('코드')['TER 보수'].ffill()
    df['구성종목수'] = df.groupby('코드')['구성종목수'].ffill()
    df['상장주식수(주)'] = df.groupby('코드')['상장주식수(주)'].ffill()
    df['수정주가(원)'] = df.groupby('코드')['수정주가(원)'].ffill()
    
    # 유량 변수 처리
    df['거래량(주)'] = df['거래량(주)'].fillna(0)

    print("새로운 변수 스펙으로 월별 데이터 집계 중...")
    
    # 4. 월별 데이터로 집계 (pd.Grouper freq='ME' 적용)
    # 수정주가 및 모든 저량 변수는 월말 최종값('last'), 거래량만 'sum' 적용
    df_monthly = df.groupby(['코드', pd.Grouper(key='날짜', freq='ME')]).agg(
        코드명=('코드명', 'first'),
        유형=('유형', 'first'),
        AUM_원=('AUM(원)', 'last'),
        TER_보수=('TER 보수', 'last'),
        구성종목수_개=('구성종목수', 'last'),
        상장주식수_주=('상장주식수(주)', 'last'),
        수정주가_원=('수정주가(원)', 'last'),
        거래량_주=('거래량(주)', 'sum')
    ).reset_index()

    # 5. 원래 컬럼명으로 복구
    df_monthly.rename(columns={
        'AUM_원': 'AUM(원)',
        'TER_보수': 'TER 보수',
        '구성종목수_개': '구성종목수',
        '상장주식수_주': '상장주식수(주)',
        '수정주가_원': '수정주가(원)',
        '거래량_주': '거래량(주)'
    }, inplace=True)

    # 6. 타 자산 데이터(Factor, RF)와의 병합 안정성을 위한 '연월(Period)' 컬럼 탑재
    df_monthly['연월'] = df_monthly['날짜'].dt.to_period('M')

    # 7. 원하는 컬럼 순서 지정하여 배치
    df_monthly = df_monthly[[
        '연월', '날짜', '코드', '코드명', '유형', 
        '구성종목수', 'AUM(원)', 'TER 보수', '상장주식수(주)', 
        '거래량(주)', '수정주가(원)'
    ]]

    # 8. 결과 저장
    df_monthly.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"✅ 변환 완료! 월별 패널 데이터가 저장되었습니다:\n{output_path}")

if __name__ == "__main__":
    main()