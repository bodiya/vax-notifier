# vax-notifier
A tool to notify people when COVID-19 vaccines become available at one or more CVS locations in your state.

# Setup
Note: This has only been tested on Ubuntu 20.10 using Chrome 89.0.4389.72 and Python 3.8.

Warning: Using this tool is likely to reduce the reputation of your IP address (it did mine). If you find that some sites say your IP is suspicious or banned, this tool is probably why. I recommend running it in a VM connected to a VPN, or on an separate remote virtual host. I am currently running it in a VM connected to a WireGuard instance hosted in Linode, which can be easily cloned.

Before you start, you will need to have an up to date Chrome, and you will need to download the Chrome Webdriver from https://chromedriver.chromium.org/


```
git clone https://github.com/bodiya/vax-notifier.git
cd vax-notifier
pip install -r requirements.txt
```

Now you'll want to configure the notifier. At the very least, in vax-notifier.conf you should change:
1. email - the address you set up to send notifications from (NOT your primary email address)
1. app_password - the app password of the above email. If using gmail or a gsuite account, you can get an app password by following these instructions: https://support.google.com/accounts/answer/185833?hl=en
1. smtp_server - if you're not sending from gmail, change this
1. list - this is who you're sending notifications to
1. admin_email - this should probably be your primary email address. If anything goes wrong you'll get an email.
1. state - the state you want to get notifications for

After that, you can run the nofifier with:
```
python cvs_vaccine_appointments.py
```

# Information for Receivers
When you try to schedule an appointment, if you receive a message like "Sit tight, we will help schedule your vaccination soon." congrats! You should be able to schedule an appointment soon.

If you receive a message like (paraphrasing) "We are out of appointments, please check back later.", one of two things is the case:
1. If only one or two locations have availability, all the available appointments may already be in the process of being scheduled.
1. If quite a few locations have availability (e.g. aroudn 2-4AM when availability is seems to be updated), you should be able to get in the "real" waiting room soon (e.g. between 5AM and 6AM for the appointments that show up as available at 4AM).  Keep trying.

Note: This bot intentionally does not try to get in the waiting room, so as not to mess with the availability for real people.

# TODO
* Add notifications for Walgreens
* Figure out a better match than state name.
* Add tests (especially for all available states)
* Improve startup instructions
