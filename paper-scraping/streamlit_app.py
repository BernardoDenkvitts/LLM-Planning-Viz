from typing import List, cast
import streamlit as st
from datetime import datetime, date, timedelta

from arxiv_searcher import (
    Paper,
    search,
    DEFAULT_OPTIONAL_KEYWORDS
)

st.set_page_config(
    page_title="AI4Society-ArXiv Searcher",
    page_icon="📚",
    layout="centered",

)

st.markdown("""
<style>
    header[data-testid="stHeader"]::before {
        content: "AI4Society";
        font-size: 1.3rem;
        font-weight: 600;
        padding-left: 2rem;
        display: flex;
        align-items: center;
        height: 100%;
        border-bottom: 1px solid;
    }

    /* st.title */
    .block-container h1 {
        text-align: center;
        margin-top: -2rem !important;
        margin-bottom: 2rem !important;
        font-weight: 700;
        font-size: 2rem;
        letter-spacing: -0.5px;
    }

    .page-subtitle {
        text-align: center;
        margin-top: -2.6rem;
        font-size: 0.95rem;
        opacity: 0.7;
    }

    .paper-title {
        font-size: 1rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        line-height: 1.4;
    }
    
    /* Reduce the padding of the expansion button. */
    div[data-testid="stExpander"] summary {
        padding: 0.3rem 1rem !important;
    }

    .paper-authors, .paper-metadata {
        font-size: 0.9rem;
    }
    
    .paper-abstract {
        font-size: 1rem;
        text-align: justify;
    }
    
    .results-count {
        font-size: 1.2rem;
        font-weight: 700;
        margin-bottom: 1.5rem;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: white;
        border-radius: 8px;
        padding: 0.5rem 0.7rem;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(37,99,235,0.4);
        color: white;
        border-color: transparent;
    }

    .stButton>button:active,
        .stButton>button:focus:not(:active) {
        border-color: transparent !important;
        outline: none !important;
        box-shadow: 0 4px 12px rgba(37,99,235,0.4) !important;
        color: black;
    }

    /* Input fields */
    .stTextInput>div>div>input {
        border-radius: 8px;
    }
            
    /* Centralize container's columns */
    div[data-testid="stHorizontalBlock"] {
        width: 100%;
        margin: 0 auto;
    }

    /* Errors/Tracebacks */
    div[data-testid="stAlertContentError"],
    div[data-testid="stAlertContentError"] * {
        color: #000000;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=timedelta(hours=1), max_entries=1000, show_spinner=False)
def search_papers(keywords: str, start_date: date, end_date: date, sort_opt: str):
    return search(
        optional_keywords=keywords,
        start_date=start_date,       
        end_date=end_date,
        sort_by=sort_opt
    )


ORDER_BY_OPTIONS = {
    "Relevance": "relevance",
    "Submitted Date": "submitted",
}

# Initialize session state
if "papers" not in st.session_state:
    st.session_state["papers"] = []

if "searched" not in st.session_state:
    st.session_state["searched"] = False

st.title("ArXiv Paper Search", anchor=False)
st.markdown(f'<div class="page-subtitle">Discover research papers on Large Language Models and related topics</div>', unsafe_allow_html=True)

keywords = st.text_input(
    "Search Keywords",
    placeholder="e.g., time-series, forecasting",
    help=f"Leave empty to use the default keywords: {', '.join(DEFAULT_OPTIONAL_KEYWORDS)}",
)

col_start_date, col_end_date, col_order_by, col_search_bt = st.columns([1, 1, 1.5, 1], vertical_alignment="center")

with col_start_date:
    start_date = st.date_input(
        "Start Date",
        value=None
    )

with col_end_date:
    end_date = st.date_input(
        "End Date",
        value="today"
    )

with col_order_by:
    sort_option = st.selectbox(
        "Order By",
        ORDER_BY_OPTIONS.keys()
    )

with col_search_bt:
    # Keeps button's vertical alignment
    st.markdown("<div style='height: 1.7rem;'></div>", unsafe_allow_html=True)
    search_button = st.button("Search")

# On click
if search_button:
    st.session_state["searched"] = False
    with st.spinner("🔎 Searching papers..."):
        # Starts from last year 01/01 at 00:00
        if start_date is None:
            start_date = date(date.today().year - 1, 1, 1)
        try:
            st.session_state["papers"] = search_papers(keywords=keywords, start_date=start_date, end_date=end_date, sort_opt=sort_option.lower())
            st.session_state["searched"] = True
        except Exception as e:
            st.error(e)

if st.session_state["searched"] and st.session_state["papers"]:
    col_results = st.columns(1)[0]
    with col_results:
        # Show number of results
        st.markdown(
            f"<div class='results-count'>{len(st.session_state['papers'])} Papers Found</div>",
            unsafe_allow_html=True
        )
    
    papers = cast(List[Paper], st.session_state["papers"])
    # Show each paper
    for paper in papers:
        paper_date = paper.published.strftime("%d/%m/%Y")
        st.markdown(f"""
            <div class="paper-card">
                <div class="paper-title">{paper.title}</div>
                <div class="paper-metadata">
                    <span class="metadata-item">📅 {paper_date}</span>
                    <span class="metadata-item">🔗 <a href="{paper.link}">View on arXiv</a></span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        with st.expander("View details"):
            authors_str = ", ".join(paper.authors)
            st.markdown(f"""
                <div class='paper-authors'><strong>Authors:</strong> {authors_str}</div>
                [📄 <a href='{paper.pdf_link}'>PDF</a>]
                <div class='paper-abstract'><strong>Abstract</strong><br>{paper.abstract}</div>
            """, unsafe_allow_html=True)

elif st.session_state["searched"] and not st.session_state["papers"]:
    # Empty state
    st.info("🔍No papers found. Try adjusting your keywords or search period.")

