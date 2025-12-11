import argparse
from dataclasses import dataclass
import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional

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
    "ARXIV_EXTRACTOR_BASE_DIR", os.path.dirname(os.path.abspath(__file__))
)

# Setup paths
LOG_DIR = os.path.join(BASE_DIR, config["log_dir"])

DATE_FORMAT_RE = re.compile(r"^\d{12}$")  # YYYYMMDDHHMM

# Setup logging
logging.basicConfig(
    filename=os.path.join(
        LOG_DIR, f"arxiv_searcher_{datetime.now().strftime('%Y%m%d')}.log"
    ),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


# Define the main keywords we're interested in
#   `DEFAULT_MUST_INCLUDE_KEYWORDS` are our keywords for the main focus: large language models
#   `DEFAULT_OPTIONAL_KEYWORDS` represent the secondary focus: automated planning
#   However, we want to find papers that include both the main and secondary focus,
#   so 'optional' doesn't mean 'not important'
DEFAULT_MUST_INCLUDE_KEYWORDS = ["large language models", "LLMs", "GPT", "BERT", "transformers"]
DEFAULT_OPTIONAL_KEYWORDS = [
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

# Define queries
queries = [
    'cat:cs.AI AND ("large language models" OR "LLMs" OR "GPT" OR "BERT" OR transformers)',
    'cat:cs.AI AND ("automated planning" OR "symbolic planning" OR "neurosymbolic planning" OR "task planning" OR "AI planning")',
    'cat:cs.AI AND ("neural-symbolic" OR "neurosymbolic") AND planning',
    'cat:cs.AI AND ("large language models" OR "LLMs" OR "GPT" OR "BERT" OR transformers) AND planning',
    'cat:cs.AI AND ("large language models" OR "LLMs" OR "GPT" OR "BERT" OR transformers) AND PDDL',
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


def is_relevant(paper, DEFAULT_MUST_INCLUDE_KEYWORDS, optional_keywords) -> bool:
    """Check if the paper is relevant based on its title and abstract"""
    text = (paper.title + " " + paper.summary).lower()
    return any(keyword.lower() in text for keyword in DEFAULT_MUST_INCLUDE_KEYWORDS) and any(
        keyword.lower() in text for keyword in optional_keywords
    )


def parse_keyword_list(raw_keywords: Optional[str]) -> List[str]:
    """
    Parse a comma-separated string of keywords into a list.

    Example:
        "time series,forecasting" -> ["time series", "forecasting"]
    """
    if not raw_keywords:
        return []
    return [item.strip() for item in raw_keywords.split(",") if item.strip()]


def validate_date_str(date_str: str) -> str:
    """Validate that the date string is in the expected format YYYYMMDDHHMM."""
    if not DATE_FORMAT_RE.match(date_str):
        raise ValueError(f"Invalid date format '{date_str}'. Expected YYYYMMDDHHMM.")
    return date_str


def search(optional_keywords: List[str], start_date: str, end_date: str, sort_by: str) -> Dict[str, Paper]:
    """
    Search arXiv for papers matching the specified criteria.

    Args:
        optional_keywords (List[str]): List of optional keywords for filtering.
        start_date (str): Start date in YYYYMMDDHHMM format.
        end_date (str): End date in YYYYMMDDHHMM format.
        sort_by (str): Sorting method, either 'relevance' or 'submitted'.
    """
    logging.info("Querying arXiv for papers.")

    optional_keywords = optional_keywords if optional_keywords else DEFAULT_OPTIONAL_KEYWORDS
    start_date = validate_date_str(start_date)
    end_date = validate_date_str(end_date)

    date_range = f"AND submittedDate:[{start_date} TO {end_date}]"
    sort_option = arxiv.SortCriterion.Relevance if sort_by == "relevance" else arxiv.SortCriterion.SubmittedDate
    
    client = arxiv.Client()
    papers = {}

    # Fetch papers for each query
    for query in queries:
        try:
            query = f"{query} {date_range}"
            search = arxiv.Search(
                query=query, max_results=300, sort_by=sort_option
            )

            for result in client.results(search):
                if is_relevant(result, DEFAULT_MUST_INCLUDE_KEYWORDS, optional_keywords):
                    papers[result.entry_id] = Paper(
                        arxiv_id=result.get_short_id(),
                        title=result.title,
                        authors=[a.name for a in result.authors],
                        abstract=result.summary,
                        published=result.published,
                        updated=result.updated,
                        link=result.entry_id,
                        pdf_link=result.entry_id.replace("abs", "pdf"),
                    )
        except Exception as e:
            logging.error(f"Error executing query '{query}': {str(e)}")
    return papers


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test local arXiv search extraction.")

    parser.add_argument(
        "--optional_keywords",
        type=str,
        default=None,
        help="Comma-separated optional keywords for filtering (e.g., 'planning,PDDL').",
    )

    parser.add_argument(
        "--start_date",
        type=str,
        default=None,
        help="Start date in YYYYMMDDHHMM format.",
    )

    parser.add_argument(
        "--end_date",
        type=str,
        default=None,
        help="End date in YYYYMMDDHHMM format.",
    )

    parser.add_argument(
        "--sort_by",
        type=str,
        default="relevance",
        choices=["relevance", "submitted"],
        help="Sorting method for arXiv results.",
    )

    args = parser.parse_args()

    results = search(
        optional_keywords=parse_keyword_list(args.optional_keywords),
        start_date=args.start_date,
        end_date=args.end_date,
        sort_by=args.sort_by,
    )

    print(f"Total papers found: {len(results)}")
    print()

    for i, (k, v) in enumerate(results.items()):
        if i >= 5:
            break

        print(f"[{i+1}] {v.arxiv_id} - {v.title}")
        print(f"Authors: {', '.join(v.authors)}")
        print(f"Published: {v.published}")
        print(f"PDF Link: {v.pdf_link}")
        print()