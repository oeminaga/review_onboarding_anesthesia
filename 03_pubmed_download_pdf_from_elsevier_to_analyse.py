# %%
import requests
from tqdm import tqdm
import pandas as pd
import time
import re
import requests
from bs4 import BeautifulSoup
import time
import os
import re
import traceback

from urllib.parse import urljoin

import argparse

def get_args():
    parser = argparse.ArgumentParser(description="Download PubMed PDFs from Elsevier")
    parser.add_argument('--output_folder', type=str, default='./pubmed_pdfs/', help='Folder to store downloaded PDFs')
    parser.add_argument('--csv_file', type=str, default='pubmed_create_csv_file_to_in_depth_analyse.csv', help='CSV file with PMIDs')
    return parser.parse_args()

args = get_args()
TO_STORE = args.output_folder
filename = args.csv_file


# Function to ensure the directory exists
def ensure_directory_exists(directory):
    import os
    if not os.path.exists(directory):
        os.makedirs(directory)


from bs4 import BeautifulSoup
import requests
import os

from playwright.sync_api import sync_playwright
import os

import requests
import os
import xml.etree.ElementTree as ET
import time
import glob
import requests
import os
import xml.etree.ElementTree as ET

from urllib.request import urlretrieve
from urllib.parse import urlparse

def get_url(pmc_id):
    import requests
from bs4 import BeautifulSoup
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.support import expected_conditions as EC
import time
import os

import chromedriver_autoinstaller
chromedriver_autoinstaller.install()

# Set up Chrome options

import undetected_chromedriver as uc

def download_pdf_with_selenium(pmc_id):
    if os.path.exists(os.path.join(TO_STORE, f"{pmc_id}.pdf")):
        print(f"PDF for PMC ID {pmc_id} already exists. Skipping download.")
        return True
    """Download PDF using Selenium with better wait times and error handling"""
    article_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmc_id}"# f"https://pmc.ncbi.nlm.nih.gov/articles/{pmc_id}/"
    print(f"Accessing article page with Selenium: {article_url}")
    driver = None

    # Configure browser options
    # 
    try:
        options = uc.ChromeOptions()
        options.add_argument('--no-first-run --no-service-autorun --password-store=basic')
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlled')
    
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.7151.69 Safari/537.36")

        # Set up download preferences
        download_dir = os.path.abspath(TO_STORE)
        prefs = {
            "download.default_directory": download_dir,
            "plugins.always_open_pdf_externally": True,  # Download PDFs instead of opening them
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        # driver = webdriver.Chrome(options=options)
        driver = uc.Chrome(options=options)

        # Set an implicit wait for all elements
        driver.implicitly_wait(10)
        
        # Navigate to the page
        driver.get(article_url)
        driver.implicitly_wait(10)
        # Instead of clicking directly, try to get the URL from the href attribute
        try:
            # Try multiple selectors to find the PDF link
            selectors = [
                'a[data-ga-category="full_text"]',
                'a[href*=".pdf"]',
                'a[href*=".pdf"].pdf-download',
                'a.pdf-download',
                'a.c-Button.pdf-download',
                'a.c-Button--primary.pdf-download',
                'a[title*="Download PDF"][href*=".pdf"]',
                'a[href^="pdf/"][aria-label="Download PDF"]',
                'a[aria-label*="Download"]',
                'a[aria-label*="view"]',
                'a.int-view.pdf-link',
                'a img[alt*="full text link"]',
                'a[title*="full text"]',
                'a[title*="ePDF"]',  # <--- Add this for extra robustness
                'a[href*="/epdf/"]'            ]

            print("PMID", pmc_id)
            pdf_link_element = None
            for selector in selectors:
                # print(f"Trying selector: {selector}")
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                # print(f"Found {len(elements)} elements with selector: {selector}")
                if elements:
                    pdf_link_element = elements[0]
                    # print(f"Found PDF link element using selector: {selector}")
                    break
            print(f"Final PDF link element: {pdf_link_element.get_attribute('href') if pdf_link_element else 'None'}")

            
            if not pdf_link_element:
                return False
            
            # Get the href attribute value (the PDF URL)
            pdf_url = pdf_link_element.get_attribute('href')
            
            if not pdf_url:
                print("Could not extract PDF URL from the element.")
                return False
            
            # print(f"Extracted PDF URL: {pdf_url}")
            # Instead of clicking, navigate directly to the PDF URL
            print(f"Navigating to the page URL {pdf_url}")
            driver.get(pdf_url)

            # When you find elements, always get the href:
            pdf_link_element = None
            for selector in selectors:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                # print(f"Found {len(elements)} elements with selector: {selector}")
                if elements:
                    for el in elements:
                        href = el.get_attribute('href')
                        # Exclude author-document.pdf links
                        if href and '.pdf' in href and 'author-document' not in href.lower():
                            pdf_link_element = el
                            break
                    if pdf_link_element:
                        break
            pdf_url = pdf_link_element.get_attribute('href') if pdf_link_element else None
            if pdf_url is None:
                print("Could not find a valid PDF URL in the page.")
                return False
            print(f"Extracted PDF URL: {pdf_url}")
            # download the PDF using Selenium
            print("Navigating to the PDF URL...")
            # Navigate to the PDF URL directly
            driver.get(pdf_url)

            # Add a longer sleep time to wait for the PDF to load
            print("Waiting for PDF to load...")
            time.sleep(10)  # Wait 15 seconds
            # Find the most recent PDF in the download directory
            list_of_files = glob.glob(os.path.join(download_dir, '*.pdf'))
            if list_of_files:
                latest_file = max(list_of_files, key=os.path.getctime)
                new_filename = os.path.join(download_dir, f"{pmc_id}.pdf")
                if os.path.exists(new_filename):
                    os.remove(new_filename)
                os.rename(latest_file, new_filename)
                print(f"Downloaded PDF successfuly: {new_filename}")
                return True
            else:
                print("No PDF file found in the download directory.")
            # Get the current URL (in case of redirects)
            final_url = driver.current_url
            print(f"Final PDF URL after navigation: {final_url}")            
            # Save the PDF using requests after getting cookies from Selenium
            cookies = driver.get_cookies()
            cookies_dict = {cookie['name']: cookie['value'] for cookie in cookies}
            
            # Create a new requests session with these cookies
            session = requests.Session()
            for cookie in cookies:
                session.cookies.set(cookie['name'], cookie['value'])
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': article_url,
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            
            print("Downloading PDF with requests session...")
            pdf_response = session.get(final_url, headers=headers)
            
            if pdf_response.status_code == 200:
                # Check if it's actually a PDF
                content_type = pdf_response.headers.get('Content-Type', '')
                is_pdf = 'application/pdf' in content_type or pdf_response.content[:4] == b'%PDF'
                
                if is_pdf:
                    # Extract filename from URL
                    #filename = final_url.split('/')[-1]
                    #if not filename.lower().endswith('.pdf'):
                    #    filename += '.pdf'
                    filename = os.path.join(TO_STORE, f"{str(pmc_id)}.pdf")
                    # Save the PDF file
                    with open(filename, 'wb') as f:
                        f.write(pdf_response.content)
                    
                    print(f"Successfully downloaded the PDF as '{filename}'")
                    return True
                else:
                    print("The response doesn't appear to be a PDF.")
                    print(f"Content-Type: {content_type}")
                    return False
            else:
                print(f"Failed to download PDF with requests. Status code: {pdf_response.status_code}")
                return False
                
        except ElementNotInteractableException:
            print("Element not interactable. Trying an alternative approach...")
            # Get the page source to extract PDF links
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            pdf_links = soup.select('a[href*=".pdf"], a[href*="/pdf/"]')
            
            if pdf_links:
                pdf_href = pdf_links[0].get('href')
                print(f"Found PDF link in page source: {pdf_href}")
                
                # Construct the full URL if necessary
                if not pdf_href.startswith('http'):
                    pdf_url = urljoin(article_url, pdf_href)
                else:
                    pdf_url = pdf_href
                
                print(f"Full PDF URL: {pdf_url}")
                
                # Navigate to the PDF URL
                print("Navigating to the PDF URL...")
                driver.get(pdf_url)
                
                # Add a longer sleep time
                print("Waiting for PDF to load...")
                time.sleep(15)
                traceback.print_exc()
                # Use the same approach as above to download the PDF
                # (Code omitted for brevity, it's identical to the above)
                return False  # Change to appropriate logic if implementing
            else:
                print("Could not find any PDF links in the page source.")
                return False
                
    except Exception as e:
        print(f"An error occurred in Selenium method: {str(e)}")
        traceback.print_exc()  # Print full traceback for debugging
        return False
    finally:
        # Close the browser
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass

def download_pdf_with_requests(article_url):
    """Download PDF using requests with extensive link finding"""
    # article_url = "https://pmc.ncbi.nlm.nih.gov/articles/PMC11264376/"
    
    print(f"\nTrying alternative method with requests: {article_url}")
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    # Add headers to mimic a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    # Step 1: Get the article page content
    try:
        response = session.get(article_url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error accessing the article page: {e}")
        return False
    
    # Step 2: Parse the HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Step 3: Extract the PMC ID from the URL
    pmc_id_match = re.search(r'PMC(\d+)', article_url)
    if pmc_id_match:
        pmc_id = pmc_id_match.group(0)  # This will get 'PMC11264376'
        print(f"Found PMC ID: {pmc_id}")
    else:
        print("Could not determine the PMC ID.")
        return False
    
    # Step 4: Look for the PDF link in various ways
    pdf_link = None
    pdf_links = []
    
    # Method 1: Look for direct PDF links
    links = soup.select('a[href*=".pdf"], a[href*="/pdf/"]')
    for link in links:
        href = link.get('href')
        if href:
            pdf_links.append(href)
    
    if pdf_links:
        print(f"Found {len(pdf_links)} potential PDF links:")
        for i, link in enumerate(pdf_links):
            print(f"{i+1}. {link}")
        pdf_link = pdf_links[0]  # Use the first one
    
    if not pdf_link:
        # Try alternative URL constructions
        potential_urls = [
            # f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/pdf/",
            # f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/pdf/{pmc_id}.pdf",
            # f"https://pmc.ncbi.nlm.nih.gov/articles/{pmc_id}/pdf/main.pdf"
            f"https://pubmed.ncbi.nlm.nih.gov/{pmc_id}"
        ]
        
        for url in potential_urls:
            print(f"Trying alternative URL: {url}")
            try:
                pdf_response = session.head(url, headers=headers, timeout=10)
                if pdf_response.status_code == 200:
                    pdf_link = url
                    print(f"Found working PDF URL: {pdf_link}")
                    break
            except requests.exceptions.RequestException:
                continue
    
    if not pdf_link:
        print("Could not find a valid PDF link.")
        return False
    
    # Step 5: Construct the full PDF URL if it's a relative URL
    if not pdf_link.startswith('http'):
        pdf_url = urljoin(article_url, pdf_link)
    else:
        pdf_url = pdf_link
    
    print(f"Full PDF URL: {pdf_url}")
    
    # Step 6: Try to download the PDF
    try:
        headers['Referer'] = article_url
        
        print("Attempting to download the PDF...")
        pdf_response = session.get(pdf_url, headers=headers, timeout=30)
        
        if pdf_response.status_code == 200:
            # Check if it's a PDF
            content_type = pdf_response.headers.get('Content-Type', '')
            is_pdf = 'application/pdf' in content_type or pdf_response.content[:4] == b'%PDF'
            
            if is_pdf:
                filename = pdf_url.split('/')[-1]
                if not filename.lower().endswith('.pdf'):
                    filename += '.pdf'
                filename = os.path.join(TO_STORE, f"{pmc_id}.pdf")
                with open(filename, 'wb') as f:
                    f.write(pdf_response.content)
                
                print(f"Successfully downloaded the PDF as '{filename}'")
                return True
            else:
                print(f"Response doesn't appear to be a PDF. Content-Type: {content_type}")
                return False
        else:
            print(f"Failed to download the PDF. Status code: {pdf_response.status_code}")
            return False
    except Exception as e:
        print(f"Error downloading the PDF: {e}")
        return False

def manually_download_pdf(article_url):
    """Alternative method that opens the browser for user to manually download the PDF"""
    
    print(f"\nOpening browser for manual download from: {article_url}")
    print("Please wait for the page to load, then click on the PDF download link.")
    print("The browser will remain open for you to save the PDF manually.")
    
    # Initialize browser without headless mode
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(options=options)
    
    try:
        # Navigate to the article page
        driver.get(article_url)
        
        # Wait for the user to manually download the PDF
        input("\nPress Enter after you've downloaded the PDF to close the browser...")
        return True
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return False
    finally:
        # Close the browser
        driver.quit()

def download_pdf_from_pmc(article_url):
    # Step 1: Get the HTML content of the article page
    print(f"Accessing article page: {article_url}")
    response = requests.get(article_url)
    
    if response.status_code != 200:
        print(f"Failed to access the article page. Status code: {response.status_code}")
        return False
    
    # Step 2: Parse the HTML to find the PDF link
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Look for the PDF download link based on the HTML structure you provided
    pdf_link_element = soup.select_one('a[href^="pdf/"][aria-label="Download PDF"]')
    
    if not pdf_link_element:
        print("Could not find the PDF download link on the page.")
        return False
    
    # Extract the relative PDF link
    relative_pdf_link = pdf_link_element['href']
    
    # Step 3: Construct the full PDF URL (using the article URL as base)
    base_url = '/'.join(article_url.split('/')[:-2])  # Remove the last part of the URL
    full_pdf_url = f"{base_url}/{relative_pdf_link}"
    
    print(f"Found PDF link: {full_pdf_url}")
    
    # Step 4: Download the PDF file
    pdf_response = requests.get(full_pdf_url)
    
    if pdf_response.status_code != 200:
        print(f"Failed to download the PDF. Status code: {pdf_response.status_code}")
        return False
    
    # Step 5: Save the PDF file
    # Extract filename from the URL
    filename = relative_pdf_link.split('/')[-1]
    
    with open(filename, 'wb') as f:
        f.write(pdf_response.content)
    
    print(f"Successfully downloaded the PDF as '{filename}'")
    return True
    
def get_pdf_url(pmc_id):
    """
    Get the PDF download URL for a given PMC ID
    """
    api_url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id={pmc_id}"
    response = requests.get(api_url)
    
    if response.status_code != 200:
        print(f"Error: Unable to get information for PMC ID {pmc_id}")
        return None
    
    # Parse the XML response
    root = ET.fromstring(response.text)
    
    # Check if records were returned
    records = root.find('records')
    if records is None or int(records.get('returned-count', 0)) == 0:
        print(f"No records found for PMC ID {pmc_id}")
        return None
    
    # Look for the PDF link in the record
    for record in records.findall('record'):
        for link in record.findall('link'):
            if link.get('format') == 'pdf':
                return link.get('href')
    
    print(f"No PDF link found for PMC ID {pmc_id}")
    return None

def download_pdf(url, output_dir, pmc_id):
    """
    Download a PDF file from a URL, supporting both HTTP and FTP
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    filename = f"{pmc_id}.pdf"
    output_path = os.path.join(output_dir, filename)
    
    # Parse the URL to determine protocol
    parsed_url = urlparse(url)
    protocol = parsed_url.scheme
    
    try:
        if protocol == 'ftp':
            # Use urlretrieve for FTP URLs
            urlretrieve(url, output_path)
        else:
            # Use requests for HTTP URLs
            response = requests.get(url)
            if response.status_code != 200:
                print(f"Error: Unable to download PDF from {url}")
                return False
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
        
        print(f"Downloaded {filename} to {output_dir}")
        return True
    
    except Exception as e:
        print(f"Error downloading {url}: {str(e)}")
        return False

def download_pmc_pdfs(pmc_ids, output_dir="downloads"):
    """
    Download PDFs for a list of PMC IDs
    """
    success_count = 0
    
    for pmc_id in pmc_ids:
        print(f"Processing PMC ID: {pmc_id}")
        pdf_url = get_pdf_url(pmc_id)
        
        if pdf_url:
            if download_pdf(pdf_url, output_dir, pmc_id):
                success_count += 1
            
            # Add a small delay to avoid overwhelming the server
            time.sleep(1)
    
    print(f"Downloaded {success_count} of {len(pmc_ids)} PDFs")

def load_pmcids_from_csv(file_path):
    df = pd.read_csv(file_path)
    # remove rows with empty PMCID
    df = df[df['PMID'].notna()]
    return df['PMID'].tolist()

def download_pdf_from_ncbi_pmc(article_url):
    """
    Download a PDF from NCBI PMC using direct inspection of the page source
    to find the actual PDF URL pattern.
    """
    
    print(f"Accessing PMC article page: {article_url}")
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    # Add headers to mimic a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    # Step 1: Get the article page content
    try:
        response = session.get(article_url, headers=headers, timeout=30)
        response.raise_for_status()  # Raise exception for bad status codes
    except requests.exceptions.RequestException as e:
        print(f"Error accessing the article page: {e}")
        return False
    
    # Step 2: Parse the HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Step 3: Extract the PMC ID from the URL or page
    pmc_id_match = re.search(r'PMC(\d+)', article_url)
    if pmc_id_match:
        pmc_id = pmc_id_match.group(0)  # This will get 'PMC11264376'
        print(f"Found PMC ID: {pmc_id}")
    else:
        # Try to find it in the page content
        pmc_id_tag = soup.find('meta', attrs={'name': 'ncbi_pcid'})
        if pmc_id_tag and pmc_id_tag.get('content'):
            pmc_id = pmc_id_tag.get('content')
            print(f"Found PMC ID from meta tag: {pmc_id}")
        else:
            print("Could not determine the PMC ID.")
            return False
    
    # Step 4: Look for the PDF link in the page
    pdf_link = None
    
    # Method 1: Look for the direct PDF link in href attributes
    pdf_links = soup.select('a[href*=".pdf"]')
    for link in pdf_links:
        href = link.get('href')
        if href and '/pdf/' in href:
            pdf_link = href
            print(f"Found PDF link (Method 1): {pdf_link}")
            break
    
    # Method 2: If not found, look for specific link patterns
    if not pdf_link:
        pdf_links = soup.select('a[href^="pdf/"]')
        if pdf_links:
            pdf_link = pdf_links[0].get('href')
            print(f"Found PDF link (Method 2): {pdf_link}")
    
    # Method 3: Look for download links with aria-label
    if not pdf_link:
        download_links = soup.select('a[aria-label*="Download"]')
        for link in download_links:
            href = link.get('href')
            if href and ('.pdf' in href or '/pdf/' in href):
                pdf_link = href
                print(f"Found PDF link (Method 3): {pdf_link}")
                break
    
    if not pdf_link:
        print("Could not find a PDF link on the page.")
        return False
    
    # Step 5: Construct the full PDF URL if it's a relative URL
    if not pdf_link.startswith('http'):
        pdf_url = urljoin(article_url, pdf_link)
    else:
        pdf_url = pdf_link
    
    print(f"Full PDF URL: {pdf_url}")
    
    # Step 6: Try to download the PDF
    try:
        # Sometimes we need to add a referer header
        headers['Referer'] = article_url
        
        print("Attempting to download the PDF...")
        pdf_response = session.get(pdf_url, headers=headers, timeout=30)
        
        # Check if the response is a PDF (by content type or beginning bytes)
        content_type = pdf_response.headers.get('Content-Type', '')
        is_pdf = 'application/pdf' in content_type or pdf_response.content[:4] == b'%PDF'
        
        if pdf_response.status_code == 200 and is_pdf:
            # Extract filename from the URL or content disposition header
            filename = pdf_url.split('/')[-1]
            
            # Sometimes the content-disposition header has the actual filename
            if 'Content-Disposition' in pdf_response.headers:
                cd = pdf_response.headers.get('Content-Disposition')
                if 'filename=' in cd:
                    filename = re.findall('filename=(.+)', cd)[0].strip('"\'')
            
            # Ensure the filename has a .pdf extension
            if not filename.lower().endswith('.pdf'):
                filename += '.pdf'
            
            # Save the PDF file
            with open(filename, 'wb') as f:
                f.write(pdf_response.content)
            
            print(f"Successfully downloaded the PDF as '{filename}'")
            return True
        else:
            print(f"Failed to download the PDF. Status code: {pdf_response.status_code}")
            print(f"Content type: {content_type}")
            
            # Try an alternative construction of the URL
            print("Trying alternative URL construction...")
            
            # For NCBI PMC, sometimes using a different URL pattern works
            alt_pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/pdf/"
            print(f"Alternative URL: {alt_pdf_url}")
            
            try:
                pdf_response = session.get(alt_pdf_url, headers=headers, timeout=30)
                
                if pdf_response.status_code == 200 and ('application/pdf' in pdf_response.headers.get('Content-Type', '') or pdf_response.content[:4] == b'%PDF'):
                    filename = f"{pmc_id}.pdf"
                    
                    with open(filename, 'wb') as f:
                        f.write(pdf_response.content)
                    
                    print(f"Successfully downloaded the PDF as '{filename}' using alternative URL")
                    return True
                else:
                    print(f"Failed to download using alternative URL. Status code: {pdf_response.status_code}")
            except Exception as e:
                print(f"Error with alternative URL: {e}")
            
            return False
    except Exception as e:
        print(f"Error downloading the PDF: {e}")
        return False
    
####  MAIN SCRIPT ####
# get PMCID from csv file
pmcids = load_pmcids_from_csv(filename)
ensure_directory_exists(TO_STORE)

# get the PMCID and download the PDF
# download_pmc_pdfs(pmcids, TO_STORE)
# %%
for pmc_id in tqdm(pmcids):
    # Construct the article URL
    # article_url = "https://pmc.ncbi.nlm.nih.gov/articles/PMC11264376/"
    # article_url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmc_id}/"
    article_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmc_id}" # https://pmc.ncbi.nlm.nih.gov/articles/{pmc_id}/"

    print("Attempting to download the PDF automatically...")
    if not download_pdf_with_selenium(pmc_id):
        print("\nAutomatic download failed. Would you like to open a browser for manual download? (yes/no)")
        choice = input().lower()
        if choice in ['yes', 'y']:
            manually_download_pdf(article_url)
        else:
            print("Download cancelled.")