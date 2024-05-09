import streamlit as st
from utils import test_connection, get_recent_calls, get_call_transcript, get_speaker_details, get_speaker_name

st.title('Gong App')

# Add a sidebar that shows the most recent Gong calls
# Check that the Gong API is working
if test_connection():
    pass
else:
    st.sidebar.warning('Connection to Gong failed, please update your credentials')

# Display the recent calls
st.sidebar.title('Recent calls:')
# Add a button to refresh the recent calls
if st.sidebar.button('Refresh Recent Calls'):
    recent_calls = get_recent_calls()
    st.session_state.recent_calls = recent_calls

# get recent calls and store them in the session state
if 'recent_calls' not in st.session_state:
    recent_calls = get_recent_calls()
    st.session_state.recent_calls = recent_calls

# Display the information about the recent calls
for call in st.session_state.recent_calls:
    # create an information box with the id, the url, the title and the date
    call_id = call['id']
    call_url = call['url']
    call_title = call['title']
    call_date = call['started']
    st.sidebar.info(f"id: **{call_id}**: [{call_title}]({call_url}) - Date: {call_date}")

#### Main content
st.write('Welcome to the Gong App! This app allows you to generate snippets from your recent Gong calls.')

# Add a user input to select a call based on the id
call_id = st.text_input('Enter the call id:', value='')
if call_id:
    speaker_details = get_speaker_details(call_id)
    call = get_call_transcript(call_id)
    # iterate over the call to get all the transcript elements and concatenate them into a single string
    transcript = ''
    for element in call[0]['transcript']:
        speaker = element['speakerId']
        speaker_name = get_speaker_name(speaker, speaker_details)
        for sentence in element['sentences']:
            transcript += speaker_name + ': ' + sentence['text'] + '\n'
    st.expander('Transcript', expanded=True).write(transcript)
    