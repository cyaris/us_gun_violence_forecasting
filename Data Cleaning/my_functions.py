import pandas as pd
import numpy as np
import glob
import re
from copy import deepcopy
import random
from proxy_requests import ProxyRequests

def get_incident_file_list():
    # format possible incident id directory into a list
    incident_file_list = [filename.split('incident/')[1] for filename in glob.glob('../gun_violence_archive_spider/www.gunviolencearchive.org/incident/*')]
    incident_file_list = list(set(np.int64(incident_file_list)))
    return incident_file_list

def get_incident_std_list():
    # format all possible_ids from std_out file into a list
    df = pd.read_csv('../Data Sources/std_out.csv', encoding='latin-1', engine='python', index_col='Unnamed: 0')
    df.columns = ['std_out']
    incident_std_list = list(df[(['gunviolencearchive.org/incident/' in s for s in df['std_out']])]['std_out'])
    incident_std_list = [i.split('/incident/')[1] for i in incident_std_list]
    incident_std_list = [i.split('\x90')[0] for i in incident_std_list]
    incident_std_list = [re.sub('[^0-9]','', i) for i in incident_std_list]
    incident_std_list = list(set(np.int64(incident_std_list)))
    return incident_std_list

def get_logged_incident_ids_list():
    # format all ids that have already been catalogued by pandas into a list
    df = pd.read_pickle('../Pickles/df1.pkl')
    logged_ids_list = sorted(list(df['incident_id'].unique()))
    return logged_ids_list

def get_id_status_queue(maximum_id):
    # instantiating get_incident_file_list and get_logged_incident_ids_list
    # for computation of new variables
    incident_file_list = get_incident_file_list()
    logged_ids_list = get_logged_incident_ids_list()
    # known_possible_ids is all ids that have been logged or recorded so far
    known_possible_ids = incident_file_list + logged_ids_list
    known_possible_ids = list(set(known_possible_ids))
    # check for what's already been added to the text file previously
    # if it hasn't been added it'll be added to a new list queue
    status_code_df = get_status_code_df()
    recorded_status_codes = list(status_code_df['id'].unique())
    # range from lowest actual id to highest actual id
    # lets check for ids that may have been missed when scraping ids
    id_status_queue = np.flip(np.arange(478855, maximum_id+1))
    id_status_queue = deepcopy(list(set(id_status_queue) - set(known_possible_ids)))
    id_status_queue = deepcopy(list(set(id_status_queue) - set(recorded_status_codes)))
    random.shuffle(id_status_queue)
    # id_status_queue = sorted(id_status_queue)[::-1]
    print('id_status_queue: ' + str(len(id_status_queue)) + '\n')
    return id_status_queue

def get_status_code_df():
    # function outputs a dataframe of all manually requested status codes
    # that have been confirmed as 200 or 404
    status_code_df = pd.read_csv('../Data Sources/brute_force_id_status_codes_2.txt')
    status_code_df.columns=['id', 'status_code']
    status_code_df['id'] = status_code_df['id'].astype(int)
    status_code_df['status_code'] = status_code_df['status_code'].astype(int)
    status_code_df = deepcopy(status_code_df[(status_code_df['status_code']!=403) & (status_code_df['status_code']!=522) & (status_code_df['status_code']!=0)])
    return status_code_df

def get_id_file_add_queue(list_input_to_check):
    # function takes a list input to catalogue in the incident directory without duplicates
    # when requests are made later, they will only be for non-catalogued IDs
    # removing any potential id that is already in the incident folder
    incident_file_list = get_incident_file_list()
    id_file_add_queue = deepcopy(list(set(list_input_to_check) - set(incident_file_list)))
    # print number of files to be added
    print('id_file_add_queue: ' + str(len(id_file_add_queue)) + '\n')
    # for loop to create the files in the incident directory
    for item in id_file_add_queue:
        open("../gun_violence_archive_spider/www.gunviolencearchive.org/incident/{}".format(item), "w+")
    # command to create list of files from id_add_list.txt
    # head to the incident directory and run the following command:\ncat id_add_list.txt | xargs touch
    # id_add_list.txt file has been deleted but can be recreated
    
def get_popular_header():
    # function to scrape whatismybrowser.com and return a popular header at random
    # popular_headers_df = pd.read_html('https://developers.whatismybrowser.com/useragents/explore/hardware_type_specific/computer/?order_by=times_seen')[0]
    popular_headers_df = pd.read_pickle('../Pickles/popular_headers_df.pkl')
    header_dic = {}
    header_dic["User-Agent"] = random.choice(list(popular_headers_df['User agent']))
    return header_dic

def request_with_random_header(request_url):
    # function takes in a url as an input and assigns a random proxy and a random header
    # function returns status_code as 0 indice
    # function returns get_raw as 1 indice
    request = ProxyRequests(request_url)
    request.set_headers(get_popular_header()) 
    request.get_with_headers() 
    return request