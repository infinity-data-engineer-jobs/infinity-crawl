import sqlite3
import time
import requests
from bs4 import BeautifulSoup
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from datetime import datetime
import os

# 1. DB 연결
def connect_db(db_path='./database/wanted_de.db'):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    return conn, cursor

# 2. 상세 데이터 가져오는 함수
def fetch_full_detail(url, driver):
    detail = {}

    # (1) requests + BeautifulSoup로 JSON 파싱
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        script_tag = soup.find('script', id='__NEXT_DATA__')
        if not script_tag or not script_tag.string:
            print(f"__NEXT_DATA__ 없음: {url}")
            return None

        data = json.loads(script_tag.string)
        initial_data = data['props']['pageProps']['initialData']

        # --- 매칭된 필드 채우기 ---
        detail['company_id'] = initial_data.get('company', {}).get('company_id')
        detail['notice_job_category'] = "데이터 엔지니어"  # 하드코딩
        detail['notice_location'] = initial_data.get('address', {}).get('full_location')
        detail['notice_title'] = initial_data.get('position')
        detail['notice_position'] = initial_data.get('intro')
        detail['notice_main_work'] = initial_data.get('main_tasks')
        detail['notice_qualification'] = initial_data.get('requirements')
        detail['notice_preferred_qualification'] = initial_data.get('preferred_points')
        detail['notice_welfare'] = initial_data.get('benefits')
        detail['notice_category'] = initial_data.get('hire_rounds')
        detail['notice_end_date'] = initial_data.get('due_time')

    except Exception as e:
        print(f"[requests 실패] {url} 에러: {e}")
        return None

    # (2) Selenium으로 스킬/경력 가져오기
    try:
        driver.get(url)
        time.sleep(1.5)  # 약간 대기

        # 스킬 태그
        try:
            skill_section = driver.find_element(By.XPATH, "//article[contains(@class,'JobSkillTags')]")
            try:
                see_more = skill_section.find_element(By.LINK_TEXT, "더 보기")
                see_more.click()
                time.sleep(0.5)
            except:
                pass

            tags = [el.text for el in skill_section.find_elements(By.CSS_SELECTOR, "ul > li > span") if el.text.strip()]
            detail['notice_tech_stack'] = '\n'.join(tags) if tags else None
        except Exception as e:
            print(f"[스킬 섹션 없음] {url}")
            detail['notice_tech_stack'] = None

        # 경력/신입 정보
        try:
            experience = None
            spans = driver.find_elements(By.XPATH, "//section[contains(@class,'JobContent')]/header//span")
            for span in spans:
                txt = span.text.strip()
                if '경력' in txt or '신입' in txt:
                    experience = txt
                    break
            detail['notice_career'] = experience
        except Exception as e:
            print(f"[경력 정보 없음] {url}")
            detail['notice_career'] = None

    except Exception as e:
        print(f"[selenium 실패] {url} 에러: {e}")
        return None

    return detail

# 3. 업데이트 함수
def update_notice(cursor, conn, notice_id, detail):
    try:
        cursor.execute("""
        UPDATE notice
        SET company_id = :company_id,
            notice_job_category = :notice_job_category,
            notice_location = :notice_location,
            notice_title = :notice_title,
            notice_position = :notice_position,
            notice_main_work = :notice_main_work,
            notice_qualification = :notice_qualification,
            notice_preferred_qualification = :notice_preferred_qualification,
            notice_welfare = :notice_welfare,
            notice_category = :notice_category,
            notice_end_date = :notice_end_date,
            notice_tech_stack = :notice_tech_stack,
            notice_career = :notice_career,
            mod_dt = :mod_dt
        WHERE notice_id = :notice_id
        """, {
            **detail,
            'notice_id': notice_id,
            'mod_dt': datetime.now().strftime('%Y-%m-%d')
        })
        conn.commit()
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            print("DB 잠김! 재시도 중...")
            time.sleep(1)
            return update_notice(cursor, conn, notice_id, detail)
        else:
            raise e

# 4. 메인 실행
if __name__ == "__main__":
    conn, cursor = connect_db()

    # 테이블에 필요한 컬럼 추가 (처음만 실행되게)
    try:
        cursor.execute("ALTER TABLE notice ADD COLUMN company_id INTEGER")
        cursor.execute("ALTER TABLE notice ADD COLUMN notice_job_category TEXT")
        cursor.execute("ALTER TABLE notice ADD COLUMN notice_location TEXT")
        cursor.execute("ALTER TABLE notice ADD COLUMN notice_title TEXT")
        cursor.execute("ALTER TABLE notice ADD COLUMN notice_position TEXT")
        cursor.execute("ALTER TABLE notice ADD COLUMN notice_main_work TEXT")
        cursor.execute("ALTER TABLE notice ADD COLUMN notice_qualification TEXT")
        cursor.execute("ALTER TABLE notice ADD COLUMN notice_preferred_qualification TEXT")
        cursor.execute("ALTER TABLE notice ADD COLUMN notice_welfare TEXT")
        cursor.execute("ALTER TABLE notice ADD COLUMN notice_category TEXT")
        cursor.execute("ALTER TABLE notice ADD COLUMN notice_end_date TEXT")
        cursor.execute("ALTER TABLE notice ADD COLUMN notice_tech_stack TEXT")
        cursor.execute("ALTER TABLE notice ADD COLUMN notice_career TEXT")
        conn.commit()
        print("테이블 컬럼 추가 완료")
    except:
        print("이미 컬럼 있음, 패스")

    cursor.execute("SELECT notice_id, notice_url FROM notice")
    notices = cursor.fetchall()

    # 드라이버 한번만 띄우기
    options = Options()
    options.add_argument("--window-size=1920,1080")
    # options.add_argument("--headless")
    # options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=options)

    failed_list = []

    for idx, (notice_id, notice_url) in enumerate(notices, 1):
        print(f"[{idx}/{len(notices)}] {notice_id} 처리중...")

        detail = fetch_full_detail(notice_url, driver)
        if detail:
            update_notice(cursor, conn, notice_id, detail)
            print("  > 업데이트 성공")
        else:
            print("  > 업데이트 실패")
            failed_list.append((notice_id, notice_url))

        time.sleep(1)

    driver.quit()
    conn.close()

    print("\n✅ 모든 작업 완료")
    if failed_list:
        print(f"❗ 실패한 {len(failed_list)}개 공고:")
        for nid, nurl in failed_list:
            print(f" - {nid}: {nurl}")
