import argparse
from shutil import copyfile
import os
import json
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import TimeoutException
import logging
import sys
import time
import traceback
import parsedatetime.parsedatetime as pdt
import datetime

## Constants 
database_filename = "all_albums_shared.json"
page_redirect_timeout = 10
class_name_shared_contacts = "viaTeb"
class_name_timerange = "cMH06"
class_name_timerange_notshared = "UmNiJe" # class name when album is not shared 

## Init 
log = logging.getLogger('')
log.setLevel(logging.INFO)
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

parser = argparse.ArgumentParser()
# actions 
parser.add_argument("-update", help="Update local database with new albums", action="store_true")
parser.add_argument("-refresh", help="Refresh local albums with online information", action="store_true")
parser.add_argument("-backup", help="Create backup for local database", action="store_true")
parser.add_argument("-authenticate", help="Authenticate session for photos.google.com", action="store_true")
parser.add_argument("-deleteLink", help="Delete public shared link from photos.google.com", action="store_true")
# settings
parser.add_argument("-dir", help="Specify working directory")
parser.add_argument("-title", help="Filter albums based on title")
parser.add_argument("-sharedWith", help="Filter albums shared with a specific person")
parser.add_argument("-notSharedWith", help="Filter albums not shared with a specific person")
parser.add_argument("-albumDate", help="Filter albums with a specific date")
parser.add_argument("-withLink", help="Filter albums with link sharing (True/False)")
parser.add_argument("-output", help="Specify output file for results")
parser.add_argument("-pageTimeout", help="Specify timeout for page redirects")

# TODO: generate html output for results 
# TODO: send email with results 
# TODO: memories email for a given time window 
# TODO: delete local albums based on search criteria using -title -sharedWith -notSharedWith

args = parser.parse_args()

console = logging.StreamHandler()
console.setLevel(logging.INFO)
log.addHandler(console)

# process settings
if (args.dir):
    os.chdir(args.dir)

if (args.pageTimeout):
    page_redirect_timeout = int(args.pageTimeout)

original_stdout = sys.stdout
if (args.output):
    sys.stdout = open(args.output, "w", encoding='utf-8')

def get_local_albums():
    albums = []
    if os.path.exists(database_filename):
        with open(database_filename, "r") as infile:
            albums = json.load(infile)
    return albums

def get_online_photoservice():
    # Authenticate to gphotos
    SCOPES = ['https://www.googleapis.com/auth/photoslibrary']
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('listshared-token.pickle'):
        with open('listshared-token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # credentials.json can be downloaded from https://console.developers.google.com/apis/credentials
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('listshared-token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    photosservice = build('photoslibrary', 'v1', credentials=creds)
    return photosservice

def get_online_albums():
    photosservice = get_online_photoservice()
    results = photosservice.albums().list(pageSize=50).execute()
    items = results.get('albums', [])
    nextPageToken = results.get('nextPageToken')
    all_albums = []
    for item in items:
        all_albums.append(item)

    while nextPageToken:
        results = photosservice.albums().list(pageToken=nextPageToken, pageSize=50).execute()
        items = results.get('albums', [])
        for item in items:
            all_albums.append(item)
        nextPageToken = results.get('nextPageToken')
    
    return all_albums

def create_chrome_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--profile-directory=Default")
    options.add_argument("--user-data-dir=" + os.getcwd() + "\\TempChromeProfiles")

    # Download ChromeDriver from https://sites.google.com/a/chromium.org/chromedriver/downloads 
    driver = webdriver.Chrome(options=options)
    return driver 

def get_online_album_info(driver, productUrl):
    calendar = pdt.Calendar()
    driver.get(productUrl)

    wait = WebDriverWait(driver, page_redirect_timeout)
    
    contacts = []
    albumDate = ''
    linkSharing = False
    try:
        # wait for redirect to https://photos.google.com/share/ to happen
        wait.until(ec.url_contains("/share/"))

        # get album contact list
        div_element = wait.until(lambda d: d.find_element_by_class_name(class_name_shared_contacts))
        if div_element: 
            contactImages = div_element.find_elements_by_tag_name('img')
            for img in contactImages:
                contacts.append(img.get_attribute('alt'))

        # album has shared link
        first_div = div_element.find_element_by_xpath(".//div[1]")
        linkSharing = (first_div.is_displayed() and "Link sharing is on" == first_div.get_attribute("title"))

    except Exception as e:
        contacts = []
        log.error ("Timeout error")
        log.error (e, exc_info=True)

    try:
        # get album date
        div_element = driver.find_element_by_class_name(class_name_timerange)
        albumDate = div_element.text # datetime.datetime(*calendar.parse(div_element.text)[0][:6])
    
    except Exception as e:
        albumDate = ''
        log.error ("Error")
        log.error (e, exc_info=True)

    if albumDate == '':
        try:
            div_element = driver.find_element_by_class_name(class_name_timerange_notshared)
            albumDate = div_element.text 
        except Exception as e:
            albumDate = ''
            log.error ("Error")
            log.error (e, exc_info=True)

    return { 'contacts': contacts, 'albumDate': albumDate, 'linkSharing': linkSharing }
    # import dateutil.parser
    # d = dateutil.parser.parse(albumDate.isoformat())
    # print(d.isoformat())


def remove_link_from_online_album(driver, productUrl):
    driver.get(productUrl)
    wait = WebDriverWait(driver, page_redirect_timeout)

    try:
        wait.until(ec.url_contains("/share/"))
    except TimeoutException as e:
        log.info(u" ## Album not shared: {0}".format(productUrl))
        log.error (u"Error removing link: {0} for {1}".format(e, productUrl))
        log.error (e, exc_info=True)
        return

    try:
        div_element = driver.find_element_by_class_name(class_name_shared_contacts)
        first_div = div_element.find_element_by_xpath(".//div[1]")
        if (first_div.is_displayed() and "Link sharing is on" == first_div.get_attribute("title")):
            first_div.click()
            
            div_sharing = wait.until(lambda d: d.find_element_by_xpath('//*[text()[contains(.,"Link sharing")]]'))
            tr_parent = div_sharing.find_element_by_xpath('./ancestor::tr[1]')
            input_check = tr_parent.find_element_by_tag_name("input")
            input_check.click()
            
            delete_label = wait.until(lambda d: d.find_element_by_xpath('//*[text()[contains(.,"Delete link")]]'))
            delete_button = delete_label.find_element_by_xpath('./ancestor::button[1]')
            driver.execute_script("arguments[0].click();", delete_button)

            log.info(u" -- Album link removed: {0}".format(productUrl))
        else:
            log.info(u" ** Album link already not shared: {0}".format(productUrl))
    except Exception as e:
        log.info(u" @@ Album link not removed: {0}".format(productUrl))
        log.error("Exception")
        log.error(e, exc_info=True)


def list_filtered_albums(title, sharedWith, notSharedWith, albumDate, withLink):
    log.info("Loading local albums... ")
    local_albums = get_local_albums()
    log.info("Done")

    log.info('Searching for albums...')
    log.info(u'   Title: {0}, Shared with: {1}, Not shared with: {2}'.format(title, sharedWith, notSharedWith))
    filtered_albums = [a for a in local_albums if (not title or title in a.get("title", "")) and (not sharedWith or sharedWith in a["sharedWith"]) and (not notSharedWith or notSharedWith not in a["sharedWith"]) and (not albumDate or albumDate in a["albumDate"]) and (not withLink or bool(withLink) == a["linkSharing"]) ]

    for r in filtered_albums:
        log.info(u' -- Album {0} '.format(r.get("title", None)))
        log.info(u'         {0}'.format(r["productUrl"]))
        log.info(u'         {0}'.format(r["sharedWith"]))
    
    print(json.dumps(filtered_albums, indent=4))

def update_database(download_albums):
    log.info("Loading local albums... ")
    local_albums = get_local_albums()
    log.info("Done")

    new_albums = []
    if download_albums:
        log.info("Loading online albums... ")
        online_albums = get_online_albums()
        log.info("Done")

        # check for new albums
        for oa in online_albums:
            la = next((a for a in local_albums if a["id"] == oa["id"]), None)

            if (la == None):
                # new albums found
                log.info(u' -- New album {0} (id={1})'.format(oa.get("title", None), oa["id"]))
                new_albums.append(oa)
            
            # TODO: Update titles & image counts & cover image
    else:
        new_albums = local_albums
        local_albums = []    

    if not new_albums:
        log.warning('No new albums found')
    else:
        log.info('Downloading online sharing info...')
        # download sharing info about new albums
        driver = create_chrome_driver()
        
        for na in new_albums:
            log.info(u' -- Album {0} (id={1}) ... '.format(na.get("title", None), na["id"]))
            info = get_online_album_info(driver, na["productUrl"])
            
            na["sharedWith"] = info["contacts"]
            na['albumDate'] = info['albumDate']
            na['linkSharing'] = info['linkSharing']

            log.info("Done")

            # adding new album to local albums
            local_albums.append(na)

            # saving local albums
            log.info('Saving local albums... ')
            with open(database_filename, "w+") as out_file:
                json.dump(local_albums, out_file, indent=4)
            log.info("Done")

        driver.quit()

        # printing new albums
        print(json.dumps(new_albums, indent=4))
    
def remove_links_from_all_albums():
    log.info("Loading local albums... ")
    local_albums = get_local_albums()
    log.info("Done")

    driver = create_chrome_driver()

    for la in local_albums:
        remove_link_from_online_album(driver, la["productUrl"])

def authenticate_selenium():
    options = webdriver.ChromeOptions()
    options.add_argument("--profile-directory=Default")
    options.add_argument("--user-data-dir=" + os.getcwd() + "\\TempChromeProfiles")
    driver = webdriver.Chrome(chrome_options=options)
    driver.get("https://photos.google.com/albums")
    
    # don't close driver
    wait = WebDriverWait(driver, 60 * 60 * 5) # timeout authentication in 5 minutes
    try:
        wait.until(ec.title_is("Albums - Google Photos"))
    except TimeoutException as e:
        log.error ("Timeout error: " + e)
        log.error (e, exc_info=True)


def create_backup_database():
    copyfile(database_filename, database_filename + ".bak")

## MAIN

# process actions 
if (args.authenticate):
    authenticate_selenium()

if (args.backup):
    log.info("Creating backup... ")
    create_backup_database()
    log.info("Done")

if (args.title or args.sharedWith or args.notSharedWith or args.albumDate or args.withLink):
    list_filtered_albums(args.title, args.sharedWith, args.notSharedWith, args.albumDate, args.withLink)

if (args.update):
    log.info("Updating database...")
    update_database(download_albums=True)
    log.info("Done")

if (args.refresh):
    log.info("Refresh local database...")
    update_database(download_albums=False)
    log.info("Done")

if (args.deleteLink):
    log.info("Removing links from all albums...")
    remove_links_from_all_albums()
    log.info("Done")

if (args.output):
    sys.stdout.close()
sys.stdout = original_stdout

if not (args.backup or args.update or args.title or args.sharedWith or args.notSharedWith or args.authenticate or args.deleteLink or args.refresh):
    parser.print_help()

## THE END