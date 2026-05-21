import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ==========================================
# 1. 경로 설정 (스크립트 위치 기준 자동 상대경로 계산)
# ==========================================
# 현재 실행 중인 스크립트 파일의 절대 경로를 잡습니다.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()

# 한 단계 위로 올라가서 프로젝트 루트인 'ETF_Replicate' 폴더를 잡습니다.
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR) 

# 통합본 파일 및 그래프 저장 폴더 경로 설정
merged_path = os.path.join(PROJECT_ROOT, 'Data_result', 'ETF_Time_Series_Merged.xlsx')
output_dir = os.path.join(PROJECT_ROOT, 'Data_result', 'Classification')

print("=" * 60)
print(f"기준 스크립트 위치: {SCRIPT_DIR}")
print(f"통합 데이터 파일 경로: {merged_path}")
print(f"그래프 저장 예정 폴더: {output_dir}")
print("=" * 60)

if not os.path.exists(merged_path):
    raise FileNotFoundError(f"통합 데이터를 찾을 수 없습니다. 경로를 확인해주세요: {merged_path}")

# ==========================================
# 2. 통합 데이터 로드
# ==========================================
print("통합 ETF 데이터 로드 중 (시간이 다소 소요될 수 있습니다)...")
df_total = pd.read_excel(merged_path)

# ==========================================
# 3. 가로 날짜 컬럼을 세로로 변환 (Melting)
# ==========================================
fixed_cols = ['코드', '코드명', '유형', '아이템코드', '아이템명', '집계주기', 'Category']
date_cols = [col for col in df_total.columns if col not in fixed_cols]

print("데이터 구조 변환 중 (Wide -> Long)...")
df_long = df_total.melt(
    id_vars=fixed_cols, 
    value_vars=date_cols, 
    var_name='Date', 
    value_name='Value'
)

# 결측치 제거 및 날짜/연도 변수 처리
df_long = df_long.dropna(subset=['Value'])
df_long['Date'] = pd.to_datetime(df_long['Date'])
df_long['Year'] = df_long['Date'].dt.year

# 데이터 문자열 전처리
df_long['Category'] = df_long['Category'].astype(str).str.strip()

# ==========================================
# 4. 데이터 재구조화 (Pivot)
# ==========================================
df_pivot = df_long.pivot_table(
    index=['코드', 'Category', 'Year', 'Date'], 
    columns='아이템명', 
    values='Value', 
    aggfunc='first'
).reset_index()

df_pivot.columns.name = None
df_pivot = df_pivot.rename(columns={'AUM(원)': 'AUM', 'TER 보수': 'TER'})

# 숫자 형변환 및 예외 처리
df_pivot['AUM'] = pd.to_numeric(df_pivot['AUM'], errors='coerce')
df_pivot['TER'] = pd.to_numeric(df_pivot['TER'], errors='coerce')
df_pivot = df_pivot.dropna(subset=['AUM'])

# ==========================================
# 5. 패널별 지표 집계 (Panel A & B)
# ==========================================
print("패널별 통계량 집계 및 스케일 조정 중...")

# [Panel A] 연도별 각 종목의 최신 관측일(기말) AUM 합산 -> 조(Trillion) 원 단위
df_panel_a = df_pivot.sort_values('Date').groupby(['코드', 'Category', 'Year']).last().reset_index()
panel_a_final = df_panel_a.groupby(['Year', 'Category'])['AUM'].sum().unstack() / 1e12

# [Panel B] 연평균 AUM 및 연평균 TER 기반 수수료 매출 산출 -> 십억(Billion) 원 단위
df_panel_b_base = df_pivot.groupby(['코드', 'Category', 'Year']).agg({
    'AUM': 'mean',
    'TER': 'mean'
}).reset_index()

# Fee_Rev = 연평균 AUM * (연평균 TER / 100)  ※ FnGuide TER 단위(%) 보정
df_panel_b_base['Fee_Rev'] = df_panel_b_base['AUM'] * (df_panel_b_base['TER'] / 100)
panel_b_final = df_panel_b_base.groupby(['Year', 'Category'])['Fee_Rev'].sum().unstack() / 1e9

# 데이터 연속성 확보 (2002년부터 2025년까지 빈 연도 빈칸 메우기)
all_years = pd.Index(range(2002, 2026), name='Year')
panel_a_final = panel_a_final.reindex(all_years).fillna(0)
panel_b_final = panel_b_final.reindex(all_years).fillna(0)

# ==========================================
# 6. 연도별 집계 결과값 화면에 출력
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
# 7. 논문 Figure 3 스타일 시각화 및 파일 지정폴더 저장 (Matplotlib)
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

# --- [수정된 저장 폴더 로직] ---
# 만약 Data_result/Classification 폴더가 없으면 자동 생성 후 저장합니다.
os.makedirs(output_dir, exist_ok=True)
output_image_path = os.path.join(output_dir, 'Figure_3_Panel_AB.png')

plt.savefig(output_image_path, dpi=300, bbox_inches='tight')
print(f"그래프 파일이 지정된 경로에 성공적으로 저장되었습니다:\n-> {output_image_path}")

# 화면에 그래프 띄우기
plt.show()
print("모든 작업이 성공적으로 완료되었습니다!")