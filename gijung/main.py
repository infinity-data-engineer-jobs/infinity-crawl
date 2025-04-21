from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException

import json
import datetime
import time
import sqlite3
import os
key = { 
    '공고PK':'notice_id',
    '회사PK':'company_id',
    '직무분야':'notice_job_category',
    '근무지역':'notice_location',
    '경력사항':'notice_career',
    '공고제목':'notice_title',
    '포지션상세':'notice_position',
    '주요업무':'notice_main_work',
    '자격요건':'notice_qualification',
    '우대사항':'notice_preferred_qualification',
    '혜택 및 복지':'notice_welfare',
    '채용 전형':'notice_category',
    '마감일':'notice_end_date',
    '기술 스택 • 툴':'notice_tech_stack',
    '공고URL':'notice_url',
    '회사명':'company_name',
    '태그':'company_tag',
    '연봉':'company_salary',
    '위치':'company_location',
    '인원':'company_headcount',
    '매출':'company_revenue',
    '기업 정보':'company_info',
    '등록일시':'reg_dt',
    '수정일시':'mod_dt'
}

db_name = 'wanted.db'
current_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_dir, db_name)

with sqlite3.connect(db_path) as con:
    with webdriver.Chrome(service=Service(ChromeDriverManager().install())) as driver:
        driver.execute_script('window.open("about:blank", "_blank");')
        tabs = driver.window_handles
        driver.switch_to.window(tabs[0])

        driver.get("https://www.wanted.co.kr/wdlist/518/899?country=kr&job_sort=job.popularity_order&years=-1&selected=899&locations=all")
        WebDriverWait(driver, 10)

        prev_height = driver.execute_script("return document. body.scrollHeight")
        
        while True:
            driver.execute_script("window.scrollTo(0,document.body.scrollHeight)")
            time.sleep(2)
            current_height = driver.execute_script("return document. body.scrollHeight")
            print(prev_height,current_height)
            if current_height == prev_height:
                break
            prev_height = current_height
        
        company_url_set = set()

        cnt = 1
        while True:
            cnt+=1
            try:
                notice = driver.find_element(By.XPATH, f'//*[@id="__next"]/div[3]/div[2]/ul/li[{cnt}]/div/a')
                notice_url = notice.get_attribute('href')
                driver.switch_to.window(tabs[1])
                driver.get(notice_url)
                WebDriverWait(driver, 10)
                time.sleep(0.5)
                #상세보기 클릭
                driver.find_element(By.XPATH, '//*[@id="__next"]/main/div[1]/div/section/section/article[1]/div/button/span[2]').click()
                row_data = {}
                row_data[key['공고URL']] = notice_url
                row_data[key['공고PK']] = notice_url.split('/')[-1]
                row_data[key['직무분야']] = '파이썬 개발자'
                row_data[key['공고제목']] = driver.find_element(By.XPATH, '//*[@id="__next"]/main/div[1]/div/section/header/h1').text
                row_data[key['경력사항']] = driver.find_element(By.XPATH, '//*[@id="__next"]/main/div[1]/div/section/header/div/div[1]/span[4]').text
                notice_context = driver.find_element(By.XPATH, '//*[@id="__next"]/main/div[1]/div/section/section').find_elements(By.TAG_NAME,'article')
                #포지션 상세~ 채용전형 수집
                notice_description = notice_context[0]
                row_data[key['포지션상세']] = notice_description.find_element(By.TAG_NAME, 'div').find_element(By.TAG_NAME, 'span').text
                for div in notice_description.find_element(By.TAG_NAME, 'div').find_elements(By.TAG_NAME, 'div'):
                    context_title = div.find_element(By.TAG_NAME, 'h3').text.strip()
                    row_data[key[context_title]] = div.find_element(By.TAG_NAME, 'span').text

                #기술스택~근무지역
                for notice_context_other in notice_context[1:]:
                    #print(notice_context_other.text,'\n')
                    context_title = notice_context_other.find_element(By.TAG_NAME, 'h2').text.strip()
                    #print(context_title)
                    if context_title == '기술 스택 • 툴':
                        row_data[key[context_title]] = notice_context_other.find_element(By.TAG_NAME, 'ul').text
                    elif context_title == '마감일':
                        row_data[key[context_title]] = notice_context_other.find_element(By.TAG_NAME, 'span').text
                    elif context_title == '근무지역':
                        row_data[key[context_title]] = notice_context_other.find_elements(By.TAG_NAME, 'div')[-1].text       
                        break

                #회사url 별도 처리를 위해 따로 변수에 저장
                company_url = driver.find_element(By.XPATH, '//*[@id="__next"]/main/div[1]/div/section/header/div/div[1]/a').get_attribute('href')
                company_url_set.add(company_url)
                row_data[key['회사PK']] = company_url.split('/')[-1]
                driver.switch_to.window(tabs[0])
                
                current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                row_data[key['등록일시']] = current_time
                row_data[key['수정일시']] = current_time
                columns = ', '.join(row_data.keys())
                placeholders = ', '.join(['?'] * len(row_data))
                values = list(row_data.values())
                query = f"INSERT INTO notice_info ({columns}) VALUES ({placeholders})"
                cur = con.cursor()
                cur.execute(query, values)
                con.commit()
                
                time.sleep(1)
            except NoSuchElementException:# 다음 공고를 못찾을 떄까지 반복
                break

        for company_url in company_url_set:
            row_data = {}
            #print(company_url)
            driver.switch_to.window(tabs[1])
            driver.get(company_url)
            WebDriverWait(driver, 10)
            time.sleep(0.5)
            row_data[key['회사PK']] = company_url.split('/')[-1]
            while True:
                driver.execute_script("window.scrollTo(0,document.body.scrollHeight)")
                time.sleep(0.2)
                current_height = driver.execute_script("return document. body.scrollHeight")
                if current_height == prev_height:
                    break
                prev_height = current_height

            row_data[key['회사명']] = driver.find_element(By.XPATH, '//*[@id="__next"]/div[3]/div[2]/div/div[1]/div[1]/div[1]/h1').text
            company_detail_context = driver.find_element(By.XPATH, '//*[@id="__next"]/div[3]/div[2]/div/div[2]').find_elements(By.TAG_NAME,'section')
            for context in company_detail_context:
                context_title = context.find_element(By.TAG_NAME, 'h2').text.strip()
                if context_title == '태그':
                    row_data[key[context_title]] = context.find_element(By.XPATH, './/div').text
                elif context_title == '매출':
                    row_data[key[context_title]] = context.find_element(By.XPATH, './/div/div[1]/div/div').text
                elif context_title == '연봉':
                    row_data[key[context_title]] = context.find_element(By.XPATH, './/div[1]/div[2]/div[1]/div/div').text.replace('만원','').replace(',','')
                elif context_title == '인원':
                    row_data[key[context_title]] = context.find_element(By.XPATH, './/div/div[1]/div[1]/div/div').text.replace('명','').replace(',','')
                elif context_title == '기업 정보':
                    company_info = {}
                    info_sections = context.find_elements(By.TAG_NAME, 'dl')
                    for section in info_sections:
                        title = section.find_element(By.TAG_NAME, 'dt').text.strip()
                        value = section.find_element(By.TAG_NAME, 'dd').text.strip()
                        company_info[title] = value
                    row_data[key['기업 정보']] = json.dumps(company_info)
            
            location_element = driver.find_element(By.XPATH, '//*[@id="__next"]/div[3]/div[2]/div/div[2]/div[1]')
            ActionChains(driver).scroll_to_element(location_element).perform()
            time.sleep(2)
            WebDriverWait(location_element.find_element(By.TAG_NAME, 'span'), 10)
            row_data[key['위치']] = location_element.find_elements(By.TAG_NAME, 'span')[-1].text
            
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            row_data[key['등록일시']] = current_time
            row_data[key['수정일시']] = current_time
            columns = ', '.join(row_data.keys())
            placeholders = ', '.join(['?'] * len(row_data))
            values = list(row_data.values())
            query = f"INSERT INTO company_info ({columns}) VALUES ({placeholders})"
            cur = con.cursor()
            cur.execute(query, values)
            con.commit()