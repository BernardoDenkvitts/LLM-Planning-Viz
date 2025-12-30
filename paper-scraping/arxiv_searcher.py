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

MAXIMUM_KEYWORDS_ALLOWED = 12

# All categories available in arxiv
# Link https://arxiv.org/category_taxonomy
ARXIV_CATEGORIES = {
    "Computer Science": [
        "cs.AI", "cs.AR", "cs.CC", "cs.CE", "cs.CG", "cs.CL", "cs.CR", "cs.CV",
        "cs.CY", "cs.DB", "cs.DC", "cs.DL", "cs.DM", "cs.DS", "cs.ET", "cs.FL",
        "cs.GL", "cs.GR", "cs.GT", "cs.HC", "cs.IR", "cs.IT", "cs.LG", "cs.LO",
        "cs.MA", "cs.MM", "cs.MS", "cs.NA", "cs.NE", "cs.NI", "cs.OS",
        "cs.PF", "cs.PL", "cs.RO", "cs.SC", "cs.SD", "cs.SE", "cs.SI", "cs.SY"
    ],
    "Mathematics": [
        "math.AC", "math.AG", "math.AP", "math.AT", "math.CA", "math.CO",
        "math.CT", "math.CV", "math.DG", "math.DS", "math.FA", "math.GM",
        "math.GN", "math.GR", "math.GT", "math.HO", "math.IT", "math.KT",
        "math.LO", "math.MG", "math.MP", "math.NA", "math.NT", "math.OA",
        "math.OC", "math.PR", "math.QA", "math.RA", "math.RT", "math.SG",
        "math.SP", "math.ST"
    ],
    "Physics": [
        # physics archive
        "physics.acc-ph", "physics.ao-ph", "physics.app-ph", "physics.atm-clus",
        "physics.atom-ph", "physics.bio-ph", "physics.chem-ph", "physics.class-ph",
        "physics.comp-ph", "physics.data-an", "physics.ed-ph", "physics.flu-dyn",
        "physics.gen-ph", "physics.geo-ph", "physics.hist-ph", "physics.ins-det",
        "physics.med-ph", "physics.optics", "physics.plasm-ph", "physics.pop-ph",
        "physics.soc-ph", "physics.space-ph",

        # High Energy Physics
        "hep-ex", "hep-lat", "hep-ph", "hep-th",

        # Mathematical Physics
        "math-ph",

        # Condensed Matter
        "cond-mat.dis-nn", "cond-mat.mes-hall", "cond-mat.mtrl-sci",
        "cond-mat.other", "cond-mat.quant-gas", "cond-mat.soft",
        "cond-mat.stat-mech", "cond-mat.str-el", "cond-mat.supr-con",

        # Astrophysics
        "astro-ph.CO", "astro-ph.GA", "astro-ph.EP", "astro-ph.HE",
        "astro-ph.IM", "astro-ph.SR",

        # Other physics-related
        "gr-qc", "quant-ph",

        # Nonlinear sciences
        "nlin.AO", "nlin.CD", "nlin.CG", "nlin.PS", "nlin.SI",

        # Nuclear
        "nucl-ex", "nucl-th"
    ],
    "Statistics": [
        "stat.AP", "stat.CO", "stat.ME", "stat.ML", "stat.OT", "stat.TH"
    ],
    "Electrical Eng. & Systems Sci.": [
        "eess.AS", "eess.IV", "eess.SP", "eess.SY"
    ],
    "Quantitative Biology": [
        "q-bio.BM", "q-bio.CB", "q-bio.GN", "q-bio.MN", "q-bio.NC",
        "q-bio.OT", "q-bio.PE", "q-bio.QM", "q-bio.SC", "q-bio.TO"
    ],
    "Quantitative Finance": [
        "q-fin.CP", "q-fin.EC", "q-fin.GN", "q-fin.MF", "q-fin.PM",
        "q-fin.PR", "q-fin.RM", "q-fin.ST", "q-fin.TR"
    ],
    "Economics": [
        "econ.EM", "econ.GN", "econ.TH"
    ]
}


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


def build_arxiv_query(keywords: List[str], category: str = "cs") -> str:
    """
    Build an arXiv search query using title/abstract fields to a specific arxiv category.

    Args:
        keywords (List[str]): List of user-provided keywords or phrases.
        operator (str): Boolean operator to combine keywords ('AND' or 'OR').
        category (str): High-level arXiv category key mapped to multiple subcategories.
    """
    
    if category not in ARXIV_CATEGORIES.keys():
        raise ValueError(f"Invalid arxiv category. Categories available: {ARXIV_CATEGORIES.keys()}") 

    def clause(keyword: str) -> str:
        kw = keyword.strip().replace('"', "")

        # Quote multi-word keywords to ensure phrase matching in arXiv queries
        # ti = title; abs = abstract
        return f'(ti:"{kw}" OR abs:"{kw}")' if " " in kw else f'(ti:{kw} OR abs:{kw})'
    
    condition = f" AND ".join(clause(kw) for kw in keywords if kw.strip())
    subcategories = ARXIV_CATEGORIES[category]
    cat_condition = " OR ".join(f"cat:{sub}" for sub in subcategories)
    return f'({cat_condition}) AND ({condition})'


def search(keywords: str, start_date: datetime.date, end_date: datetime.date, sort_by: str, category: str) -> List[Paper]:
    """
    Search arXiv for papers matching the specified criteria.

    Args:
        keywords (str): str of keywords for filtering (e.g "time-series, forecasting").
        start_date (datetime.date): Start date.
        end_date (datetime.date): End date.
        sort_by (str): Sorting method, either 'relevance' or 'submitted'.
        category (str): Specific research category
    """
    logging.info("Querying arXiv for papers.")

    if end_date < start_date:
        raise ValueError("End Date must be greater than or equal to Start Date")

    if not keywords:
        raise ValueError("At least one keyword must be provided")

    keywords = [item.strip() for item in keywords.split(",")]
    if len(keywords) > MAXIMUM_KEYWORDS_ALLOWED:
        raise ValueError(f"Too many keywords provided ({len(keywords)}). Maximum allowed is {MAXIMUM_KEYWORDS_ALLOWED}.")

    start_date = start_date.strftime("%Y%m%d0000")
    end_date = end_date.strftime("%Y%m%d2359")
    date_range = f"AND submittedDate:[{start_date} TO {end_date}]"


    client = arxiv.Client()
    query = build_arxiv_query(keywords=keywords, category=category)
    # Fetch papers for the query
    query = f"{query} {date_range}"

    print("Keywords for filtering: ", keywords)
    print(f"Date Range: {start_date} - {end_date}")
    print(f"Query being used: {query}\n")

    search = arxiv.Search(
        query=query, max_results=200, sort_by=arxiv.SortCriterion.Relevance if sort_by == "relevance" else arxiv.SortCriterion.SubmittedDate
    )

    try:
        return [
            Paper(
                arxiv_id=result.get_short_id(),
                title=result.title,
                authors=[a.name for a in result.authors],
                abstract=result.summary,
                published=result.published,
                updated=result.updated,
                link=result.entry_id,
                pdf_link=result.pdf_url,
            )
            for result in client.results(search)
        ]
    except Exception as e:
        logging.error("Error getting results: %s", e)
        raise Exception("Error fetching papers")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test local arXiv search extraction.")

    parser.add_argument(
        "--keywords",
        type=str,
        default=None,
        help="Comma-separated keywords for filtering (e.g., 'planning,PDDL').",
    )

    parser.add_argument(
        "--category",
        type=str,
        choices=ARXIV_CATEGORIES.keys(),
        help="ArXiv categories",
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
        category=args.category
    )

    for i in range(len(results)):
        if i >= 5:
            break
        paper = results[i]
        print(f"[{i+1}] {paper.arxiv_id} - {paper.title}")
        print(f"Authors: {', '.join(paper.authors)}")
        print(paper.abstract)
        print()

    print()
    print(f"Total papers found: {len(results)}")