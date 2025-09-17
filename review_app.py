import streamlit as st
import requests
import json
import sqlite3
import os
import pandas as pd
import time
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# --- Page Configuration ---
st.set_page_config(
    page_title="Smart Document Review System",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)
# save logging file
if not os.path.exists("./logs"):
    os.makedirs("./logs")
logging.basicConfig(filename='./logs/review_app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger("streamlit").setLevel(logging.ERROR)  # Suppress Streamlit's default logging

def log_event(event: str, details: dict = None, level: str = "info"):
    """
    Log an event with optional details.
    Args:
        event (str): Event name or message.
        details (dict, optional): Additional details to log.
        level (str): Logging level ("info", "warning", "error", "debug").
    """
    msg = event
    if details:
        msg += " | " + json.dumps(details, default=str)
    if level == "info":
        logging.info(msg)
    elif level == "warning":
        logging.warning(msg)
    elif level == "error":
        logging.error(msg)
    elif level == "debug":
        logging.debug(msg)
    else:
        logging.info(msg)
# --- Custom CSS ---
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
    }
    .card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #e0e7ff;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    }
    .criteria-card {
        border-left: 4px solid #667eea;
        background: linear-gradient(135deg, #f8faff 0%, #e0e7ff 100%);
    }
    .metric-card {
        text-align: center;
        background: linear-gradient(135deg, #f0f4ff 0%, #ddd6fe 100%);
    }
    .stButton > button {
        border-radius: 8px;
        border: none;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    .success-message {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    .warning-message {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #ffc107;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# --- Configuration ---
API_URL = "http://localhost:8000/analyze"  # Update with your API URL

# --- Session State Initialization ---
def init_session_state():
    """Initialize session state variables"""
    defaults = {
        "system_prompt": "You are an expert document reviewer with extensive knowledge across multiple domains. Provide thorough, objective analysis in JSON format.",
        "user_prompt": "Analyze this document and provide structured evaluation with scores (0-5) for each criterion.",
        "selected_criteria": [],
        "batch_results": [],
        "analyzing": False,
        "current_page": "main",
        "domain": "General",
        "model": "claude",
        "reviewer_name": os.getenv("USER", "Anonymous"),
        "cancel_analysis": False,
        "show_analytics": False,
        "show_prompt_modal": False,
        "analysis_depth": "Standard",
        "document_type": "Research Paper",
        "session_id": str(uuid.uuid4())  # Generate unique session ID
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# --- Database Setup ---
@st.cache_resource
def init_database():
    """Initialize SQLite database with proper schema"""
    db_path = "review_system.db"
    conn = sqlite3.connect(db_path, check_same_thread=False)
    
    # Create tables with improved schema
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS criteria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            evaluation_guide TEXT NOT NULL,
            domain TEXT NOT NULL,
            created_by TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            UNIQUE(name, domain)
        );
        
        CREATE TABLE IF NOT EXISTS prompt_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            system_prompt TEXT NOT NULL,
            user_prompt TEXT NOT NULL,
            description TEXT,
            domain TEXT,
            created_by TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        );
        
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            reviewer TEXT NOT NULL,
            domain TEXT NOT NULL,
            document_type TEXT NOT NULL,
            model_used TEXT NOT NULL,
            analysis_data TEXT NOT NULL,
            overall_score REAL,
            review_quality REAL DEFAULT 0,
            review_comment TEXT,
            session_id TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS domains (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            color TEXT DEFAULT '#1f77b4',
            created_by TEXT NOT NULL,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        );
        
        CREATE INDEX IF NOT EXISTS idx_criteria_domain ON criteria(domain);
        CREATE INDEX IF NOT EXISTS idx_reviews_date ON reviews(created_date);
        CREATE INDEX IF NOT EXISTS idx_reviews_domain ON reviews(domain);
    """)
    
    # Migration: Add session_id column if it doesn't exist
    try:
        # Check if session_id column exists
        cursor = conn.execute("PRAGMA table_info(reviews)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'session_id' not in columns:
            st.info("🔄 Migrating database: Adding session_id column to reviews table...")
            conn.execute("ALTER TABLE reviews ADD COLUMN session_id TEXT")
            conn.commit()
            st.success("✅ Database migration completed successfully!")
    except Exception as e:
        st.warning(f"⚠️ Database migration note: {e}")
    
    conn.commit()
    return conn

conn = init_database()

# --- Database Manager Class ---
class DatabaseManager:
    def __init__(self, connection):
        self.conn = connection

    def get_criteria(self, domain: Optional[str] = None) -> List[Tuple]:
        """Get criteria from database"""
        if domain:
            query = "SELECT id, name, description, evaluation_guide FROM criteria WHERE domain = ? AND is_active = TRUE ORDER BY name"
            rows = self.conn.execute(query, (domain,)).fetchall()
        else:
            query = "SELECT id, name, description, evaluation_guide, domain FROM criteria WHERE is_active = TRUE ORDER BY domain, name"
            rows = self.conn.execute(query).fetchall()
        return rows
    
    def save_criteria(self, name: str, description: str, evaluation_guide: str, domain: str, created_by: str) -> bool:
        """Save or update criteria"""
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO criteria (name, description, evaluation_guide, domain, created_by)
                VALUES (?, ?, ?, ?, ?)
            """, (name, description, evaluation_guide, domain, created_by))
            self.conn.commit()
            return True
        except Exception as e:
            st.error(f"Error saving criteria: {e}")
            return False
    
    def delete_criteria(self, criteria_id: int) -> bool:
        """Soft delete criteria"""
        try:
            self.conn.execute("UPDATE criteria SET is_active = FALSE WHERE id = ?", (criteria_id,))
            self.conn.commit()
            return True
        except Exception as e:
            st.error(f"Error deleting criteria: {e}")
            return False
    
    def get_prompt_templates(self) -> List[Tuple]:
        """Get all prompt templates"""
        query = "SELECT id, name, system_prompt, user_prompt, description, domain FROM prompt_templates WHERE is_active = TRUE ORDER BY name"
        return self.conn.execute(query).fetchall()
    
    def save_prompt_template(self, name: str, system_prompt: str, user_prompt: str, description: str, domain: str, created_by: str) -> bool:
        """Save prompt template"""
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO prompt_templates (name, system_prompt, user_prompt, description, domain, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, system_prompt, user_prompt, description, domain, created_by))
            self.conn.commit()
            return True
        except Exception as e:
            st.error(f"Error saving template: {e}")
            return False
    
    def delete_prompt_template(self, template_id: int) -> bool:
        """Delete prompt template"""
        try:
            self.conn.execute("UPDATE prompt_templates SET is_active = FALSE WHERE id = ?", (template_id,))
            self.conn.commit()
            return True
        except Exception as e:
            st.error(f"Error deleting template: {e}")
            return False
    
    def get_domains(self) -> List[Tuple]:
        """Get all active domains"""
        query = "SELECT id, name, description, color FROM domains WHERE is_active = TRUE ORDER BY name"
        return self.conn.execute(query).fetchall()
    
    def save_domain(self, name: str, description: str = "", color: str = "#1f77b4", created_by: str = "User") -> bool:
        """Save domain"""
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO domains (name, description, color, created_by)
                VALUES (?, ?, ?, ?)
            """, (name, description, color, created_by))
            self.conn.commit()
            return True
        except Exception as e:
            st.error(f"Error saving domain: {e}")
            return False
    
    def delete_domain(self, domain_id: int) -> bool:
        """Delete domain (soft delete)"""
        try:
            self.conn.execute("UPDATE domains SET is_active = FALSE WHERE id = ?", (domain_id,))
            self.conn.commit()
            return True
        except Exception as e:
            st.error(f"Error deleting domain: {e}")
            return False
    
    def get_domain_names(self) -> List[str]:
        """Get list of domain names for selectboxes"""
        domains = self.get_domains()
        domain_names = [domain[1] for domain in domains]  # Extract names
        
        # Ensure default domains exist
        default_domains = ["General", "Healthcare", "Technology", "Business", "Legal", "Education"]
        for domain in default_domains:
            if domain not in domain_names:
                self.save_domain(domain, f"Default {domain} domain", "#1f77b4", "System")
                domain_names.append(domain)
        
        return sorted(domain_names)
    
    def get_analytics_data(self) -> Dict:
        """Get analytics data for dashboard"""
        try:
            # Get total reviews
            total_reviews = self.conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
            
            # Get unique reviewers
            unique_reviewers = self.conn.execute("SELECT COUNT(DISTINCT reviewer) FROM reviews").fetchone()[0]
            
            # Get average score
            avg_score_result = self.conn.execute("SELECT AVG(overall_score) FROM reviews WHERE overall_score IS NOT NULL").fetchone()[0]
            avg_score = avg_score_result if avg_score_result else 0.0
            
            # Get recent reviews (last 7 days)
            recent_reviews = self.conn.execute("""
                SELECT COUNT(*) FROM reviews 
                WHERE created_date >= datetime('now', '-7 days')
            """).fetchone()[0]
            
            return {
                'total_reviews': total_reviews,
                'unique_reviewers': unique_reviewers,
                'avg_score': avg_score,
                'recent_reviews': recent_reviews
            }
        except Exception as e:
            st.error(f"Error getting analytics data: {e}")
            return {
                'total_reviews': 0,
                'unique_reviewers': 0,
                'avg_score': 0.0,
                'recent_reviews': 0
            }

    def get_reviews(self, limit: Optional[int] = None, group_by_session: bool = False) -> List[Dict]:
        """Get reviews from database"""
        try:
            query = """
                SELECT id, filename, reviewer, domain, document_type, model_used, 
                       overall_score, review_quality, review_comment, session_id, 
                       created_date, analysis_data
                FROM reviews 
                ORDER BY created_date DESC
            """
            if limit:
                query += f" LIMIT {limit}"
            
            rows = self.conn.execute(query).fetchall()
            
            reviews = []
            for row in rows:
                review = {
                    'id': row[0],
                    'filename': row[1],
                    'reviewer': row[2],
                    'domain': row[3],
                    'document_type': row[4],
                    'model_used': row[5],
                    'overall_score': row[6],
                    'review_quality': row[7],
                    'review_comment': row[8],
                    'session_id': row[9],
                    'created_date': row[10],
                    'analysis_data': row[11]
                }
                
                # Add session information if grouping by session
                if group_by_session and review['session_id']:
                    session_info = self.conn.execute("""
                        SELECT MIN(created_date) as session_start, COUNT(*) as review_count
                        FROM reviews WHERE session_id = ?
                    """, (review['session_id'],)).fetchone()
                    
                    if session_info:
                        review['session_start_time'] = session_info[0]
                        review['session_review_count'] = session_info[1]
                
                reviews.append(review)
            
            return reviews
        except Exception as e:
            st.error(f"Error getting reviews: {e}")
            return []

    def export_reviews_to_dict(self, filters: Optional[Dict] = None) -> List[Dict]:
        """Export reviews as dictionary with optional filters"""
        try:
            query = """
                SELECT id, filename, reviewer, domain, document_type, model_used,
                       overall_score, review_quality, review_comment, session_id,
                       created_date, analysis_data
                FROM reviews WHERE 1=1
            """
            params = []
            
            if filters:
                if 'domain' in filters:
                    query += " AND domain = ?"
                    params.append(filters['domain'])
                if 'reviewer' in filters:
                    query += " AND reviewer = ?"
                    params.append(filters['reviewer'])
                if 'date_from' in filters:
                    query += " AND date(created_date) >= ?"
                    params.append(filters['date_from'])
                if 'date_to' in filters:
                    query += " AND date(created_date) <= ?"
                    params.append(filters['date_to'])
            
            query += " ORDER BY created_date DESC"
            
            rows = self.conn.execute(query, params).fetchall()
            
            reviews = []
            for row in rows:
                review = {
                    'id': row[0],
                    'filename': row[1],
                    'reviewer': row[2],
                    'domain': row[3],
                    'document_type': row[4],
                    'model_used': row[5],
                    'overall_score': row[6],
                    'review_quality': row[7],
                    'review_comment': row[8],
                    'session_id': row[9],
                    'created_date': row[10],
                    'analysis_data': row[11]
                }
                  # Parse analysis data
                try:
                    if review['analysis_data']:
                        review['analysis_data_parsed'] = json.loads(review['analysis_data'])
                    else:
                        review['analysis_data_parsed'] = {}
                except:
                    review['analysis_data_parsed'] = {}
                
                reviews.append(review)
            
            return reviews
        except Exception as e:
            st.error(f"Error exporting reviews: {e}")
            return []

    def update_review_score(self, review_id: int, review_quality: float, review_comment: str) -> bool:
        """Update review quality score and comment"""
        try:
            self.conn.execute("""
                UPDATE reviews 
                SET review_quality = ?, review_comment = ?
                WHERE id = ?
            """, (review_quality, review_comment, review_id))
            self.conn.commit()
            return True
        except Exception as e:
            st.error(f"Error updating review score: {e}")
            return False
    
    def save_review(self, filename: str, reviewer: str, domain: str, document_type: str, model_used: str, analysis_data: Dict, overall_score: float, session_id: str) -> bool:
        """Save review to database"""
        try:
            # Convert analysis data to JSON string
            analysis_data_json = json.dumps(analysis_data, default=str)
            
            self.conn.execute("""
                INSERT INTO reviews (filename, reviewer, domain, document_type, model_used, analysis_data, overall_score, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (filename, reviewer, domain, document_type, model_used, analysis_data_json, overall_score, session_id))
            self.conn.commit()
            return True
        except Exception as e:
            st.error(f"Error saving review: {e}")
            return False

# Initialize database manager
db = DatabaseManager(conn)

# --- Default Data Population ---
def populate_default_data():
    """Populate database with default criteria and templates"""
    default_criteria = {
        "General": {
            "Clarity": {
                "description": "How clearly the document presents its content, objectives, and conclusions",
                "guide": "5: Crystal clear, excellent structure\n4: Clear with minor issues\n3: Generally clear\n2: Some unclear sections\n1: Mostly unclear\n0: Very confusing"
            },
            "Relevance": {
                "description": "How relevant the content is to its stated purpose and target audience",
                "guide": "5: Highly relevant and applicable\n4: Very relevant\n3: Moderately relevant\n2: Somewhat relevant\n1: Limited relevance\n0: Not relevant"
            },
            "Quality": {
                "description": "Overall quality including accuracy, depth, and comprehensiveness",
                "guide": "5: Exceptional quality\n4: High quality\n3: Good quality\n2: Acceptable quality\n1: Poor quality\n0: Very poor quality"
            },
            "Evidence": {
                "description": "Quality and adequacy of supporting evidence and references",
                "guide": "5: Excellent evidence with comprehensive citations\n4: Good evidence quality\n3: Adequate evidence\n2: Limited evidence\n1: Weak evidence\n0: No supporting evidence"
            }
        },
        "Healthcare": {
            "Clinical Relevance": {
                "description": "Relevance to clinical practice and patient care",
                "guide": "5: Directly applicable to practice\n4: Highly relevant\n3: Moderately relevant\n2: Some relevance\n1: Limited relevance\n0: Not relevant"
            },
            "Evidence Quality": {
                "description": "Quality of clinical evidence and study design",
                "guide": "5: High-quality RCTs/meta-analyses\n4: Good evidence quality\n3: Moderate evidence\n2: Limited evidence\n1: Weak evidence\n0: Poor/no evidence"
            },
            "Safety Assessment": {
                "description": "Evaluation of safety considerations and risk assessment",
                "guide": "5: Comprehensive safety analysis\n4: Good safety evaluation\n3: Adequate safety discussion\n2: Limited safety considerations\n1: Poor safety assessment\n0: No safety discussion"
            },
            "Methodology": {
                "description": "Quality of research methodology and study design",
                "guide": "5: Rigorous methodology, well-designed\n4: Good methodology\n3: Acceptable design\n2: Some methodological issues\n1: Poor methodology\n0: Major methodological flaws"
            }
        },
        "Technology": {
            "Technical Accuracy": {
                "description": "Accuracy of technical information and implementation details",
                "guide": "5: Technically accurate and comprehensive\n4: Good technical accuracy\n3: Generally accurate\n2: Some technical issues\n1: Poor technical accuracy\n0: Significant technical errors"
            },
            "Innovation": {
                "description": "Level of innovation and novelty in the approach",
                "guide": "5: Highly innovative breakthrough\n4: Significant innovation\n3: Some innovative elements\n2: Minor innovations\n1: Limited innovation\n0: No innovation"
            },
            "Feasibility": {
                "description": "Practical feasibility of implementation",
                "guide": "5: Highly feasible and practical\n4: Feasible with minor challenges\n3: Generally feasible\n2: Some feasibility concerns\n1: Difficult to implement\n0: Not feasible"
            }
        }
    }
    
    # Check if data already exists
    existing = conn.execute("SELECT COUNT(*) FROM criteria").fetchone()[0]
    if existing > 0:
        return
    
    # Insert default criteria
    for domain, criteria_set in default_criteria.items():
        for name, details in criteria_set.items():
            db.save_criteria(name, details["description"], details["guide"], domain, "System")
    
    # Insert default prompt templates
    default_prompts = [
        {
            "name": "Standard Analysis",
            "system": "You are an expert document reviewer with extensive knowledge across multiple domains. Provide objective, thorough analysis in JSON format with detailed justifications for each score.",
            "user": "Analyze this document thoroughly and provide scores (0-5) for each criterion with detailed justifications. Include overall assessment, strengths, weaknesses, and recommendations.",
            "description": "Standard template for comprehensive document analysis",
            "domain": "General"
        },
        {
            "name": "Healthcare Focus",
            "system": "You are a healthcare expert specializing in medical literature review and clinical analysis. Focus on clinical relevance, evidence quality, and patient safety considerations.",
            "user": "Evaluate this healthcare document for clinical relevance, evidence quality, methodology, and safety considerations. Provide detailed analysis suitable for healthcare professionals.",
            "description": "Specialized template for healthcare and medical documents",
            "domain": "Healthcare"
        },
        {
            "name": "Technical Review",
            "system": "You are a technical expert specializing in technology and engineering documentation. Focus on technical accuracy, innovation, and implementation feasibility.",
            "user": "Analyze this technical document for accuracy, innovation, feasibility, and overall technical quality. Provide detailed technical assessment.",
            "description": "Template optimized for technical and engineering documents",
            "domain": "Technology"
        }
    ]
    
    for prompt in default_prompts:
        db.save_prompt_template(prompt["name"], prompt["system"], prompt["user"], prompt["description"], prompt["domain"], "System")

populate_default_data()

# --- UI Components ---
def render_header():
    """Render main header"""
    st.markdown("""
    <div class="main-header">
        <h1>📄 Smart Document Review System</h1>
        <p>AI-powered analysis with customizable criteria and intelligent prompts</p>
    </div>
    """, unsafe_allow_html=True)

def render_sidebar():
    """Render sidebar configuration"""
    with st.sidebar:
        st.markdown("## ⚙️ Configuration")
        
        # Reviewer Profile
        st.markdown("### 👤 Profile")
        reviewer = st.text_input("Reviewer Name", value=st.session_state.reviewer_name, key="sidebar_reviewer")
        st.session_state.reviewer_name = reviewer
        
        # Domain Selection
        st.markdown("### 🎯 Evaluation Domain")
        domains = db.get_domain_names()
        domain = st.selectbox("Analysis Domain", domains, index=domains.index(st.session_state.domain), key="sidebar_domain")
        st.session_state.domain = domain
        
        # Template Selection
        st.markdown("### 📚 Prompt Templates")
        templates = db.get_prompt_templates()
        template_options = {template[1]: template for template in templates}  # Map name to template data
        selected_template_name = st.selectbox(
            "Select Template",
            options=["None"] + list(template_options.keys()),
            key="sidebar_template_selector"
        )
        if selected_template_name != "None":
            selected_template = template_options[selected_template_name]
            st.session_state.system_prompt = selected_template[2]  # system_prompt
            st.session_state.user_prompt = selected_template[3]    # user_prompt
            st.success(f"✅ Loaded template: {selected_template_name}")
        
        # Model Selection
        st.markdown("### 🤖 AI Model")
        models = {"claude-opus-4-20250514": "🔮 Claude Opus","claude-3-7-sonnet-20250219": "🔮 Claude", "o4-mini": "⚡ OpenAI | o4-mini", "deepseek-reasoner": "🧠 DeepSeek | Reasoning", "deepseek-chat": "🧠 DeepSeek | Chat"}
        model = st.selectbox("AI Model", list(models.keys()), format_func=lambda x: models[x], key="sidebar_model")
        st.session_state.model = model
        
        # Quick Navigation
        st.markdown("### 🚀 Quick Actions")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📝 Criteria", use_container_width=True, key="nav_criteria"):
                st.session_state.current_page = "criteria"
                st.rerun()
        with col2:
            if st.button("✏️ Prompts", use_container_width=True, key="nav_prompts"):
                st.session_state.current_page = "prompts"
                st.rerun()
        
        col3, col4 = st.columns(2)
        with col3:
            if st.button("📊 Analytics", use_container_width=True, key="nav_analytics"):
                st.session_state.current_page = "analytics"
                st.rerun()
        with col4:
            if st.button("📋 History", use_container_width=True, key="nav_history"):
                st.session_state.current_page = "history"
                st.rerun()
        
        # Status Information
        st.markdown("### 📊 Status")
        criteria_count = len(db.get_criteria(domain))
        template_count = len(db.get_prompt_templates())
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Criteria", criteria_count)
        with col2:
            st.metric("Templates", template_count)
        
        if st.session_state.analyzing:
            st.warning("🔄 Analyzing...")
        else:
            st.success("✅ Ready")

def render_criteria_management():
    """Render enhanced criteria management interface"""
    st.markdown("## 📝 Criteria Management")
    
    # Navigation
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🏠 Back to Main", key="back_from_criteria"):
            st.session_state.current_page = "main"
            st.rerun()
      # Tabs for different operations
    tab1, tab2, tab3 = st.tabs(["📋 View Criteria", "➕ Add New", "✏️ Manage"])
    
    with tab1:
        st.markdown("### 📋 Current Criteria")
        criteria = db.get_criteria(st.session_state.domain)
        
        if criteria:
            for crit_id, name, description, guide in criteria:
                with st.expander(f"📌 {name}"):
                    st.markdown(f"**Description:** {description}")
                    st.markdown("**Evaluation Guide:**")
                    st.code(guide, language="text")
        else:
            st.info(f"No criteria found for {st.session_state.domain} domain")
            if st.button("➕ Add Some Criteria", key="add_criteria_prompt"):
                # Switch to add tab
                st.info("Switch to 'Add New' tab to create criteria for this domain.")
    
    with tab2:
        st.markdown("### ➕ Add New Criteria")
        
        with st.form("add_criteria", clear_on_submit=True):
            name = st.text_input("Criteria Name*", placeholder="e.g., Technical Accuracy", key="new_criteria_name")
            description = st.text_area("Description*", height=100, 
                                     placeholder="Describe what this criteria evaluates...", 
                                     key="new_criteria_desc")
            
            st.markdown("**Evaluation Guide* (Scoring 0-5)**")
            guide = st.text_area("Evaluation Guide", height=150,
                                placeholder="5: Excellent - [description]\n4: Good - [description]\n3: Fair - [description]\n2: Poor - [description]\n1: Very Poor - [description]\n0: Not Applicable - [description]",
                                key="new_criteria_guide")
            
            available_domains = db.get_domain_names()
            target_domain = st.selectbox("Target Domain",
                                       available_domains,
                                       index=available_domains.index(st.session_state.domain) if st.session_state.domain in available_domains else 0,
                                       key="new_criteria_domain")
            
            if st.form_submit_button("✅ Add Criteria", type="primary", use_container_width=True):
                if name and description and guide:
                    if db.save_criteria(name, description, guide, target_domain, st.session_state.reviewer_name):
                        st.success(f"✅ Added criteria: {name}")
                        st.rerun()
                else:
                    st.error("❌ Please fill in all required fields")
    
    with tab3:
        st.markdown("### ✏️ Manage Existing Criteria")
        all_criteria = db.get_criteria()
        
        if all_criteria:
            # Group by domain
            domain_groups = {}
            for crit_id, name, description, guide, domain in all_criteria:
                if domain not in domain_groups:
                    domain_groups[domain] = []
                domain_groups[domain].append((crit_id, name, description, guide))
            
            for domain, criteria_list in domain_groups.items():
                st.markdown(f"#### 🏷️ {domain} Domain")
                
                for crit_id, name, description, guide in criteria_list:
                    with st.expander(f"✏️ {name}"):
                        with st.form(f"edit_criteria_{crit_id}"):
                            new_description = st.text_area("Description", value=description, height=80, key=f"edit_desc_{crit_id}")
                            new_guide = st.text_area("Evaluation Guide", value=guide, height=120, key=f"edit_guide_{crit_id}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("💾 Update", use_container_width=True):
                                    if db.save_criteria(name, new_description, new_guide, domain, st.session_state.reviewer_name):
                                        st.success(f"✅ Updated: {name}")
                                        st.rerun()
                            with col2:
                                if st.form_submit_button("🗑️ Delete", use_container_width=True):
                                    if db.delete_criteria(crit_id):
                                        st.success(f"🗑️ Deleted: {name}")
                                        st.rerun()
        else:
            st.info("No criteria available")

def render_prompt_management():
    """Render enhanced prompt template and domain management"""
    st.markdown("## ✏️ Prompt & Domain Management")
    
    # Navigation
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🏠 Back to Main", key="back_from_prompts"):
            st.session_state.current_page = "main"
            st.rerun()
    
    # Enhanced tabs with domain management
    tab1, tab2, tab3, tab4 = st.tabs(["📚 Templates", "➕ Create Template", "✏️ Manage Templates", "🌐 Domains"])
    
    with tab1:
        st.markdown("### 📚 Available Templates")
        templates = db.get_prompt_templates()
        
        if templates:
            # Filter by domain
            col1, col2 = st.columns([2, 1])
            with col1:
                all_domains = ["All"] + db.get_domain_names()
                domain_filter = st.selectbox("Filter by Domain", all_domains, key="template_domain_filter")
            
            # Display templates
            for temp_id, name, system_prompt, user_prompt, description, domain in templates:
                if domain_filter == "All" or domain == domain_filter:
                    with st.expander(f"📄 {name} ({domain})"):
                        if description:
                            st.markdown(f"**Description:** {description}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**System Prompt:**")
                            st.code(system_prompt[:200] + "..." if len(system_prompt) > 200 else system_prompt)
                        with col2:
                            st.markdown("**User Prompt:**")
                            st.code(user_prompt[:200] + "..." if len(user_prompt) > 200 else user_prompt)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(f"📥 Load Template", key=f"load_{temp_id}", use_container_width=True):
                                st.session_state.system_prompt = system_prompt
                                st.session_state.user_prompt = user_prompt
                                st.success(f"✅ Loaded template: {name}")
                                st.rerun()
                        with col2:
                            if st.button(f"✏️ Edit Template", key=f"edit_{temp_id}", use_container_width=True):
                                st.session_state.editing_template_id = temp_id
                                st.session_state.current_page = "prompts"
                                st.rerun()
        else:
            st.info("No templates available")
    
    with tab2:
        st.markdown("### ➕ Create New Template")
        
        with st.form("create_template", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                template_name = st.text_input("Template Name*", key="new_template_name")
                available_domains = db.get_domain_names()
                template_domain = st.selectbox("Domain", available_domains, key="new_template_domain")
            with col2:
                template_description = st.text_area("Description", height=80, key="new_template_desc")
            
            st.markdown("**System Prompt* (AI Role & Personality)**")
            system_prompt = st.text_area("System Prompt", height=150, 
                                       value=st.session_state.get('system_prompt', ''),
                                       placeholder="Define the AI's role, expertise, and approach...",
                                       key="new_system_prompt")
            
            st.markdown("**User Prompt* (Analysis Instructions)**")
            user_prompt = st.text_area("User Prompt", height=150,
                                     value=st.session_state.get('user_prompt', ''),
                                     placeholder="Specify analysis requirements and output format...",
                                     key="new_user_prompt")
            
            if st.form_submit_button("✅ Save Template", type="primary", use_container_width=True):
                if template_name and system_prompt and user_prompt:
                    if db.save_prompt_template(template_name, system_prompt, user_prompt, 
                                             template_description or "", template_domain, st.session_state.reviewer_name):
                        st.success(f"✅ Saved template: {template_name}")
                        st.rerun()
                else:
                    st.error("❌ Please fill in required fields (Name, System Prompt, User Prompt)")
    
    with tab3:
        st.markdown("### ✏️ Manage Templates")
        
        # Check if editing a specific template
        editing_template_id = st.session_state.get('editing_template_id', None)
        if editing_template_id:
            # Find the template being edited
            templates = db.get_prompt_templates()
            template_to_edit = None
            for temp_id, name, system_prompt, user_prompt, description, domain in templates:
                if temp_id == editing_template_id:
                    template_to_edit = (temp_id, name, system_prompt, user_prompt, description, domain)
                    break
            
            if template_to_edit:
                temp_id, name, system_prompt, user_prompt, description, domain = template_to_edit
                st.markdown(f"#### Editing: {name}")
                
                with st.form(f"edit_template_{temp_id}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        new_name = st.text_input("Template Name", value=name, key=f"edit_name_{temp_id}")
                        available_domains = db.get_domain_names()
                        try:
                            domain_index = available_domains.index(domain)
                        except ValueError:
                            domain_index = 0
                        new_domain = st.selectbox("Domain", available_domains, index=domain_index, key=f"edit_domain_{temp_id}")
                    with col2:
                        new_description = st.text_area("Description", value=description or "", height=80, key=f"edit_desc_{temp_id}")
                    
                    new_system = st.text_area("System Prompt", value=system_prompt, height=120, key=f"edit_system_{temp_id}")
                    new_user = st.text_area("User Prompt", value=user_prompt, height=120, key=f"edit_user_{temp_id}")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        if st.form_submit_button("💾 Update", use_container_width=True):
                            if new_name and new_system and new_user:
                                # Delete old template and create new one (to handle name changes)
                                db.delete_prompt_template(temp_id)
                                if db.save_prompt_template(new_name, new_system, new_user, new_description, new_domain, st.session_state.reviewer_name):
                                    st.success(f"✅ Updated: {new_name}")
                                    st.session_state.editing_template_id = None
                                    st.rerun()
                            else:
                                st.error("❌ Please fill in required fields")
                    with col2:
                        if st.form_submit_button("📥 Load", use_container_width=True):
                            st.session_state.system_prompt = new_system
                            st.session_state.user_prompt = new_user
                            st.success(f"✅ Loaded: {name}")
                    with col3:
                        if st.form_submit_button("�️ Delete", use_container_width=True):
                            if db.delete_prompt_template(temp_id):
                                st.success(f"🗑️ Deleted: {name}")
                                st.session_state.editing_template_id = None
                                st.rerun()
                    with col4:
                        if st.form_submit_button("❌ Cancel", use_container_width=True):
                            st.session_state.editing_template_id = None
                            st.rerun()
            else:
                st.error("Template not found")
                st.session_state.editing_template_id = None
        else:
            # Show all templates for management
            templates = db.get_prompt_templates()
            if templates:
                st.markdown("**Select a template to edit:**")
                for temp_id, name, system_prompt, user_prompt, description, domain in templates:
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.write(f"📄 **{name}** ({domain})")
                        if description:
                            st.caption(description[:100] + "..." if len(description) > 100 else description)
                    with col2:
                        if st.button("✏️ Edit", key=f"manage_edit_{temp_id}", use_container_width=True):
                            st.session_state.editing_template_id = temp_id
                            st.rerun()
                    with col3:
                        if st.button("🗑️ Delete", key=f"manage_delete_{temp_id}", use_container_width=True):
                            if db.delete_prompt_template(temp_id):
                                st.success(f"🗑️ Deleted: {name}")
                                st.rerun()
                    st.markdown("---")
            else:
                st.info("No templates to manage")
    
    with tab4:
        st.markdown("### 🌐 Domain Management")
        
        # Create new domain
        with st.expander("➕ Create New Domain"):
            with st.form("create_domain", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    domain_name = st.text_input("Domain Name*", key="new_domain_name")
                    domain_color = st.color_picker("Color", value="#1f77b4", key="new_domain_color")
                with col2:
                    domain_description = st.text_area("Description", height=80, key="new_domain_desc")
                
                if st.form_submit_button("✅ Create Domain", type="primary", use_container_width=True):
                    if domain_name:
                        if db.save_domain(domain_name, domain_description, domain_color, st.session_state.reviewer_name):
                            st.success(f"✅ Created domain: {domain_name}")
                            st.rerun()
                    else:
                        st.error("❌ Please enter a domain name")
        
        # Manage existing domains
        st.markdown("**Existing Domains:**")
        domains = db.get_domains()
        
        if domains:
            for domain_id, name, description, color in domains:
                with st.container():
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.markdown(f"<span style='color: {color}'>🌐</span> **{name}**", unsafe_allow_html=True)
                        if description:
                            st.caption(description)
                    with col2:
                        # Count templates using this domain
                        template_count = len([t for t in db.get_prompt_templates() if t[5] == name])
                        st.metric("Templates", template_count)
                    with col3:
                        if name not in ["General", "Healthcare", "Technology", "Business", "Legal", "Education"]:
                            if st.button("🗑️ Delete", key=f"delete_domain_{domain_id}", use_container_width=True):
                                if template_count > 0:
                                    st.error(f"❌ Cannot delete domain '{name}' - it has {template_count} templates")
                                else:
                                    if db.delete_domain(domain_id):
                                        st.success(f"🗑️ Deleted domain: {name}")
                                        st.rerun()
                        else:
                            st.caption("Default domain")
                    st.markdown("---")
        else:
            st.info("No custom domains created yet")

def render_analytics():
    """Render analytics dashboard"""
    st.markdown("## 📊 Analytics Dashboard")
    
    # Navigation
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🏠 Back to Main", key="back_from_analytics"):
            st.session_state.current_page = "main"
            st.rerun()
    
    # Get analytics data
    analytics = db.get_analytics_data()
    
    if analytics['total_reviews'] > 0:        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📋 Total Reviews", analytics['total_reviews'])
        with col2:
            st.metric("👥 Reviewers", analytics['unique_reviewers'])
        with col3:
            st.metric("⭐ Avg Score", f"{analytics['avg_score']:.1f}")
        with col4:
            st.metric("📅 This Week", analytics['recent_reviews'])
        
        # Recent reviews grouped by session
        st.markdown("### 📋 Recent Review Sessions")
        recent_reviews = db.get_reviews(limit=5, group_by_session=True)
        
        if recent_reviews:
            # Group reviews by session
            sessions = {}
            for review in recent_reviews:
                session_id = review.get('session_id', 'No Session')
                if session_id not in sessions:
                    sessions[session_id] = {
                        'session_start': review.get('session_start_time', review['created_date'])[:10],
                        'session_count': review.get('session_review_count', 1),
                        'reviews': []
                    }
                sessions[session_id]['reviews'].append(review)
            
            # Display sessions
            for session_id, session_data in sessions.items():
                with st.container():
                    st.markdown(f"**🗂️ Session {session_id[:8]}...** - {session_data['session_start']} ({session_data['session_count']} files)")
                    
                    # Create DataFrame for this session
                    df_data = []
                    for review in session_data['reviews']:
                        try:
                            analysis_data = json.loads(review['analysis_data'])
                            df_data.append({
                                'Filename': review['filename'],
                                'Reviewer': review['reviewer'],
                                'Domain': review['domain'],
                                'Score': review['overall_score'],
                                'Date': review['created_date'][:10]
                            })
                        except:
                            continue
                    
                    if df_data:
                        df = pd.DataFrame(df_data)
                        st.dataframe(df, use_container_width=True, height=min(150, len(df_data) * 35 + 38))
                    
                    st.markdown("---")
        else:
            st.info("No review sessions found yet.")
        
        # Domain breakdown
        st.markdown("### 🎯 Domain Analysis")
        try:
            domain_data = conn.execute("""
                SELECT domain, COUNT(*) as count, AVG(overall_score) as avg_score
                FROM reviews 
                GROUP BY domain
                ORDER BY count DESC
            """).fetchall()
            
            if domain_data:
                domain_df = pd.DataFrame(domain_data, columns=['Domain', 'Count', 'Avg Score'])
                col1, col2 = st.columns(2)
                with col1:
                    st.bar_chart(domain_df.set_index('Domain')['Count'])
                    st.caption("Review Count by Domain")
                with col2:
                    st.bar_chart(domain_df.set_index('Domain')['Avg Score'])
                    st.caption("Average Score by Domain")
        except Exception as e:
            st.error(f"Error generating domain analysis: {e}")
    else:
        st.info("No analytics data available yet. Complete some document analyses to see insights here.")

def generate_analysis_prompt(selected_criteria: List[str], domain: str, analysis_depth: str = "Standard") -> str:
    """Generate analysis prompt based on selected criteria"""
    criteria = db.get_criteria(domain)
    criteria_dict = {name: (description, guide) for _, name, description, guide in criteria}
    
    criteria_details = []
    for criterion in selected_criteria:
        if criterion in criteria_dict:
            description, guide = criteria_dict[criterion]
            criteria_details.append(f"- **{criterion}**: {description} \n  - **Guide:** {guide}")
        else:
            criteria_details.append(f"- **{criterion}**: Custom criterion")
    
    criteria_text = "\n".join(criteria_details)
    
    depth_instructions = {
        "Quick": "Provide a concise analysis focusing on key points.",
        "Standard": "Provide a balanced analysis with adequate detail.",
        "Detailed": "Provide a comprehensive analysis with extensive justifications and examples."
    }
    
    depth_instruction = depth_instructions.get(analysis_depth, depth_instructions["Standard"])
    
    prompt = f"""Please analyze the following article and provide a structured evaluation based on these specific criteria:

{criteria_text}

Analysis Depth: {analysis_depth}
Instructions: {depth_instruction}

For each criterion, provide:
1. scoring according to the guide provided by the criteria
2. A brief justification explaining the score
3. the confidence level of your assessment (0-100%)


Additionally, provide:
- A concise summary of the document's main points
- Key strengths of the document
- Areas for improvement or weaknesses
- Specific recommendations for enhancement
- An overall quality assessment
- Confidence level for your analysis (0-100%)

Output your analysis only in JSON format with this structure:
{{
    "filename": "document_name",
    "summary": "document_summary",
    "overall_score": overall_numeric_score,
    "confidence_level": confidence_percentage,
    "analysis_depth": "{analysis_depth}",
    "criteria_scores": [
        {{"criterion_name": name ,"score": score, "confidence": confidence score, "justification": justify your score}}
        ...
        ],
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "recommendations": ["recommendation1", "recommendation2"],
    "processing_notes": "any_additional_observations"
}}
Follow this format strictly and ensure all fields are included. BE FACTUAL AND DONT FABRICATE. Build clear sentences. If a criterion is not applicable, assign a score of 0 and provide a justification explaining why it does not apply.
Do not include any additional text outside of the JSON structure nor mark json area.
"""
    log_event(f"Generated prompt for domain '{domain}' with depth '{analysis_depth}': {prompt}...")
    return prompt

def analyze_document(pdf_file, selected_criteria: List[str]) -> Dict:
    """Analyze a single document"""
    response = None
    try:
        # Generate prompt
        prompt = generate_analysis_prompt(selected_criteria, st.session_state.domain, st.session_state.analysis_depth)
        
        # Prepare API request
        files = {"file": (pdf_file.name, pdf_file, "application/pdf")}
        data = {
            "system_prompt": st.session_state.system_prompt,
            "user_prompt": prompt,
            "model": st.session_state.model
        }
        
        # Make API call
        # calculate the time laps for the following functiion
        log_event(f"1 | Sending API request for {pdf_file.name} with model {st.session_state.model}...")
        start_time = time.time()
        response = requests.post(API_URL, files=files, data=data, timeout=3600) #3600
        elapsed_time = time.time() - start_time
        log_event(f"1 | API request completed for {pdf_file.name} in {elapsed_time:.2f} seconds")
        response.raise_for_status()
        
        api_data = response.json()
        log_event(f"3 | API response received for {pdf_file.name}: {api_data}")  # Log first 100 chars
        text = api_data.get("summary", api_data)

        log_event(f"2 | Summary | API response received for {pdf_file.name}: {text}")  # Log first 100 chars
        # Parse JSON response
        if text.strip().startswith("```json"):
            text_clean = text.strip().removeprefix("```json").removesuffix("```").strip()
        else:
            text_clean = text.replace("```json", "").strip()
            text_clean = text_clean.replace("```", "").strip()
        
        if text_clean.strip().startswith("```"):
            text_clean = text_clean.strip().removeprefix("```").removesuffix("```").strip()
        
        if text_clean.endswith("```"):
            text_clean = text_clean.removesuffix("```").strip()
        
        if text_clean.startswith("{"):
            parsed_review = json.loads(text_clean)
            
            # Add metadata
            parsed_review.update({
                "filename": pdf_file.name,
                "reviewer": st.session_state.reviewer_name,
                "timestamp": datetime.now().isoformat(),
                "time_lapsed": elapsed_time,
                "processing_successful": True
            })
            log_event(str(parsed_review), level="warning")
            
            return parsed_review
        else:
            log_event(text, level="error")
            raise ValueError("Response is not valid JSON")
            
    except Exception as e: 
        # Return error result
        log_event(f"error in parsing the json {response.json()}", level="error")
        return {
            "filename": pdf_file.name,
            "reviewer": st.session_state.reviewer_name,
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "processing_successful": False,
            "time_lapsed": 0,
            "overall_score": 0,
            "summary": f"Analysis failed: {str(e)}"
        }

def render_main_interface():
    """Render main document analysis interface"""
    st.markdown("## 📄 Document Analysis")
      # Quick settings - use a collapsible section instead of expander
    show_settings = st.checkbox("⚙️ Show Quick Settings", value=False, key="show_quick_settings")
    
    if show_settings:
        st.markdown("#### ⚙️ Quick Settings")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.session_state.document_type = st.selectbox(
                "Document Type",
                ["Research Paper", "Technical Report", "Policy Document", "Training Material", "Review Article", "White Paper", "Guidelines", "Manual", "Other"],
                index=["Research Paper", "Technical Report", "Policy Document", "Training Material", "Review Article", "White Paper", "Guidelines", "Manual", "Other"].index(st.session_state.document_type),
                key="main_document_type"
            )
        with col2:
            st.session_state.analysis_depth = st.selectbox(
                "Analysis Depth",
                ["Standard", "Detailed", "Quick"],
                index=["Standard", "Detailed", "Quick"].index(st.session_state.analysis_depth),
                key="main_analysis_depth"
            )
        with col3:
            if st.button("🎨 Edit Prompts", use_container_width=True):
                st.session_state.current_page = "prompts"
                st.rerun()
        st.markdown("---")
    
    # File Upload
    uploaded_files = st.file_uploader(
        "📁 Upload PDF Documents",
        type=['pdf'],
        accept_multiple_files=True,
        help="Select one or more PDF files for analysis",
        disabled=st.session_state.analyzing,
        key="main_file_uploader"
    )
    
    if uploaded_files:
        st.success(f"📁 {len(uploaded_files)} files ready for analysis")
          # Criteria Selection
        st.markdown("### 🎯 Select Evaluation Criteria")
        criteria = db.get_criteria(st.session_state.domain)
        
        if criteria:
            criteria_options = [name for _, name, _, _ in criteria]
            selected_criteria = st.multiselect(
                "Choose criteria for analysis",
                options=criteria_options,
                default=criteria_options[:3] if len(criteria_options) >= 3 else criteria_options,
                key="main_criteria_selector"
            )
            
            # Show selected criteria details
            if selected_criteria:
                st.markdown("### 📋 Selected Criteria Details")                
                for criterion in selected_criteria:
                    criteria_detail = next((c for c in criteria if c[1] == criterion), None)
                    if criteria_detail:
                        _, name, description, guide = criteria_detail
                        
                        # Create a card-like display instead of nested expander
                        with st.container():
                            st.markdown(f"#### 📌 {name}")
                            st.write(f"📝 **Description:** {description}")
                            
                            # Use a toggle for the evaluation guide
                            if st.toggle(f"Show Evaluation Guide for {name}", key=f"guide_toggle_{name}"):
                                st.code(guide, language="text")
                            
                            st.markdown("---")
                
                # Analysis Controls
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    if st.button("🚀 Start Analysis", type="primary", 
                               disabled=st.session_state.analyzing, use_container_width=True):
                        st.session_state.analyzing = True
                        st.session_state.selected_criteria = selected_criteria
                        st.session_state.cancel_analysis = False
                        st.rerun()
                
                with col2:
                    if st.button("⏹️ Stop", disabled=not st.session_state.analyzing, key="stop_analysis"):
                        st.session_state.analyzing = False
                        st.session_state.cancel_analysis = True
                        st.warning("Analysis stopped")
                        st.rerun()
                
                with col3:
                    if st.button("🔄 Clear Results", key="clear_results"):
                        st.session_state.batch_results = []
                        st.info("Results cleared")
                        st.rerun()
                
                # Analysis Progress
                if st.session_state.analyzing:
                    st.markdown("#### ⏳ Analysis in Progress")
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    batch_results = []
                    total_files = len(uploaded_files)
                    
                    for idx, pdf_file in enumerate(uploaded_files):
                        if st.session_state.cancel_analysis:
                            status_text.warning("Analysis cancelled by user.")
                            break
                        
                        # Update progress
                        progress = (idx + 1) / total_files
                        progress_bar.progress(progress)
                        status_text.text(f"Processing file {idx + 1} of {total_files}: {pdf_file.name}")
                        
                        # Analyze document
                        result = analyze_document(pdf_file, selected_criteria)
                        batch_results.append(result)
                    
                    # Complete analysis
                    st.session_state.analyzing = False
                    st.session_state.batch_results = batch_results
                    st.success(f"✅ Analysis complete! Processed {len(batch_results)} documents.")
                    save_all_results_to_database()
                    st.rerun()
        else:
            st.warning(f"No criteria available for {st.session_state.domain} domain")
            if st.button("➕ Add Criteria", key="add_criteria_main"):
                st.session_state.current_page = "criteria"
                st.rerun()
    
    # Results Display
    if st.session_state.batch_results:
        st.markdown("### 📊 Analysis Results")
        
        # Results summary
        total_results = len(st.session_state.batch_results)
        successful_results = len([r for r in st.session_state.batch_results if r.get('processing_successful', False)])
          # Calculate average score outside the columns to ensure it's in scope
        avg_score = 0
        if successful_results > 0:
            avg_score = sum(r.get('overall_score', 0) for r in st.session_state.batch_results if r.get('processing_successful', False)) / successful_results
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Documents", total_results)
        with col2:
            st.metric("Successfully Analyzed", successful_results)
        with col3:
            if successful_results > 0:
                st.metric("Average Score", f"{avg_score:.1f}")
            else:
                st.metric("Average Score", "N/A")
        
        # Results Table and Download Options
        st.markdown("#### 📋 Results Table & Downloads")
        
        # Create results table
        if successful_results > 0:
            # Prepare data for table
            table_data = []
            for idx, result in enumerate(st.session_state.batch_results):
                if result.get('processing_successful', False):
                    row = {
                        'Document': result.get('filename', f'Document {idx+1}'),
                        'Overall Score': f"{result.get('overall_score', 0):.1f}",
                        'Summary': result.get('summary', '')[:100] + '...' if result.get('summary', '') and len(result.get('summary', '')) > 100 else result.get('summary', 'No summary'),
                        'Strengths Count': len(result.get('strengths', [])),
                        'Weaknesses Count': len(result.get('weaknesses', [])),
                        'Status': '✅ Success' if result.get('processing_successful', False) else '❌ Failed'
                    }
                    
                    # Add individual criteria scores
                    criteria_scores = result.get('criteria_scores', [])
                    for criterion in criteria_scores:
                        score = criterion["score"]
                        criterion_name = criterion["criterion_name"]
                        row[f'{criterion_name} Score'] = f"{score}"
                    
                    table_data.append(row)
            
            # Display table
            if table_data:
                import pandas as pd
                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True, height=300)
                
                # Download options
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # CSV Download
                    csv_data = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv_data,
                        file_name=f"analysis_results_{st.session_state.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col2:
                    # JSON Download (detailed results)
                    detailed_results = []
                    for result in st.session_state.batch_results:
                        if result.get('processing_successful', False):
                            detailed_results.append({
                                'filename': result.get('filename', 'Unknown'),
                                'overall_score': result.get('overall_score', 0),
                                'summary': result.get('summary', ''),
                                'strengths': result.get('strengths', []),
                                'weaknesses': result.get('weaknesses', []),
                                'criteria_scores': result.get('criteria_scores', []),
                                'domain': st.session_state.domain,
                                'reviewer': st.session_state.reviewer_name,
                                'model': st.session_state.model,
                                'analysis_timestamp': result.get('timestamp', datetime.now().isoformat()),
                                'session_id': st.session_state.session_id
                            })
                    
                    json_data = json.dumps(detailed_results, indent=2, default=str)
                    st.download_button(
                        label="📥 Download JSON",
                        data=json_data,
                        file_name=f"analysis_results_detailed_{st.session_state.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
                
                with col3:
                    # Excel Download with formatting
                    try:
                        from io import BytesIO
                        import xlsxwriter
                        
                        # Create Excel file in memory
                        output = BytesIO()
                        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
                        
                        # Summary worksheet
                        summary_sheet = workbook.add_worksheet('Summary')
                        bold = workbook.add_format({'bold': True})
                        
                        summary_sheet.write('A1', 'Analysis Summary', bold)
                        summary_sheet.write('A3', 'Total Documents:', bold)
                        summary_sheet.write('B3', total_results)
                        summary_sheet.write('A4', 'Successfully Analyzed:', bold)
                        summary_sheet.write('B4', successful_results)
                        summary_sheet.write('A5', 'Average Score:', bold)
                        summary_sheet.write('B5', f"{avg_score:.1f}" if successful_results > 0 else "N/A")
                        summary_sheet.write('A6', 'Domain:', bold)
                        summary_sheet.write('B6', st.session_state.domain)
                        summary_sheet.write('A7', 'Reviewer:', bold)
                        summary_sheet.write('B7', st.session_state.reviewer_name)
                        
                        # Results worksheet
                        results_sheet = workbook.add_worksheet('Results')
                        
                        # Write headers
                        for col, header in enumerate(df.columns):
                            results_sheet.write(0, col, header, bold)
                        
                        # Write data
                        for row_idx, row_data in df.iterrows():
                            for col_idx, value in enumerate(row_data):
                                results_sheet.write(row_idx + 1, col_idx, str(value))
                        
                        workbook.close()
                        output.seek(0)
                        

                    except ImportError:
                        st.caption("Excel download requires xlsxwriter package")
        
        st.markdown("---")
        st.markdown("#### 📄 Detailed Results")
        
        # Individual results
        for idx, result in enumerate(st.session_state.batch_results):
            with st.expander(f"📄 {result.get('filename', f'Document {idx+1}')} - Score: {result.get('overall_score', 0):.1f}"):
                if result.get('processing_successful', False):
                    
                    # Display scores
                    scores = result.get('criteria_scores', [])
                    scores = {criterion["criterion_name"]: criterion["score"] for criterion in scores}
                    if scores:
                        score_cols = st.columns(min(4, len(scores)))
                        for i, (criterion, score) in enumerate(scores.items()):
                            with score_cols[i % len(score_cols)]:
                                st.metric(criterion, f"{score}/5")

                    
                    # Display summary
                    if result.get('summary'):
                        st.markdown("**Summary:**")
                        st.write(result['summary'])
                    
                    # Display strengths and weaknesses
                    col1, col2 = st.columns(2)
                    with col1:
                        strengths = result.get('strengths', [])
                        if strengths:
                            st.markdown("**Strengths:**")
                            for strength in strengths:
                                st.write(f"• {strength}")
                    
                    with col2:
                        weaknesses = result.get('weaknesses', [])
                        if weaknesses:
                            st.markdown("**Weaknesses:**")
                            for weakness in weaknesses:
                                st.write(f"• {weakness}")
                    st.markdown("----")
                    # Display scores with justifications
                    criteria_scores = result.get('criteria_scores', [])
                    if criteria_scores:
                            st.markdown("*Criteria Evaluations:*")
                            for criterion in criteria_scores:
                                with st.container():
                                    st.metric(criterion["criterion_name"], f"{criterion['score']}/5")
                                    st.markdown(f"**Justification:** {criterion.get('justification', 'No justification provided')}")
                                    st.markdown("---")

                    
                else:
                    st.error(f"Analysis failed: {result.get('error', 'Unknown error')}")


def save_all_results_to_database():
    saved_count = 0
    for result in st.session_state.batch_results:
        if db.save_review(
                    result.get('filename', 'Unknown'),
                    st.session_state.reviewer_name,
                    st.session_state.domain,
                    st.session_state.document_type,
                    st.session_state.model,
                    result,
                    result.get('overall_score', 0),
                    st.session_state.session_id
                ):
                    saved_count += 1
            
    if saved_count > 0:
        st.success(f"✅ Successfully saved {saved_count} reviews to database!")
    else:
        st.error("❌ Failed to save reviews to database")


def render_history_management():
    """Render comprehensive history management page"""
    st.markdown("## 📋 Review History Management")
    
    # Navigation
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🏠 Back to Main", key="back_from_history"):
            st.session_state.current_page = "main"
            st.rerun()
    
    # Filters section
    st.markdown("### 🔍 Filters & Search")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Domain filter
        all_domains = db.conn.execute("SELECT DISTINCT domain FROM reviews ORDER BY domain").fetchall()
        domain_options = ["All"] + [row[0] for row in all_domains]
        selected_domain = st.selectbox("Domain", domain_options, key="hist_domain_filter")
    
    with col2:
        # Reviewer filter
        all_reviewers = db.conn.execute("SELECT DISTINCT reviewer FROM reviews ORDER BY reviewer").fetchall()
        reviewer_options = ["All"] + [row[0] for row in all_reviewers]
        selected_reviewer = st.selectbox("Reviewer", reviewer_options, key="hist_reviewer_filter")
    
    with col3:
        # Date range
        date_from = st.date_input("From Date", key="hist_date_from", value=None)
    
    with col4:
        date_to = st.date_input("To Date", key="hist_date_to", value=None)
    
    # Build filters
    filters = {}
    if selected_domain != "All":
        filters['domain'] = selected_domain
    if selected_reviewer != "All":
        filters['reviewer'] = selected_reviewer
    if date_from:
        filters['date_from'] = date_from.isoformat()
    if date_to:
        filters['date_to'] = date_to.isoformat()
    
    # Export section
    st.markdown("### 📥 Export Data")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Export as CSV", key="export_csv", use_container_width=True):
            export_data = db.export_reviews_to_dict(filters)
            if export_data:
                # Convert to DataFrame for CSV export
                df_export = []
                for review in export_data:
                    row = {
                        'ID': review['id'],
                        'Filename': review['filename'],
                        'Reviewer': review['reviewer'],
                        'Domain': review['domain'],
                        'Document Type': review['document_type'],
                        'Model Used': review['model_used'],
                        'Overall Score': review['overall_score'],
                        'Review Quality': review.get('review_quality', ''),
                        'Review Comment': review.get('review_comment', ''),
                        'Session ID': review.get('session_id', ''),
                        'Created Date': review['created_date']
                    }
                    # Add analysis details
                    analysis = review.get('analysis_data_parsed', {})
                    if analysis:
                        row['Summary'] = analysis.get('summary', '')
                        row['Strengths'] = '; '.join(analysis.get('strengths', []))
                        row['Weaknesses'] = '; '.join(analysis.get('weaknesses', []))
                        # Add criteria scores
                        for criterion, score in analysis.get('scores', {}).items():
                            row[f'Score_{criterion}'] = score
                    
                    df_export.append(row)
                
                df = pd.DataFrame(df_export)
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"review_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
    
    with col2:
        if st.button("📋 Export as JSON", key="export_json", use_container_width=True):
            export_data = db.export_reviews_to_dict(filters)
            if export_data:
                json_str = json.dumps(export_data, indent=2, default=str)
                st.download_button(
                    label="📥 Download JSON",
                    data=json_str,
                    file_name=f"review_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )
    
    with col3:
        if st.button("🔄 Refresh Data", key="refresh_history", use_container_width=True):
            st.rerun()
    
    # Get filtered reviews
    try:
        all_reviews = db.export_reviews_to_dict(filters)
        
        # Debug: Check data structure
        if all_reviews and len(all_reviews) > 0:
            st.write("🔍 Debug Info (first review keys):", list(all_reviews[0].keys())[:10])
    except Exception as e:
        st.error(f"❌ Error fetching export data: {e}")
        # Fallback to regular get_reviews
        st.info("🔄 Falling back to basic review list...")
        try:
            basic_reviews = db.get_reviews()
            all_reviews = []
            for review in basic_reviews:
                # Convert to expected format
                review_dict = {
                    'id': review.get('id', 'Unknown'),
                    'filename': review.get('filename', 'Unknown File'),
                    'reviewer': review.get('reviewer', 'Unknown Reviewer'),
                    'domain': review.get('domain', 'Unknown Domain'),
                    'document_type': review.get('document_type', 'Unknown Type'),
                    'model_used': review.get('model_used', 'Unknown Model'),
                    'overall_score': review.get('overall_score', 0),
                    'review_quality': review.get('review_quality'),
                    'review_comment': review.get('review_comment'),
                    'session_id': review.get('session_id'),
                    'created_date': review.get('created_date', 'Unknown Date'),
                    'analysis_data_parsed': {}
                }
                
                # Try to parse analysis_data
                try:
                    if 'analysis_data' in review and review['analysis_data']:
                        analysis_data = json.loads(review['analysis_data'])
                        review_dict['analysis_data_parsed'] = analysis_data
                except:
                    pass
                
                all_reviews.append(review_dict)
        except Exception as fallback_error:
            st.error(f"❌ Fallback also failed: {fallback_error}")
            all_reviews = []
    
    if not all_reviews:
        st.info("📭 No reviews found with the current filters.")
        return
    
    # Display summary
    st.markdown("### 📊 Summary")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📋 Total Reviews", len(all_reviews))
    with col2:
        avg_score = sum(r.get('overall_score', 0) for r in all_reviews) / len(all_reviews) if all_reviews else 0
        st.metric("⭐ Avg Score", f"{avg_score:.1f}")
    with col3:
        reviewed_count = sum(1 for r in all_reviews if r.get('review_quality') is not None)
        st.metric("👤 Human Reviewed", reviewed_count)
    with col4:
        unique_sessions = len(set(r.get('session_id') for r in all_reviews if r.get('session_id')))
        st.metric("🗂️ Sessions", unique_sessions)
    
    # Table display with pagination
    st.markdown("### 📋 Review History Table")
    
    # Pagination
    reviews_per_page = st.selectbox("Reviews per page", [1, 10, 25, 50, 100], index=0, key="hist_per_page")
    total_pages = (len(all_reviews) - 1) // reviews_per_page + 1
    
    if total_pages > 1:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("⬅️ Previous", disabled=st.session_state.get('hist_page', 1) <= 1, key="hist_prev"):
                st.session_state.hist_page = max(1, st.session_state.get('hist_page', 1) - 1)
                st.rerun()
        with col2:
            current_page = st.number_input("Page", min_value=1, max_value=total_pages, 
                                         value=st.session_state.get('hist_page', 1), key="hist_page_input")
            st.session_state.hist_page = current_page
        with col3:
            if st.button("➡️ Next", disabled=st.session_state.get('hist_page', 1) >= total_pages, key="hist_next"):
                st.session_state.hist_page = min(total_pages, st.session_state.get('hist_page', 1) + 1)
                st.rerun()
        
        st.write(f"Page {st.session_state.get('hist_page', 1)} of {total_pages}")
    
    # Get current page data
    start_idx = (st.session_state.get('hist_page', 1) - 1) * reviews_per_page
    end_idx = start_idx + reviews_per_page
    page_reviews = all_reviews[start_idx:end_idx]
      # Display reviews table
    for i, review in enumerate(page_reviews):
        with st.container():
            # Review header - add safe access to avoid KeyError
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                filename = review.get('filename', 'Unknown File')
                review_id = review.get('id', 'Unknown ID')
                st.markdown(f"**📄 {filename}** (ID: {review_id})")
            with col2:
                created_date = review.get('created_date', 'Unknown Date')
                st.write(f"📅 {created_date[:10] if created_date != 'Unknown Date' else created_date}")
            with col3:
                overall_score = review.get('overall_score', 0)
                st.write(f"⭐ {overall_score:.1f}")
            with col4:
                # Review/Edit button
                if st.button("✏️ Review", key=f"review_btn_{review_id}", use_container_width=True):
                    st.session_state[f"editing_review_{review_id}"] = True
                    st.rerun()
            
            # Show basic info - add safe access
            col1, col2, col3 = st.columns(3)
            with col1:
                domain = review.get('domain', 'Unknown Domain')
                st.write(f"**Domain:** {domain}")
            with col2:
                reviewer = review.get('reviewer', 'Unknown Reviewer')
                st.write(f"**Reviewer:** {reviewer}")
            with col3:
                model_used = review.get('model_used', 'Unknown Model')
                st.write(f"**Model:** {model_used}")
              # Human review section (if editing)
            if st.session_state.get(f"editing_review_{review_id}", False):
                st.markdown("#### 👤 Human Review")
                
                col1, col2 = st.columns([1, 2])
                with col1:
                    review_quality = st.slider(
                        "Review Quality Score", 
                        min_value=0.0, max_value=10.0, step=0.1,
                        value=float(review.get('review_quality', 5.0)),
                        key=f"quality_{review_id}"
                    )
                with col2:
                    review_comment = st.text_area(
                        "Review Comments",
                        value=review.get('review_comment', ''),
                        height=100,
                        key=f"comment_{review_id}"
                    )
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("💾 Save Review", key=f"save_review_{review_id}", use_container_width=True):
                        if db.update_review_score(review_id, review_quality, review_comment):
                            st.success("✅ Review updated successfully!")
                            st.session_state[f"editing_review_{review_id}"] = False
                            st.rerun()
                        else:
                            st.error("❌ Failed to update review")
                
                with col2:
                    if st.button("❌ Cancel", key=f"cancel_review_{review_id}", use_container_width=True):
                        st.session_state[f"editing_review_{review_id}"] = False
                        st.rerun()
                
                with col3:
                    # View full analysis
                    if st.button("👁️ View Analysis", key=f"view_analysis_{review_id}", use_container_width=True):
                        st.session_state[f"viewing_analysis_{review_id}"] = True
                        st.rerun()
              # Show analysis details if viewing
            if st.session_state.get(f"viewing_analysis_{review_id}", False):
                st.markdown("#### 🔍 Analysis Details")
                analysis = review.get('analysis_data_parsed', {})
                
                if analysis:
                    if 'summary' in analysis:
                        st.markdown(f"**Summary:** {analysis['summary']}")
                    
                    if 'scores' in analysis:
                        st.markdown("**Scores:**")
                        score_cols = st.columns(len(analysis['scores']))
                        for idx, (criterion, score) in enumerate(analysis['scores'].items()):
                            with score_cols[idx]:
                                st.metric(criterion, f"{score}/5")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if 'strengths' in analysis and analysis['strengths']:
                            st.markdown("**Strengths:**")
                            for strength in analysis['strengths']:
                                st.write(f"• {strength}")
                    
                    with col2:
                        if 'weaknesses' in analysis and analysis['weaknesses']:
                            st.markdown("**Weaknesses:**")
                            for weakness in analysis['weaknesses']:
                                st.write(f"• {weakness}")
                
                if st.button("🔽 Hide Analysis", key=f"hide_analysis_{review_id}"):
                    st.session_state[f"viewing_analysis_{review_id}"] = False
                    st.rerun()
            
            # Current human review status
            review_quality = review.get('review_quality')
            if review_quality is not None:
                review_comment = review.get('review_comment', 'No comment')
                st.info(f"👤 Human Review: {review_quality:.1f}/10 - {review_comment}")
            
            st.markdown("---")

# --- Main Application ---
def main():
    """Main application function with error handling"""
    try:
        render_header()
        render_sidebar()
          # Page routing with error handling for each page
        try:
            if st.session_state.current_page == "criteria":
                render_criteria_management()
            elif st.session_state.current_page == "prompts":
                render_prompt_management()
            elif st.session_state.current_page == "analytics":
                render_analytics()
            elif st.session_state.current_page == "history":
                render_history_management()
            else:
                render_main_interface()
        except Exception as e:
            st.error(f"❌ Error in {st.session_state.current_page} page: {str(e)}")
            st.info("Please try refreshing the page or contact support if the issue persists.")
            
            # Option to reset to main page
            if st.button("🏠 Return to Main Page"):
                st.session_state.current_page = "main"
                st.rerun()
    
    except Exception as e:
        st.error(f"❌ Critical application error: {str(e)}")
        st.info("Please refresh the page to restart the application.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
