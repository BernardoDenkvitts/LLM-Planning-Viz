import argparse
from dataclasses import dataclass
import json
import logging
import os
from datetime import date, datetime
from typing import List

import arxiv


# Load configuration
def load_config():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    with open(config_path, "r") as f:
        return json.load(f)


config = load_config()

# Use environment variable if set, otherwise use config file
BASE_DIR: str = os.environ.get(
    "ARXIV_SEARCHER_BASE_DIR", os.path.dirname(os.path.abspath(__file__))
)

# Setup paths
LOG_DIR = os.path.join(BASE_DIR, config["log_dir"])

# Setup logging
logging.basicConfig(
    filename=os.path.join(
        LOG_DIR, f"arxiv_searcher_{datetime.now().strftime('%Y%m%d')}.log"
    ),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


DEFAULT_KEYWORDS = [
    "automated planning",
    "symbolic planning",
    "neurosymbolic planning",
    "task planning",
    "AI planning",
    "PDDL",
    "constraint-based planning",
    "hierarchical task planning",   
    "multi-agent planning",
    "robot planning",
]

@dataclass
class Paper:
    arxiv_id: str
    title: str
    authors: List[str] 
    abstract: str
    published: datetime
    updated: datetime
    link: str
    pdf_link: str


def build_arxiv_query(keywords: List[str], operator: str, category: str="cs.AI"):
    """Create arxiv query based on keywords and category"""
    def format(keyword: str) -> str:
        # Quote only multi-word phrases
        return f'"{keyword}"' if " " in keyword else keyword
    
    condition = f" {operator} ".join(format(kw) for kw in keywords)
    return f'cat:{category} AND ({condition})'


def is_relevant(paper, must_include) -> bool:
    text = (paper.title + " " + paper.summary).lower()
    return any(keyword.lower() in text for keyword in must_include)


def search(keywords: str, start_date: datetime.date, end_date: datetime.date, sort_by: str) -> List[Paper]:
    """
    Search arXiv for papers matching the specified criteria.

    Args:
        keywords str: str of keywords for filtering (e.g "time-series, forecasting"). If empty (""), the function uses
            the default keyword list defined in DEFAULT_KEYWORDS.
        start_date datetime.date: Start date.
        end_date datetime.date: End date.
        sort_by (str): Sorting method, either 'relevance' or 'submitted'.
    """
    logging.info("Querying arXiv for papers.")

    if end_date < start_date:
        raise ValueError("End Date must be greater than or equal to Start Date")

    start_date = start_date.strftime("%Y%m%d0000")
    end_date = end_date.strftime("%Y%m%d2359")

    date_range = f"AND submittedDate:[{start_date} TO {end_date}]"

    print(f"Date Range: {start_date} - {end_date}")

    client = arxiv.Client()
    papers = []

    is_default_keywords = not keywords
    keywords = DEFAULT_KEYWORDS if is_default_keywords else [item.strip() for item in keywords.split(",")]
    query = build_arxiv_query(keywords=keywords, operator="OR" if is_default_keywords else "AND")

    print("Keywords for filtering:", keywords)

    # Fetch papers for the query
    query = f"{query} {date_range}"
    print(f"Query being used: {query}")
    search = arxiv.Search(
        query=query, max_results=200, sort_by=arxiv.SortCriterion.Relevance if sort_by == "relevance" else arxiv.SortCriterion.SubmittedDate
    )

    for result in client.results(search):
        if is_relevant(result, keywords):
            papers.append(Paper(
                arxiv_id=result.get_short_id(),
                title=result.title,
                authors=[a.name for a in result.authors],
                abstract=result.summary,
                published=result.published,
                updated=result.updated,
                link=result.entry_id,
                pdf_link=result.pdf_url,
            ))
    return papers


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test local arXiv search extraction.")

    parser.add_argument(
        "--keywords",
        type=str,
        default=None,
        help="Comma-separated keywords for filtering (e.g., 'planning,PDDL').",
    )

    parser.add_argument(
        "--start_date",
        type=str,
        default="2024-01-01",
        help="Start date in YYYY-MM-DD format.",
    )

    parser.add_argument(
        "--end_date",
        type=str,
        default=None,
        help="End date in YYYY-MM-DD format.",
    )

    parser.add_argument(
        "--sort_by",
        type=str,
        default="relevance",
        choices=["relevance", "submitted"],
        help="Sorting method for arXiv results.",
    )

    args = parser.parse_args()

    end_date = args.end_date if args.end_date != None else str(date.today())

    results = search(
        keywords=args.keywords,
        start_date=datetime.strptime(args.start_date, "%Y-%m-%d").date(),
        end_date=datetime.strptime(end_date, "%Y-%m-%d").date(),
        sort_by=args.sort_by,
    )

    print(f"Total papers found: {len(results)}")
    print()

    for i in range(len(results)):
        if i >= 3:
            break
        paper = results[i]
        print(f"[{i+1}] {paper.arxiv_id} - {paper.title}")
        print(f"Authors: {', '.join(paper.authors)}")
        print(paper.abstract)
        print()