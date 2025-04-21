from bs4 import BeautifulSoup
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import sys, os, re
from notice.models import JobNotice, Company
import time

de_tech = [
    "Python","SQL","Java","Scala","Bash", "Trino", "Keras", "ArgoCD", "Hudi", "Iceberg", "Kotlin", "Databricks", "MSK", "Shell Scripting","Tensorflow", "Pytorch", "Excel", "Tableau","R","Go","RDBMS","PostgreSQL","MySQL","Oracle","SQL Server","SQLite","MariaDB","NoSQL","MongoDB","Cassandra","Redis","HBase","Couchbase","DynamoDB","Cosmos DB","Data Warehouse","Redshift","BigQuery","Snowflake","Synapse Analytics","Teradata","Vertica","Hive","Data Lake","S3","GCS","HDFS","Spark","PySpark","Spark Streaming","kafka", "Flink","MapReduce","Pig","NiFi","StreamSets","Stitch","Fivetran","Matillion","Talend","Informatica","DataStage","Glue","Azure","GCP","dbt","CDC","Debezium","Striim","Kafka","Airflow","Luigi","Azkaban","AWS","GCP","EC2","RDS","EMR","Datahub","Redash", "Superset","Kinesis","VPC","IAM","HDInsight","Data Modeling","Data Governance","Alation", "Collibra", "Apache Atlas", "Hadoop", "YARN", "ZooKeeper", "Avro", "Parquet", "CI/CD","Jenkins","CircleCI","Docker","Kubernetes","ECS", "EKS", "AKS", "GKE", "Prometheus","Grafana","ELK", "Elasticsearch","Logstash","Athena","Kibana","CloudWatch","Datadog", "Splunk", "Monitoring","Terraform","Pulumi", "Ansible", "API", "REST","Git", "MLOps"
]

# Find Tech Stack
def preprocess(text):
    # 영단어와 한글 조사 분리: "Hadoop과" → "Hadoop 과"
    text = re.sub(r'([a-zA-Z]+)(?=[가-힣])', r'\1 ', text)
    # 특수문자 제거 후 소문자로 변환
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    return text

def find_tech(text, techlist):
    find_text = preprocess(text)
    find_text_set = set(find_text.split())
    rtn_list = set()

    for item in techlist:
        if item.lower() in find_text_set:
            rtn_list.add(item)

    return list(rtn_list)

def scroll_to_bottom(driver, pause_time=0.5):
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        # 스크롤 맨 아래로 이동
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # 로딩 대기
        time.sleep(pause_time)

        # 새로운 높이 확인
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break  # 더 이상 로딩된 콘텐츠가 없을 경우 종료
        last_height = new_height

def find_content(h3):
    parent_div = h3.find_parent('div')
    div_inner1 = parent_div.find('span')
    div_inner2 = div_inner1.find('span')
    content = div_inner2.get_text(separator="\n").strip()
    
    return content

def get_company_info(driver, company_link):
    driver.get(company_link)
    time.sleep(0.5)
    try:
        # 회사 정보 추출
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        company_id = int(company_link.rstrip('/').split('/')[-1])
        
        company_info_wrapper = soup.find('div', {'data-testid': 'company-info'})
        company_name_tag = company_info_wrapper.find('h1') if company_info_wrapper else None
        company_name = company_name_tag.text.strip() if company_name_tag else None
        
        tag_container = soup.find('div', class_=re.compile(r'CompanyTags_CompanyTags__'))
        company_tag = []
        if tag_container is not None:
            tag_inners = tag_container.find_all('button')
            company_tag = [tag.text for tag in tag_inners]
        
        salary_container = soup.find('div', class_=re.compile(r'HiredAverageSalaryChart_wrapper__chartContents__'))
        salary_inner1 = salary_container.find_all('div')[0]
        salary_inner2 = salary_inner1.find('div')
        company_salary = salary_inner2.find('div').text
        
        # 위치 요소를 찾을 때까지 명시적으로 대기
        location_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='HiredAverageSalaryChart_wrapper__chartContents__']"))
        )
        
        # ActionChains를 사용한 스크롤
        actions = ActionChains(driver)
        actions.move_to_element(location_element)
        actions.perform()
        
        # 스크롤 후 잠시 대기
        time.sleep(0.5)
        
        # BeautifulSoup으로 업데이트된 페이지 소스 파싱
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        location_container = soup.find('span', class_=re.compile(r'CompanyLocation_CompanyLocation__Address__'))
        company_location = location_container.text if location_container else ''
        
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        headcount_container = soup.find('div', class_=re.compile(r'EmployeeLineChart_wrapper__'))
        headcount_inner = headcount_container.find_all('div')[0]
        headcount_inner2 = headcount_inner.find('div')
        company_headcount = headcount_inner2.find('div').text
        
        
        revenue_container = soup.find('div', class_=re.compile(r'SalesChart_wrapper__'))
        if revenue_container is None:
            company_revenue = ''
        else:
            revenue_inner = revenue_container.find_all('div')[0]
            revenue_inner2 = revenue_inner.find('div')
            company_revenue = revenue_inner2.find('div').text
        
        company_info = dict()
        info_container = soup.find('div', class_=re.compile(r'CompanyInfoTable_wrapper__'))
        if info_container is not None :
            info_inners = info_container.find_all('dl')
            for i in info_inners:
                company_info[i.find('dt').text] = i.find('dd').text
        
        # 추출한 정보 저장
        company = Company.objects.update_or_create(
            company_id=company_id,
            defaults={
                'company_name': company_name,
                'company_tag': company_tag,
                'company_salary': company_salary,
                'company_location': company_location,
                'company_headcount': company_headcount,
                'company_revenue': company_revenue,
                'company_info': company_info  
            }
        )

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(f'company_id: {str(company_id)}')
        print(f'file name: {str(fname)}')
        print(f'error type: {str(exc_type)}')
        print(f'error msg: {str(e)}')
        print(f'line number: {str(exc_tb.tb_lineno)}')
        return False

    return True
    
def get_job_notice_info(driver, job_link, category):
    # 회사 정보 추출
    driver.get(job_link)
    
    try:
        # 예시로 직무명을 찾을 때까지 기다림
        company_page = driver.find_element(By.CSS_SELECTOR, 'a[data-attribute-id="company__click"]')  # 회사 페이지 요소의 CSS_SELECTOR
        company_link = company_page.get_attribute('href')
        get_company_info(driver, company_link)  # 회사 정보 추출 함수 호출
        time.sleep(0.5)
        driver.get(job_link)
        wait = WebDriverWait(driver, 10)
        button = wait.until(EC.element_to_be_clickable(
            (By.XPATH, '//*[starts-with(@class, "Button_Button__root__")]')
        ))
        button.click()
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # notice_id
        notice_id = int(job_link.rstrip('/').split('/')[-1])
        
        # company_id
        company_id = int(company_link.rstrip('/').split('/')[-1])
        
        # notice_job_category
        notice_job_category = category
        
        # notice_location, notice_career 
        location_career = soup.find_all('span', class_=re.compile(r'JobHeader_JobHeader__Tools__Company__Info__'))
        notice_location = location_career[0].text.strip()
        notice_career = location_career[1].text.strip()
        
        # notice_title
        tile_container = soup.find('header', class_=re.compile(r'JobHeader_JobHeader__'))
        notice_title = tile_container.find('h1').text.strip()
        
        # notice_position
        jobdescription_container = soup.find('div', class_=re.compile(r'JobDescription_JobDescription__paragraph__wrapper__'))
        position_inner1 = jobdescription_container.find('span')
        position_inner2 = position_inner1.find('span')
        notice_position = position_inner2.get_text(separator="\n").strip()
        
        notice_main_work = ''
        notice_qualification = ''
        notice_preferred_qualification = ''
        notice_welfare = ''
        notice_category = ''
        
        
        # 포지션 상세 내용
        for h3 in jobdescription_container.find_all('h3'):
            if h3.text.strip() == '주요업무':
                content = find_content(h3)
                notice_main_work = content
            elif h3.text.strip() == '자격요건':
                content = find_content(h3)
                notice_qualification = content
            elif h3.text.strip() == '우대사항':
                content = find_content(h3)
                notice_preferred_qualification = content
            elif h3.text.strip() == '혜택 및 복지':
                content = find_content(h3)
                notice_welfare = content
            elif h3.text.strip() == '채용 전형':
                content = find_content(h3)
                notice_category = content
        
        # 주요업무, 자격요건, 우대사항 내부의 기술스택들을 notice_tech_stack에 추가 필요
        tech_set = set()
        tech_set.update(find_tech(notice_main_work, de_tech))
        tech_set.update(find_tech(notice_qualification, de_tech))
        tech_set.update(find_tech(notice_preferred_qualification, de_tech))
        
        # notice_end_date
        end_date_container = soup.find('article', class_=re.compile(r'JobDueTime_JobDueTime__'))
        notice_end_date = end_date_container.find('span').text.strip()
        
        # notice_tech_stack
        notice_tech_list = []
        notice_tech_stack = ''
        tech_stack_container = soup.find_all('li', class_=re.compile(r'SkillTagItem_SkillTagItem__'))
        if len(tech_stack_container) == 0:
            notice_tech_stack = ''
        else:
            for li in tech_stack_container:
                tech_stack = li.find('span').text.strip()
                notice_tech_list.append(tech_stack)
                # notice_tech_stack += tech_stack + '\n'
        tech_set.update(notice_tech_list)
        notice_tech_stack = '\n'.join(tech_set)
        print(f'notice_tech_stack : {notice_tech_stack}')

        # notice_url
        notice_url = job_link
        
        # DB Insert
        jobnotice, created = JobNotice.objects.update_or_create(
            notice_id=notice_id,
            defaults={
                'company_id' : company_id,
                'notice_job_category' : notice_job_category,
                'notice_location' : notice_location,
                'notice_career' : notice_career,
                'notice_title' : notice_title,
                'notice_position' : notice_position,
                'notice_main_work' : notice_main_work,
                'notice_qualification' : notice_qualification,
                'notice_preferred_qualification' : notice_preferred_qualification,
                'notice_welfare' : notice_welfare,
                'notice_category' : notice_category,
                'notice_end_date' : notice_end_date,
                'notice_tech_stack' : notice_tech_stack,
                'notice_url' : notice_url
            }
        )
        print(f"Created: {created}")

        time.sleep(0.5)  # 각 페이지 간 잠시 대기

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(f'notice_id: {str(notice_id)}')
        print(f'file name: {str(fname)}')
        print(f'error type: {str(exc_type)}')
        print(f'error msg: {str(e)}')
        print(f'line number: {str(exc_tb.tb_lineno)}')
        return False
    
    return True

def crawler_run():
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.implicitly_wait(10)
    driver.maximize_window()

    driver.get("https://www.wanted.co.kr/wdlist/518/1025?country=kr&job_sort=job.latest_order&years=-1&locations=all")
    time.sleep(2)
    scroll_to_bottom(driver)

    job_cards = driver.find_elements(By.CSS_SELECTOR, 'a[data-attribute-id="position__click"]')
    links = [card.get_attribute('href') for card in job_cards]
    category = '빅데이터 엔지니어'

    print(f"총 {len(job_cards)}개의 공고 발견")
    
    for link in links:
        get_job_notice_info(driver, link, category)
        
    # get_job_notice_info(driver, 'https://www.wanted.co.kr/wd/275870', '빅데이터 엔지니어')
    # get_company_info(driver, 'https://www.wanted.co.kr/company/2331')

    