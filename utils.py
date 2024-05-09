import requests
import os
from datetime import datetime, timedelta


# Get the environment variables
from dotenv import load_dotenv
load_dotenv()

gong_base_url = os.getenv("GONG_BASE_URL")
gong_api_key = os.getenv("GONG_API_KEY")
gong_secret = os.getenv("GONG_SECRET")


# Function to test the connection to Gong
def test_connection():
    url = gong_base_url + "/v2/users"
    r = requests.get(url, auth=(gong_api_key,gong_secret))
    return r.json()

# Function to show the most recent calls
def get_recent_calls():
    url = gong_base_url + "/v2/calls"
    # start date should be 3 days ago, end date should be today
    now = datetime.now()
    days_ago = now - timedelta(days=3)
    # Format date and time according to the specified pattern
    from_date = days_ago.strftime("%Y-%m-%dT%H:%M:%S")
    to_date = now.strftime("%Y-%m-%dT%H:%M:%S")

    # generate the query string for the API: fromDateTime=2022-07-01T02:00:00-05:00&toDateTime=2022-07-31T02:00:00-05:00
    query_string = f"?fromDateTime={from_date}Z&toDateTime={to_date}Z"

    r = requests.get(url + query_string, auth=(gong_api_key,gong_secret))
    
    # we only want the calls
    calls = r.json()['calls']
    return calls

# Function to get the call details
def get_call_transcript(call_id):
    url = gong_base_url + f"/v2/calls/transcript"
    body = {
        "filter": {
            "callIds": [call_id]
            }
        }
    r = requests.post(url, json=body, auth=(gong_api_key,gong_secret))
    # only get the callTranscripts
    call = r.json()['callTranscripts']
    return call

# Function to get the Speaker details, returns a dictionary with the speaker details
def get_speaker_details(call_id):
    url = gong_base_url + f"/v2/calls/extensive"
    body = {
            "filter": {
                "callIds": [call_id]
            },
            "contentSelector": {
                "exposedFields": {
                    "parties": True
                }
            }
        }
    r = requests.post(url, json=body, auth=(gong_api_key,gong_secret))
    print(r.json()['calls'][0]['parties'])
    speakers = r.json()['calls'][0]['parties']
    return speakers

# Function to return the speaker name based on the speaker id
def get_speaker_name(speaker_id, speakers):
    for speaker in speakers:
        if speaker['speakerId'] == speaker_id:
            return speaker['name']
    return "Unknown Speaker"