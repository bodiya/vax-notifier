import bs4
import configparser
import json
from os import environ
from random import randrange
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
import smtplib
import ssl
import time

config_file = "config/vax-notifier.conf"
config = configparser.ConfigParser()
config.read(config_file)

sender_email = config.get("Sender", "email", vars=environ)
app_password = config.get("Sender", "app_password", vars=environ)
smtp_server = config.get("Sender", "smtp_server", vars=environ)

addresses_to_notify = json.loads(config.get("Receivers", "receivers_list", vars=environ))
admin_email = config.get("Receivers", "admin_email", vars=environ)

state = config.get("Preferences", "state", vars=environ)
scheduled_mode = config.getboolean("Preferences", "scheduled_mode", vars=environ)
refresh_rate = config.getint("Preferences", "refresh_rate", vars=environ)
refresh_variance = config.getint("Preferences", "refresh_variance", vars=environ)
found_delay = config.getint("Preferences", "found_delay", vars=environ)
ignore_list = json.loads(config.get("Preferences", "ignore_list", vars=environ))
ignore_list = {i.casefold() for i in ignore_list}
chrome_arguments = json.loads(config.get("Preferences", "chrome_arguments", vars=environ))
connectivity_test = config.getboolean("Preferences", "connectivity_test", vars=environ, fallback=False)


def send_email(message, receivers=addresses_to_notify):
    # reload notification list, so restarts aren't required when you add people
    config.read(config_file)
    addresses_to_notify = json.loads(config.get("Receivers", "receivers_list", vars=environ))

    port = 587
    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server, port) as server:
        server.starttls(context=context)
        server.login(sender_email, app_password)
        server.sendmail(sender_email, receivers, message)


def send_error(context):
    print(context)
    message = f"""\
Subject: Error with vax-notifier

An error occurred. If this is related to the page failing to load, you may want to consider running this from a different IP address.

{context}
"""
    send_email(message=message, receivers=[admin_email])


def send_report(locations, city_counter):
    num_cities = len(locations)
    cities = "\n".join(locations)
    message = f"""\
Subject: {num_cities}/{city_counter} CVS locations have vaccine appointments

COVID-19 vaccine appointments were detected at https://www.cvs.com/immunizations/covid-19-vaccine

You can try to schedule an appointment at:
https://www.cvs.com/vaccine/intake/store/cvd-schedule.html?icid=coronavirus-lp-vaccine-sd-statetool

For more information see:
https://github.com/bodiya/vax-notifier#information-for-receivers

Appointments available at:
{cities}
"""

    send_email(message)


# Be nice to the server, don't be super regular
def delay():
    wait_time = refresh_rate + randrange(refresh_variance)
    time.sleep(wait_time)


def getVaxAppt(cvsUrl):
    chrome_options = webdriver.ChromeOptions()

    # don't load images
    chrome_options.add_experimental_option(
        "prefs", {"profile.default_content_settings.images": 2}
    )
    chrome_options.add_experimental_option(
        "prefs", {"profile.managed_default_content_settings.images": 2}
    )

    # load any other chrome options
    for arg in chrome_arguments:
        chrome_options.add_argument(arg)

    driver = webdriver.Chrome(options=chrome_options)

    while True:
        try:
            driver.get(cvsUrl)
            print("refreshed")
            state_selector = WebDriverWait(driver, 10).until(
                ec.presence_of_element_located((By.ID, "selectstate"))
            )
            Select(state_selector).select_by_visible_text(state)

            submit_button = driver.find_element_by_xpath('//button[normalize-space()="Get started"]')
            submit_button.click()
            html = driver.page_source
            soup = bs4.BeautifulSoup(html, "html.parser")
        except Exception as ex:
            send_error(str(ex))
            delay()
            continue

        try:
            no_availability_text = "Fully Booked"
            all_statuses = soup.findAll("span", {"class": "status"})
            city_count = len(all_statuses)
            print("Found %i cities" % city_count)
            matches = []
            filtered_matches = []
            for status in all_statuses:
                city = status.parent.parent.find("span", {"class": "city"})
                if no_availability_text == status.text:
                    # When experimenting, it's sometimes nice to match a lot
                    if connectivity_test:
                        matches.append(city.text)
                else:
                    print("%s found in %s" % (status.text, city.text))
                    matches.append(city.text)

            filtered_matches = {m.casefold() for m in matches} - ignore_list
            if len(filtered_matches) > 0:
                # note: entries in the ignore list will be included if there
                #       are also other cities with availability
                send_report(matches, city_count)
                if scheduled_mode:
                    exit(0)
                else:
                    time.sleep(found_delay)  # wait a while before looking again
            else:
                print("No appointments available in " + state)
        except Exception as ex:
            send_error(str(ex))

        # if running in a container on the public cloud,
        # sleeping can be expensive
        if scheduled_mode:
            exit(1)
        else:
            delay()


getVaxAppt("https://www.cvs.com/immunizations/covid-19-vaccine")
