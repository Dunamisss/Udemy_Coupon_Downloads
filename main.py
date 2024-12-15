import concurrent.futures
import logging
import math
import os
import time
from typing import Dict, List, Union

import requests
from bs4 import BeautifulSoup
from colorama import Fore, Style
from fake_useragent import UserAgent
from requests.exceptions import ConnectionError

# Set up logging
logging.basicConfig(filename='Coupon_Logfile.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize fake user agent
user_agent = UserAgent()

def end():
    print("----------------------------------------")
    print(Fore.GREEN + "Kindly check your downloads directory")
    print("All coupons are saved in " + Style.BRIGHT + "coupons.txt" + Style.RESET_ALL)
    logging.info("All coupons have been saved in coupons.txt")
    logging.info("----------------------------------------")

def fetch_page_content(url: str, headers: Dict[str, str]) -> Union[str, None]:
    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        logging.info(f"Fetched page content for URL: {url}")
        return res.text
    except requests.RequestException as e:
        logging.error(f"Error fetching URL {url}: {e}")
        return None

def get_coupons(go_links: List[str]) -> List[Dict[str, str]]:
    coupons = []
    titles = []
    headers = {'User-Agent': user_agent.random}
    for coupon_link in go_links:
        page_content = fetch_page_content(coupon_link, headers)
        if page_content:
            soup = BeautifulSoup(page_content, 'html.parser')
            coupon = soup.find('div', attrs={'class': 'ui segment'}).a['href']
            title = soup.find('h1', attrs={'class': 'ui grey header'}).getText()
            coupons.append(coupon)
            titles.append(title)
            logging.info(f"Fetched coupon for '{title}' - {coupon}")
    return [{'title': title, 'coupon': coupon} for title, coupon in zip(titles, coupons)]

def get_go_links(list_url: List[str]) -> List[Dict[str, str]]:
    go_links = []
    headers = {'User-Agent': user_agent.random}
    for link in list_url:
        page_content = fetch_page_content(link, headers)
        if page_content:
            soup = BeautifulSoup(page_content, 'html.parser')
            link_class = soup.find('div', attrs={'class': 'ui center aligned basic segment'}).a['href']
            go_links.append(link_class)
            logging.info(f"Found redirect link: {link_class}")
    return get_coupons(go_links)

def get_links(url: str) -> List[Dict[str, str]]:
    headers = {'User-Agent': user_agent.random}
    page_content = fetch_page_content(url, headers)
    if page_content:
        soup = BeautifulSoup(page_content, 'html.parser')
        link_class = soup.select('.card-header')
        hn = [item.get('href') for item in link_class]
        for href in hn:
            logging.info(f"Found coupon link: {href}")
        return get_go_links(hn)
    return []

def display_menu(courses: List[Dict[str, str]]):
    print("Available Courses:")
    for i, course in enumerate(courses, start=1):
        print(Fore.YELLOW + f"{i}. {course['title']}" + Style.RESET_ALL)
    print(Fore.YELLOW + "0. Quit" + Style.RESET_ALL)

def process_udemy_or_eduonix(provider: str):
    json_url = 'https://jobs.e-next.in/public/assets/data/udemy.json' if provider == '1' else 'https://jobs.e-next.in/public/assets/data/eduonix.json'
    try:
        courses_data = get_course_data(json_url)
        if courses_data:
            display_menu(courses_data)
            selected_courses = select_courses(courses_data)
            if selected_courses:
                save_coupons_to_file(selected_courses, provider)
                logging.info("Finished fetching and saving courses")
                print(Fore.GREEN + '>> Finished fetching and saving courses' + Style.RESET_ALL)
                print("----------------------------------------")
            else:
                print(Fore.YELLOW + "No courses selected." + Style.RESET_ALL)
        else:
            print(Fore.RED + 'Failed to fetch course data.' + Style.RESET_ALL)
    except ConnectionError:
        print(Fore.RED + '[!] Please check your network connection!' + Style.RESET_ALL)
        logging.error("Connection error occurred")
    except KeyboardInterrupt:
        print(Fore.RED + '[!] CTRL + C detected\n[!] Quitting...' + Style.RESET_ALL)
        logging.info("Script interrupted by user")

def process_discudemy():
    try:
        print(Fore.CYAN + '>> Fetching coupons...' + Style.RESET_ALL)
        logging.info("Started fetching coupons")
        urls = [f'https://www.discudemy.com/all/{page_num}' for page_num in range(1, 8)]
        with concurrent.futures.ThreadPoolExecutor() as executor:
            courses = list(executor.map(get_links, urls))
            courses = [course for sublist in courses for course in sublist]
        display_menu(courses)
        selected_courses = select_courses(courses)
        if selected_courses:
            selected_coupons = [course['coupon'] for course in selected_courses]
            selected_titles = [course['title'] for course in selected_courses]
            end()
            save_coupons_to_file(selected_coupons, selected_titles)
            logging.info("Finished fetching and saving coupons")
            print(Fore.GREEN + '>> Finished fetching and saving coupons' + Style.RESET_ALL)
            print("----------------------------------------")
        else:
            print(Fore.YELLOW + "No coupons selected." + Style.RESET_ALL)
    except ConnectionError:
        print(Fore.RED + '[!] Please check your network connection!' + Style.RESET_ALL)
        logging.error("Connection error occurred")
    except KeyboardInterrupt:
        print(Fore.RED + '[!] CTRL + C detected\n[!] Quitting...' + Style.RESET_ALL)
        logging.info("Script interrupted by user")

def get_course_data(json_url: str) -> Union[List[Dict[str, Union[str, List[str]]]], None]:
    headers = {'User-Agent': user_agent.random}
    response = requests.get(json_url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Failed to fetch course data. Status code: {response.status_code}")
        return None

def select_courses(courses_data: List[Dict[str, Union[str, List[str]]]]) -> List[Dict[str, Union[str, List[str]]]]:
    selected_courses = []
    while True:
        choice = input(Fore.CYAN + "Enter the number of the course you're interested in (0 to quit): " + Style.RESET_ALL)
        if choice == '0':
            break
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(courses_data):
                selected_courses.append(courses_data[choice_num - 1])
            else:
                print(Fore.RED + "Invalid choice. Please enter a valid course number." + Style.RESET_ALL)
        except ValueError:
            print(Fore.RED + "Invalid input. Please enter a number." + Style.RESET_ALL)
    return selected_courses

def save_coupons_to_file(courses: Union[List[Dict[str, str]], List[str]], provider: str):
    filename = 'coupons.txt' if provider in ['1', '2'] else 'discudemy_coupons.txt'
    try:
        with open(filename, 'w') as file:
            if provider == '3':  # For discudemy
                for coupon in courses:
                    file.write(f"{coupon}\n")
            else:  # For Udemy and Eduonix
                for course in courses:
                    if isinstance(course, str):  # If course is a string (URL)
                        file.write(f"{course}\n")
                    else:  # If course is a dictionary
                        title = course.get('title', 'Unknown Title')
                        coupon = course.get('coupon', 'No Coupon')
                        slug = course.get('url', 'No URL')
                        course_url = f"https://jobs.e-next.in/course/udemy/{slug}" if provider == '1' else f"https://jobs.e-next.in/course/eduonix/{slug}"
                        file.write(f"{title} - {coupon} - {course_url}\n")
        print(Fore.GREEN + f"Coupons saved in {filename}" + Style.RESET_ALL)
        logging.info(f"Coupons saved in {filename}")
    except Exception as e:
        print(f"Error saving coupons: {e}")
        logging.error(f"Error saving coupons: {e}")

def fetch_tutorialbar_data() -> List[Dict[str, str]]:
    url = 'https://www.tutorialbar.com/all-courses/'
    num_courses = 100
    courses_per_page = 12
    num_pages = math.ceil(num_courses / courses_per_page)
    courses = []
    headers = {'User-Agent': user_agent.random}
    for page in range(1, num_pages + 1):
        res = requests.get(url, headers=headers, params={'page': page})
        soup = BeautifulSoup(res.text, 'html.parser')
        course_list = soup.select('article.col_item.column_grid.rh-heading-hover-color.rh-bg-hover-color.no-padding.rh-cartbox.two_column_mobile')
        for course in course_list:
            title = course.select_one('h3').text
            link = course.select_one('a')['href']
            courses.append({"title": title, "link": link})
        logging.info(f"Page {page} fetched")
        if len(courses) >= num_courses:
            break
    return courses

def process_tutorialbar():
    courses = fetch_tutorialbar_data()
    print('Scraping completed. Here are the courses:')
    display_menu(courses)
    selected_courses = select_courses(courses)
    if selected_courses:
        filename = 'selected_courses.html'
        try:
            with open(filename, 'w') as file:
                file.write('<!DOCTYPE html>\n<html>\n<body>\n')
                for course in selected_courses:
                    file.write(f'<a href="{course["link"]}" target="_blank">{course["title"]}</a><br>\n')
                file.write('</body>\n</html>')
            print(Fore.GREEN + f"Selected courses saved to {filename}" + Style.RESET_ALL)
        except Exception as e:
            print(Fore.RED + f"Error saving courses: {e}" + Style.RESET_ALL)
    else:
        print(Fore.YELLOW + "No courses selected to save." + Style.RESET_ALL)

def main_menu() -> str:
    print(Fore.BLUE + "Select your course provider:" + Style.RESET_ALL)
    print(Fore.YELLOW + "1. Udemy" + Style.RESET_ALL)
    print(Fore.YELLOW + "2. Eduonix" + Style.RESET_ALL)
    print(Fore.YELLOW + "3. Udemy Extras" + Style.RESET_ALL)
    print(Fore.YELLOW + "4. TutorialBar" + Style.RESET_ALL)
    while True:
        choice = input(Fore.CYAN + "Enter your choice (1, 2, 3, or 4): " + Style.RESET_ALL)
        if choice in ['1', '2', '3', '4']:
            return choice
        else:
            print(Fore.RED + "Invalid choice. Please enter 1, 2, 3, or 4." + Style.RESET_ALL)

def main():
    while True:
        t1 = time.time()
        choice = main_menu()
        if choice == '1' or choice == '2':
            process_udemy_or_eduonix(choice)
        elif choice == '3':
            process_discudemy()
        elif choice == '4':
            process_tutorialbar()
        t2 = time.time()
        print(Fore.MAGENTA + f'Took {round(t2 - t1)} secs' + Style.RESET_ALL)
        logging.info(f"Script execution completed in {round(t2 - t1)} seconds")
        continue_choice = input(Fore.CYAN + "Do you want to continue? (yes/no): " + Style.RESET_ALL)
        if continue_choice.lower() != 'yes':
            break

if __name__ == "__main__":
    main()
