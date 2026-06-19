import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ==========================================
# 1. 경로 설정 및 데이터 로드
# ==========================================
csv_path = r"C:\Users\USER\Desktop\ETF_Replicate\Data_result\Panel_change_Data\ETF_Data_panel_labeled.csv"
output_dir = r"C:\Users\USER\Desktop\ETF_Replicate\Data_result\Classification"

print("=" * 60)
print(f"입력 데이터 파일 경로: {csv_path}")
print(f"그래프 저장 예정 폴더: {output_dir}")
print("=" * 60)

if not os.path.exists(csv_path):
    raise FileNotFoundError(f"지정된 경로에서 데이터를 찾을 수 없습니다: {csv_path}")

print("라벨링된 ETF 데이터 로드 중...")
df_pivot = pd.read_csv(csv_path)

# ==========================================
# 2. 데이터 전처리 및 유효 라벨 선별 (필터링)
# ==========================================
print("데이터 전처리 및 broad-based / specialized 라벨 선별 중...")

# [수정] '날짜' 컬럼을 판다스 datetime으로 변환
df_pivot['날짜'] = pd.to_datetime(df_pivot['날짜'])
df_pivot['Year'] = df_pivot['날짜'].dt.year

# 카테고리 텍스트 정제 (공백 제거 및 소문자 통일)
df_pivot['Category'] = df_pivot['Category'].astype(str).str.strip().str.lower()

# 'broad-based'와 'specialized' 라벨만 선별
valid_categories = ['broad-based', 'specialized']
df_pivot = df_pivot[df_pivot['Category'].isin(valid_categories)].copy()

# 시각화 표기용 대문자 변환 ('broad-based' -> 'Broad-based')
df_pivot['Category'] = df_pivot['Category'].str.capitalize()

# 이미지 구조 기반 컬럼명 표준화 및 숫자 형변환
df_pivot = df_pivot.rename(columns={'AUM(원)': 'AUM', 'TER 보수': 'TER'})
df_pivot['AUM'] = pd.to_numeric(df_pivot['AUM'], errors='coerce')
df_pivot['TER'] = pd.to_numeric(df_pivot['TER'], errors='coerce')

# 분석에 필수적인 AUM 결측치 제거
df_pivot = df_pivot.dropna(subset=['AUM'])

# ==========================================
# 3. 패널별 지표 집계 (Panel A & B)
# ==========================================
print("패널별 통계량 집계 및 스케일 조정 중...")

# [Panel A] 연도별 각 종목의 최신 관측일(기말) AUM 합산 -> 조(Trillion) 원 단위
# [수정] 'Date' 대신 '날짜' 컬럼 기준으로 정렬 및 그룹화
df_panel_a = df_pivot.sort_values('날짜').groupby(['코드', 'Category', 'Year']).last().reset_index()
panel_a_final = df_panel_a.groupby(['Year', 'Category'])['AUM'].sum().unstack() / 1e12

# [Panel B] 연평균 AUM 및 연평균 TER 기반 수수료 매출 산출 -> 십억(Billion) 원 단위
df_panel_b_base = df_pivot.groupby(['코드', 'Category', 'Year']).agg({
    'AUM': 'mean',
    'TER': 'mean'
}).reset_index()

# Fee_Rev = 연평균 AUM * (연평균 TER / 100)
df_panel_b_base['Fee_Rev'] = df_panel_b_base['AUM'] * (df_panel_b_base['TER'] / 100)
panel_b_final = df_panel_b_base.groupby(['Year', 'Category'])['Fee_Rev'].sum().unstack() / 1e9

# 데이터 연속성 확보 (2002년부터 2025년까지 빈 연도 빈칸 메우기)
all_years = pd.Index(range(2002, 2026), name='Year')
panel_a_final = panel_a_final.reindex(all_years).fillna(0)
panel_b_final = panel_b_final.reindex(all_years).fillna(0)

# ==========================================
# 4. 연도별 집계 결과값 화면에 출력
# ==========================================
print("\n" + "="*65)
print(" [Panel A] 연도별 총 운용자산 (AUM, 단위: 조 원)")
print("="*65)
print(panel_a_final.round(2).to_string())

print("\n" + "="*65)
print(" [Panel B] 연도별 추정 수수료 매출 (Fee Revenues, 단위: 십억 원)")
print("="*65)
print(panel_b_final.round(2).to_string())
print("="*65 + "\n")


# ==========================================
# 5. Panel B 결과 이상치 및 원인 검증
# ==========================================
print("\n" + "="*80)
print(" [검증 단계 시작] Panel B 추정 수수료 매출 데이터 집중 분석")
print("="*80)

# 검증 1단계: 2020년 이후 Specialized 수수료 폭발 주범(상위 종목) 찾기
check_df = df_panel_b_base[df_panel_b_base['Year'] >= 2020]
top_revenue_etfs = check_df.sort_values(by='Fee_Rev', ascending=False).head(15)

print("\n✔ [1단계] 2020년 이후 추정 수수료 매출(Fee_Rev) 기여도 상위 15개 종목")
print("-" * 80)
print(top_revenue_etfs[['Year', '코드', 'Category', 'AUM', 'TER', 'Fee_Rev']].to_string(index=False))
print("-" * 80)

# 검증 2단계: 연도별/카테고리별 자산가중평균 보수율(Weighted TER) 추이 확인
df_pivot['AUM_x_TER'] = df_pivot['AUM'] * df_pivot['TER']
weighted_ter_df = df_pivot.groupby(['Year', 'Category']).agg({
    'AUM_x_TER': 'sum',
    'AUM': 'sum'
}).reset_index()
weighted_ter_df['Weighted_TER(%)'] = weighted_ter_df['AUM_x_TER'] / weighted_ter_df['AUM']
final_weighted_ter = weighted_ter_df.pivot_table(index='Year', columns='Category', values='Weighted_TER(%)')

print("\n✔ [2단계] 연도별 각 카테고리의 '자산 가중평균 보수율(Weighted TER, %)'")
print("-" * 80)
print(final_weighted_ter.round(4).to_string())
print("-" * 80)

# 검증 3단계: 집계 방식 왜곡 가능성 차단 (매 시점 매출 선계산 후 연평균 적용)
df_pivot['Fee_Rev_Daily'] = df_pivot['AUM'] * (df_pivot['TER'] / 100)
panel_b_alternative = df_pivot.groupby(['코드', 'Category', 'Year'])['Fee_Rev_Daily'].mean().reset_index()
panel_b_final_alt = panel_b_alternative.groupby(['Year', 'Category'])['Fee_Rev_Daily'].sum().unstack() / 1e9
panel_b_final_alt = panel_b_final_alt.reindex(all_years).fillna(0)

print("\n✔ [3단계] 대안 방식(일별 매출 선계산 후 연평균) 적용 시 2020년 이후 결과 비교")
print("-" * 80)
print(" [기존 방식 수수료 매출 (십억 원)]")
print(panel_b_final.tail(6).round(2).to_string())
print("\n [보정된 방식 수수료 매출 (십억 원)]")
print(panel_b_final_alt.tail(6).round(2).to_string())
print("-" * 80)

# 검증 4단계: 연도별 상장 종목 수(Count) 추이 확인
etf_counts = df_pivot.groupby(['Year', 'Category'])['코드'].nunique().unstack().reindex(all_years).fillna(0)

print("\n✔ [4단계] 연도별 시장에 존재하는 고유 ETF 종목 수 (샘플 사이즈)")
print("-" * 80)
print(etf_counts.to_string())
print("="*80)


# ==========================================
# 6. 논문 Figure 3 스타일 시각화 및 파일 저장
# ==========================================
print("Figure 3 패널 A & B 시각화 그래프 생성 중...")
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))

# Panel A: Assets under management (AUM)
ax1.plot(panel_a_final.index, panel_a_final.get('Broad-based', 0), label='Broad-based ETFs', color='blue', linestyle='--')
ax1.plot(panel_a_final.index, panel_a_final.get('Specialized', 0), label='Specialized ETFs', color='red', linestyle='-')
ax1.set_title('Panel A: Assets under management', fontsize=12, fontweight='bold')
ax1.set_xlabel('Year')
ax1.set_ylabel('AUM (Trillion KRW)')
ax1.legend()

# Panel B: Implied fee revenues (수수료 매출)
ax2.plot(panel_b_final.index, panel_b_final.get('Broad-based', 0), label='Broad-based ETFs', color='blue', linestyle='--')
ax2.plot(panel_b_final.index, panel_b_final.get('Specialized', 0), label='Specialized ETFs', color='red', linestyle='-')
ax2.set_title('Panel B: Implied fee revenues', fontsize=12, fontweight='bold')
ax2.set_xlabel('Year')
ax2.set_ylabel('Annual fee revenues (Billion KRW)')
ax2.legend()

plt.tight_layout()

# 그래프 폴더 생성 및 저장
os.makedirs(output_dir, exist_ok=True)
output_image_path = os.path.join(output_dir, 'Figure_3_Panel_AB.png')

plt.savefig(output_image_path, dpi=300, bbox_inches='tight')
print(f"그래프 파일이 저장되었습니다:\n-> {output_image_path}")

plt.show()
print("모든 작업이 완료되었습니다!")