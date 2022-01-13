from bs4 import BeautifulSoup
import requests
import re
import json
import pandas as pd
from os.path import exists
import smtplib
from email.message import EmailMessage

#   Config - change these!
wishlist_url   = "https://www.amazon.co.uk/gp/registry/wishlist/1A1NYHTAZ3N6V/"
email_user     = 'me@example.com'
email_password = 'P455w0rd!'
email_to       = 'you@example.com'
smtp_server    = "smtp.example.com"

#   Set up the lists
item_list  = []
price_list = []
id_list    = []

#   Message text
message = "Here are the recent price drops:\n"

def get_wishlist(url):
    #   Load the wishlist
    response = requests.get(url)
    page_html = response.text
    #   Parse the page
    soup = BeautifulSoup(page_html, 'html.parser')
    return soup

def get_items(soup):
    #   Get the item names
    for match in soup.find_all('a', id=re.compile("itemName_")):
        item = match.string.strip()
        item_list.append(item)

def get_prices_and_ids(soup):
    #   Get the price and ID from data attributes
    for match in soup.find_all("li", class_="g-item-sortable"):
        price = match.attrs["data-price"]
        price_list.append(price)
        json_data = json.loads(match.attrs["data-reposition-action-params"])
        # Will be something like "ASIN:B095PV5G87|A1F83G8C2ARO7P"
        id = json_data["itemExternalId"].split(":")[1].split("|")[0]
        id_list.append(id)

def get_paginator(soup):
    ##  Find the paginator
    if soup.find("div", {"id": "endOfListMarker"}) is None:
        #   If the end tag doesn't exist, continue
        for match in soup.find_all('input', class_="showMoreUrl"):
            paginator = "https://www.amazon.co.uk" + match.attrs["value"]
    else:
        paginator = None
    return paginator

def get_all(url):
    global counter
    counter = counter + 1
    print( "Getting page " + str(counter))
    soup = get_wishlist(url)
    get_items(soup)
    get_prices_and_ids(soup)
    paginator = get_paginator(soup)
    if paginator is not None:
        get_all(paginator)

#   Send Email
def send_email(message):
    global email_user
    global email_password
    global email_to
    global smtp_server
    msg = EmailMessage()
    msg.set_content(message)
    msg['Subject'] = "Today's price drops"
    msg['From']    = email_user
    msg['To']      = to
    server = smtplib.SMTP_SSL(smtp_server, 465)
    server.ehlo()
    server.login(email_user, email_password)
    server.send_message(msg)
    server.quit()

#   Get all the items on the wishlist
#   Which page are we on?
counter = 0
get_all(wishlist_url)

#   Place into a DataFrame
all_items = zip(id_list, item_list, price_list)
new_prices = pd.DataFrame(list(all_items), columns = ["ID", "Name", "Price"])

#   Read the old file
if exists("old_prices.csv"):
    old_prices = pd.read_csv("old_prices.csv")
else:
    old_prices = new_prices.copy()

#   Compare prices
for id in old_prices["ID"]:
    new_price = new_prices.loc[new_prices["ID"]==id, "Price"].values[0]
    name      = new_prices.loc[new_prices["ID"]==id, "Name" ].values[0]
    #   If a book has recently been added to the wishlist, it won't have an old price
    if id in old_prices.values:
        old_price = old_prices.loc[old_prices["ID"]==id, "Price"].values[0]
        #   Anything less than a quid is good knowing about.
        #   Some prices are ""-Infinity", so check the price is more than zero
        if float(new_price) < 1 and float(new_price) > 0:
            message += (name + "\n£" + str(new_price) + " was £" + str(old_price) + " https://www.amazon.co.uk/dp/"+id + "\n")
        elif float(new_price) < float(old_price):
            message += (name + "\n£" + str(new_price) + " was £" + str(old_price) + " https://www.amazon.co.uk/dp/"+id + "\n")

#   Send the email with the price drop alert
#print(message)
send_email(message)

#   Save the Data
new_prices.to_csv('old_prices.csv', index=False)