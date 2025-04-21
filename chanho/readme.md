## 🗃️ 업무 및 우대사항 내 기술 스택 추출

### 📌 `de_tech` 리스트
- **역할**: 크롤링한 공고의 기술 스택에서 유효한 기술 키워드를 추출할 때 비교 기준으로 사용하는 리스트입니다.
- **구성**: Python, Java, SQL, AWS, Kafka, Hadoop 등 **데이터 엔지니어링 및 백엔드 중심 기술**로 구성됩니다.
- **위치**: `wanted_crawler.py` 최상단 혹은 별도 config 파일에서 정의

- de_tech = ['Python', 'Java', 'SQL', 'AWS', 'Kafka', 'Spark', 'Airflow', 'Docker', 'Hadoop', 'Kubernetes', ...]


### 📌 `def preprocess(text: str)` 함수
- **역할**: 영단어와 한글 분리, 특수문자 제거 등의 역할을 하는 함수


### 📌 `def find_tech(text: str, tech_list: list)` 함수
- **역할**: 전처리된 공고 본문 텍스트에서 기술 키워드를 추출 -> tech_list에 있는 기술 스택을 기준으로 텍스트에서 존재 여부 확인 -> 일치하는 기술명을 리스트로 반환

### 📌 `find_tech 적용 위치`
```
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


    # 기술 스택 저장
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
    
    # 공고의 모든 기술 스택을 set에 저장 후 \n구분자로 구분하여 저장
    tech_set.update(notice_tech_list)
    notice_tech_stack = '\n'.join(tech_set)
    print(f'notice_tech_stack : {notice_tech_stack}')

```