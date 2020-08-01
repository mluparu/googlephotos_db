# Google Photos database 
A tool to manage your albums in Google Photos. Of course, you can manage your albums using the Google Photos interface on your phone or the web. Unfortunately, if your album collection reaches 300+ albums, managing them using that UI is simply impractical. 

This script allows you to create a local copy of the album metadata (including information that is not available through the Google Photos APIs like sharing info) and then perform searches to narrow in albums that are shared with specific contacts or albums that perhaps you forgot to share. The local database is stored as JSON, thus making it very easy to read and parse for other purposes that are not covered by this tool or by the Google Photos interface

## Installation instructions
1. Install Python 

There are many ways to install Python. I install Anaconda from https://docs.anaconda.com/anaconda/install/windows/ To activate the conda environment run this command
> conda activate base

2. Install Google API Client

Install the Python support for Google API by following the instructions here: https://developers.google.com/docs/api/quickstart/python 

> pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

3. Requst API Access to Google Photos

You can follow the instructions here https://developers.google.com/photos/library/guides/get-started or start from https://console.developers.google.com/apis/library and search for "Photos Library API". In the "Photos Library API" page select "Enable" and follow the step-by-step instructions.

Make sure you enable the OAuth client and in the last steps and download credentials.json to a local folder that you will use as the working directory that you will eventually pass as a parameter to this Python script

4. Install Chrome Web Driver 

Download it from here: https://sites.google.com/a/chromium.org/chromedriver/downloads  
Make sure the webdriver version matches the version of Chrome you have installed on your local box (check your version by typing chrome://version in the address bar) 

You will need to add the chromedriver binary to the system path. If you're using PowerShell, you can run this command

> $env:Path+= ";<chromedriver_folder>"

5. Install Selenium 

> pip install --upgrade selenium 

6. Install additional Python packages 

> pip install parsedatetime

7. Authenticate the Chrome WebDriver session to your Google account

This is going to be the first time you run the Python script. If you get an error, this means that one of the steps above didn't go so well

> python .\googlephotos_db.py -auth -d "working_folder"

If you can see your Google Photos albums, this step succeeded and you can close the Chrome window. Congratulation! You should now be able to run GooglePhotosDb 

## Usage

For all uses, you will want to designate a "working_folder" where the credentials will be cached, the database will be stored, as well as the temporary Chrome profile created solely for this purpose. 

### 1. First time update
GooglePhotos_DB provides several operations over albums, but the one you will first use (and the most lenghty one) is to update the local database by scraping your albums (using a mix of Photos API and Chrome automation)

> python .\googlephotos_db.py -u -d "working_folder"

The first time you run this comamnd, you will need to also authenticate for the Google Photos API access. Your browser will open and you will need to grant access to the Google app you created in step #3. If authentication is successful, yoi will see a message in your browser "The authentication flow has completed. You may close this window.". You will also likely receive an email from Google notifying you that you granted Photos access to this app. 

Now the program will enumerate all your albums and collect the list of contacts you shared your albums with.

### 2. Keeping your database up-to-date
There are 2 ways to refresh your local album database. One is an update that checks whether there are any new albums created and adds them to the database (this will only read the metadata for these new albums):

> python .\googlephotos_db.py -u -d "working_folder"

The other deeper update rechecks all existing albums in the database for any changes in titles, and contacts they are shared with:

> python .\googlephotos_db.py -r -d "working_folder"

### 3. Removing public shared links from your albums
In recent history, Google added support for sharing an album without creating a publicly accessible link for that album (basically only the authenticalted contacts you shared the album with can see the content, not everyone that gets a hold of the link). One thing that they didn't provide is the ability to remove the "shared link" feature from existing albums in one click. If you have hundreds of albums, going one by one to remove the "shared link" is NotFun(tm). To automatically remove "shared link" from all of your albums, run this command:

> python .\googlephotos_db.py -deleteLink -d "working_folder"

### 4. Searching for a specific album
Once the local database of albums is available, you can search for specific albums according to a few criteria: 
|Switch|Criteria|
|--|--|
|-title "text"|contains a certain string in its title|
|-sharedWith "contact"|is shared with a specific person|
|-notSharedWith "contact"|is not shared with a specific person|
|-albumDate "date"|album has a particular date|
|-withLink True/False|albums that have a public link or not |

Usually search results will be displayed on screen, but you can redirect them to a specific file using the -output "filename" switch. 

### 5. Backup database
Creates a backup database. Recommended before a big update/refresh

> python .\googlephotos_db.py -backup -d "working_folder"
