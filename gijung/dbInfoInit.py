import sqlite3
import os
import datetime
# NOTICE_INFO_COLUM = {
#     '공고PK':'notice_id',
#     '회사PK':'company_id',
#     '직무분야':'notice_job_category',
#     '근무지역':'notice_location',
#     '경력사항':'notice_career',
#     '공고제목':'notice_title',
#     '포지션상세':'notice_position',
#     '주요업무':'notice_main_work',
#     '자격요건':'notice_qualification',
#     '우대사항':'notice_preferred_qualification',
#     '혜택 및 복지':'notice_welfare',
#     '채용 전형':'notice_category',
#     '마감일':'notice_end_date',
#     '기술 스택 • 툴':'notice_tech_stack',
#     '공고URL':'notice_url',
#     '등록일시':'reg_dt',
#     '수정일시':'mod_dt'
# }

# COMPANY_INFO_COLUM = {
#     '회사PK':'company_id',
#     '회사명':'company_name',
#     '태그':'company_tag',
#     '연봉':'company_salary',
#     '위치':'company_location',
#     '인원':'company_headcount',
#     '매출':'company_revenue',
#     '기업정보':'company_info',
#     '등록일시':'reg_dt',
#     '수정일시':'mod_dt'
# }

db_name = 'wanted.db'
current_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_dir, db_name)

with sqlite3.connect(db_path) as con:
    cur = con.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS notice_info (
        notice_id TEXT PRIMARY KEY,
        company_id TEXT,
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
        reg_dt TEXT,
        mod_dt TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS company_info (
        company_id TEXT PRIMARY KEY,
        company_name TEXT,
        company_tag TEXT,
        company_salary TEXT,
        company_location TEXT,
        company_headcount TEXT,
        company_revenue TEXT,
        company_info TEXT,
        reg_dt TEXT,
        mod_dt TEXT
        )
    ''')
    con.commit()
