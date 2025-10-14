import sqlite3
import re
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer, util

def connect_db():
    conn = sqlite3.connect('job_applications.db')
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

"""def extract_keywords(texts, top_n=20):
    kw_model = KeyBERT()
    
    if isinstance(texts, str):  
        texts = [texts]
    
    all_keywords = []
    for text in texts:
        keywords = kw_model.extract_keywords(text, top_n=top_n, stop_words='english')
        all_keywords.append([kw[0] for kw in keywords])
    return all_keywords"""

def update_schema_with_keywords():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(job_postings)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'keywords' not in columns:
        cursor.execute("ALTER TABLE job_postings ADD COLUMN keywords TEXT")
        print("keywords column added to job_postings.")
    else:
        print("keywords column already exists in job_postings.")
    conn.commit()
    conn.close()

"""def store_keywords_for_job(job_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT description FROM job_postings WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    if row:
        description = row[0]
        keywords = extract_keywords(description)[0]
        keyword_str = ','.join(keywords)
        cursor.execute("UPDATE job_postings SET keywords = ? WHERE id = ?", (keyword_str, job_id))
        conn.commit()
    conn.close()

def store_keywords_for_all_jobs():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM job_postings")
    job_ids = [row[0] for row in cursor.fetchall()]
    conn.close()

    for job_id in job_ids:
        store_keywords_for_job(job_id)"""

def clean_text(text):
    text = text.lower()
    text = re.sub(r'[-]', ' ', text)  
    text = re.sub(r'[^\w\s]', '', text)
    return text

def match_resume_to_jobs(resume_text):
    resume_text = clean_text(resume_text)
    resume_words = set(resume_text.split())

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, keywords FROM job_postings WHERE keywords IS NOT NULL")
    jobs = cursor.fetchall()
    conn.close()

    matches = []
    for job_id, title, keyword_str in jobs:
        job_keywords = set(clean_text(keyword_str).split(','))
        overlap = resume_words.intersection(job_keywords)

        print(f"\nJob: {title}")
        print(f"Resume words: {list(resume_words)[:10]}...")
        print(f"Job keywords: {list(job_keywords)}")
        print(f"Overlap: {list(overlap)}")

        match_score = round(len(overlap) / len(job_keywords) * 100, 2) if job_keywords else 0
        matches.append({'job_id': job_id, 'title': title, 'match_score': match_score})

    print("\nFinal matched jobs:", matches)
    return sorted(matches, key=lambda x: x['match_score'], reverse=True)


def match_resume_to_jobs(resume_text):
    model = SentenceTransformer('all-MiniLM-L6-v2')  # Fast, lightweight, no TensorFlow
    resume_embedding = model.encode(resume_text, convert_to_tensor=True)

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, description FROM job_postings")
    jobs = cursor.fetchall()
    conn.close()

    matches = []
    for job_id, title, description in jobs:
        job_embedding = model.encode(description, convert_to_tensor=True)
        similarity = util.cos_sim(resume_embedding, job_embedding).item()
        match_score = round(similarity * 100, 2)

        matches.append({
            'job_id': job_id,
            'title': title,
            'match_score': match_score
        })

    return sorted(matches, key=lambda x: x['match_score'], reverse=True)
