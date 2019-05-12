#! /usr/bin/env python
from __future__ import print_function

import re
import os
import sys
import time
import json
import random
import traceback
import feedparser

# HTML parsing stuff
from html.parser import HTMLParser
from html.entities import name2codepoint

# email stuff
if sys.version[0] == 3:
    import urllib.request as urllib
else:
    import urllib as urllib

from smtplib import SMTP as smtp
from email import encoders
from email.mime import base, text, multipart
from email.utils import formatdate


class XKCDHTMLParser(HTMLParser):
    def handle_starttag(self, tag, attrs):
        self.xkcd_data = {}
        if tag == "img":
            for attr in attrs:
                # attributes here are tuples
                # e.g., "('src', 'https://imgs.xkcd.com/comics/cubesat_launch.png')"
                self.xkcd_data[attr[0]] = attr[1]


def send_mail(config, subject, message, files_to_attach):
    # unpack some config stuff
    email = config["email_config"]["email"]
    password = config["email_config"]["password"]
    email_name = config["email_config"]["name"]
    to_list = config["mailing_list"]["emails"]
    to_list_name = config["mailing_list"]["name"]

    # connect to gmail
    server = smtp('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.login(email, password)

    # build up the message
    msg = multipart.MIMEMultipart()
    msg.attach(text.MIMEText(message))
    msg['From'] = email_name
    msg['To'] = to_list_name
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    for f in files_to_attach:
        part = base.MIMEBase('application', "octet-stream")
        with open(f, "rb") as fp:
            part.set_payload(fp.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="{0}"'.format(os.path.basename(f)))
        msg.attach(part)

    server.sendmail(email, to_list, msg.as_string())
    server.quit()


# --- config/state getters and setters


def get_config(config_file):
    with open(config_file, "r") as f:
        return json.load(f)


def get_state(state_file):
    with open(state_file, "r") as f:
        return json.load(f)


def update_state(state_file, latest_comic):
    with open(state_file, "r") as f:
        data = json.load(f)
    with open(state_file, "w") as f:
        data["latest_comic"] = latest_comic
        json.dump(data, f)


def send_comic(config, comic_rss_entry, comic_id):
    parser = XKCDHTMLParser()
    parser.feed(comic_rss_entry.summary)

    title = comic_rss_entry.title
    alt_text = parser.xkcd_data["alt"]
    picture_url = parser.xkcd_data["src"]

    message = """Link: {}
Title: {}

Alt Text: {}
""".format(comic_rss_entry.link, title, alt_text)

    # Get the picture
    files = []
    try:
        filepath = os.path.join(config["image_folder_path"], str(comic_id) + ".png")
        urllib.urlretrieve(picture_url, filepath)
        files.append(filepath)
    except Exception as e:
        print("Unexpected exception when trying to get image! {}".format(e))

    send_mail(config, "New XKCD! (#{})".format(comic_id), message, files)


def runner(config_file, state_file):
    match = r"https:\/\/xkcd\.com\/([0-9]+)\/"
    while True:
        try:
            feed = feedparser.parse("https://xkcd.com/rss.xml")

            config = get_config(config_file)
            if not os.path.exists(config["image_folder_path"]):
                os.makedirs(config["image_folder_path"])
            state = get_state(state_file)
            latest_comic = state["latest_comic"]

            for entry in feed.entries[::-1]:
                if entry:
                    comic_id = int(re.match(match, entry.link).group(1))
                    if comic_id > latest_comic:
                        print("--- New Comic {} ---".format(entry.link))
                        latest_comic = comic_id
                        send_comic(config, entry, comic_id)

            update_state(state_file, latest_comic)
        except Exception as  e:
            print("Unexpected error: {}".format(e), file=sys.stderr)
            print(traceback.format_exc())

        poll_time = config["poll_interval_sec"]
        sleep_time = int(poll_time + float(poll_time) * (random.random() / 0.25))
        print("Sleeping for {} seconds...".format(sleep_time), end="\n\n")
        time.sleep(sleep_time)


if __name__ == "__main__":
    CONFIG_FILEPATH = "./config.json"
    STATE_FILEPATH = "./state.json"

    if not os.path.exists(CONFIG_FILEPATH):
        print("must have a configuration file ({}) in the working directory!".format(CONFIG_FILEPATH), file=sys.stderr)
        sys.exit(-1)

    if not os.path.exists(STATE_FILEPATH):
        print("Warning: creating initial state with current comic at 0", file=sys.stderr)
        with open(STATE_FILEPATH, "w") as f:
            data = {"latest_comic": 0}
            json.dump(data, f)

    runner(CONFIG_FILEPATH, STATE_FILEPATH)

