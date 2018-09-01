# -*- coding: utf-8 -*-
"""
Created on Wed Jun 27 17:21:04 2018

@author: Christophe Foyer
"""

from selenium.webdriver.firefox.options import Options
from selenium import webdriver

import pandas as pd
import numpy as np

from lxml import etree as et

webdriver_options = Options()
webdriver_options.add_argument("--headless")

profile = webdriver.FirefoxProfile()
profile.native_events_enabled = False

times_twenty_five = 20

### Times Higher Education
dataframes = []
for page_num in range(0,times_twenty_five):
    print(page_num)
    
    driver = webdriver.Firefox(profile, firefox_options=webdriver_options)
    
    driver.get('https://www.timeshighereducation.com/world-university-rankings/2018/world-ranking#!/page/'+str(page_num)+'/length/25/sort_by/rank/sort_order/asc/cols/stats')
               
    elem = driver.find_element_by_id('datatable-1_wrapper')
    
    html = elem.get_attribute('innerHTML')
    
    driver.close()
    
    #doesn't do a good job of chopping off the rest
    #but I know what we're looking for so manual chop time
    html = html.split('</table>')[0]+'</table>'
    
    tree=et.fromstring(html)
    
    for div in tree.xpath("//div[@class=\'location\']"):
        div.getparent().remove(div)
    
    html = et.tostring(tree)
    
    dataframe = pd.read_html(html)
    
    dataframes = dataframes + dataframe
    
rankings_times = pd.concat(dataframes)

def cleanup_times(val):
    val = val.replace("=", "")
    val = val.split("-")[0]
    return val

def cleanup_times2(val):
    val = val.replace("Explore", "")
    return val

rankings_times["Rank"] = rankings_times["Rank"].apply(cleanup_times)
rankings_times["Name"] = rankings_times["Name"].apply(cleanup_times2)
rankings_times = rankings_times.reset_index(drop=True)

### QS
driver = webdriver.Firefox(profile, firefox_options=webdriver_options)
driver.get('https://www.topuniversities.com/university-rankings/world-university-rankings/2019')
dataframes = []
for page_num in range(0,times_twenty_five):
    print(page_num)
    
    elem = driver.find_element_by_id('qs-rankings_wrapper')
    
    html = elem.get_attribute('innerHTML')
    
    dataframe = pd.read_html(html)
    
    dataframes = dataframes + dataframe
    
    driver.execute_script("document.getElementById('popup-text').style.display = 'none';")
    driver.execute_script("document.getElementById('sliding-popup').style.display = 'none';")
    next_button = driver.find_elements_by_xpath("//a[@id='qs-rankings_next']")[0]
    next_button.click()

driver.close()

rankings_qs = pd.concat(dataframes)

rankings_qs = rankings_qs.rename(columns={"# RANK": 'Rank', 'UNIVERSITY':'Name'})
rankings_qs.columns = [col[0] for col in rankings_qs.columns]
rankings_qs = rankings_qs.drop(["COMPARE", "STARSSTARS STARS QS Stars is distinct from rankings. So far, 150 universities in over 35 countries have been rated in up to 12 categories. Click the QS Stars for detailed results"], axis=1)

def rchop(thestring, ending):
  if thestring.endswith(ending):
    return thestring[:-len(ending)]
  return thestring

def cleanup_qs(val):
    val = rchop(val, 'More')
    return val

def cleanup_qs2(val):
    val = str(val)
    val = val.replace("=", "")
    val = int(val)
    return val
    
rankings_qs["Name"] = rankings_qs["Name"].apply(cleanup_qs)
rankings_qs["Rank"] = rankings_qs["Rank"].apply(cleanup_qs2)
rankings_qs = rankings_qs.reset_index(drop=True)

qs_stripped = rankings_qs[['Rank', 'Name']].rename(columns={'Rank':'Rank_QS'})
times_stripped = rankings_times[['Rank', 'Name']].rename(columns={'Rank':'Rank_Times'})

times_stripped['Name_old'] = times_stripped['Name']
times_stripped['diff'] = np.nan

def dropcommon(val):
    val = val.replace("The", "")
    val = val.replace("the", "")
    val = val.replace("of", "")
    val = val.replace("University", "")
    return val

#This attempts to sync the names

from fuzzywuzzy import fuzz
from fuzzywuzzy import process 

match_sensitivity = 85

import time
#import jellyfish
for index, row in times_stripped.iterrows():
    print(index)
    print(row['Name'])
#    diff = rankings_qs[["Name"]].copy()
#    diff['dist'] = diff["Name"].apply(lambda x: jellyfish.jaro_distance(dropcommon(row['Name']), dropcommon(x))/jellyfish.levenshtein_distance(dropcommon(row['Name']), dropcommon(x)))
#    times_stripped.loc[index, 'Name'] = diff['Name'].iloc[diff['dist'].idxmax()]
#    times_stripped.loc[index,'diff'] = diff['dist'].max()
    s = process.extractOne(row['Name'], rankings_qs["Name"].tolist(), scorer=fuzz.token_sort_ratio)
    if s[1] < match_sensitivity:
        try:
            s_alt = process.extractOne(row['Name'].split('(')[1].split(')')[0], rankings_qs["Name"].tolist(), scorer=fuzz.token_sort_ratio)
            if s_alt[1] < match_sensitivity:
                times_stripped.loc[index, 'Name'] = s_alt[0]
            else:
                times_stripped.loc[index, 'Name'] = 'nan'
        except:
            times_stripped.loc[index, 'Name'] = 'nan'
            print('no match ' + str(s[1]))
            time.sleep(1)
    else:
        times_stripped.loc[index, 'Name'] = s[0]


ranks = pd.merge(qs_stripped, times_stripped, on='Name', how='outer')

import plotly.offline as offline
import plotly.graph_objs as go

layout= go.Layout(
    title= 'QS vs Times University Rankings',
    hovermode= 'closest',
    xaxis= dict(
        title= 'Ranks (QS)'
    ),
    yaxis=dict(
        title= 'Rank (Times)'
    ),
    showlegend= False
)

offline.plot({'data':[go.Scatter(x=ranks['Rank_QS'],
                         y=ranks['Rank_Times'],
                         text=ranks['Name'],
                         mode='markers')],
              'layout':layout})