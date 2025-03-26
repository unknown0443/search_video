import os
import time
import requests
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from tqdm import tqdm

# ✅ 크롤링할 검색어 목록 (각 300개씩)
SEARCH_TERMS = [
    "레드벨벳 슬기", "레드벨벳 아이린", "레드벨벳 조이", "레드벨벳 웬디", 
    "뉴진스 다니엘", "뉴진스 해린", "아이브 장원영", "아이브 안유진", 
    "엑소 카이", "엑소 디오", "엑소 백현", 
    "bts 정국", "bts 진", "bts 지민", "bts 뷔", 
    "stray kids 필릭스", "stray kids 현진"
]

NUM_IMAGES = 300  # ✅ 가져올 이미지 개수
SAVE_DIR = "bing(all)"  # ✅ 전체 저장 폴더
os.makedirs(SAVE_DIR, exist_ok=True)  # ✅ 상위 폴더 생성

# ✅ 다운로드된 이미지 목록 파일
DOWNLOAD_RECORD = "downloaded_images.txt"
if os.path.exists(DOWNLOAD_RECORD):
    with open(DOWNLOAD_RECORD, "r") as f:
        downloaded_images = set(f.read().splitlines())  # ✅ 기존 다운로드된 URL 저장
else:
    downloaded_images = set()

# ✅ Chrome WebDriver 설정
options = Options()
# options.add_argument("--headless")  # 👉 주석 처리하면 브라우저 화면 확인 가능
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

for term in SEARCH_TERMS:
    term_dir = os.path.join(SAVE_DIR, term.replace(" ", "_"))  # ✅ 하위 폴더명 설정
    os.makedirs(term_dir, exist_ok=True)  # ✅ 인물별 폴더 생성
    
    search_url = f"https://www.bing.com/images/search?q={term}&form=HDRSC2&first=1"
    driver.get(search_url)

    image_urls = set()
    scroll_count = 0
    max_scrolls = 60  # ✅ 최대 스크롤 횟수 증가 (기존 30 -> 60)
    prev_image_count = 0  # ✅ 이전 스크롤에서 수집된 이미지 개수

    while len(image_urls) < NUM_IMAGES and scroll_count < max_scrolls:
        # ✅ 페이지 끝까지 스크롤 내리기 (스크롤 여러 번 실행)
        for _ in range(5):  # 5번 반복해서 확실히 아래로 이동
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(1.5, 3))  # 🔥 로딩 대기

        # ✅ "이미지 더 보기" 버튼 클릭 추가
        try:
            more_button = driver.find_element(By.CSS_SELECTOR, "a.btn_seemore.cbtn.mBtn.linkBtn")
            driver.execute_script("arguments[0].click();", more_button)
            time.sleep(random.uniform(2, 4))  # 버튼 클릭 후 딜레이
            print(f"{term} - 🖱️ '이미지 더 보기' 버튼 클릭")
        except:
            pass  # 버튼이 없는 경우 무시하고 계속 진행
        
        # ✅ 이미지 URL 수집 (중복된 URL은 저장 안 함)
        image_elements = driver.find_elements(By.CSS_SELECTOR, "img.mimg")
        for img in image_elements:
            img_url = img.get_attribute("src")
            if img_url and "http" in img_url and img_url not in downloaded_images:
                image_urls.add(img_url)

        scroll_count += 1
        new_images = len(image_urls) - prev_image_count
        prev_image_count = len(image_urls)

        print(f"{term} - 🔄 스크롤 {scroll_count}회 완료, 현재 {len(image_urls)}개 이미지 수집됨...")

        # ✅ 새로운 이미지가 추가되지 않으면 강제로 이동
        if new_images < 10:
            print(f"{term} - ⚠️ 새로운 이미지가 충분하지 않음, 강제 스크롤 이동")
            try:
                last_element = driver.find_element(By.CSS_SELECTOR, "img.mimg:last-child")
                driver.execute_script("arguments[0].scrollIntoView();", last_element)
                time.sleep(3)
            except:
                print(f"{term} - ❌ 스크롤 강제 이동 실패")

    print(f"{term} - 🔍 총 {len(image_urls)}개의 이미지 URL을 찾았습니다!")

    # ✅ 중복 체크하면서 이미지 다운로드
    new_downloaded = 0
    for i, img_url in enumerate(tqdm(list(image_urls)[:NUM_IMAGES], desc=f"📥 {term} 이미지 다운로드 진행 중")):
        if img_url in downloaded_images:
            print(f"⚠️ {term} - 중복된 이미지, 스킵: {img_url}")
            continue

        try:
            response = requests.get(img_url, stream=True, timeout=10)
            if response.status_code == 200:
                img_path = os.path.join(term_dir, f"image_{i+1}.jpg")
                with open(img_path, "wb") as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                downloaded_images.add(img_url)  # ✅ 다운로드 목록에 추가
                new_downloaded += 1
        except Exception as e:
            print(f"❌ 다운로드 실패: {img_url} -> {str(e)}")

    print(f"✅ {term} 크롤링 완료! 총 {new_downloaded}개 저장됨")

# ✅ 다운로드된 이미지 URL 저장 (다음 실행 시 중복 방지)
with open(DOWNLOAD_RECORD, "w") as f:
    for url in downloaded_images:
        f.write(url + "\n")

driver.quit()
print(f"✅ 모든 크롤링 완료! 전체 데이터는 '{SAVE_DIR}' 폴더에 저장됨")
