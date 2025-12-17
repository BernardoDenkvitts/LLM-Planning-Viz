import argparse
from dataclasses import dataclass
import json
import logging
import os
from datetime import datetime
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
    "ARXIV_EXTRACTOR_BASE_DIR", os.path.dirname(os.path.abspath(__file__))
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


def is_relevant(paper, must_include: List[str], optional_keywords: List[str]) -> bool:
    """Check if the paper is relevant based on its title and abstract"""
    text = (paper.title + " " + paper.summary).lower()
    return any(keyword.lower() in text for keyword in must_include) and any(
        keyword.lower() in text for keyword in optional_keywords
    )


def search(optional_keywords: str, start_date: datetime.date, end_date: datetime.date, sort_by: str) -> List[Paper]:
    """
    Search arXiv for papers matching the specified criteria.

    Args:
        optional_keywords str: str of optional keywords for filtering (e.g "time-series, forecasting"). If empty (""), the function uses
            the default optional keyword list defined in DEFAULT_OPTIONAL_KEYWORDS.
        start_date datetime.date: Start date.
        end_date datetime.date: End date.
        sort_by (str): Sorting method, either 'relevance' or 'submitted'.
    """
    logging.info("Querying arXiv for papers.")

    if end_date < start_date:
        raise ValueError("End Date must be greater than or equal to Start Date")

    optional_keywords = DEFAULT_OPTIONAL_KEYWORDS if not optional_keywords else [item.strip() for item in optional_keywords.split(",")]
    print("Optional keywords for filtering:", optional_keywords)

    start_date = start_date.strftime("%Y%m%d0000")
    end_date = end_date.strftime("%Y%m%d2359")

    date_range = f"AND submittedDate:[{start_date} TO {end_date}]"
    sort_option = arxiv.SortCriterion.Relevance if sort_by == "relevance" else arxiv.SortCriterion.SubmittedDate
    
    print(f"Date Range: {start_date} - {end_date}")

    client = arxiv.Client()
    papers = []

    # Fetch papers for each query
    for query in queries:
        try:
            query = f"{query} {date_range}"
            search = arxiv.Search(
                query=query, max_results=200, sort_by=sort_option
            )

            for result in client.results(search):
                if is_relevant(result, DEFAULT_MUST_INCLUDE_KEYWORDS, optional_keywords):
                    papers.append(Paper(
                        arxiv_id=result.get_short_id(),
                        title=result.title,
                        authors=[a.name for a in result.authors],
                        abstract=result.summary,
                        published=result.published,
                        updated=result.updated,
                        link=result.entry_id,
                        pdf_link=result.entry_id.replace("abs", "pdf"),
                    ))
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

    results = search(
        optional_keywords=args.optional_keywords,
        start_date=datetime.strptime(args.start_date, "%Y-%m-%d").date(),
        end_date=datetime.strptime(args.end_date, "%Y-%m-%d").date(),
        sort_by=args.sort_by,
    )

    print(f"Total papers found: {len(results)}")
    print()

    for i in range(len(results)):
        if i >= 5:
            break
        paper = results[i]
        print(f"[{i+1}] {paper.arxiv_id} - {paper.title}")
        print(f"Authors: {', '.join(paper.authors)}")
        print(paper.abstract)
        print()