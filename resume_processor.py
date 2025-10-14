import os
import PyPDF2
from docx import Document
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class ResumeProcessor:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            max_features=1000
        )
    
    def extract_text_from_pdf(self, file_path):
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return self.clean_text(text)
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""
    
    def extract_text_from_docx(self, file_path):
        """Extract text from DOCX file"""
        try:
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return self.clean_text(text)
        except Exception as e:
            print(f"Error extracting text from DOCX: {e}")
            return ""
    
    def extract_text_from_file(self, file_path):
        """Extract text from resume file based on extension"""
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif file_extension in ['.doc', '.docx']:
            return self.extract_text_from_docx(file_path)
        else:
            print(f"Unsupported file format: {file_extension}")
            return ""
    
    def clean_text(self, text):
        """Clean and preprocess text"""
        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep alphanumeric and spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        # Convert to lowercase
        text = text.lower().strip()
        return text
    
    def calculate_similarity(self, resume_text, job_description):
        """Calculate similarity score between resume and job description"""
        if not resume_text or not job_description:
            return 0.0
        
        try:
            # Combine resume and job description for vectorization
            documents = [resume_text, job_description]
            
            # Fit and transform the documents
            tfidf_matrix = self.vectorizer.fit_transform(documents)
            
            # Calculate cosine similarity
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            # Convert to percentage (0-100)
            return round(similarity * 100, 2)
        except Exception as e:
            print(f"Error calculating similarity: {e}")
            return 0.0
    
    def process_resume(self, file_path, job_description):
        """Process resume file and calculate match score"""
        # Extract text from resume
        resume_text = self.extract_text_from_file(file_path)
        
        if not resume_text:
            return 0.0, "Could not extract text from resume"
        
        # Calculate similarity score
        match_score = self.calculate_similarity(resume_text, job_description)
        
        return match_score, "Success"
