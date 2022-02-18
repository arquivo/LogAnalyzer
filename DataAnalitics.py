import pandas as pd
from user_agents import parse
import re
import click
import ipinfo
import numpy
import matplotlib.pyplot as plt
import collections
import numpy as np

#import pdb;pdb.set_trace()

# Access to the ipinfo database
access_token = 'ACESS_TOKEN'
handler = ipinfo.getHandler(access_token, cache_options={'ttl':30, 'maxsize': 4096})

# Get the user agent acronyms from the file
with open("./utils/UserAgents/userAgentBots.txt") as f:
    content = f.readlines()
# Remove whitespace characters like `\n` at the end of each line
list_bot_agents = [x.strip().lower() for x in content]
regexBot_userAgent = r'|'.join(list_bot_agents)
regexp_userAgent = re.compile(regexBot_userAgent)

# Get the hostnames from the file
with open("./utils/Hostnames/HostnameBotsClouds.txt") as f:
    content = f.readlines()
# Remove whitespace characters like `\n` at the end of each line
list_hostname = [x.strip().lower() for x in content]
regexBot_hostname = r'|'.join(list_hostname)
regexp_hostname = re.compile(regexBot_hostname)

# List with the cloud providers that we consider as bots.
list_ISP_Bot = ["private", "microsoft", "facebook", "google", "amazon", "fundacao"]

# List with the information about the IP, is an addition to the ipinfo cache.
dic_IP_Information = {}

# List of the requests already processed. Sometimes there are duplicate requests.
list_requests_queries = []

# Dictionary with the response time value ranges (Image and Page Search API)
dic_responseTime_page = {"0-25": 0,"25-50": 0,"50-100": 0,"100-200": 0,"200-400": 0,"400-800": 0,"800+": 0}
dic_responseTime_image = {"0-25": 0,"25-50": 0,"50-100": 0,"100-200": 0,"200-400": 0,"400-800": 0,"800+": 0}

def processHostname(hostname):
    """
    Check if the received hostname is a bot, based on our list
    """
    if regexp_hostname.search(hostname.lower()):
        return True
    return False

#FIXME need to be more used
def processISP(ISP):
    """
    Check if the received ISP is a bot, based on our list
    """
    for elem in list_ISP_Bot:
        if elem in ISP.lower():
            return True
    return False

def processAutomaticRequests(userAgent, ipAddress):
    """
    Check if the received user agent and IP is a bot, based on our list
    """
    if "10.0.23." not in ipAddress and "127.0.0.1" not in ipAddress and not pd.isnull(userAgent):
        if regexp_userAgent.search(userAgent.lower()):
            return True #Good Request
        else:
            return False #Bad/Bot Request
    else:
        return False #Bad/Bot Request 

def getGeographicalAttributes(df, i, dic_IP_Information):
    """
    Process the IP to generate other attributes using ipinfo
    """
    try:
        # Get details from ipinfo
        details = handler.getDetails(df.at[i, 'IP_ADDRESS'])

        df.at[i, 'ISP'] = details.org
        df.at[i, 'COUNTRY'] = details.country_name
        df.at[i, 'CITY'] = details.region
        df.at[i, 'PROVINCE'] = details.city
        df.at[i, 'TIMEZONE'] = details.timezone

        try:
            # Sometimes get the hostname gives unexpected errors
            df.at[i, 'HOSTNAME'] = details.hostname
            dic_IP_Information[df.at[i, 'IP_ADDRESS']] = [details.org, details.country_name, details.region, details.city, details.timezone, details.hostname]
            
            # Check if the keyword "bot" is in the hostname string
            if "bot" in df.at[i, 'HOSTNAME']:
                df.at[i, 'BOT'] = 1
        except:
            dic_IP_Information[df.at[i, 'IP_ADDRESS']] = [details.org, details.country_name, details.region, details.city, details.timezone, ""]
    
    except:
        #This happens when there is an error with the private/internal IPs
        if "172" in df.at[i, 'IP_ADDRESS']:
            df.at[i, 'ISP'] = "Private"
        else:
            df.at[i, 'NOTES'] = "Problems on IP from try?"

def dataAnalyzerQueryDataset():

    #Read file into DataFrame
    names_apache = ["IP_ADDRESS", "REQUEST", "USER_AGENT", "TRACKINGID", "TIMESTAMP", "YEAR", "MONTH", "DAY", "HOUR", "MINUTE", "TYPE_SEARCH", "QUERY", "PAGE", "MAXITEMS", "PAGE_SEARCH_RESPONSE(ms)", "PAGE_SEARCH_PARAMETERS", "IMAGE_SEARCH_RESPONSE(ms)", "IMAGE_SEARCH_PARAMETERS", "IMAGE_SEARCH_RESULTS", "SESSION_ID", "POSITION"]
    df = pd.read_csv("Final_Apache_Image_Page_Arquivo_Webapp.csv", sep=';')
    
    #Progress Bar based on the shap of the dataframe
    with click.progressbar(length=df.shape[0], show_pos=True) as progress_bar:
        
        #Init New Collumns
        
        #Geographic location
        df["COUNTRY"] = ""
        df["CITY"] = ""
        df["ISP"] = ""
        df["PROVINCE"] = ""
        df['TIMEZONE'] = "" 
        df['HOSTNAME'] = ""

        #Device
        df['TYPE_DEVICE'] = "Browser"
        df['BROWSER_FAMILY'] = ""
        df['BROWSER_VERSION'] = ""
        df['OS_FAMILY'] = ""
        df['OS_VERSION'] = ""
        df['DEVICE_FAMILY'] = ""
        df['DEVICE_BRAND'] = ""
        df['DEVICE_MODEL'] = ""
        
        #ABSOLUTE_POSITION
        df['ABSOLUTE_POSITION'] = ""

        #BOT
        df['BOT'] = 0

        #NOTES/PROBLEMS
        df['NOTES'] = ""

        #USER
        df['UNIQUE_USER'] = ""

        for i in df.index:
            progress_bar.update(1)

            # Search.jsp is not used by our front-end. So, there is a high probability that it is a bot or some error
            if not df.at[i, 'REQUEST'].startswith("GET /search.jsp") and not df.at[i, 'REQUEST'].startswith("GET /image.jsp") and not df.at[i, 'REQUEST'].startswith("GET /images.jsp"):
                
                #String with the request, IP address, and user agent. I already see the same ip with different user agent.
                string_request_ip = df.at[i, 'REQUEST'] + df.at[i, 'IP_ADDRESS'] + df.at[i, 'USER_AGENT']
                
                if string_request_ip in list_requests_queries:
                    df.at[i, 'BOT'] = 1
                else:
                    list_requests_queries.append(string_request_ip)
                    #Check if the IP Adress if null (can never happen)
                    if not pd.isnull(df.at[i, 'IP_ADDRESS']):
                        
                        #Check if the request is not from a Automatic source
                        if processAutomaticRequests(df.at[i, 'USER_AGENT'], df.at[i, 'IP_ADDRESS']):

                            #Setup the device with the user agent
                            user_agent = parse(df.at[i, 'USER_AGENT'])
                            
                            #Double Check
                            if user_agent.is_bot:
                                df.at[i, 'BOT'] = 1
                            else:
                                string_user = str(df_log.at[i, 'IP_ADDRESS']) + str(df_log.at[i, 'USER_AGENT'])
                                df_log.at[i, 'UNIQUE_USER'] = int(hashlib.sha1(string_user.encode("utf-8")).hexdigest(), 16) % (10 ** 8)

                                #0 = Browser (default), 1 = Mobile, 2 = Tablet
                                if user_agent.is_mobile:
                                    df.at[i, 'TYPE_DEVICE'] = "Mobile"
                                elif user_agent.is_tablet:
                                    df.at[i, 'TYPE_DEVICE'] = "Tablet"

                                # Accessing user agent's browser attributes
                                df.at[i, 'BROWSER_FAMILY'] =user_agent.browser.family
                                df.at[i, 'BROWSER_VERSION'] = user_agent.browser.version_string

                                # Accessing user agent's operating system properties
                                df.at[i, 'OS_FAMILY'] = user_agent.os.family
                                df.at[i, 'OS_VERSION'] = user_agent.os.version_string

                                # Accessing user agent's device properties
                                df.at[i, 'DEVICE_FAMILY'] = user_agent.device.family
                                df.at[i, 'DEVICE_BRAND'] = user_agent.device.brand
                                df.at[i, 'DEVICE_MODEL'] = user_agent.device.model

                                #Calculate the absolute position 
                                if not pd.isnull(df.at[i, 'POSITION']):
                                    if df.at[i, 'PAGE'] == 0:
                                        df.at[i, 'ABSOLUTE_POSITION'] = df.at[i, 'POSITION']
                                    else:
                                        df.at[i, 'ABSOLUTE_POSITION'] = df.at[i, 'MAXITEMS'] * df.at[i, 'PAGE'] + df.at[i, 'POSITION']

                                #Gett all the geographic information
                                if i == 0:
                                    getGeographicalAttributes(df, i, dic_IP_Information)
                                else:
                                    #Check if we already saw this information
                                    if df.at[i, 'IP_ADDRESS'] not in dic_IP_Information:                               
                                        getGeographicalAttributes(df, i, dic_IP_Information)
                                    else:
                                        df.at[i, 'ISP'] = dic_IP_Information[df.at[i, 'IP_ADDRESS']][0]
                                        df.at[i, 'COUNTRY'] = dic_IP_Information[df.at[i, 'IP_ADDRESS']][1]
                                        df.at[i, 'CITY'] = dic_IP_Information[df.at[i, 'IP_ADDRESS']][2]
                                        df.at[i, 'PROVINCE'] = dic_IP_Information[df.at[i, 'IP_ADDRESS']][3]
                                        df.at[i, 'TIMEZONE'] = dic_IP_Information[df.at[i, 'IP_ADDRESS']][4]
                                        df.at[i, 'HOSTNAME'] = dic_IP_Information[df.at[i, 'IP_ADDRESS']][5]
                        else:
                            df.at[i, 'BOT'] = 1
                    else:
                        df.at[i, 'NOTES'] = "No IP?"
            else:
                #We will not consider the request from search.jsp since we are not using anymore and do not have the new parameter tracking_id
                df.at[i, 'BOT'] = 1

    df = df[df['BOT']==0]
    df.to_csv('FINAL_GEO.csv', sep=';', encoding='utf-8')


def results():

    #Grid lines configuration
    gridLineColor='black'
    gridLinestyle=':'
    gridLineWidth=0.8
    gridLineAlpha=0.5
    
    #Bar config
    barPrimaryColor='green'
    barSecondaryColor='red'
    
    #Horizontal Bar Charts Config
    BarChartwidth=15
    horizontalBarChartHeight=10
    verticalBarChartHeight=6

    #Horizontal Bar Charts Config
    pieChartwidth=12
    pieChartHeight=6

    #Read file into DataFrame
    names_apache = ["IP_ADDRESS", "REQUEST", "USER_AGENT", "TRACKINGID", "TIMESTAMP", "YEAR", "MONTH", "DAY", "HOUR", "MINUTE", "TYPE_SEARCH", "QUERY", "PAGE", "MAXITEMS", "PAGE_SEARCH_RESPONSE(ms)", "PAGE_SEARCH_PARAMETERS", "IMAGE_SEARCH_RESPONSE(ms)", "IMAGE_SEARCH_PARAMETERS", "IMAGE_SEARCH_RESULTS", "SESSION_ID", "POSITION", "COUNTRY CITY", "ISP", "PROVINCE", "TIMEZONE", "HOSTNAME", "TYPE_DEVICE", "BROWSER_FAMILY", "BROWSER_VERSION OS_FAMILY", "OS_VERSION", "DEVICE_FAMILY", "DEVICE_BRAND", "DEVICE_MODEL", "ABSOLUTE_POSITION", "BOT", "NOTES"]
    df = pd.read_csv("FINAL_GEO.csv", sep=';')

    ####################################################################################################################
    ####################################################################################################################
    # An analysis will be performed using the matplotlib and pandas libraries. This analysis will be divided into:
    # (1) Type of device (between: Browser, Mobile, Tablet);
    # (2) Geographic Distribution;
    # (3) Type of Search;
    # (4) Postion;
    # (5) Top 10 Queries;
    # (6) Absolute Postion;
    # (7) Number of unique user per month;
    # (8) Number of queries per month;
    # (9) Distribution of the Response Time (APIs)
    ####################################################################################################################
    ####################################################################################################################

    # (1) Type of device (between: Browser, Mobile, Tablet)
    
    ## (1.1) Type of device (between: Browser, Mobile, Tablet) all platforms
    plt.figure(figsize=(pieChartwidth, pieChartHeight))
    plt.pie(df.TYPE_DEVICE.value_counts(), labels= df.TYPE_DEVICE.value_counts().index, autopct='%1.1f%%', startangle=90)
    plt.title('Type of Devices')
    plt.savefig('TypeOFDevice.png')

    ## (1.2) Type of device (between: Browser, Mobile, Tablet) image search
    plt.figure(figsize=(pieChartwidth, pieChartHeight))
    plt.pie(df[df['TYPE_SEARCH'] == 'imagesearch'].TYPE_DEVICE.value_counts(), labels= df[df['TYPE_SEARCH'] == 'imagesearch'].TYPE_DEVICE.value_counts().index, autopct='%1.1f%%', startangle=90)
    plt.title('Type of Devices (Image Search)')
    plt.savefig('TypeOFDevice_ImageSearch.png')

    ## (1.2) Type of device (between: Browser, Mobile, Tablet) page search
    plt.figure(figsize=(pieChartwidth, pieChartHeight))
    plt.pie(df[df['TYPE_SEARCH'] == 'textsearch'].TYPE_DEVICE.value_counts(), labels= df[df['TYPE_SEARCH'] == 'textsearch'].TYPE_DEVICE.value_counts().index, autopct='%1.1f%%', startangle=90)
    plt.title('Type of Devices (Page Search)')
    plt.savefig('TypeOFDevice_PageSearch.png')

    ## (1.3) Operating system mobile
    plt.figure(figsize=(pieChartwidth, pieChartHeight))
    plt.pie(df[df['TYPE_DEVICE'] == 'Mobile'].OS_FAMILY.value_counts(), labels= df[df['TYPE_DEVICE'] == 'Mobile'].OS_FAMILY.value_counts().index, autopct='%1.1f%%', startangle=90)
    plt.title('Operating System Mobile')
    plt.savefig('OS_Mobile.png')

    ## (1.4) Operating system browser
    plt.figure(figsize=(pieChartwidth, pieChartHeight))
    plt.pie(df[df['TYPE_DEVICE'] == 'Browser'].OS_FAMILY.value_counts().nlargest(3), labels= df[df['TYPE_DEVICE'] == 'Browser'].OS_FAMILY.value_counts().nlargest(3).index, autopct='%1.1f%%', startangle=90)
    plt.title('Operating System Browser')
    plt.savefig('OS_Browser.png')

    ## (1.5) Operating system browser
    plt.figure(figsize=(pieChartwidth, pieChartHeight))
    plt.pie(df[df['TYPE_DEVICE'] == 'Tablet'].OS_FAMILY.value_counts(), labels= df[df['TYPE_DEVICE'] == 'Tablet'].OS_FAMILY.value_counts().index, autopct='%1.1f%%', startangle=90)
    plt.title('Operating System Tablet')
    plt.savefig('OS_Tablet.png')

    # (2) Geographic Distribution

    ## (2.1) Geographic Distribution - Countries

    fig, ax = plt.subplots(figsize=(BarChartwidth, horizontalBarChartHeight))

    #Calculate the percentage of request per country
    total = df.COUNTRY.count()
    langs = df.COUNTRY.value_counts().nlargest(10).index
    langs_users_num = df.COUNTRY.value_counts().nlargest(10)
    percent = langs_users_num/total*100
    new_labels = [i+'  {:.2f}%'.format(j) for i, j in zip(langs, percent)]

    plt.barh(langs, langs_users_num[::-1], color='green')
    plt.yticks(range(len(langs)), new_labels[::-1])
    plt.tight_layout()

    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.axes.get_xaxis().set_visible(False)
    ax.tick_params(axis="y", left=False)
    ax.set_ylabel('Country %')
    ax.set_title(u'Percentage of records per country')
    plt.subplots_adjust(left=0.38)
    plt.autoscale(enable=True, axis='x')
    plt.grid(axis='x',color=gridLineColor, linestyle=gridLinestyle, linewidth=gridLineWidth, alpha=gridLineAlpha)
    fig.savefig('Country.png', bbox_inches='tight')


    ## (2.2) Geographic Distribution - ISP

    fig, ax = plt.subplots(figsize=(BarChartwidth, horizontalBarChartHeight))

    #Calculate the percentage of request per ISP
    total = df.ISP.count()
    langs = df.ISP.value_counts().nlargest(10).index
    langs_users_num = df.ISP.value_counts().nlargest(10)
    percent = langs_users_num/total*100
    new_labels = [i+'  {:.2f}%'.format(j) for i, j in zip(langs, percent)]

    plt.barh(langs, langs_users_num[::-1], color='green')
    plt.yticks(range(len(langs)), new_labels[::-1])
    plt.tight_layout()

    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.axes.get_xaxis().set_visible(False)
    ax.tick_params(axis="y", left=False)
    ax.set_ylabel('ISP %')
    ax.set_title(u'Percentage of records per isp')
    plt.subplots_adjust(left=0.38)
    plt.autoscale(enable=True, axis='x')
    plt.grid(axis='x',color=gridLineColor, linestyle=gridLinestyle, linewidth=gridLineWidth, alpha=gridLineAlpha)
    fig.savefig('ISP.png', bbox_inches='tight')    


    ## (2.3) Geographic Distribution - City

    fig, ax = plt.subplots(figsize=(BarChartwidth, horizontalBarChartHeight))

    #Calculate the percentage of request per city
    total = df.CITY.count()
    langs = df.CITY.value_counts().nlargest(10).index
    langs_users_num = df.CITY.value_counts().nlargest(10)
    percent = langs_users_num/total*100
    new_labels = [i+'  {:.2f}%'.format(j) for i, j in zip(langs, percent)]

    plt.barh(langs, langs_users_num[::-1], color='green')
    plt.yticks(range(len(langs)), new_labels[::-1])
    plt.tight_layout()

    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.axes.get_xaxis().set_visible(False)
    ax.tick_params(axis="y", left=False)
    ax.set_ylabel('City %')
    ax.set_title(u'Percentage of records per city')
    plt.subplots_adjust(left=0.38)
    plt.autoscale(enable=True, axis='x')
    plt.grid(axis='x',color=gridLineColor, linestyle=gridLinestyle, linewidth=gridLineWidth, alpha=gridLineAlpha)
    fig.savefig('CITY.png', bbox_inches='tight')
    
    ## (2.4) Geographic Distribution - Province

    fig, ax = plt.subplots(figsize=(BarChartwidth, horizontalBarChartHeight))

    #Calculate the percentage of request per province
    total = df.PROVINCE.count()
    langs = df.PROVINCE.value_counts().nlargest(10).index
    langs_users_num = df.PROVINCE.value_counts().nlargest(10)
    percent = langs_users_num/total*100
    new_labels = [i+'  {:.2f}%'.format(j) for i, j in zip(langs, percent)]

    plt.barh(langs, langs_users_num[::-1], color='green')
    plt.yticks(range(len(langs)), new_labels[::-1])
    plt.tight_layout()

    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.axes.get_xaxis().set_visible(False)
    ax.tick_params(axis="y", left=False)
    ax.set_ylabel('Province %')
    ax.set_title(u'Percentage of records per province')
    plt.subplots_adjust(left=0.38)
    plt.autoscale(enable=True, axis='x')
    plt.grid(axis='x',color=gridLineColor, linestyle=gridLinestyle, linewidth=gridLineWidth, alpha=gridLineAlpha)
    fig.savefig('PROVINCE.png', bbox_inches='tight')

    ## (2.5) Geographic Distribution - TIMEZONE
    fig, ax = plt.subplots(figsize=(BarChartwidth, horizontalBarChartHeight))

    #Calculate the percentage of request per timezone
    total = df.TIMEZONE.count()
    langs = df.TIMEZONE.value_counts().nlargest(10).index
    langs_users_num = df.TIMEZONE.value_counts().nlargest(10)
    percent = langs_users_num/total*100
    new_labels = [i+'  {:.2f}%'.format(j) for i, j in zip(langs, percent)]

    plt.barh(langs, langs_users_num[::-1], color='green')
    plt.yticks(range(len(langs)), new_labels[::-1])
    plt.tight_layout()

    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.axes.get_xaxis().set_visible(False)
    ax.tick_params(axis="y", left=False)
    ax.set_ylabel('Timezone %')
    ax.set_title(u'Percentage of records per timezone')
    plt.subplots_adjust(left=0.38)
    plt.autoscale(enable=True, axis='x')
    plt.grid(axis='x',color=gridLineColor, linestyle=gridLinestyle, linewidth=gridLineWidth, alpha=gridLineAlpha)
    fig.savefig('TIMEZONE.png', bbox_inches='tight')

    # (3) Type of Search
    
    fig, ax = plt.subplots(figsize=(10, 5))
    plt.pie(df.TYPE_SEARCH.value_counts(), labels= df.TYPE_SEARCH.value_counts().index, autopct='%1.1f%%', startangle=90)
    plt.title('Type of Search')
    plt.savefig('TYPE_SEARCH.png')

    # (4) Position

    ## (4.1) Position - total
    fig, ax = plt.subplots(figsize=(BarChartwidth, horizontalBarChartHeight))
    plt.figure(figsize=(12, 6))
    plt.bar(df.POSITION.value_counts().nlargest(10).index, df.POSITION.value_counts().nlargest(10), color='g')
    plt.xlabel('Click Positions')
    plt.ylabel('Number Occurrences')
    plt.savefig('Position.png')

    ## (4.2) Position - imagesearch
    fig, ax = plt.subplots(figsize=(BarChartwidth, horizontalBarChartHeight))
    plt.figure(figsize=(12, 6))
    plt.bar(df[df['TYPE_SEARCH'] == 'imagesearch'].POSITION.value_counts().nlargest(10).index, df[df['TYPE_SEARCH'] == 'imagesearch'].POSITION.value_counts().nlargest(10), color='g')
    plt.xlabel('Click Positions Image Search')
    plt.ylabel('Number Occurrences')
    plt.savefig('Position_imagesearch.png')

    ## (4.3) Position - textsearch
    fig, ax = plt.subplots(figsize=(BarChartwidth, horizontalBarChartHeight))
    plt.figure(figsize=(12, 6))
    plt.bar(df[df['TYPE_SEARCH'] == 'textsearch'].POSITION.value_counts().nlargest(10).index, df[df['TYPE_SEARCH'] == 'textsearch'].POSITION.value_counts().nlargest(10), color='g')
    plt.xlabel('Click Positions Image Search')
    plt.ylabel('Number Occurrences')
    plt.savefig('Position_textsearch.png')

    # (5) Top 10 Queries

    ## (5.1) Top 10 Queries - total

    fig, ax = plt.subplots(figsize=(BarChartwidth, horizontalBarChartHeight))
    y_pos = numpy.arange(len(df.QUERY.value_counts().nlargest(10).index))
    p1=ax.barh(y_pos, df.QUERY.value_counts().nlargest(10), align='center',color=barPrimaryColor)
    ax.set_yticks(y_pos)

    ax.set_yticklabels(df.QUERY.value_counts().nlargest(10).index)
    ax.invert_yaxis()  # labels read top-to-bottom
    ax.set_xlabel('Total')
    ax.set_ylabel('Queries')
    ax.set_title(u'Most popular queries - Total')
    
    fig.tight_layout()#Will not cut off the Y-axis subtitles
    plt.subplots_adjust(left=0.38)
    plt.autoscale(enable=True, axis='x')
    plt.grid(axis='x',color=gridLineColor, linestyle=gridLinestyle, linewidth=gridLineWidth, alpha=gridLineAlpha)
    fig.savefig('TopQueriesALL.png', bbox_inches='tight')
    
    ## (5.2) Top 10 Queries - textsearch
    fig, ax = plt.subplots(figsize=(BarChartwidth, horizontalBarChartHeight))
    y_pos = numpy.arange(len(df[df['TYPE_SEARCH'] == 'textsearch'].QUERY.value_counts().nlargest(10).index))
    p1=ax.barh(y_pos, df[df['TYPE_SEARCH'] == 'textsearch'].QUERY.value_counts().nlargest(10), align='center',color=barPrimaryColor)
    ax.set_yticks(y_pos)

    ax.set_yticklabels(df[df['TYPE_SEARCH'] == 'textsearch'].QUERY.value_counts().nlargest(10).index)
    ax.invert_yaxis()  # labels read top-to-bottom
    ax.set_xlabel('Total')
    ax.set_ylabel('Queries')
    ax.set_title(u'Most popular queries - Page Search')
    
    fig.tight_layout()#Will not cut off the Y-axis subtitles
    plt.subplots_adjust(left=0.38)
    plt.autoscale(enable=True, axis='x')
    plt.grid(axis='x',color=gridLineColor, linestyle=gridLinestyle, linewidth=gridLineWidth, alpha=gridLineAlpha)
    fig.savefig('TopQueriesPageSearch.png', bbox_inches='tight')

    ## (5.2) Top 10 Queries - imagesearch

    fig, ax = plt.subplots(figsize=(BarChartwidth, horizontalBarChartHeight))
    y_pos = numpy.arange(len(df[df['TYPE_SEARCH'] == 'imagesearch'].QUERY.value_counts().nlargest(10).index))
    p1=ax.barh(y_pos, df[df['TYPE_SEARCH'] == 'imagesearch'].QUERY.value_counts().nlargest(10), align='center',color=barPrimaryColor)
    ax.set_yticks(y_pos)

    ax.set_yticklabels(df[df['TYPE_SEARCH'] == 'imagesearch'].QUERY.value_counts().nlargest(10).index)
    ax.invert_yaxis()  # labels read top-to-bottom
    ax.set_xlabel('Total')
    ax.set_ylabel('Queries')
    ax.set_title(u'Most popular queries - Image Search')
    
    fig.tight_layout()#Will not cut off the Y-axis subtitles
    plt.subplots_adjust(left=0.38)
    plt.autoscale(enable=True, axis='x')
    plt.grid(axis='x',color=gridLineColor, linestyle=gridLinestyle, linewidth=gridLineWidth, alpha=gridLineAlpha)
    fig.savefig('TopQueriesImageSearch.png', bbox_inches='tight')

    # (6) Absolute position

    ## (6.1) Absolute position - total
    top25 = df.ABSOLUTE_POSITION.value_counts().sort_index()[:26]
    top25[26] = df.ABSOLUTE_POSITION.value_counts().sort_index()[25:].count()
    
    fig, ax = plt.subplots(figsize=(BarChartwidth, horizontalBarChartHeight))
    ax.set_title(u'Click Position Distribution - Total')
    plt.bar(top25.index, top25, color='g')
    plt.xlabel('Click Absolute Positions - Total')
    plt.ylabel('Number Occurrences')
    plt.savefig('Position_ABSOLUTE_POSITION.png')

    ## (6.1) Absolute position - imagesearch
    top25 = df[df['TYPE_SEARCH'] == 'imagesearch'].ABSOLUTE_POSITION.value_counts().sort_index()[:26]
    top25[26] = df[df['TYPE_SEARCH'] == 'imagesearch'].ABSOLUTE_POSITION.value_counts().sort_index()[25:].count()
    
    fig, ax = plt.subplots(figsize=(BarChartwidth, horizontalBarChartHeight))
    ax.set_title(u'Click Position Distribution - Image Search')
    plt.bar(top25.index, top25, color='g')
    plt.xlabel('Click Absolute Positions - Image Search')
    plt.ylabel('Number Occurrences')
    plt.savefig('Position_ABSOLUTE_POSITION_imagesearch.png')

    ## (6.1) Absolute position - textsearch
    top25 = df[df['TYPE_SEARCH'] == 'textsearch'].ABSOLUTE_POSITION.value_counts().sort_index()[:26]
    top25[26] = df[df['TYPE_SEARCH'] == 'textsearch'].ABSOLUTE_POSITION.value_counts().sort_index()[25:].count()

    fig, ax = plt.subplots(figsize=(BarChartwidth, horizontalBarChartHeight))
    ax.set_title(u'Click Position Distribution - Page Search')
    plt.bar(top25.index, top25, color='g')
    plt.xlabel('Click Absolute Positions - Page Search')
    plt.ylabel('Number Occurrences')
    plt.savefig('Position_ABSOLUTE_POSITION_textsearch.png')

    # (7) Number of unique user per month

    fig, ax = plt.subplots(figsize=(BarChartwidth, verticalBarChartHeight))
    p1=ax.bar(["June", "July", "August"], df.groupby('MONTH')['IP_ADDRESS'].nunique().nlargest(3),color=barPrimaryColor)
    ax.set_xlabel('Month')
    ax.set_ylabel('Number unique user')
    ax.set_title(u'Number of unique user per month - Total')
    
    fig.tight_layout()
    plt.subplots_adjust(left=0.38)
    plt.autoscale(enable=True, axis='x')
    fig.savefig('UsersMonth.png', bbox_inches='tight')

    # (8) Number of queries per month

    ## (8.1) Number of queries per month - total
    fig, ax = plt.subplots(figsize=(BarChartwidth, verticalBarChartHeight))
    p1=ax.bar(["June", "July", "August"], df.groupby('MONTH')['QUERY'].nunique().nlargest(3),color=barPrimaryColor)
    ax.set_xlabel('Month')
    ax.set_ylabel('Number unique user')
    ax.set_title(u'Number of queries per month - Total')
    
    fig.tight_layout()
    plt.subplots_adjust(left=0.38)
    plt.autoscale(enable=True, axis='x')
    fig.savefig('QueriesMonth.png', bbox_inches='tight')

    ## (8.2) Number of queries per month - textsearch
    fig, ax = plt.subplots(figsize=(BarChartwidth, verticalBarChartHeight))
    p1=ax.bar(["June", "July", "August"], df[df['TYPE_SEARCH'] == 'textsearch'].groupby('MONTH')['QUERY'].nunique().nlargest(3),color=barPrimaryColor)
    ax.set_xlabel('Month')
    ax.set_ylabel('Number unique user')
    ax.set_title(u'Number of queries per month - Page Search')
    
    fig.tight_layout()
    plt.subplots_adjust(left=0.38)
    plt.autoscale(enable=True, axis='x')
    fig.savefig('QueriesMonthPageSearch.png', bbox_inches='tight')

    ## (8.3) Number of queries per month - imagesearch
    fig, ax = plt.subplots(figsize=(BarChartwidth, verticalBarChartHeight))
    p1=ax.bar(["June", "July", "August"], df[df['TYPE_SEARCH'] == 'imagesearch'].groupby('MONTH')['QUERY'].nunique().nlargest(3),color=barPrimaryColor)
    ax.set_xlabel('Month')
    ax.set_ylabel('Number unique user')
    ax.set_title(u'Number of queries per month - Image Search')
    
    fig.tight_layout()
    plt.subplots_adjust(left=0.38)
    plt.autoscale(enable=True, axis='x')
    fig.savefig('QueriesMonthImageSearch.png', bbox_inches='tight')

    #Process again the dataframe to process the column "PAGE_SEARCH_RESPONSE(ms)" (we can include this step inside the function "dataAnalyzerQueryDataset")
    with click.progressbar(length=df.shape[0], show_pos=True) as progress_bar_data:
        for i in df.index:
            progress_bar_data.update(1)
            
            #Check if ISP is not NULL, and check if ISP is not from a BOT (i.e., cloud provider)
            if not pd.isnull(df.at[i, 'ISP']) and not processISP(df.at[i, 'ISP']):
                
                #Add new values from Page Search Response API into dic_responseTime_page
                if not pd.isnull(df.at[i, 'PAGE_SEARCH_RESPONSE(ms)']):
                    if int(df.at[i, 'PAGE_SEARCH_RESPONSE(ms)']) < 25:
                        dic_responseTime_page["0-25"] +=1
                    elif  int(df.at[i, 'PAGE_SEARCH_RESPONSE(ms)']) > 25 and int(df.at[i, 'PAGE_SEARCH_RESPONSE(ms)']) < 50:
                        dic_responseTime_page["25-50"] +=1
                    elif  int(df.at[i, 'PAGE_SEARCH_RESPONSE(ms)']) > 50 and int(df.at[i, 'PAGE_SEARCH_RESPONSE(ms)']) < 100:
                        dic_responseTime_page["50-100"] +=1
                    elif  int(df.at[i, 'PAGE_SEARCH_RESPONSE(ms)']) > 100 and int(df.at[i, 'PAGE_SEARCH_RESPONSE(ms)']) < 200:
                        dic_responseTime_page["100-200"] +=1
                    elif  int(df.at[i, 'PAGE_SEARCH_RESPONSE(ms)']) > 200 and int(df.at[i, 'PAGE_SEARCH_RESPONSE(ms)']) < 400:
                        dic_responseTime_page["200-400"] +=1
                    elif  int(df.at[i, 'PAGE_SEARCH_RESPONSE(ms)']) > 400 and int(df.at[i, 'PAGE_SEARCH_RESPONSE(ms)']) < 800:
                        dic_responseTime_page["400-800"] +=1
                    elif  int(df.at[i, 'PAGE_SEARCH_RESPONSE(ms)']) > 800:
                        dic_responseTime_page["800+"] +=1
                
                #Add new values from Image Search Response API into dic_responseTime_image
                if not pd.isnull(df.at[i, 'IMAGE_SEARCH_RESPONSE(ms)']):
                    if int(df.at[i, 'IMAGE_SEARCH_RESPONSE(ms)']) < 25:
                        dic_responseTime_image["0-25"] +=1
                    elif  int(df.at[i, 'IMAGE_SEARCH_RESPONSE(ms)']) > 25 and int(df.at[i, 'IMAGE_SEARCH_RESPONSE(ms)']) < 50:
                        dic_responseTime_image["25-50"] +=1
                    elif  int(df.at[i, 'IMAGE_SEARCH_RESPONSE(ms)']) > 50 and int(df.at[i, 'IMAGE_SEARCH_RESPONSE(ms)']) < 100:
                        dic_responseTime_image["50-100"] +=1
                    elif  int(df.at[i, 'IMAGE_SEARCH_RESPONSE(ms)']) > 100 and int(df.at[i, 'IMAGE_SEARCH_RESPONSE(ms)']) < 200:
                        dic_responseTime_image["100-200"] +=1
                    elif  int(df.at[i, 'IMAGE_SEARCH_RESPONSE(ms)']) > 200 and int(df.at[i, 'IMAGE_SEARCH_RESPONSE(ms)']) < 400:
                        dic_responseTime_image["200-400"] +=1
                    elif  int(df.at[i, 'IMAGE_SEARCH_RESPONSE(ms)']) > 400 and int(df.at[i, 'IMAGE_SEARCH_RESPONSE(ms)']) < 800:
                        dic_responseTime_image["400-800"] +=1
                    elif  int(df.at[i, 'IMAGE_SEARCH_RESPONSE(ms)']) > 800:
                        dic_responseTime_image["800+"] +=1

    # (9) Distribution of the Response Time (APIs)

    ## (9.1) Distribution of the Response Time (Image Search API)
    plt.figure(figsize=(12, 6))
    plt.bar(list(dic_responseTime_image.keys()), dic_responseTime_image.values(), color='g')
    plt.xlabel('Response Time Search (ms)')
    plt.ylabel('Number Occurrences')
    plt.title(u'Response Time API - Image Search')
    plt.savefig('Response_Time_Image_HIST.png')
    
    ## (9.2) Distribution of the Response Time (Page Search API)
    plt.figure(figsize=(12, 6))
    plt.bar(list(dic_responseTime_page.keys()), dic_responseTime_page.values(), color='g')
    plt.xlabel('Response Time Page Search (ms)')
    plt.ylabel('Number Occurrences')
    plt.title(u'Response Time API - Page Search')
    plt.savefig('Response_Time_HIST.png')

if __name__ == '__main__':
    
    #Process the dataset and add new columns
    dataAnalyzerQueryDataset()

    #Process the dataset and generate the graphs
    results()