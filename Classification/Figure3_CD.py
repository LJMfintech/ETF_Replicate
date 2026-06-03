import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def extract_year_from_yyyymmdd(series):
    """
    20021014 같은 YYYYMMDD 형태의 정수나 문자열에서
    앞 4자리(연도)만 안전하게 잘라내어 반환하는 전용 함수
    """
    years = []
    for val in series:
        if pd.isna(val) or str(val).strip() == '' or str(val).lower() == 'nan':
            years.append(np.nan)
            continue
            
        s = str(val).strip().split('.')[0]
        s = s.replace('-', '').replace('/', '').replace('.', '')
        
        try:
            if s.isdigit() and len(s) >= 4:
                year_val = int(s[:4])
                if 1990 <= year_val <= 2030:
                    years.append(year_val)
                else:
                    years.append(np.nan)
            else:
                years.append(np.nan)
        except:
            years.append(np.nan)
            
    return years

def main():
    print("\n" + "="*60)
    print("🚀 [Figure3_CD.py] YYYYMMDD 포맷 해독 및 연도별 상세 스펙 출력")
    print("="*60)
    
    # 1. 경로 설정
    CURRENT_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = CURRENT_DIR.parent
    RESULT_DIR = PROJECT_ROOT / "Data_result" / "Classification"
    class_file = RESULT_DIR / "etf_step3_classified.csv"
    output_image = RESULT_DIR / "figure3_CD_launches_closures.png"
    
    if not class_file.exists():
        print(f"🚨 [에러] 분류 결과 파일이 존재하지 않습니다: {class_file}")
        return

    # 2. 데이터 로드
    df = pd.read_csv(class_file)
    df.columns = [col.strip() for col in df.columns]
    
    # 3. 컬럼 매핑
    launch_col = '상장일' if '상장일' in df.columns else df.columns[7]
    closure_col = '상장폐지일' if '상장폐지일' in df.columns else df.columns[8]
    cat_col = 'Category'

    # 연도 데이터 변환 추출
    df['Launch_Year'] = extract_year_from_yyyymmdd(df[launch_col])
    df['Closure_Year'] = extract_year_from_yyyymmdd(df[closure_col])
    
    print(f"✅ 총 마스터 데이터 파싱 완료 (상장 기록: {df['Launch_Year'].notna().sum()}개 / 폐지 기록: {df['Closure_Year'].notna().sum()}개)")
    print("\n" + "-"*50)
    print("📊 [연도별 ETF 상장(Launches) 및 폐지(Closures) 상세 현황]")
    print("-"*50)
    print(f"{'연도':<6} | {'Broad 상장':<10} {'Spec 상장':<10} | {'Broad 폐지':<10} {'Spec 폐지':<10}")
    print("-"*50)

    # 4. 2002년 ~ 2025년 고정 기간 루프 및 터미널 화면 직접 출력
    all_years = sorted(list(range(2002, 2026)))
    categories = ['Broad-based', 'Specialized']
    
    plot_data = []
    for yr in all_years:
        # 연도별 카운트 계산
        b_launch = df[(df['Launch_Year'] == yr) & (df[cat_col] == 'Broad-based')].shape[0]
        s_launch = df[(df['Launch_Year'] == yr) & (df[cat_col] == 'Specialized')].shape[0]
        
        b_closure = df[(df['Closure_Year'] == yr) & (df[cat_col] == 'Broad-based')].shape[0]
        s_closure = df[(df['Closure_Year'] == yr) & (df[cat_col] == 'Specialized')].shape[0]
        
        # 터미널에 한 줄씩 직관적으로 프린트 (표 파일이 아닌 순수 텍스트 결과창 출력)
        print(f"{yr:<6} | {b_launch:<12} {s_launch:<12} | {b_closure:<12} {s_closure:<12}")
        
        # 맷플롯립 시각화용 데이터 백업 적재
        for cat in categories:
            launches = b_launch if cat == 'Broad-based' else s_launch
            closures = b_closure if cat == 'Broad-based' else s_closure
            plot_data.append({
                'Year': yr, 'Category': cat,
                'Launches': launches, 'Closures': closures
            })
            
    print("-"*50)
    
    df_summary = pd.DataFrame(plot_data)
    broad_df = df_summary[df_summary['Category'] == 'Broad-based'].set_index('Year')
    spec_df = df_summary[df_summary['Category'] == 'Specialized'].set_index('Year')

    # 5. 시각화 패널 생성
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['xtick.direction'] = 'in'
    plt.rcParams['ytick.direction'] = 'in'
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2))
    xtick_years = np.arange(2002, 2026, 4)
    
    # Panel C
    ax_c = axes[0]
    ax_c.bar(broad_df.index, broad_df['Launches'], label='Broad-based ETFs', 
             color='white', edgecolor='black', hatch='///', linewidth=1.2)
    ax_c.bar(spec_df.index, spec_df['Launches'], bottom=broad_df['Launches'], label='Specialized ETFs', 
             color='lightgray', edgecolor='black', linewidth=1.2)
    ax_c.set_title('C          Number of ETF launches', loc='left', fontsize=12, fontweight='bold')
    ax_c.set_ylabel('Number of ETFs', fontsize=11)
    
    # Panel D
    ax_d = axes[1]
    ax_d.bar(broad_df.index, broad_df['Closures'], label='Broad-based ETFs', 
             color='white', edgecolor='black', hatch='\\\\\\', linewidth=1.2)
    ax_d.bar(spec_df.index, spec_df['Closures'], bottom=broad_df['Closures'], label='Specialized ETFs', 
             color='lightgray', edgecolor='black', linewidth=1.2)
    ax_d.set_title('D          Number of ETF closures', loc='left', fontsize=12, fontweight='bold')
    ax_d.set_ylabel('Number of ETFs', fontsize=11)
    
    for ax in axes:
        ax.set_xticks(xtick_years)
        ax.set_xticklabels([str(y) for y in xtick_years])
        ax.set_xlim(2001, 2026)
        ax.set_xlabel('Year', fontsize=11)
        ax.grid(True, linestyle=':', alpha=0.6)
        ax.legend(loc='upper left', frameon=True, facecolor='white', edgecolor='none', fontsize=10)
        ax.spines['top'].set_visible(True)
        ax.spines['right'].set_visible(True)

    plt.tight_layout()
    plt.savefig(output_image, dpi=300, bbox_inches='tight')
    plt.close()
    
    print("\n" + "="*60)
    print("✨ [최종 통과] 수치 매크로 출력 및 고해상도 이미지 빌드 완료!")
    print(f"📍 이미지 저장 경로: {output_image}")
    print("="*60 + "\n")

if __name__ == '__main__':
    main()