from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from django.utils import timezone
from datetime import datetime
import time

def crawl_company(company_id):
    company_url = f"https://www.wanted.co.kr/company/{company_id}"


    # 크롬 드라이버 옵션
    options = Options()
    options.add_argument('--headless')  # 창 없이 실행
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")

    # 드라이버 실행 및 페이지 로딩
    driver = webdriver.Chrome(options=options)
    driver.get(company_url)
    time.sleep(3)  # 렌더링 대기 (필요 시 늘릴 수 있음)

    # 페이지 파싱
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    driver.quit()

    # company_name(회사명)
    company_name = soup.find('h1', class_='wds-14f7cyg')
    if company_name:
        company_name = company_name.get_text(strip=True)

    # company_tag(태그)
    company_tag = None

    company_tag_title = soup.find('h2', string=lambda text: text and '태그' in text)
    if company_tag_title:
        container = company_tag_title.find_parent()
        if container:
            buttons = container.find_all('button')
            tag_list = [btn.get_text(strip=True) for btn in buttons]
            company_tag = "\n".join(tag_list)

    # company_salary(연봉)
    company_salary = None


    summary_wrappers = soup.find_all('div', class_='ChartSummary_wrapper__xphdJ')
    for wrapper in summary_wrappers:
        
        label_span = wrapper.find('span')
        if label_span and '올해 입사자 평균연봉' in label_span.get_text():
            salary_div = wrapper.find('div', class_='wds-yh9s95')
            if salary_div:
                company_salary = salary_div.get_text(strip=True)
            break  
            
            
    # company_location(위치)
    company_location = None

    # company_headcount(인원)
    company_headcount = None

    employee_label = soup.find('span', string=lambda text: text and '인원' in text)
    if employee_label:
        container = employee_label.find_parent()
        if container:
            employee_div = container.find('div', class_='wds-yh9s95')
            if employee_div:
                company_headcount = employee_div.get_text(strip=True)

    # company_revenu(매출)
    company_revenue = None

    revenue_label = soup.find('span', string=lambda text: text and '매출' in text)
    if revenue_label:
        container = revenue_label.find_parent()
        if container:
            revenue_div = container.find('div', class_='wds-yh9s95')
            if revenue_div:
                company_revenue = revenue_div.get_text(strip=True)

    # company_inf(기업정보)
    company_info = {}

    info_section = soup.find('h2', string=lambda text: text and '기업 정보' in text)
    if info_section:
        container = info_section.find_parent()
        if container:
            dl_tags = container.find_all('dl')
            for dl in dl_tags:
                dt = dl.find('dt')
                dd = dl.find('dd')
                if dt and dd:
                    key = dt.get_text(strip=True)
                    value = dd.get_text(strip=True)
                    company_info[key] = value

    # 현재 시각
    now = datetime.now()

    company_data = {
        "company_id": company_id,
        "company_name": company_name,
        "company_tag": company_tag,
        "company_salary": company_salary,
        "company_location": company_location,
        "company_headcount": company_headcount,
        "company_revenue": company_revenue,
        "company_info": company_info,
        "reg_dt": now,
        "mod_dt": now
    }

    return company_data