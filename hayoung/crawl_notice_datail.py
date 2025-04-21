from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from django.utils import timezone
from bs4 import BeautifulSoup
from datetime import datetime
import time

def crawl_notice(position_id, company_id):
    notice_url = f"https://www.wanted.co.kr/wd/{position_id}"

    # 크롬 드라이버 옵션
    options = Options()
    options.add_argument('--headless')  # 창 없이 실행
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")

    # 드라이버 실행 및 페이지 로딩
    driver = webdriver.Chrome(options=options)
    driver.get(notice_url)

    try:
        more_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(., '상세 정보 더 보기')]"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", more_button)
        time.sleep(1)

        driver.execute_script("arguments[0].click();", more_button)

        time.sleep(2)
        print("'상세 정보 더 보기' 클릭 성공")
    except Exception as e:
        print(f"'상세 정보 더 보기' 클릭 실패: {e}")
        
    # 최종 HTML 가져와서 파싱
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    driver.quit()

    #notice_job_category 고정
    job_category = "DBA"

    #notice_location, notice_career 데이터 가져오기
    info_tags_1 = soup.find_all('span', class_='JobHeader_JobHeader__Tools__Company__Info__b9P4Y wds-rgovpd')
    notice_location = info_tags_1[0].get_text(strip=True) if len(info_tags_1) > 0 else None
    notice_career = info_tags_1[1].get_text(strip=True) if len(info_tags_1) > 1 else None


    # notice_title(공고제목)
    notice_title_tag = soup.find('h1', class_='wds-jtr30u')
    notice_title = notice_title_tag.get_text(strip=True) if notice_title_tag else None


    # notice_position(포지션상세)
    notice_position_section = soup.find('section', class_='JobContent_descriptionWrapper__RMlfm')

    if notice_position_section:
        h2_tags = notice_position_section.find_all('h2')
        for h2 in h2_tags:
            if '포지션 상세' in h2.get_text():
                div = h2.find_next_sibling('div', class_='JobDescription_JobDescription__paragraph__wrapper__WPrKC')
                if div:
                    span = div.find('span', class_='wds-wcfcu3')
                    if span:
                        notice_position = " ".join(span.stripped_strings)
                break


    # notice_main_work(주요업무)
    notice_main_work = None

    # 여러 개의 주요 섹션이 있으니 반복
    section_divs = soup.find_all('div', class_='JobDescription_JobDescription__paragraph__87w8I')
    for div in section_divs:
        h3 = div.find('h3')
        if h3 and '주요업무' in h3.get_text():
            target_span = div.find('span', class_='wds-wcfcu3')
            if target_span:
                notice_main_work = " ".join(target_span.stripped_strings)
            break  # 찾았으면 반복 종료

    # notice_qualification(자격요건)
    notice_qualification = None

    section_divs = soup.find_all('div', class_='JobDescription_JobDescription__paragraph__87w8I')
    for div in section_divs:
        h3 = div.find('h3')
        if h3 and '자격요건' in h3.get_text():
            target_span = div.find('span', class_='wds-wcfcu3')
            if target_span:
                notice_qualification = " ".join(target_span.stripped_strings)
            break  

    # notice_preferred_qualificatio(우대사항)
    notice_preferred_qualification = None

    for section in soup.find_all('div', class_='JobDescription_JobDescription__paragraph__87w8I'):
        h3 = section.find('h3')
        if h3 and '우대사항' in h3.get_text():
            outer_span = section.find('span', class_='wds-wcfcu3')
            if outer_span:
                inner_span = outer_span.find('span')
                if inner_span:
                    notice_preferred_qualification = inner_span.get_text(strip=True)  # ← 여기가 최종!



    # notice_welfare(혜택 및 복지)
    notice_welfare = None

    section_divs = soup.find_all('div', class_='JobDescription_JobDescription__paragraph__87w8I')
    for div in section_divs:
        h3 = div.find('h3')
        if h3 and '혜택 및 복지' in h3.get_text():
            target_span = div.find('span', class_='wds-wcfcu3')
            if target_span:
                notice_welfare = " ".join(target_span.stripped_strings)
            break  

    # notice_category(채용 전형)
    notice_category = None

    section_divs = soup.find_all('div', class_='JobDescription_JobDescription__paragraph__87w8I')
    for div in section_divs:
        h3 = div.find('h3')
        if h3 and '채용 전형' in h3.get_text():
            target_span = div.find('span', class_='wds-wcfcu3')
            if target_span:
                notice_category = " ".join(target_span.stripped_strings)
            break  
        
        
    # notice_end_date(마감일)
    notice_end_date = None
    notice_end_date_title = soup.find('h2', string=lambda text: text and '마감일' in text)
    if notice_end_date_title:
        span = notice_end_date_title.find_next_sibling('span', class_='wds-lgio6k')
        if span:
            notice_end_date = span.get_text(strip=True)
            
    # notice_tech_stack(기술 스택 • 툴 (없을수 있음))
    notice_tech_stack = None 
    notice_tech_stack_title = soup.find('h2', string=lambda text: text and '기술 스택' in text)

    if notice_tech_stack_title:
        container = notice_tech_stack_title.find_parent()
        if container:
            ul = container.find('ul')
            if ul:
                spans = ul.find_all('span', class_='wds-1m3gvmz') 
                tech_stack_list = [span.get_text(strip=True) for span in spans]
                notice_tech_stack = "\n".join(tech_stack_list)

    # 현재 시각
    now = datetime.now()

    notice_data = {
        "notice_id": position_id,
        "company_id": company_id,
        "notice_job_category": job_category,
        "notice_location": notice_location,
        "notice_career": notice_career,
        "notice_title": notice_title,
        "notice_position": notice_position,
        "notice_main_work": notice_main_work,
        "notice_qualification": notice_qualification,
        "notice_preferred_qualification": notice_preferred_qualification,
        "notice_welfare": notice_welfare,
        "notice_category": notice_category,
        "notice_end_date": notice_end_date,
        "notice_tech_stack": notice_tech_stack,
        "notice_url": notice_url,
        "reg_dt": now,
        "mod_dt": now
    }

    return notice_data