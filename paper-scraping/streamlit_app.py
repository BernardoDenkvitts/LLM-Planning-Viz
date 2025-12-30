from pathlib import Path
from typing import List
import streamlit as st
from datetime import date, timedelta

from arxiv_searcher import (
    Paper,
    search,
    ARXIV_CATEGORIES
)

st.set_page_config(
    page_title="AI4Society-ArXiv Searcher",
    page_icon="📚",
    layout="centered"
)

def load_css(file_path: str):
    """Load CSS from external file."""
    with open(file_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


css_path = Path(__file__).parent / "styles.css"
load_css(css_path)

@st.cache_data(ttl=timedelta(hours=1), max_entries=1000, show_spinner=False)
def search_papers(keywords: str, start_date: date, end_date: date, sort_opt: str, category_option: str) -> List[Paper]:
    return search(
        keywords=keywords,
        start_date=start_date,       
        end_date=end_date,
        sort_by=sort_opt,
        category=category_option
    )


ORDER_BY_OPTIONS = {
    "Relevance": "relevance",
    "Submitted Date": "submitted",
}

DEFAULT_KEYWORDS = "large language models, multi-agent systems"

# Initialize session state
if "search_results" not in st.session_state:
    st.session_state["search_results"] = {
        "papers": [],
        "searched": False
    }

st.title("ArXiv Paper Search", anchor=False)
st.markdown(f'<div class="page-subtitle">Discover and explore research papers across the arXiv using keyword-based search</div>', unsafe_allow_html=True)

col_keywords, col_category = st.columns([2.5, 1])

with col_keywords:
    keywords = st.text_input(
        "Search Keywords or Phrases",
        placeholder=f"e.g., {DEFAULT_KEYWORDS} ...",
        help=("Enter one or more keywords or phrases separated by commas. "
            "Results include only papers where all keywords are present. "
            f"If left empty, the default keywords - {DEFAULT_KEYWORDS} - will be used."
        )
    )

with col_category:
    category_option = st.selectbox(
        "Category",
        ARXIV_CATEGORIES.keys(),
        index=0,
        help="Focus your search on a specific research field"
    )

col_start_date, col_end_date, col_order_by, col_search_bt = st.columns([1, 1, 1.5, 1], vertical_alignment="center")

with col_start_date:
    start_date = st.date_input(
        "Start Date",
        value=date(date.today().year - 1, 1, 1)
    )

with col_end_date:
    end_date = st.date_input(
        "End Date",
        value="today"
    )

with col_order_by:
    sort_option = st.selectbox(
        "Order By",
        ORDER_BY_OPTIONS.keys(),
        help="Order applied to ArXiv search"
    )

with col_search_bt:
    # Keeps button's vertical alignment
    st.markdown("<div style='height: 1.7rem;'></div>", unsafe_allow_html=True)
    search_button = st.button("Search")

# On click
if search_button:
    st.session_state["search_results"]["searched"] = False
    with st.spinner("🔎 Searching papers..."):
        # Starts from last year 01/01 at 00:00
        if start_date is None:
            start_date = date(date.today().year - 1, 1, 1)
        try:
            if not keywords:
                keywords = DEFAULT_KEYWORDS

            st.session_state["search_results"]["papers"] = search_papers(keywords=keywords, start_date=start_date, end_date=end_date, sort_opt=sort_option.lower(), category_option=category_option)
            st.session_state["search_results"]["searched"] = True
        except Exception as e:
            if str(e) != "Error fetching papers":
                st.error(f"⚠️ An error occurred: {e}")
            else:
                st.warning("We couldn't fetch papers right now. Please try again in a few minutes.")

if st.session_state["search_results"]["searched"] and st.session_state["search_results"]["papers"]:
    col_results = st.columns(1)[0]
    with col_results:
        # Show number of results
        st.markdown(
            f"<div class='results-count'>{len(st.session_state['search_results']['papers'])} Papers Found</div>",
            unsafe_allow_html=True
        )

    # Show each paper
    for paper in st.session_state["search_results"]["papers"]:
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

elif st.session_state["search_results"]["searched"] and not st.session_state["papers"]:
    # Empty state
    st.info("🔍 No papers found. Try adjusting your keywords or search period.")