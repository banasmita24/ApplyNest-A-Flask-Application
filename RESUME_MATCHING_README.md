# Resume-Job Match Scoring System

This document describes the new Resume-Job Match Scoring system added to the ApplyNest Flask application.

## Features

### 1. Resume Text Extraction
- Supports PDF files using PyPDF2
- Supports DOCX files using python-docx
- Automatic text cleaning and preprocessing
- Handles various file formats commonly used for resumes

### 2. TF-IDF Similarity Scoring
- Uses scikit-learn's TfidfVectorizer for text analysis
- Calculates cosine similarity between resume and job description
- Generates match scores as percentages (0-100%)
- Considers n-grams (1-2 words) for better matching

### 3. Database Integration
- Added `match_score` column to `job_applications` table
- Added `status` column with default value 'Pending'
- Automatic score calculation during application submission

### 4. Admin Dashboard Enhancements
- **Match Score Column**: Displays color-coded match scores
  - Green (70%+): High match
  - Yellow (50-69%): Medium match  
  - Red (<50%): Low match
- **Sorting Options**: Sort by match score, name, email, job title, or status
- **Order Control**: Ascending or descending order
- **Recalculate Scores**: Button to recalculate scores for existing applications

### 5. User Experience Improvements
- Real-time match score display after application submission
- Clear file format requirements (PDF, DOC, DOCX)
- Visual feedback with color-coded scores

## Installation

1. Install the new dependencies:
```bash
pip install -r requirements.txt
```

2. The database will automatically update with the new schema when you run the application.

## Usage

### For Users
1. Apply for jobs as usual
2. Upload resume in PDF, DOC, or DOCX format
3. Receive immediate feedback on match score
4. View your applications in the user dashboard

### For Admins
1. View applications sorted by match score by default
2. Use sorting controls to organize applications
3. Click "Recalculate Scores" if job descriptions are updated
4. Quickly identify top candidates using color-coded scores

## Technical Details

### Resume Processing
- Text extraction handles various PDF and DOCX formats
- Preprocessing removes special characters and normalizes text
- TF-IDF vectorization with English stop words removal
- Cosine similarity calculation for final scoring

### Performance Considerations
- Scores are calculated during application submission
- Caching of vectorizer for better performance
- Batch processing available for score recalculation

### Error Handling
- Graceful handling of unsupported file formats
- Fallback to 0% score if text extraction fails
- User-friendly error messages

## File Structure

- `resume_processor.py`: Core resume processing and scoring logic
- `app.py`: Updated with scoring integration and new routes
- `forms.py`: Enhanced file upload form
- `templates/admin_dashboard.html`: Updated with match score display and sorting
- `test_resume_processor.py`: Test script for the processor

## Future Enhancements

- Support for more file formats (RTF, TXT)
- Advanced NLP features (named entity recognition)
- Machine learning model integration
- Bulk score recalculation
- Score history tracking
- Custom scoring weights for different job types
