import re
import socket
from datetime import datetime
from urlextract import URLExtract
import urllib.parse as urlparse
from urllib.parse import parse_qs
import click
import argparse
import csv
import os
from dateutil.parser import parse
import pandas as pd
from urllib.parse import unquote
import hashlib

# When you need to connect to a database
#from pandas.io import sql
#import mysql.connector
#from sqlalchemy import create_engine
#import mysql.connector


#Global Variables
data = []
map_refer = {}

# Missing a ArgumentParser
#parser = argparse.ArgumentParser(description='Description of your program')
#parser.add_argument('-p','--path', help='Localization of the patching files', default= "./Files/")
#args = vars(parser.parse_args())


def extract(request):
    """
    Extract url domain from wayback request.
    """
    extractor = URLExtract()
    try:
        urls = extractor.find_urls('/'.join(request.split('/')[3:]))
        if urls:
            return urls[0]
        else: 
            return None
    except:
        import pdb;pdb.set_trace()

def getParametersFromRequestWayback(request, df, i):
    """
    Extract parameters from wayback request.
    """
    # Just a sanity check.
    if not pd.isnull(df.at[i, 'DATE']):
        try:
            # Generate timestamp using the parameter DATE
            date_simple = df.at[i, 'DATE'].replace("[", "").replace("]", "")
            date = datetime.strptime(date_simple, "%d/%b/%Y:%H:%M:%S")
            
            # Just a sanity check.
            if re.match(r"GET /wayback/[0-9]+", request):

                #Extract url domain 
                url = extract(request)
                if urlparse.urlparse(url).netloc != "":
                    final_url = urlparse.urlparse(url).netloc
                else:
                    final_url = url
                
                #Put into a list to later generate a dataframe
                data.append([df.at[i, "IP_ADDRESS"], df.at[i, "USER_AGENT"], date.timestamp(), df.at[i, "REQUEST"], df.at[i, "STATUS_CODE"], df.at[i, "PREVIOUS_REQUEST"], final_url])
        except:
            raise ValueError("Error - getParametersFromRequestWayback function")

def getParametersFromRequest(request, df, i, boolRequest):
    """
    Extract and process the parameters from query request.
    Function only used for Apache logs.
    """
    
    # Check whether we are processing the request or the previous_request
    if boolRequest:
        #This request will not be analyzed in the first analysis, however it is done for later analysis.
        #Image Search JSP and Page Search JSP will be treated as equals.
        if request.startswith("GET /search.jsp?") or request.startswith("GET /images.jsp?"):
            
            # Set the parameter BOOL_QUERY (i.e., =1 means the line is a query)
            df.at[i, 'BOOL_QUERY'] = 1
            
            # Set the parameter TYPE_SEARCH
            if request.startswith("GET /search.jsp?"):
                df.at[i, 'TYPE_SEARCH'] = "search_jsp"
            else:
                df.at[i, 'TYPE_SEARCH'] = "images_jsp"
            
            # Parse the REQUEST and Set the parameters TRACKINGID, USER_TRACKING_ID, SEARCH_TRACKING_ID, QUERY, LANG_REQUEST, FROM_REQUEST, TO_REQUEST
            parsed = urlparse.urlparse(request)
            try:
                df.at[i, 'TRACKINGID'] = parse_qs(parsed.query)['trackingId'][0]
                df.at[i, 'USER_TRACKING_ID'] = parse_qs(parsed.query)['trackingId'][0].split("_")[0]
                df.at[i, 'SEARCH_TRACKING_ID'] = parse_qs(parsed.query)['trackingId'][0].split("_")[1]
            except:
                df.at[i, 'TRACKINGID'] = ""
            try:
                df.at[i, 'QUERY'] = unquote(parse_qs(parsed.query)['query'][0])
                df.at[i, 'LANG_REQUEST'] = parse_qs(parsed.query)['l'][0]
            except:
                df.at[i, 'BOT'] = 1
            try:
                df.at[i, 'FROM_REQUEST'] = parse_qs(parsed.query)['dateStart'][0]
                df.at[i, 'TO_REQUEST'] =  parse_qs(parsed.query)['dateEnd'][0]
            except:
                df.at[i, 'FROM_REQUEST'] = None
                df.at[i, 'TO_REQUEST'] =  None          
        
        #Image Search API and Page Search API calls will be treated as equals.
        elif "textsearch?" in request or "imagesearch?" in request:
            
            # Set the parameter BOOL_QUERY (i.e., =1 means the line is a query)
            df.at[i, 'BOOL_QUERY'] = 1

            # Set the parameter TYPE_SEARCH
            if request.startswith("GET /imagesearch?"):
                df.at[i, 'TYPE_SEARCH'] = "imagesearch"
            else:
                df.at[i, 'TYPE_SEARCH'] = "textsearch"
            
            # Parse the REQUEST and Set the parameters TRACKINGID, USER_TRACKING_ID, SEARCH_TRACKING_ID, QUERY, MAXITEMS, PAGE, FROM_REQUEST, TO_REQUEST
            parsed = urlparse.urlparse(request)
            try:
                df.at[i, 'TRACKINGID'] = parse_qs(parsed.query)['trackingId'][0]
                df.at[i, 'USER_TRACKING_ID'] = parse_qs(parsed.query)['trackingId'][0].split("_")[0]
                df.at[i, 'SEARCH_TRACKING_ID'] = parse_qs(parsed.query)['trackingId'][0].split("_")[1]
            except:
                df.at[i, 'TRACKINGID'] = ""
            try:
                #import pdb;pdb.set_trace()
                df.at[i, 'QUERY'] = unquote(parse_qs(parsed.query)['q'][0])
                offset = int(parse_qs(parsed.query)['offset'][0])
                df.at[i, 'MAXITEMS'] = int(parse_qs(parsed.query)['maxItems'][0])
                df.at[i, 'PAGE'] = int(offset/df.at[i, 'MAXITEMS'])
            except:
                df.at[i, 'BOT'] = 1
            try:
                df.at[i, 'FROM_REQUEST'] = parse_qs(parsed.query)['from'][0]
                df.at[i, 'TO_REQUEST'] =  parse_qs(parsed.query)['to'][0]
            except:
                df.at[i, 'FROM_REQUEST'] = None
                df.at[i, 'TO_REQUEST'] =  None
        
    #Process the parameter REQUEST and set the parameter PREVIOUS_REQUEST
    else:
        if request.startswith("GET /search.jsp?") or request.startswith("GET /images.jsp?"):
            parsed = urlparse.urlparse(request)
            df.at[i, 'PREVIOUS_QUERY'] = parse_qs(parsed.query)['query'][0]
        elif request.startswith("GET /imagesearch?") or request.startswith("GET /textsearch?"):
            parsed = urlparse.urlparse(request)
            df.at[i, 'PREVIOUS_QUERY'] = parse_qs(parsed.query)['q'][0]

def processDataframe(request, previous_request, file_name, df, i, all_info_date):
    """
    Function to process each log depending on the format (Apache vs Log4j)
    """

    # Check if we are processing the Apache Log
    if "logfile" in file_name:
        getParametersFromRequest(request.replace(" HTTP/1.1", ""), df, i, True)
        if pd.isnull(previous_request):
            getParametersFromRequest(previous_request.replace(" HTTP/1.1", ""), df, i, False)
    
    # if we are not processing the Apache Log
    else:
        #Only thing needed from request
        parsed = urlparse.urlparse(request)
        try:
            df.at[i, 'TRACKINGID'] = parse_qs(parsed.query)['trackingId'][0]
            df.at[i, 'USER_TRACKING_ID'] = parse_qs(parsed.query)['trackingId'][0].split("_")[0]
            df.at[i, 'SEARCH_TRACKING_ID'] = parse_qs(parsed.query)['trackingId'][0].split("_")[1]
        except:
            df.at[i, 'TRACKINGID'] = ""

    # Just a sanity check.
    if not pd.isnull(df.at[i, 'DATE']):
        try:
            # Generate TIMESTAMP using the parameter DATE and Set the parameters YEAR, MONTH, DAY, HOUR, MINUTE
            date_simple = df.at[i, 'DATE'].replace("[", "").replace("]", "")
            date = datetime.strptime(date_simple, "%d/%b/%Y:%H:%M:%S")
            df.at[i, 'TIMESTAMP'] = date.timestamp()
            if all_info_date:
                df.at[i, 'YEAR'] = date.year
                df.at[i, 'MONTH'] = date.month
                df.at[i, 'DAY'] = date.day
                df.at[i, 'HOUR'] = date.hour
                df.at[i, 'MINUTE'] = date.minute
        except:
            df.at[i, 'BOT'] = 1
    else:
        df.at[i, 'BOT'] = 1
    return date

def mergeFiles():
    """
    Function that will process each log and merge them (The core of this file).
    """
    
    click.secho("Start Process...", fg='green')
    
    #Location\path of the Logs.
    mypath = "./data/"
    
    #Create Dataframes for each (Apache Log, Image Search API Log4j, Page Search API Log4j, Webapp API Log4j).
    df_merge_apache_file = None
    df_merge_image_file = None
    df_merge_page_file = None
    df_merge_arquivo_webapp_file = None
    
    # Just to initialize variables that we are going to use (can be removed).
    df_log = None
    df_image = None
    df_page = None
    df_arquivo = None
    
    ## For each log file:
    for subdir, dirs, files in os.walk(mypath):
        
        #If list is not empty.
        if files:
            
            ## Progress bar with the number of log files.
            with click.progressbar(length=len(files), show_pos=True) as progress_bar_total:
                for file in files:
                    progress_bar_total.update(1)
                    
                    #Get Filename
                    file_name = os.path.join(subdir, file)

                    # Process Apache Logs
                    if file_name.startswith("./data/logs/arquivo.pt_apache/logfile"):

                        #Read file into Dataframe
                        names_apache = ["IP_ADDRESS", "CLIENT_ID", "USER_ID", "DATE", "ZONE", "REQUEST", "STATUS_CODE", "SIZE_RESPONSE", "PREVIOUS_REQUEST", "USER_AGENT", "RESPONSE_TIME"]
                        df_log = pd.read_csv(file_name, sep='\s+', names=names_apache)

                        #Init new collumns
                        df_log["UNIQUE_USER"] = ""
                        df_log["SPELLCHECKED"] = 0
                        df_log["REFER"] = ""

                        #Tracking
                        df_log["TRACKINGID"] = ""
                        df_log["USER_TRACKING_ID"] = ""
                        df_log["SEARCH_TRACKING_ID"] = ""

                        #Date
                        df_log["TIMESTAMP"] = 0
                        df_log["YEAR"] = 0
                        df_log["MONTH"] = 0
                        df_log["DAY"] = 0
                        df_log["HOUR"] = 0
                        df_log["MINUTE"] = 0

                        #Search and Query
                        df_log["TYPE_SEARCH"] = ""
                        df_log["QUERY"] = ""
                        df_log["LANG_REQUEST"] = ""
                        df_log["FROM_REQUEST"] = ""
                        df_log["TO_REQUEST"] = ""
                        df_log["PREVIOUS_QUERY"] = ""
                        df_log["MAXITEMS"] = 0
                        df_log["PAGE"] = 0

                        #Query from robots or internal requests (default is 0, "Not a Bot")
                        df_log["BOT"] = 0

                        ## Progress Bar of the number of lines processed (Apache Log File).
                        with click.progressbar(length=df_log.shape[0], show_pos=True) as progress_bar:
                            for i in df_log.index:
                                progress_bar.update(1)
                                
                                #Get Request
                                request = df_log.at[i, 'REQUEST']
                                
                                #Get Previous Request
                                previous_request = df_log.at[i, 'PREVIOUS_REQUEST']
                                
                                #Problem with some requestes
                                if isinstance(request, str) and isinstance(previous_request, str):                                             
                                    
                                    #We will create different files (Query Log file and Wayback Log file)
                                    
                                    # Check if the request is not from wayback
                                    if "wayback" not in request:
                                        
                                        # Only process requests from textsearch, imagesearch, search.jsp, and images.jsp.
                                        if request.startswith("GET /textsearch?") or request.startswith("GET /imagesearch?") or request.startswith("GET /search.jsp?") or request.startswith("GET /images.jsp?"):
                                            
                                            processDataframe(request, previous_request, file_name, df_log, i, True)

                                            #Generate a unique identifier for each user, making it an anonymized user.
                                            string_user = str(df_log.at[i, 'IP_ADDRESS']) + str(df_log.at[i, 'USER_AGENT'])
                                            df_log.at[i, 'UNIQUE_USER'] = int(hashlib.sha1(string_user.encode("utf-8")).hexdigest(), 16) % (10 ** 8)
                                            
                                            #Check if the entry was generated because the user clicked on the query suggestion.
                                            if "spellchecked=true" in previous_request:
                                                df_log.at[i, 'SPELLCHECKED'] = 1
                                            
                                            #Get a dictionary with the refers
                                            if "arquivo.pt" not in previous_request:
                                                df_log.at[i, 'REFER'] = previous_request
                                                if previous_request not in map_refer:
                                                    map_refer[previous_request] = 1
                                                else:
                                                    map_refer[previous_request] += 1
                                        else:
                                            #This condition removes lines such as "GET /js/jquery-1.3.2.min.js HTTP/1.1"
                                            df_log.at[i, 'BOT'] = 1
                                    else:
                                        """
                                        Process the wayback requests
                                        """
                                        #Set the entrie as "Bot" to not appear in the queries dataset.
                                        df_log.at[i, 'BOT'] = 1
                                        
                                        getParametersFromRequestWayback(request, df_log, i)
                                else:
                                    df_log.at[i, 'BOT'] = 1

                        #Remove entries from "BOTs"
                        df_log = df_log[df_log['BOT']==0]
                        
                        #Concatenate the file with previous files
                        df_log = df_log[['IP_ADDRESS', 'STATUS_CODE', 'REQUEST', 'USER_AGENT', 'TRACKINGID', 'USER_TRACKING_ID', 'SEARCH_TRACKING_ID', 'TIMESTAMP', 'YEAR', 'MONTH', 'DAY', 'HOUR', 'MINUTE', 'TYPE_SEARCH', 'QUERY', 'PAGE', 'MAXITEMS', 'LANG_REQUEST', 'FROM_REQUEST', 'TO_REQUEST', 'REFER', 'SPELLCHECKED', 'UNIQUE_USER']]                        
                        frames = [df_merge_apache_file, df_log]
                        df_merge_apache_file = pd.concat(frames)

                    ## Logs Image Search API  
                    if file_name.startswith("./data/logs/arquivo.pt_image_search/imagesearch"):

                        #Read file into DataFrame
                        names_image_search = ["DATE", "LOG_TYPE", "APPLICATION", "-", "IP_ADDRESS", "USER_AGENT", "URL_REQUEST", "IMAGE_SEARCH_RESPONSE(ms)", "IMAGE_SEARCH_PARAMETERS", "IMAGE_SEARCH_RESULTS"]
                        df_image = pd.read_csv(file_name, sep='\t', error_bad_lines=False, names=names_image_search)

                        #Init New Collumns
                        df_image["TRACKINGID"] = ""
                        df_image["BOT"] = 0
                        df_image["TIMESTAMP"] = 0

                        ## Progress Bar of the number of lines processed (Image Search API Log4j).
                        with click.progressbar(length=df_image.shape[0], show_pos=True) as progress_bar:
                            for i in df_image.index:
                                progress_bar.update(1)

                                # Just a sanity check.
                                if not pd.isnull(df_image.at[i, 'IP_ADDRESS']):
                                    
                                    request = df_image.at[i, 'URL_REQUEST']
                                    
                                    # Just a sanity check.
                                    if not pd.isnull(request):
                                        
                                        #Missing process better the URL #FIXME
                                        processDataframe(request, "", file_name, df_image, i, False)
                                        
                                        #Remove "ms" from the string
                                        df_image.at[i, 'IMAGE_SEARCH_RESPONSE(ms)'] = df_image.at[i, 'IMAGE_SEARCH_RESPONSE(ms)'].replace("ms", "")
                                    else:
                                        df_image.at[i, 'BOT'] = 1
                                else:
                                    df_image.at[i, 'BOT'] = 1

                        #Remove entries from "BOTs" and entries with empty TRACKINGID
                        df_image = df_image[df_image['BOT']==0]
                        df_image = df_image[df_image["TRACKINGID"] != ""]

                        #Concatenate the file with previous files
                        df_image = df_image[["TIMESTAMP", "IP_ADDRESS", "USER_AGENT", "URL_REQUEST", "IMAGE_SEARCH_RESPONSE(ms)", "IMAGE_SEARCH_PARAMETERS", "IMAGE_SEARCH_RESULTS", "TRACKINGID"]]
                        frames = [df_merge_image_file, df_image]
                        df_merge_image_file = pd.concat(frames)

                    if file_name.startswith("./data/logs/arquivo.pt_pagesearch/pagesearchwebapp"):

                        #Read file into DataFrame
                        names_page_search = ["DATE", "LOG_TYPE", "APPLICATION", "-", "IP_ADDRESS", "USER_AGENT", "URL_REQUEST", "PAGE_SEARCH_RESPONSE(ms)",  "PAGE_SEARCH_PARAMETERS", "PAGE_SEARCH_SEARCH_RESULTS"]
                        df_page = pd.read_csv(file_name, sep='\t', error_bad_lines=False, names=names_page_search, encoding='utf-8')

                        #We only need entrie from the keyword "PageSearchController"
                        df_page = df_page[df_page['APPLICATION']=="PageSearchController"]
                        
                        #Init New Collumns
                        df_page["TRACKINGID"] = ""
                        df_page["BOT"] = 0
                        df_page["TIMESTAMP"] = 0

                        ## Progress Bar of the number of lines processed (Page Search API Log4j).
                        with click.progressbar(length=df_page.shape[0], show_pos=True) as progress_bar:
                            for i in df_page.index:
                                progress_bar.update(1)
                                
                                # Just a sanity check.
                                if not pd.isnull(df_page.at[i, 'IP_ADDRESS']) and "(versionHistory)" not in df_page.at[i, 'IP_ADDRESS']:
                                    
                                    request = df_page.at[i, 'URL_REQUEST']
                                    
                                    # Just a sanity check.
                                    if not pd.isnull(request):

                                        #Missing process better the URL #FIXME
                                        processDataframe(request, "", file_name, df_page, i, False)
                                        
                                        #Remove "ms" from the string
                                        df_page.at[i, 'PAGE_SEARCH_RESPONSE(ms)'] = df_page.at[i, 'PAGE_SEARCH_RESPONSE(ms)'].replace("ms", "")
                                    else:
                                        df_page.at[i, 'BOT'] = 1
                                else:
                                    df_page.at[i, 'BOT'] = 1

                        #Remove entries from "BOTs" and empty TRACKINGID
                        df_page = df_page[df_page['BOT']==0]
                        df_page = df_page[df_page["TRACKINGID"] != ""]

                        #Concatenate the file with previous files
                        df_page = df_page[["TIMESTAMP", "IP_ADDRESS", "USER_AGENT", "URL_REQUEST", "PAGE_SEARCH_RESPONSE(ms)",  "PAGE_SEARCH_PARAMETERS", "PAGE_SEARCH_SEARCH_RESULTS", "TRACKINGID"]]
                        frames = [df_merge_page_file, df_page]
                        df_merge_page_file = pd.concat(frames)

                    if file_name.startswith("./data/logs/arquivo.pt_arquivo_webapp/arquivo-webapp.log"):
                        
                        #Read file into DataFrame
                        names_arquivo = ["DATE", "LOG_TYPE", "USER", "NADA", "IP_ADDRESS", "USER_AGENT", "REQUEST", "TRACKINGID", "SESSION_ID", "TIMESTAMP_URL", "URL"]
                        df_arquivo = pd.read_csv(file_name, sep='\t', error_bad_lines=False, names=names_arquivo)

                        #Init New Collumns
                        df_arquivo["BOT"] = 0
                        df_arquivo["TIMESTAMP"] = 0
                        df_arquivo["POSITION"] = 0

                        ## Progress Bar of the number of lines processed (Webapp Log4j).
                        with click.progressbar(length=df_arquivo.shape[0], show_pos=True) as progress_bar:
                            for i in df_arquivo.index:
                                progress_bar.update(1)
                                try:
                                    # Only entries with the name "ViewTracking"
                                    if "ViewTracking" not in df_arquivo.at[i, 'LOG_TYPE']:
                                        df_arquivo.at[i, 'IP_ADDRESS'] = str(df_arquivo.at[i, 'IP_ADDRESS']).replace("\'", "")
                                        
                                        # Remove our own requests
                                        if "10.0.23." not in df_arquivo.at[i, 'IP_ADDRESS']:
                                            df_arquivo.at[i, 'SESSION_ID'] = str(df_arquivo.at[i, 'SESSION_ID']).replace("\'", "")
                                            
                                            # Generate TIMESTAMP using the parameter DATE
                                            date = datetime.strptime(df_arquivo.at[i, 'DATE'], "%d/%b/%Y:%H:%M:%S")
                                            df_arquivo.at[i, 'TIMESTAMP'] = date.timestamp()

                                            # Process the collumn TRACKINGID and separate in POSITION e TRACKINGID
                                            list_elements_trackingid = str(df_arquivo.at[i, "TRACKINGID"]).replace("\'", "").split("_")
                                            df_arquivo.at[i, "POSITION"] = list_elements_trackingid[2]
                                            df_arquivo.at[i, "TRACKINGID"] = '_'.join(list_elements_trackingid[0:2])
                                        else:
                                            df_arquivo.at[i, 'BOT'] = 1
                                    else:
                                        df_arquivo.at[i, 'BOT'] = 1
                                except:
                                    df_arquivo.at[i, 'BOT'] = 1
                        
                        #Remove entries from "BOTs"
                        df_arquivo = df_arquivo[df_arquivo['BOT']==0]

                        #Concatenate the file with previous files
                        df_arquivo = df_arquivo[["IP_ADDRESS", "USER_AGENT", "TIMESTAMP", "REQUEST", "SESSION_ID", "POSITION", "TRACKINGID"]]
                        frames = [df_merge_arquivo_webapp_file, df_arquivo]
                        df_merge_arquivo_webapp_file = pd.concat(frames)

    print(map_refer)

    #Create DataBase with only the Wayback requests
    df = pd.DataFrame(data, columns=["IP_ADDRESS", "USER_AGENT", 'TIMESTAMP', "REQUEST", "STATUS_CODE", "PREVIOUS_REQUEST", "URL_WAYBACK"])
    df.to_csv('WAYBACK.csv', sep=';', encoding='utf-8')
    
    #Create DataBase for each one
    df_merge_page_file.to_csv('Final_Page.csv', sep=';', encoding='utf-8')
    df_merge_image_file.to_csv('Final_Image.csv', sep=';', encoding='utf-8')
    df_merge_apache_file.to_csv('Final_Apache.csv', sep=';', encoding='utf-8')
    df_merge_arquivo_webapp_file.to_csv('Final_Arquivo_Webapp.csv', sep=';', encoding='utf-8')
    
    #Left Merge Apache with Page Search Api log
    df_final_merge_apache_page = pd.merge(df_merge_apache_file[['IP_ADDRESS', 'REQUEST', 'USER_AGENT', 'TRACKINGID', 'TIMESTAMP', 'YEAR', 'MONTH', 'DAY', 'HOUR', 'MINUTE', 'TYPE_SEARCH', 'QUERY', 'PAGE', 'MAXITEMS']], df_merge_page_file[['TRACKINGID', "PAGE_SEARCH_RESPONSE(ms)",  "PAGE_SEARCH_PARAMETERS",]], how = 'left', on = ['TRACKINGID'])
    df_final_merge_apache_page.to_csv('Final_Apache_Page.csv', sep=';', encoding='utf-8')

    #Left Merge df_final_merge_apache_page with Image Search Api log
    df_final_merge_apache_page_image = pd.merge(df_final_merge_apache_page, df_merge_image_file[['TRACKINGID', "IMAGE_SEARCH_RESPONSE(ms)", "IMAGE_SEARCH_PARAMETERS", "IMAGE_SEARCH_RESULTS",]], how = 'left', on = ['TRACKINGID'])
    df_final_merge_apache_page_image.to_csv('Final_Apache_Image_Page.csv', sep=';', encoding='utf-8')

    #Left Merge df_final_merge_apache_page_image with WebApp log
    df_final = pd.merge(df_final_merge_apache_page_image, df_merge_arquivo_webapp_file[['TRACKINGID', 'SESSION_ID', 'POSITION']], how = 'left', on = ['TRACKINGID'])
    df_final.to_csv('Final_Apache_Image_Page_Arquivo_Webapp.csv', sep=';', encoding='utf-8')

    """
    #Engine to connect to database mysql
    engine = connect_db()

    df_merge_apache_file.to_sql(name='Table_all', con=engine, if_exists="replace", index=False)

    #sql.write_frame(df_merge_page_file, con=, name='table_name_for_df', if_exists='replace', flavor='mysql')
    #df_merge_page_file.to_sql("table_name", mycursor, if_exists="replace", index=False)


    #def connect_db():
        #USE teste_python;
        #SHOW TABLES;
        #engine = create_engine('mysql+mysqlconnector://root@localhost/teste_python', echo=False)
        #return engine

    """

if __name__ == '__main__':
    

    mypath = "./Logs"
    
    #UnTar Files
    for subdir, dirs, files in os.walk(mypath):
        if files:           
            ## Progress Bar of the number of log files processed
            with click.progressbar(length=len(files), show_pos=True) as progress_bar_total:
                for file in files:
                    progress_bar_total.update(1)
                    file_name = os.path.join(subdir, file)

                    # Untar the files
                    os.system("tar xvzf " +  file_name)

    #Process Files
    mergeFiles()

# Problems and Future Work:
#    1. Not all columns are being passed to csv. 
#    2. This was the decision made, for this first analysis. For instance, the collumn SPELLCHECKED
#    3. Connect to a database mysql