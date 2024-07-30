import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import json
import time

def open_chrome_tab_with_debugging(url):
    """
    The function opens a new Chrome tab with debugging enabled and navigates to the specified URL.
    :param url: The `url` parameter is the URL of the webpage that you want to open in a new Chrome tab
    for debugging
    :return: a WebDriver object if it is successfully initialized, or None if there is an error.
    """
    try:
        options = webdriver.ChromeOptions()
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        driver.get(url)
        driver.maximize_window()
        return driver
    except Exception as e:
        print(f"Error initializing WebDriver: {str(e)}")
        return None

def get_all_urls_and_buttons(driver, url):
    try:
        driver.get(url)
        time.sleep(2)  # Allow time for page to load
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        urls = [a['href'] for a in soup.find_all('a', href=True)]
        buttons = [button.get('id') for button in soup.find_all('button')]

        return urls, buttons
    except Exception as e:
        print(f"Error fetching URLs and buttons: {e}")
        return [], []

def get_page_content(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        content = soup.get_text()
        return content
    except Exception as e:
        print(f"Error fetching page content: {e}")
        return ""

def scrape_site(driver, url):
    data = {
        "url": url,
        "content": get_page_content(url),
        "nested_pages": []
    }

    urls, buttons = get_all_urls_and_buttons(driver, url)
    data["buttons"] = buttons

    for nested_url in urls:
        if not nested_url.startswith('http'):
            nested_url = url + nested_url
        nested_page_data = scrape_site(driver, nested_url)
        data["nested_pages"].append(nested_page_data)

    return data

def main(url):
    driver = open_chrome_tab_with_debugging(url)
    if driver:
        site_data = scrape_site(driver, url)
        with open('site_data.json', 'w') as f:
            json.dump(site_data, f, indent=4)
        driver.quit()

if __name__ == "__main__":
    target_url = "https://www.bankofbaroda.in/personal-banking/loans/personal-loan"  # Replace with the target URL
    main(target_url)

# https://www.bankofbaroda.in/personal-banking/loans/personal-loan