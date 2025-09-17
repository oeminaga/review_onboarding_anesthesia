# %%
import csv
import time
import json
from openai import OpenAI
from Bio import Entrez
import logging
from dotenv import load_dotenv
import os

from tqdm import tqdm
# Setting up logging
# Configure your own logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("pubmed_analysis.log"),  # Save to this file
                        logging.StreamHandler()  # Also print to console
                        ])
# save the logging files
logger = logging.getLogger(__name__)

# -------------------------------
# Configuration
# -------------------------------
# GET FROM .ENV or other secure place
load_dotenv()
Entrez.email = os.getenv("ENTREZ_EMAIL")  # Always tell NCBI who you are
CLAUDIA_API_KEY = os.getenv("CLAUDIA_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def extract_ids(article):
    """Extract PMC, PMID, and DOI from PubmedArticle."""
    ids = {'pmc': None, 'pubmed': None, 'doi': None}
    try:
        for aid in article.get('PubmedData', {}).get('ArticleIdList', []):
            id_type = aid.attributes.get('IdType')
            if id_type in ids:
                ids[id_type] = str(aid)
    except Exception as e:
        logger.warning(f"Failed to extract IDs: {e}")
    return ids


def get_pubmed_abstracts_paged(query, start_date, end_date,
                               total_limit=50, batch_size=10, delay=1):
    abstracts = []
    retstart = 0

    logger.info(f"🔍 Searching PubMed with query: {query}")
    logger.info(f"📅 Date range: {start_date} to {end_date}")
    logger.info(f"📊 Total limit: {total_limit}, Batch size: {batch_size}, ⏳ Delay: {delay}s")

    prog = tqdm(total=total_limit, desc="Fetching abstracts")

    while retstart < total_limit:
        try:
            search_handle = Entrez.esearch(
                db="pubmed",
                term=query,
                retmax=batch_size,
                retstart=retstart,
                datetype="pdat",
                mindate=start_date,
                maxdate=end_date
            )
            search_results = Entrez.read(search_handle)
            search_handle.close()

            id_list = search_results.get("IdList", [])
            if not id_list:
                logger.info(f"🔍 No more results found. Total abstracts fetched: {len(abstracts)}")
                break

            fetch_handle = Entrez.efetch(
                db="pubmed",
                id=",".join(id_list),
                retmode="xml"
            )
            records = Entrez.read(fetch_handle)
            fetch_handle.close()

            for article in records.get('PubmedArticle', []):
                try:
                    citation = article['MedlineCitation']
                    article_data = citation['Article']
                    ids = extract_ids(article)

                    title = article_data.get('ArticleTitle', '')
                    abstract_parts = article_data.get('Abstract', {}).get(
                        'AbstractText', [])
                    abstract = ' '.join(
                        str(p) for p in abstract_parts
                        ) if abstract_parts else ''

                    authors = ', '.join(
                        f"{a.get('LastName', '')} {a.get('ForeName', '')}".strip()
                        for a in article_data.get('AuthorList', [])
                        if 'LastName' in a and 'ForeName' in a
                    )

                    journal = article_data.get('Journal', {}).get('Title', '')
                    pub_date = article_data.get('Journal', {}).get('JournalIssue', {}).get('PubDate', {})
                    year = pub_date.get('Year', '')

                    pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{ids['pubmed']}" if ids['pubmed'] else None
                    pmc_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{ids['pmc']}" if ids['pmc'] else None

                    abstracts.append({
                        "pmid": ids['pubmed'],
                        "pmc": ids['pmc'],
                        "doi": ids['doi'],
                        "title": title,
                        "abstract": abstract,
                        "authors": authors,
                        "journal": journal,
                        "year": year,
                        "pubmed_url": pubmed_url,
                        "pmc_url": pmc_url
                    })

                    if len(abstracts) >= total_limit:
                        prog.update(total_limit)
                        prog.close()
                        return abstracts

                except Exception as article_error:
                    logger.warning(f"⚠️ Skipped one article due to error: {article_error}")
                    continue

            retstart += batch_size
            prog.update(len(id_list))
            prog.set_postfix(Fetched=len(abstracts))
            time.sleep(delay)

        except Exception as e:
            logger.error(f"❌ PubMed API error: {e}")
            break

    prog.close()
    return abstracts


def analyze_with_claudia(title, abstract):
    """
    Uses Anthropic's Claude model to extract onboarding-related data from abstract.
    """
    import anthropic
    client = anthropic.Anthropic(api_key=CLAUDIA_API_KEY)  # Replace with your Anthropic API key

    prompt = f"""
                You are an academic assistant. Based on the title and abstract below, determine if this study is about onboarding.
                If it is, extract:
                0. Is this study related to onboarding/mentorship in anesthesiology or pain care?
                1. Onboarding strategy
                2. Target population
                3. Anticipated outcomes

                Return only a JSON object with keys:
                - is_related_to_onboarding
                - onboarding_strategy
                - target_population
                - anticipated_outcome

                Title: {title}
                Abstract: {abstract}
                
                BE VERY PRECISE AND CONCISE. DO NOT ADD ANYTHING ELSE.
                BE SURE IT IS RELATED TO ONBOARDING IN ANESTHESIOLOGY OR PAIN CARE.
                """

    try:
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1024,
            temperature=0.01,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        content = response.content[0].text
        content = content.strip('`').replace('json\n', '').replace('```', '').strip()
        return json.loads(content)
    except Exception as e:
        print(f"❌ Claudia API error: {e}")
        return {}


def analyze_with_openai(title, abstract):
    prompt = f"""
    You are an expert in medical education. Based on the title and abstract below, determine:
    0. Is this study related to onboarding/mentorship in anesthesiology or pain care?
    1. Is it related to onboarding?
    2. If yes, extract:
       - Onboarding strategy
       - Target population
       - Anticipated outcomes

    Return only a JSON object with keys:
    - is_related_to_onboarding (true or false)
    - onboarding_strategy
    - target_population
    - anticipated_outcome

    Title: {title}
    Abstract: {abstract}
    
    BE VERY PRECISE AND CONCISE. DO NOT ADD ANYTHING ELSE.
    BE SURE IT IS RELATED TO ONBOARDING IN ANESTHESIOLOGY OR PAIN CARE.
    """

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.responses.create(
            model="gpt-4",
            instructions="Analyze the following medical abstract for onboarding-related content for anesthesiology.",
            input=prompt,
            temperature=0.01
        )
        content = response.output_text
        content = content.strip('`').replace('json\n', '').replace('```', '').strip()
        return json.loads(content)
    except Exception as e:
        print(f"❌ OpenAI API error: {e}")
        return {}


def save_results_to_csv(data, filename="pubmed_dual_llm_analysis.csv"):
    fieldnames = [
        "Title", "Abstract", "Authors", "Journal", "Year", "PMID", "PMC",
        "DOI", "pubmed_url", "pmc_url",
        "ClaudiaIsRelated", "ClaudiaStrategy", "ClaudiaPopulation",
        "ClaudiaOutcome",
        "OpenAIIsRelated", "OpenAIStrategy", "OpenAIPopulation",
        "OpenAIOutcome"
    ]
    with open(filename, mode="w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    print(f"✅ CSV saved to {filename}")


def main():
    query = '"anesthesiology" AND ("onboarding" OR "orientation" OR "mentorship" OR "induction training")'
    start_date = "2015/01/01"
    end_date = "2025/05/01"
    total_limit = 1000

    print("🔍 Fetching PubMed abstracts...")
    # save the logging file
    Entrez.log_file = "./pubmed_analysis.log"
    logger.info(f"Query: {query}, Start Date: {start_date}, End Date: {end_date}, Total Limit: {total_limit}")
    abstracts = get_pubmed_abstracts_paged(query,
                                           start_date,
                                           end_date,
                                           total_limit=total_limit)
    final_results = []

    for i, entry in enumerate(abstracts, start=1):
        print(f"\n📄 [{i}/{len(abstracts)}] Analyzing: {entry['title'][:80]}...")
        logging.info(f"Analyzing abstract {i}/{len(abstracts)}: {entry['title'][:80]}")
        """
        if not entry["abstract"]:
            print("❌ No abstract found, skipping...")
            logging.warning(f"No abstract found for entry {i}, skipping...")
            final_results.append({
                "Title": entry["title"],
                "Abstract": entry["abstract"],
                "Authors": entry["authors"],
                "Journal": entry["journal"],
                "Year": entry["year"],
                "ClaudiaIsRelated": "NA",
                "ClaudiaStrategy": "NA",
                "ClaudiaPopulation": "NA",
                "ClaudiaOutcome": "NA",
                "OpenAIIsRelated": "NA",
                "OpenAIStrategy": "NA",
                "OpenAIPopulation": "NA",
                "OpenAIOutcome": "NA"
            })
            continue
        """
        claudia_result = analyze_with_claudia(entry["title"], entry["abstract"])
        openai_result = analyze_with_openai(entry["title"], entry["abstract"])
        logging.info("web scraping completed successfully")

        final_results.append({
            "Title": entry["title"],
            "Abstract": entry["abstract"],
            "Authors": entry["authors"],
            "Journal": entry["journal"],
            "Year": entry["year"],
            "PMID": entry["pmid"],
            "PMC": entry["pmc"],
            "DOI": entry["doi"],
            "pubmed_url": entry["pubmed_url"],
            "pmc_url": entry["pmc_url"],
            "ClaudiaIsRelated": claudia_result.get("is_related_to_onboarding", ""),
            "ClaudiaStrategy": claudia_result.get("onboarding_strategy", ""),
            "ClaudiaPopulation": claudia_result.get("target_population", ""),
            "ClaudiaOutcome": claudia_result.get("anticipated_outcome", ""),
            "OpenAIIsRelated": openai_result.get("is_related_to_onboarding", ""),
            "OpenAIStrategy": openai_result.get("onboarding_strategy", ""),
            "OpenAIPopulation": openai_result.get("target_population", ""),
            "OpenAIOutcome": openai_result.get("anticipated_outcome", ""),
        })

        time.sleep(2)

    save_results_to_csv(final_results)
#%%
if __name__ == "__main__":
    main()
