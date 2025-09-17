# Onboarding Scoping Review

## Overview
This repository includes the scripts used to run the scoping review "Onboarding Practices in Anesthesiology: Agent-Augmented Scoping Review”.

## Installation & Setup

### Prerequisites
- Python 3.7+
- Required packages (install via pip):

```bash
pip install streamlit requests pandas sqlite3
```

### Optional for Enhanced Features
```bash
pip install plotly  # For advanced charts
```
## Worfklow of the scoping review
### 1. Run Pubmed Search and Screening
```bash
python 01_dual_llm_pubmed_analysis.py --query '"anesthesiology" AND ("onboarding" OR "orientation")' --start_date "2020/01/01" --end_date "2025/05/01" --total_limit 100
```
### 2. Merge different screening results and exclude search items that did not reach consensus threshold.
```bash
python 02_merge_csv_multiple.py --folder ./csv_files --threshold 3 --match_columns ClaudiaIsRelated OpenAIIsRelated --match_value True
```

### 3. Download PDF files related to the included articles. Please provide the PubMed link, PMC link, and DOI (Example: pubmed_create_csv_file_to_in_depth_analyse.csv).
```bash
python 03_pubmed_download_pdf_from_elsevier_to_analyse.py --output_folder ./pubmed_pdfs/ --csv_file pubmed_create_csv_file_to_in_depth_analyse.csv
```

### 4. Run GUI for Evaluation Assessment of the included articles.
```bash
./04_run_improved_app.bat
```
### 5. Import the citation information of included articles into EndNote.
```bash
python 05_export_to_endnote.py --input_csv merged_output.csv --pdf_dir pubmed_pdfs --output_enw endnote_import/output.enw
```
## Usage of GUI for Evaluation Assessment of Articles
### 1. Start the Application
```bash
./04_run_improved_app.bat
```


### 2. Configure Your Profile
1. Enter your name in the sidebar
2. Select your analysis domain
3. Choose your preferred AI model

### 3. Manage Criteria
1. Click "📝 Criteria" in the sidebar
2. **View**: Browse existing criteria by domain
3. **Add New**: Create custom criteria with detailed evaluation guides
4. **Manage**: Edit or delete existing criteria

### 4. Manage Prompts
1. Click "✏️ Prompts" in the sidebar
2. **Templates**: Browse and load existing prompt templates
3. **Create New**: Design custom prompts for specific analysis needs
4. **Manage**: Edit, load, or delete prompt templates

### 5. Analyze Documents
1. Return to main interface
2. Upload PDF documents
3. Select evaluation criteria
4. Configure analysis settings
5. Click "🚀 Start Analysis"
6. Review results and save to database

### 6. View Analytics
1. Click "📊 Analytics" in the sidebar
2. View overall statistics
3. Analyze domain-specific trends
4. Review historical data

## Key Features

### 🎯 **Domain-Specific Analysis**
- **General**: Basic quality, clarity, relevance
- **Healthcare**: Clinical relevance, evidence quality, safety
- **Technology**: Technical accuracy, innovation, feasibility
- **Business**: Market analysis, financial viability
- **Legal**: Compliance, precedent analysis
- **Education**: Pedagogical effectiveness, clarity

### 🤖 **AI Model Support**
- **Claude**: Advanced reasoning and analysis
- **OpenAI**: GPT-based document understanding
- **Gemini**: Google's multimodal AI

### 📊 **Comprehensive Scoring**
- 0-5 scale scoring system
- Detailed justifications for each score
- Overall quality assessment
- Confidence level indicators

### 💾 **Data Management**
- SQLite database for reliable storage
- Export capabilities for results
- Historical analysis tracking
- Backup and restore functionality

## API Configuration

The application expects an API endpoint at `http://localhost:8000/analyze` that accepts:
- `file`: PDF document
- `system_prompt`: AI system instructions
- `user_prompt`: Analysis instructions
- `model`: AI model to use

Update the `API_URL` variable in the code to match your API endpoint.

## Database Schema

The application creates three main tables:
- `criteria`: Evaluation criteria definitions
- `prompt_templates`: Reusable prompt templates
- `reviews`: Analysis results and metadata

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure all required packages are installed
   - Use `pip install -r requirements.txt` if available

2. **Database Issues**
   - Delete `review_system.db` to reset the database
   - Check file permissions in the application directory

3. **API Connection**
   - Verify the API endpoint is running
   - Check network connectivity
   - Update `API_URL` if needed

4. **Performance Issues**
   - For large documents, increase timeout values
   - Consider using "Quick" analysis depth for faster processing

### Support
For additional support or feature requests, check the application logs and error messages for specific guidance.

## Future Enhancements

- 📧 Email notifications for completed analyses
- 🔄 Batch export/import of criteria and templates
- 📈 Advanced analytics with trend analysis
- 🌐 Multi-language support
- 🔐 User authentication and role management
- ☁️ Cloud storage integration
