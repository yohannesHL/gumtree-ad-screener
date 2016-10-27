#!/usr/bin/env python3

import re
import urllib
import codecs
import os
import sys
from lxml import html
import requests
import time
import webbrowser

PAGE_LIMIT = 2

def get_content(el, pattern=None):
    if (el.text_content is None):
        return ''

    text = el.text_content()

    if(pattern is not None):
        pe = re.compile(pattern)
        text = pe.findall(text)
        text = text.join('')
    return text


def get_class_text(el, className, pattern=None):
    class_el = el.find_class(className)[0]
    text = get_content(class_el, pattern=pattern)
#     if(className !='listing-attributes'):
#         text = text.replace("\n", " ")
    return text


def read_file(file):
    out = []
    if file is not None:
        try:
            f = open(file, 'r');
        except Exception as e:
            f = open(file, 'w+');
        finally:
            f.close()

        with codecs.open(file, 'r') as f:
            raw_lines = f.readlines()
            for raw_line in raw_lines:
                raw = raw_line.replace("\n", "")
                out.append(raw)
    return out


def parse_lines(lines, delimiter):
    out = []
    if delimiter is None:
        return lines
    for line in lines:
        out.append(line.split(delimiter))
    return out


def prepare_data(data, delimiter):
    out = []
    if delimiter is None:
        delimiter = '::'
    for x in data:
        out.append(delimiter.join(x))
    return out


def write_file(file, data):

    with codecs.open(file, mode="w") as f:
        for line in data:
            line = line.replace('\n','')
            f.write('%s\n' %line)


def get_attr(text):
    patterns = {
        'Seller type': 'Seller type(.*)\n',
        'Property type': 'Property type(.*)\n',
        'Number of beds': 'Number of beds(.*)\n',
        'Date available': 'Date available: (.*)\n'
    }
    out = []
    for (key, p) in patterns.items():

        st = re.compile(p)
        found = st.findall(text)
        if(len(found) > 0):
            out.append(key + ': ' + found[0])

    return '\n'.join(out)


def scrape_data(link_el):
    link = link_el[0]

    url = link.attrib['href']
    title = get_class_text(link, 'listing-title')
    loc = get_class_text(link, 'listing-location')
    desc = get_class_text(link, 'listing-description')
    avail = get_class_text(link, 'listing-attributes')
    avail = get_attr(avail)

    price = get_class_text(link, 'listing-price')
    posted = get_class_text(link, 'listing-posted-date')

    return (url, title, loc, desc, avail, price, posted)



def get_page_data(listingsWrap):
    items = []
    if len(listingsWrap) > 0:

        listingsWrap = listingsWrap[0]  # ul

        for listing in listingsWrap.iterchildren():  # li

            link_el = listing.find_class('listing-link')

            if (len(link_el) == 0):
                continue

            (lurl, title, loc, desc, avail, price, posted) = scrape_data(link_el)

            items.append((lurl, title, loc, desc, avail, price, posted))

    return items


def parse_days(text):
    val = text.replace('\n', '').lower()
    multipliers = {
        'now': 0,
        'hour': 0,
        'minute': 0,
        'day': 1
    }
    out = 0
    try:
        days = re.findall('\d+', val)[0]
        days = int(days)
    except Exception as e:
        days = 0
        # print(e)
        pass

    for (key, multiplier) in multipliers.items():
        if(key in val):
            out = days * multiplier

    return out
def getPages(limit):
    return ['page%d' % x for x in range(1, limit)]


def process_items(items, ids_tokeep, ids_seen, seen_ads, table, listed_ids):

    for (lurl, title, loc, desc, avail, price, posted) in items:
        href = BASE + lurl
        id = lurl.split('/')[-1]
        id = id.replace(' ', '')
        days = parse_days(posted)
        if id in ids_tokeep or (days < 16 and 'office' not in desc.lower() and 'office' not in title.lower() and id not in ids_seen):

            if id not in ids_seen:
                seen_ads.append([id, title, price])

                print('New ', id, id in ids_seen, id in ids_tokeep)
                print('title: ', title)
            # sys.stderr.write('\t%s\n%s%s' % (href, price, posted))

            #print("<tr><td>" + title + "</td><td>" + price + "</td><td>" + area + "</td><td>" + avail + "</td><td>" + posted + "</td><td>" + desc + "</td></tr>")

            #sys.stderr.write('\t%s\n%s%s%s%s%s\n' % (href,price, area, title, avail,  posted))
            #print(lurl, title, area, desc, avail, price, posted)
            if(id not in listed_ids):
                listed_ids.append(id)
                table.append("<tr><td width='25%'><i data-id=" + str(id) + "></i><a href='" + href + "'><span>" + title + "</span></a></td><td width='25%'>" +
                             desc + "</td><td><ul><li>" + price + "</li><li>" + posted + "</li></ul><td>" + avail.replace('\n', '<br>') + "</td></tr>")

    return seen_ads, table, listed_ids
def concat(list1, list2):
    return list1 + list2
def process(config, seen_ads, tokeep, listed_ids):
    cats = config['cats']
    areas = config['areas']
    base_url = config['base_url']
    page_ids = getPages(config['max_pages'])
    params = config['params']
    ids_seen = get_ids(seen_ads)
    ids_tokeep = get_ids(tokeep)
    table = []
    for cat in cats:
        HOME_BASE = base_url + "/" + cat + "/"
        for area in areas:
            for pageId in page_ids:

                url = HOME_BASE + area + '/' + pageId + params

                print("Area: %s\nUrl: %s \n" % (area, url))
                items = get_items(url)
                seen_ads, table, listed_ids = process_items(items, ids_tokeep, ids_seen, seen_ads, table, listed_ids)

                # tables=concat(tables, table)
                # seen_ads=concat(seen_ads, seen_ads0)
                # listed_ids=concat(listed_ids, listed_ids0)
    return seen_ads, table, listed_ids


def get_items(url):
    page = requests.get(url)
    tree = html.fromstring(page.content)
    listingsWrap = tree.find_class('list-listing-mini')

    # pagination-next

    return get_page_data(listingsWrap)


def attach_remaining_ads():
    remaining = []
    for id in tokeep:
        if(id not in listed_ids):
            url = 'http://www.gumtree.com/search?q=' + id

            table.append("<tr><td width='25%'><i data-id=" + str(id) + "></i><a href='" + url + "'><span>" + id + "</span></a></td><td width='25%'>" +
                         'desc' + "</td><td><ul><li>" + 'price' + "</li><li>" + 'area' + "</li><li>" + 'posted' + "</li></ul><td>" + 'avail' + "</td></tr>")


def get_first_item(item):
    if(type(item) is list):
        return item[0]
    return item

def save_listing_html(table):
    htmlTpl = u"<html><head><title>New Rentals</title></head><body><table>{}</table></body></html>"

    html_content = htmlTpl.format('\n'.join(table))  # .encode('utf-8'), 'utf-8' )
    write_file('listings.html', [html_content])

def review_and_keep(seen_ads, tokeep, table ):
    ids_seen = get_ids(seen_ads)
    ids_tokeep = get_ids(tokeep)

    id_pat = re.compile("data-id=(.*)></i>")
    title_pat = re.compile("<span>(.*)</span></a>")
    tk_len0 = len(ids_tokeep)


    new_table = []
    for item in table:
        text = item.replace('\n', '')
        id = id_pat.findall(text)
        title = title_pat.findall(text)

        if (len(title) == 0):
            title = [id[0]]

        title = title[0]
        id = id[0]
        id = id.replace(' ', '')

        # print(id,title)
        option = input('keep ad : {} ? '.format(title))
        if('k' in option and id not in ids_tokeep):
            # keep
            idx = ids_seen.index(id)
            tokeep.append(seen_ads[idx])

            ids_tokeep.append(id);
            new_table.append(item)
        elif ('d' in option):
            try:
                idx = ids_tokeep.index(id)
                del tokeep[idx]
                del ids_tokeep[idx]
            except Exception as e:
                pass

    print('keeping : %d ads' % len(ids_tokeep))

    keep_data = prepare_data(tokeep, '::')
    write_file('keep.txt', keep_data)

    save_listing_html(new_table)

areas = [
    "streatham"
    # "brixton",
    # "lambeth",
    # "vauxhall",
    # "tulse-hill"
]
cats = [
    "studios-bedsits-rent",
    "flats-and-houses-for-rent"]
BASE = "http://www.gumtree.com"
# HOME_BASE = BASE + "/flatshare-offered/"


file = 'seen_links.txt'

seen_ads = []
tokeep = []

get_ids = lambda data: [get_first_item(x) for x in data]

seen_ads = parse_lines(read_file(file), '::')
# ids_seen = get_ids(seen_ads)

tokeep = parse_lines(read_file('keep.txt'), '::')
# ids_tokeep = get_ids(tokeep)

params = '?distance=3&min_price=90&max_price=170&seller_type=private'
listed_ids = []
table = []

config = {
    'cats' : cats,
    'areas': areas,
    'base_url': BASE,
    'max_pages': 2,
    'params': params
}

#
seen_ads, table, listed_ids = process(config, seen_ads, tokeep, listed_ids)

# save fetched ids
seen_data = prepare_data(seen_ads, '::')
write_file(file, seen_data)



#
save_listing_html(table)


# review ads and update listing
review_and_keep(seen_ads, tokeep, table )

webbrowser.open_new_tab(os.path.abspath('') + '/listings.html')
