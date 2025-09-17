# %%
import csv
import os
import requests
import xml.etree.ElementTree as ET
import time
# %%

def get_pmids_from_csv(csv_path='merged_output.csv'):
    """
    Reads merged_output.csv and returns a list of all unique PMIDs.
    """
    pmids = set()
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            pmid = row.get('PMID')
            if pmid:
                pmids.add(pmid)
    return list(pmids)

def fetch_pubmed_article_for_endnote(pmid):
    """
    Retrieve all relevant information for an article using the PubMed API (NCBI E-utilities)
    based on PMID, and return a dictionary suitable for EndNote import.
    """
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": pmid,
        "retmode": "xml"
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    root = ET.fromstring(response.text)

    article = root.find(".//PubmedArticle")
    if article is None:
        raise ValueError(f"No article found for PMID {pmid}")

    # Title
    title = article.findtext(".//ArticleTitle", default="")

    # Abstract
    abstract = " ".join([elem.text for elem in article.findall(".//AbstractText") if elem.text])

    # Journal
    journal = article.findtext(".//Journal/Title", default="")

    # Year, Volume, Issue, Pages
    year = article.findtext(".//JournalIssue/PubDate/Year", default="")
    volume = article.findtext(".//JournalIssue/Volume", default="")
    issue = article.findtext(".//JournalIssue/Issue", default="")
    pages = article.findtext(".//MedlinePgn", default="")

    # Authors
    authors = []
    for author in article.findall(".//AuthorList/Author"):
        last = author.findtext("LastName", default="")
        fore = author.findtext("ForeName", default="")
        if last and fore:
            authors.append(f"{last}, {fore}")
        elif last:
            authors.append(last)

    # PMID
    pmid_val = article.findtext(".//PMID", default=pmid)

    return {
        "Title": title,
        "Abstract": abstract,
        "Journal": journal,
        "Year": year,
        "Volume": volume,
        "Issue": issue,
        "Pages": pages,
        "Authors": authors,
        "PMID": pmid_val
    }

def generate_enw_from_pubmed(pmids, pdf_dir='pubmed_pdfs', output_enw='endnote_import/output.enw'):
    """
    For a list of PMIDs, fetch article info from PubMed and generate an EndNote .enw file.
    Checks for corresponding PDFs in pdf_dir.
    """
    os.makedirs(os.path.dirname(output_enw), exist_ok=True)
    with open(output_enw, 'w', encoding='utf-8') as enwfile:
        for pmid in pmids:
            try:
                article = fetch_pubmed_article_for_endnote(pmid)
            except Exception as e:
                print(f"Error fetching PMID {pmid}: {e}")
                continue
            pdf_path = os.path.join(pdf_dir, f"{pmid}.pdf")
            has_pdf = os.path.isfile(pdf_path)
            if not has_pdf:
                continue
            enwfile.write('%0 Journal Article\n')
            # Authors
            for author in article.get("Authors", []):
                enwfile.write(f'%A {author}\n')
            # Title
            enwfile.write(f'%T {article.get("Title", "")}\n')
            # Journal
            enwfile.write(f'%J {article.get("Journal", "")}\n')
            # Year
            enwfile.write(f'%D {article.get("Year", "")}\n')
            # Volume
            enwfile.write(f'%V {article.get("Volume", "")}\n')
            # Issue
            enwfile.write(f'%N {article.get("Issue", "")}\n')
            # Pages
            enwfile.write(f'%P {article.get("Pages", "")}\n')
            # PMID
            enwfile.write(f'%M {article.get("PMID", pmid)}\n')
            # Abstract
            if article.get("Abstract", ""):
                enwfile.write(f'%X {article.get("Abstract", "")}\n')
            
            enwfile.write('\n')  # End of record
            time.sleep(0.34)  # Wait to respect NCBI rate limits
    print(f"EndNote .enw file generated: {output_enw}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Export PubMed articles to EndNote .enw format")
    parser.add_argument('--input_csv', type=str, default='merged_output.csv', help='CSV file with PMIDs')
    parser.add_argument('--pdf_dir', type=str, default='pubmed_pdfs', help='Directory containing PDFs')
    parser.add_argument('--output_enw', type=str, default='endnote_import/output.enw', help='Output .enw file path')
    args = parser.parse_args()

    pmid_list = get_pmids_from_csv(args.input_csv)
    generate_enw_from_pubmed(pmid_list, pdf_dir=args.pdf_dir, output_enw=args.output_enw)
