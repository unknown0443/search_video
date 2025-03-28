import psycopg2

def get_db_connection():
    """PostgreSQL DB 연결."""
    return psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="1234",  # 실제 비밀번호로 교체하세요.
        host="localhost",
        port="5432"
    )

MEMBER_NAME_MAP = {
    # Gang Harin
    "강해린": ["Gang Harin"],
    "해린": ["Gang Harin"],
    "고양이": ["Gang Harin"],

    # Kim Minji
    "김민지": ["Kim Minji"],
    "민지": ["Kim Minji"],
    "킴민지": ["Kim Minji"],

    # Pham Hanni
    "팜하니": ["Pham Hanni"],
    "하니": ["Pham Hanni"],
    "하니팜": ["Pham Hanni"],

    # Danielle
    "다니엘": ["Danielle"],
    "다니": ["Danielle"],

    
}

def get_standard_names(korean_name):
    """
    입력된 한국어 이름을 표준 영어 이름 리스트로 반환.
    매핑이 없으면, 원래 이름을 리스트로 반환.
    """
    return MEMBER_NAME_MAP.get(korean_name, [korean_name])

def format_hhmmss(seconds):
    """정수 초를 시:분:초 문자열(00:00:00)로 변환"""
    sec = int(seconds)
    hh = sec // 3600
    mm = (sec % 3600) // 60
    ss = sec % 60
    return f"{hh:02d}:{mm:02d}:{ss:02d}"
