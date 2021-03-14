import bs4
import configparser
import json
from random import randrange
from selenium import webdriver
import smtplib
import ssl
import time

config_file = "vax-notifier.conf"
config = configparser.ConfigParser()
config.read(config_file)

sender_email = config["Sender"]["email"]
app_password = config["Sender"]["app_password"]
smtp_server = config["Sender"]["smtp_server"]

addresses_to_notify = json.loads(config["Receivers"]["list"])
admin_email = config["Receivers"]["admin_email"]

state = config["Preferences"]["state"]
refresh_rate = config["Preferences"].getint("refresh_rate")
refresh_variance = config["Preferences"].getint("refresh_variance")
found_delay = config["Preferences"].getint("found_delay")


def send_email(message, receivers=addresses_to_notify):
    # reload notification list, so restarts aren't required when you add people
    config.read(config_file)
    addresses_to_notify = json.loads(config["Receivers"]["list"])

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
    message = f"""\
Subject: {num_cities}/{city_counter} CVS locations have vaccine appointments

COVID-19 vaccine appointments were detected at https://www.cvs.com/immunizations/covid-19-vaccine

You can try to schedule an appointment at:
https://www.cvs.com/vaccine/intake/store/cvd-schedule.html?icid=coronavirus-lp-vaccine-sd-statetool

For more information see:
https://github.com/bodiya/vax-notifier#information-for-receivers

Appointments available at:
"""
    for location in locations:
        message += "\t".join([location["city"], location["status"]]) + "\n"

    send_email(message)


# Be nice to the server, don't be super regular
def delay():
    wait_time = refresh_rate + randrange(refresh_variance)
    time.sleep(wait_time)


def getVaxAppt(cvsUrl):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36",
    }

    driver = webdriver.Chrome()
    driver.get(cvsUrl)

    while True:
        try:
            driver.refresh()
            print("refreshed")
            state_element = driver.find_element_by_link_text(state)
            state_element.click()
            html = driver.page_source
            soup = bs4.BeautifulSoup(html, "html.parser")
            time.sleep(4)
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
            for status in all_statuses:
                city = status.parent.parent.find("span", {"class": "city"})
                if no_availability_text == status.text:
                    # When experimenting, it's sometimes nice to match a lot
                    # matches.append({"city": city.text, "status": status.text})
                    pass
                else:
                    print("%s found in %s" % (status.text, city.text))
                    matches.append({"city": city.text, "status": status.text})

            if len(matches) > 0:
                send_report(matches, city_count)
                time.sleep(found_delay)  # wait a while before looking again
            else:
                print("No appointments available in " + state)
        except Exception as ex:
            send_error(str(ex))

        delay()


getVaxAppt("https://www.cvs.com/immunizations/covid-19-vaccine")
