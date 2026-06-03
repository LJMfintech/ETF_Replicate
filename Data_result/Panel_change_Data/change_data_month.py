import pandas as pd
import numpy as np
import os

def main():
    # 1. 스크립트 파일이 있는 현재 폴더 위치를 자동으로 탐색 (가장 안전한 상대경로 방식)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    input_path = os.path.join(current_dir, 'ETF_Data_panel.csv')
    output_path = os.path.join(current_dir, 'ETF_Data_panel_monthly.csv')

    print(f"입력 파일을 찾는 위치: {input_path}")
    
    # 파일 존재 여부 확인
    if not os.path.exists(input_path):
        print(f"❌ 에러: {input_path} 파일을 찾을 수 없습니다.")
        print("ETF_Data_panel.csv 파일과 이 스크립트 파일이 같은 폴더에 있는지 다시 확인해 주세요.")
        return

    print("데이터를 불러오는 중입니다...")
    df = pd.read_csv(input_path)

    # 2. 날짜 데이터 타입 변환 및 정렬
    df['날짜'] = pd.to_datetime(df['날짜'])
    df = df.sort_values(by=['ETF코드', '날짜'])

    # 3. 결측치(Missing Values) 사전 처리
    # AUM과 TER은 저량 변수이므로 직전 값으로 채움 (Forward Fill)
    df['AUM(원)'] = df.groupby('ETF코드')['AUM(원)'].ffill()
    df['TER 보수'] = df.groupby('ETF코드')['TER 보수'].ffill()
    
    # 거래대금, 거래량은 유량 변수이므로 거래가 없었던 날은 0으로 채움
    df['거래대금(원)'] = df['거래대금(원)'].fillna(0)
    df['거래량(주)'] = df['거래량(주)'].fillna(0)
    
    # 일별 수익률이 누락된 경우 0%로 간주
    df['수정주가수익률(%)'] = df['수정주가수익률(%)'].fillna(0)

    # 4. 월별 수익률 복리 계산 함수 정의
    def compound_returns(s):
        return ((1 + s / 100).prod() - 1) * 100

    print("월별 데이터로 집계 중입니다...")
    
    # 5. 월별 데이터로 집계 (Resampling / Groupby)
    df_monthly = df.groupby(['ETF코드', pd.Grouper(key='날짜', freq='ME')]).agg(
        ETF명=('ETF명', 'first'),
        유형=('유형', 'first'),
        AUM_원=('AUM(원)', 'last'),           # 저량: 월말 데이터
        TER_보수=('TER 보수', 'last'),        # 저량: 월말 데이터
        거래대금_원=('거래대금(원)', 'sum'),   # 유량: 월간 합산
        거래량_주=('거래량(주)', 'sum'),       # 유량: 월간 합산
        수정주가수익률_퍼센트=('수정주가수익률(%)', compound_returns) # 복리 누적
    ).reset_index()

    # 6. 원래 컬럼명으로 복구
    df_monthly.rename(columns={
        'AUM_원': 'AUM(원)',
        'TER_보수': 'TER 보수',
        '거래대금_원': '거래대금(원)',
        '거래량_주': '거래량(주)',
        '수정주가수익률_퍼센트': '수정주가수익률(%)'
    }, inplace=True)

    # 7. 결과 저장
    df_monthly.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"✅ 변환 완료! 월별 데이터가 다음 경로에 저장되었습니다:\n{output_path}")

if __name__ == "__main__":
    main()