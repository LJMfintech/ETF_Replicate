import os
import pandas as pd

# 1. 파일 경로 설정 (상대 경로 기준)
# 코드 위치(E:\ETF_Replicate\Classification)에서 상위 폴더(..)로 나간 뒤 Data_result로 들어갑니다.
excel_path = os.path.join(
    "..", "Data_result", "Classification", "ETF_List_Final.xlsx"
)
output_path = os.path.join("..", "Data_result", "Classification", "Index.csv")


def extract_unique_indexes(input_file, output_file):
    print("데이터를 불러오는 중입니다...")
    print(f"입력 파일 경로: {os.path.abspath(input_file)}")
    print(f"출력 파일 경로: {os.path.abspath(output_file)}")

    try:
        # 2. 엑셀 파일 로드 (D열과 J열만 가져옴, Excel은 0부터 시작하므로 D=3, J=9)
        df = pd.read_excel(input_file, usecols=[3, 9])

        # 열 이름 강제 지정
        df.columns = ["ETF기초지수명", "Category"]

        # 3. 중복 제거 ('ETF기초지수명' 기준 최초 등장만 남김)
        df_unique = df.drop_duplicates(subset=["ETF기초지수명"], keep="first")

        # 결측치(빈 칸) 제거
        df_unique = df_unique.dropna(subset=["ETF기초지수명"])

        # 저장할 폴더가 없으면 자동으로 생성하는 안전장치
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 4. CSV 파일로 저장 (한글 깨짐 방지를 위해 utf-8-sig 사용)
        df_unique.to_csv(output_file, index=False, encoding="utf-8-sig")

        print(f"\n성공적으로 처리되었습니다!")
        print(f"저장된 파일: {os.path.abspath(output_file)}")
        print(f"추출된 고유 지수 개수: {len(df_unique)}개")

    except FileNotFoundError:
        print(f"\n에러: 파일을 찾을 수 없습니다. 경로를 확인해주세요.")
        print(f"현재 실행 위치(cwd): {os.getcwd()}")
        print(f"확인하려 한 경로: {os.path.abspath(input_file)}")
    except Exception as e:
        print(f"\n에러가 발생했습니다: {e}")


if __name__ == "__main__":
    extract_unique_indexes(excel_path, output_path)