from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import sqlite3
from datetime import datetime
import json
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from functools import wraps

@dataclass
class CompanyData:
    company_id: int
    company_name: str
    company_tag: str = ''
    company_salary: str = ''
    company_location: str = ''
    company_headcount: str = ''
    company_revenue: str = ''
    company_info: str = ''

@dataclass
class JobData:
    company_id: int
    notice_job_category: str
    notice_location: str = ''
    notice_career: str = ''
    notice_title: str = ''
    notice_position: str = ''
    notice_main_work: str = ''
    notice_qualification: str = ''
    notice_preferred_qualification: str = ''
    notice_welfare: str = ''
    notice_category: str = ''
    notice_end_date: str = ''
    notice_tech_stack: str = ''
    notice_url: str = ''

class WantedCrawler:
    def __init__(self, headless: bool = True):
        self.driver = self._setup_driver(headless)
        self.wait = WebDriverWait(self.driver, 60)
        
    def _setup_driver(self, headless: bool) -> webdriver.Chrome:
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--start-maximized')  # 전체 화면으로 시작
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36')
        driver = webdriver.Chrome(options=options)
        driver.maximize_window()  # 창 최대화
        return driver
    
    def retry(max_retries: int = 5, delay: int = 2):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        if attempt == max_retries - 1:
                            raise e
                        print(f"{func.__name__} 실패 (시도 {attempt + 1}/{max_retries}): {e.__class__.__name__} - {e.args}")
                        time.sleep(delay)
                return None
            return wrapper
        return decorator
    
    def _find_element(self, by: By, value: str) -> Any:
        return self.wait.until(EC.presence_of_element_located((by, value)))
    
    def _find_elements(self, by: By, value: str) -> List[Any]:
        return self.wait.until(EC.presence_of_all_elements_located((by, value)))
    
    def scroll_to_bottom(self) -> None:
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            print(f"새로운 공고 로드 중... 현재 스크롤 높이: {new_height}")
    
    @retry()
    def get_job_detail(self, job_url: str) -> Optional[Dict[str, List[Dict[str, str]]]]:
        self.driver.execute_script(f"window.open('{job_url}');")
        self.driver.switch_to.window(self.driver.window_handles[-1])
        
        try:
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(2)
            
            # "상세 정보 더 보기" 버튼 클릭
            try:
                more_info_button = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.Button_Button__root__MS62F.Button_Button__outlined__n6mA4.Button_Button__outlinedAssistive__FrGzM.Button_Button__outlinedSizeLarge__H9zAo.Button_Button__fullWidth__HwmHX"))
                )
                more_info_button.click()
                print("상세 정보 더 보기 버튼 클릭 성공")
                time.sleep(2)  # 내용이 로드될 때까지 충분히 대기
            except Exception as e:
                print(f"상세 정보 더 보기 버튼 클릭 실패: {str(e)}")
                return None  # 버튼 클릭 실패시 None 반환
            
            # 페이지 소스 가져오기
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # 마감일 추출
            end_date = ""
            try:
                end_date_element = soup.select_one("article.JobDueTime_JobDueTime__yvhtg span.wds-lgio6k")
                if end_date_element:
                    end_date = end_date_element.text.strip()
            except Exception as e:
                print(f"마감일 추출 실패: {str(e)}")
            
            # 경력 추출
            career = ""
            try:
                career_element = soup.select_one("header > div > div:nth-of-type(1) > span:nth-of-type(4)")
                if career_element:
                    career = career_element.text.strip()
                    print(f"경력 추출 성공: {career}")
            except Exception as e:
                print(f"경력 추출 실패: {str(e)}")
            
            # 근무위치 추출
            location = ""
            try:
                location_element = soup.select_one(".JobWorkPlace_JobWorkPlace__map__location__6pp2d")
                if location_element:
                    location = location_element.text.strip()
                    print(f"근무위치 추출 성공: {location}")
            except Exception as e:
                print(f"근무위치 추출 실패: {str(e)}")
            
            # 기술 스택 추출
            tech_stack = []
            try:
                tech_stack_elements = soup.select(".SkillTagItem_SkillTagItem__MAo9X span")
                for element in tech_stack_elements:
                    tech_text = element.text.strip()
                    if tech_text:
                        tech_stack.append(tech_text)
            except Exception as e:
                print(f"기술 스택 추출 실패: {str(e)}")
            
            def extract_contents(tag_name: str) -> List[Dict[str, str]]:
                contents = []
                elements = soup.find_all(tag_name)
                processed_titles = set()  # 이미 처리된 타이틀을 추적
                
                # 데이터베이스 테이블 필드와 관련된 키워드 정의
                company_info_keywords = ["태그"]  # company_info 테이블 관련 키워드
                job_notice_keywords = [  # job_notice 테이블 관련 키워드
                    "주요업무", "자격요건", "우대사항", "복지", "채용", "기술 스택", "마감일", "근무지역"
                ]
                
                for element in elements:
                    tag_text = element.text.strip()
                    
                    # 이미 처리된 타이틀은 건너뛰기
                    if tag_text in processed_titles:
                        continue
                    
                    # 불필요한 내용 필터링
                    if "하단 네비게이션" in tag_text or "이 포지션을" in tag_text:
                        continue
                        
                    # h1 태그는 공고 제목으로 저장
                    if tag_name == 'h1':
                        if tag_text:
                            contents.append({
                                'title': tag_text,
                                'content': tag_text
                            })
                            processed_titles.add(tag_text)
                        continue
                    
                    # h2, h3 태그 처리
                    try:
                        next_section = element.find_next_sibling()
                        if next_section:
                            content_text = next_section.text.strip()
                            
                            # 태그 이름이 내용에 포함되어 있다면 제거
                            if content_text.startswith(tag_text):
                                content_text = content_text[len(tag_text):].strip()
                            
                            # 괄호와 줄바꿈 제거
                            content_text = content_text.replace('(', '').replace(')', '').replace('\n', ' ').strip()
                            
                            if tag_text and content_text:
                                # 데이터베이스 테이블 필드와 관련된 내용만 저장
                                if any(keyword in tag_text.lower() for keyword in company_info_keywords + job_notice_keywords):
                                    contents.append({
                                        'title': tag_text,
                                        'content': content_text
                                    })
                                    processed_titles.add(tag_text)
                    except:
                        pass
                    
                    # 태그 관련 처리
                    if tag_name == 'h2' and "태그" in tag_text:
                        tag_buttons = []
                        try:
                            buttons = soup.select(".Button_Button__root__MS62F.Button_Button__outlined__n6mA4.Button_Button__outlinedAssistive__FrGzM.Button_Button__outlinedSizeSmall__UUC5v")
                            for button in buttons:
                                tag_name = button.get('data-tag-name')
                                if tag_name:
                                    tag_buttons.append(tag_name)
                        except:
                            pass
                        if tag_buttons:  # 태그가 있는 경우에만 추가
                            contents.append({
                                'title': tag_text,
                                'content': '\n'.join(tag_buttons),
                                'tags': '\n'.join(tag_buttons)
                            })
                            processed_titles.add(tag_text)
                    elif tag_name == 'h2' and "기술 스택" in tag_text:
                        if tech_stack:  # 기술 스택이 있는 경우에만 추가
                            contents.append({
                                'title': tag_text,
                                'content': None,
                                'tech_stack': '\n'.join(tech_stack)
                            })
                            processed_titles.add(tag_text)
                return contents
            
            return {
                'h1_contents': extract_contents('h1'),
                'h2_contents': extract_contents('h2'),
                'h3_contents': extract_contents('h3'),
                'end_date': end_date,
                'location': location,
                'tech_stack': '\n'.join(sorted(tech_stack)) if tech_stack else '',
                'career': career
            }
            
        finally:
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
    
    @retry()
    def get_company_info(self, company_id: str) -> Optional[CompanyData]:
        company_url = f"https://www.wanted.co.kr/company/{company_id}"
        self.driver.execute_script(f"window.open('{company_url}');")
        self.driver.switch_to.window(self.driver.window_handles[-1])
        
        try:
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(2)
            
            # 페이지 소스 가져오기
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            company_data = CompanyData(company_id=int(company_id), company_name='')
            
            # 위치 정보
            try:
                location_element = soup.select_one(".CompanyLocation_CompanyLocation__Address__gIRT7")
                if location_element:
                    company_data.company_location = location_element.text.strip()
                    print("위치 정보 추출 완료")
                else:
                    company_data.company_location = ''
                    print("위치 정보 없음")
            except:
                company_data.company_location = ''
                print("위치 정보 없음")
            
            # 연봉 정보
            try:
                salary_element = soup.select_one(".SalaryChart_wrapper__barchartWrapper__ckAFp .wds-yh9s95")
                if salary_element:
                    company_data.company_salary = salary_element.text.strip()
                    print("연봉 정보 추출 완료")
                else:
                    company_data.company_salary = ''
                    print("연봉 정보 없음")
            except:
                company_data.company_salary = ''
                print("연봉 정보 없음")
            
            # 인원수 정보
            try:
                headcount_element = soup.select_one(".EmployeeChart_wrapper__AX68I .wds-yh9s95")
                if headcount_element:
                    company_data.company_headcount = headcount_element.text.strip()
                    print("인원수 정보 추출 완료")
                else:
                    company_data.company_headcount = ''
                    print("인원수 정보 없음")
            except:
                company_data.company_headcount = ''
                print("인원수 정보 없음")
            
            # 매출 정보
            try:
                revenue_element = soup.select_one(".SalesChart_wrapper__vUNiD .wds-yh9s95")
                if revenue_element:
                    company_data.company_revenue = revenue_element.text.strip()
                    print("매출 정보 추출 완료")
                else:
                    company_data.company_revenue = ''
                    print("매출 정보 없음")
            except:
                company_data.company_revenue = ''
                print("매출 정보 없음")
            
            # 기업정보
            try:
                company_info_wrapper = soup.select_one(".CompanyInfoTable_wrapper__xI_Gq")
                if company_info_wrapper:
                    dl_elements = company_info_wrapper.find_all("dl")
                    company_info_dict = {}
                    for dl in dl_elements:
                        dt_elements = dl.find_all("dt")
                        dd_elements = dl.find_all("dd")
                        
                        for dt, dd in zip(dt_elements, dd_elements):
                            key = dt.text.strip()
                            value = dd.text.strip().replace('\n', '')
                            if key and value:
                                company_info_dict[key] = value
                    company_data.company_info = json.dumps(company_info_dict, ensure_ascii=False)
                    print("기업정보 추출 완료")
                else:
                    company_data.company_info = json.dumps({}, ensure_ascii=False)
                    print("기업정보 없음")
            except:
                company_data.company_info = json.dumps({}, ensure_ascii=False)
                print("기업정보 없음")
            
            return company_data
            
        finally:
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
    
    def setup_database(self) -> None:
        conn = sqlite3.connect('wanted_job_postings.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS company_info (
            company_id INTEGER PRIMARY KEY,
            company_name TEXT,
            company_tag TEXT,
            company_salary TEXT,
            company_location TEXT,
            company_headcount TEXT,
            company_revenue TEXT,
            company_info TEXT,
            reg_dt DATETIME DEFAULT CURRENT_TIMESTAMP,
            mod_dt DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_notice (
            notice_id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            notice_job_category TEXT,
            notice_location TEXT,
            notice_career TEXT,
            notice_title TEXT,
            notice_position TEXT,
            notice_main_work TEXT,
            notice_qualification TEXT,
            notice_preferred_qualification TEXT,
            notice_welfare TEXT,
            notice_category TEXT,
            notice_end_date TEXT,
            notice_tech_stack TEXT,
            notice_url TEXT,
            reg_dt DATETIME DEFAULT CURRENT_TIMESTAMP,
            mod_dt DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES company_info(company_id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_to_database(self, company_data: CompanyData, job_data: JobData) -> None:
        conn = sqlite3.connect('wanted_job_postings.db')
        cursor = conn.cursor()
        
        try:
            # 회사정보 저장
            cursor.execute('''
            INSERT OR REPLACE INTO company_info 
            (company_id, company_name, company_tag, company_salary, company_location, 
             company_headcount, company_revenue, company_info, mod_dt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                company_data.company_id,
                company_data.company_name,
                company_data.company_tag,
                company_data.company_salary,
                company_data.company_location,
                company_data.company_headcount,
                company_data.company_revenue,
                company_data.company_info
            ))
            
            # 공고정보 저장
            cursor.execute('''
            INSERT INTO job_notice 
            (company_id, notice_job_category, notice_location, notice_career, 
             notice_title, notice_position, notice_main_work, notice_qualification,
             notice_preferred_qualification, notice_welfare, notice_category,
             notice_end_date, notice_tech_stack, notice_url, mod_dt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                job_data.company_id,
                job_data.notice_job_category,
                job_data.notice_location,
                job_data.notice_career,
                job_data.notice_title,
                job_data.notice_position,
                job_data.notice_main_work,
                job_data.notice_qualification,
                job_data.notice_preferred_qualification,
                job_data.notice_welfare,
                job_data.notice_category,
                job_data.notice_end_date,
                job_data.notice_tech_stack,
                job_data.notice_url
            ))
            
            conn.commit()
            print("데이터 저장 완료")
            
        except Exception as e:
            print(f"데이터 저장 중 에러 발생: {str(e)}")
            conn.rollback()
        
        finally:
            conn.close()
    
    def extract_job_info(self, job_detail: Dict[str, List[Dict[str, str]]]) -> JobData:
        job_data = JobData(company_id=0, notice_job_category='')
        
        def extract_from_content(content: Dict[str, str]) -> None:
            title = content['title'].lower() if content.get('title') else ''
            content_text = content.get('content', '')
            
            if not title:
                return
                
            if any(keyword in title for keyword in ['주요업무', '담당업무']):
                if not job_data.notice_main_work:  # 값이 없을 때만 저장
                    job_data.notice_main_work = content_text
            elif any(keyword in title for keyword in ['자격요건', '필수요건', '지원자격', '자격사항']):
                if not job_data.notice_qualification:
                    job_data.notice_qualification = content_text
            elif any(keyword in title for keyword in ['우대사항', '우대조건', '우대해요']):
                if not job_data.notice_preferred_qualification:
                    job_data.notice_preferred_qualification = content_text
            elif any(keyword in title for keyword in ['혜택', '복지', '처우', '혜택 및 복지']):
                if not job_data.notice_welfare:
                    job_data.notice_welfare = content_text
            elif any(keyword in title for keyword in ['채용', '전형', '프로세스']):
                if not job_data.notice_category:
                    job_data.notice_category = content_text
        
        # h2 태그에서 정보 추출
        for content in job_detail.get('h2_contents', []):
            extract_from_content(content)
            
        # h3 태그에서 정보 추출 (h2에서 찾지 못한 정보가 있다면)
        for content in job_detail.get('h3_contents', []):
            extract_from_content(content)
        
        if job_detail.get('h1_contents'):
            job_data.notice_title = job_detail['h1_contents'][0].get('title', '')
        
        # 마감일, 근무위치, 기술 스택, 경력 정보 설정
        job_data.notice_end_date = job_detail.get('end_date', '')
        job_data.notice_location = job_detail.get('location', '')
        job_data.notice_tech_stack = job_detail.get('tech_stack', '')
        job_data.notice_career = job_detail.get('career', '')
        
        return job_data
    
    def run(self) -> None:
        self.setup_database()
        url = "https://www.wanted.co.kr/wdlist/518/1634?country=kr&job_sort=job.latest_order&years=-1&selected=1634&locations=all"
        
        try:
            print("페이지 접속 중...")
            self.driver.get(url)
            
            self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "JobList_JobList__contentWrapper__QuyH1"))
            )
            print("페이지 로드 완료")
            
            print("모든 공고를 로드하는 중...")
            self.scroll_to_bottom()
            print("모든 공고 로드 완료")
            
            job_cards = self._find_elements(By.CSS_SELECTOR, "div[data-cy='job-card']")
            
            for idx, card in enumerate(job_cards, 1):
                try:
                    a_tag = card.find_element(By.TAG_NAME, "a")
                    company_id = a_tag.get_attribute("data-company-id")
                    company_name = a_tag.get_attribute("data-company-name")
                    href = a_tag.get_attribute("href")
                    
                    # 직무 카테고리 추출
                    try:
                        job_category_element = self._find_element(By.CLASS_NAME, "FilterSelect_FilterSelect__title__iSg1w")
                        position_name = job_category_element.text.strip() if job_category_element else ""
                    except:
                        position_name = ""
                    
                    print(f"\n=== {idx}번째 공고 처리 중 ===")
                    print(f"회사명: {company_name}")
                    print(f"포지션: {position_name}")
                    
                    job_detail = self.get_job_detail(href)
                    if job_detail:
                        job_info = self.extract_job_info(job_detail)
                        job_data = JobData(
                            company_id=int(company_id),
                            notice_job_category=position_name.replace("개발・", ""),
                            notice_location=job_info.notice_location,
                            notice_career=job_info.notice_career,
                            notice_title=job_info.notice_title,
                            notice_position=position_name.replace("개발・", ""),
                            notice_main_work=job_info.notice_main_work,
                            notice_qualification=job_info.notice_qualification,
                            notice_preferred_qualification=job_info.notice_preferred_qualification,
                            notice_welfare=job_info.notice_welfare,
                            notice_category=job_info.notice_category,
                            notice_end_date=job_info.notice_end_date,
                            notice_tech_stack=job_info.notice_tech_stack,
                            notice_url=href
                        )
                        
                        company_info = self.get_company_info(company_id)
                        if company_info:
                            company_info.company_name = company_name
                            company_info.company_location = job_info.notice_location
                            
                            for h2 in job_detail['h2_contents']:
                                if h2['title'] == "태그" and 'tags' in h2:
                                    company_info.company_tag = h2['tags']
                                    break
                            
                            self.save_to_database(company_info, job_data)
                            
                            # 저장된 정보 출력
                            print("\n=== 저장된 정보 ===")
                            print("회사 정보:")
                            print(f"  - 회사 ID: {company_info.company_id}")
                            print(f"  - 회사명: {company_info.company_name}")
                            print(f"  - 회사 태그: {company_info.company_tag}")
                            print(f"  - 회사 위치: {company_info.company_location}")
                            print(f"  - 회사 연봉: {company_info.company_salary}")
                            print(f"  - 회사 인원수: {company_info.company_headcount}")
                            print(f"  - 회사 매출: {company_info.company_revenue}")
                            print(f"  - 회사 정보: {company_info.company_info}")
                            
                            print("\n공고 정보:")
                            print(f"  - 공고 제목: {job_data.notice_title}")
                            print(f"  - 직무 카테고리: {job_data.notice_job_category}")
                            print(f"  - 근무 위치: {job_data.notice_location}")
                            print(f"  - 경력: {job_data.notice_career}")
                            print(f"  - 주요 업무: {job_data.notice_main_work}")
                            print(f"  - 자격 요건: {job_data.notice_qualification}")
                            print(f"  - 우대 사항: {job_data.notice_preferred_qualification}")
                            print(f"  - 복지: {job_data.notice_welfare}")
                            print(f"  - 채용 전형: {job_data.notice_category}")
                            print(f"  - 마감일: {job_data.notice_end_date}")
                            print(f"  - 기술 스택: {job_data.notice_tech_stack}")
                            print(f"  - 공고 URL: {job_data.notice_url}")
                            print("==================\n")
                
                except Exception as e:
                    print(f"{idx}번째 공고 정보를 가져오는 중 에러 발생: {str(e)}")
                    continue
        
        except Exception as e:
            print(f"에러 발생: {str(e)}")
        
        finally:
            self.driver.quit()
            print("드라이버 종료")

if __name__ == "__main__":
    crawler = WantedCrawler()
    crawler.run() 
