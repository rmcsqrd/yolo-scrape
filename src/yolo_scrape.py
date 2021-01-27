# imports
from psaw import PushshiftAPI
import praw
import logging
import time
from datetime import datetime as dt
import os
import pandas as pd
import configparser

class WSB_Scraper:
    def __init__(self, credentials, time_max, time_min, save_path):

        # setup API stuff
        client_id, client_secret, user_agent = credentials
        self.r_api = praw.Reddit(client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent)
        self.ps_api = PushshiftAPI(self.r_api)

        # setup time stuff
        self.time_max = time_max  # front date (more recent)
        self.time_min = time_min  # how far back to go (in past)
        self.time_curr = time_max # current timestamp of most recent call

        # setup save config stuff
        self.save_path = save_path
        if os.path.exists(self.save_path):
            new_path = os.path.splitext(save_path)[0]+"old.csv"
            os.rename(save_path, new_path)

    def API_Call(self):
        # get ids within date range from Pushshift API, we do this first because we can sort by date
        results = list(self.ps_api.search_submissions(before=self.time_curr,
                                                      subreddit='wallstreetbets',
                                                      limit=10))

        # next, we take the ids we parsed and make a reddit api call so we have updated info on scores, etc
        # this is because Pushshift gets posts at time of posting but doesn't track them afterwards (I think?)
        
        self.time_curr = int(results[-1].created_utc)  # update timestamp with oldest call for next time
        result_dict = {
                       'id':[],
                       'created_utc':[],
                       'score':[],
                       'upvoteratio':[],
                       'author':[],
                       'title':[],
                       'selftext':[],
                      }
        for result in results:
            print("calling {}".format(result.id))
            logging.info("calling {}".format(result.id))
    
            # make submission call from reddit
            submission = self.r_api.submission(id=result.id)

            # unpack information into result_dict
            result_dict['id'].append(submission.id)
            result_dict['created_utc'].append(result.created_utc)  # pushshift has this info, not praw
            result_dict['score'].append(submission.score)
            result_dict['upvoteratio'].append(submission.upvote_ratio)
            result_dict['author'].append(submission.author)
            result_dict['title'].append(submission.title)
            result_dict['selftext'].append(submission.selftext)
                
        result_df = pd.DataFrame(data=result_dict)
        print("Saving dataframe...\n")
        logging.info("Saving dataframe...\n")
        self.SaveDF(result_df)
        self.CheckDone()

    def SaveDF(self, df):
        if os.path.exists(self.save_path):
            df.to_csv(save_path, mode='a', header=False, index=False)
        else:
            df.to_csv(save_path, index=False)

    def CheckDone(self):
        # little recursive helper function to check if done
        if self.time_curr < self.time_min:
            print("Done parsing")
            logging.info("Done parsing")
        else:
            logging.info("Current Time Stamp = {}, making next call".format(self.time_curr))
            print("Current Time Stamp = {}, making next call".format(self.time_curr))
            time.sleep(1)
            self.API_Call()

def GetTimeBounds():
    config = configparser.ConfigParser()
    config.read(os.getcwd()+"/config/config.ini")

    time_max = config["TIME_PARAMS"]["time_max"]
    time_min = config["TIME_PARAMS"]["time_min"]
    return int(time_max), int(time_min)

def GetCredentials():
    # get reddit scraping credentials from config/config.ini
    # modify/rename dummy_config.ini appropriately 
    config = configparser.ConfigParser()
    config.read(os.getcwd()+"/config/config.ini")

    client_id = config["CREDENTIAL_PARAMS"]["client_id"]
    client_secret = config["CREDENTIAL_PARAMS"]["client_secret"]
    user_agent = config["CREDENTIAL_PARAMS"]["user_agent"]

    credentials = [client_id, client_secret, user_agent]
    return credentials

if __name__ == "__main__":
    
    credentials = GetCredentials()
    time_max, time_min = GetTimeBounds()
    save_path = os.getcwd()+"/out/WSB_POSTS_MAX{}_MIN{}.csv".format(time_max, time_min)
    log_path = os.getcwd()+"/out/WSB_POSTS_MAX{}_MIN{}.log".format(time_max, time_min)
    logging.basicConfig(filename=log_path,  level=logging.DEBUG)

    scraper = WSB_Scraper(credentials, time_max, time_min, save_path)
    scraper.API_Call()


