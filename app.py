import streamlit as st
import json
import time
import os
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi
import ffmpeg
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load the list of videos
with open('videos.json', 'r') as f:
    videos = json.load(f)

# Load the prompts
with open('prompts.json', 'r') as f:
    prompts = json.load(f)

# Generate a detailed outline of the video
openai_api_key = os.getenv('OPENAI_API_KEY')
if openai_api_key is None:
    raise ValueError("OPENAI_API_KEY environment variable not set")

# initialize the OpenAI client
client = OpenAI(
    api_key=openai_api_key
    )

if 'insights' not in st.session_state:
    print(st.session_state)
    if 'selected_video' not in st.session_state:
        # Display the list of videos for the user to select
        selected_video = st.selectbox('Select a video', videos)
        st.session_state.selected_video = selected_video

        # Add a button for the user to submit the selected video
        if st.button("Submit"):
            st.write("Ok! let's go!")

        # Fetch the transcript of the video
        transcript = YouTubeTranscriptApi.get_transcript(selected_video['youtube_id'])
        
        
        # write the transcript to a file in the data folder
        with open(f'data/{selected_video["youtube_id"]}.json', 'w') as f:
            json.dump(transcript, f)

        # Turn the JSON transcript into a human-readable format
        transcript_text = ''
        for line in transcript:
            transcript_text += f"{line['text']} "
        
        # store the transcript, youtube_id in the session state
        st.session_state.transcript = transcript_text
        st.session_state.youtube_id = selected_video['youtube_id']
        st.session_state.file = selected_video['file']

        # Save the transcript text to a file
        with open(f'data/{selected_video["youtube_id"]}.txt', 'w') as t:
            t.write(transcript_text)

    # Get the outline from the OpenAI API
    if 'outline' not in st.session_state:
        # Create the prompt to generate the outline based on the transcript
        prompt_for_outline = prompts['outline'] + st.session_state.transcript
        print("Generating outline")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an editor. Your job is to create a detailed outline of the video."},
                {"role": "user", "content": prompt_for_outline}
            ],
            max_tokens=500
        )
        st.session_state.outline = response.choices[0].message.content.strip()
    else:
        print("Outline already generated and in cache")
    # Display the outline to the user in an expandable section
    with st.expander("Read Outline to find the key insights"):
        # show the outline as a markdown
        st.markdown(st.session_state.outline)

    # Allow the user to share 3 key insights, the insights should each be inputted in a separate text box
    with st.form("insights_form"):
        st.markdown("Please share 3 key insights from the video that you would like to create clips and posts for.")
        insight1 = st.text_input("Insight 1")
        insight2 = st.text_input("Insight 2")
        insight3 = st.text_input("Insight 3")

        insights = [insight1, insight2, insight3]
        print(insights)
        st.session_state.insights = insights
        # When the user presses the 'Submit' button, the form is processed and the app is rerun
        st.form_submit_button("Submit Insights")
                
else:
#  'insights' in st.session_state:
    youtube_id = st.session_state.youtube_id
    file = st.session_state.file
    insights = st.session_state.insights
    # Extract the most relevant short section of the transcript for each key insight
    def extract_sections(transcript, insights):
        sections = []
        for insight in insights:
            # This is a placeholder. You'll need to implement this part based on your specific requirements.
            sections.append({
                'insight': insight,
                'timestamps': (0, 10)
            })
        return sections

    # Extract the sections from the transcript
    sections = extract_sections(st.session_state.transcript, st.session_state.insights)

    # Create short video clips for each of the sections, show a progress bar
    st.write("Creating video clips for each key insight")
    progress_bar = st.progress(0)
    for i, section in enumerate(sections):
        start_time, end_time = section['timestamps']
        # write the files in a folder named after the video id in the clips folder
        os.makedirs(f'clips/{youtube_id}', exist_ok=True)
        output_file = f'clips/{youtube_id}/clip_{i}.mp4'
        # if the file already exists, delete it
        if os.path.exists(output_file):
            os.remove(output_file)
        (
            ffmpeg
            .input(file, ss=start_time, to=end_time)
            .output(output_file)
            .run()
        )
        # Update the progress bar
        progress_bar.progress((i+1)/len(sections))

    def generate_post(prompt, section, insight):
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a social media manager. Your job is to write a post based on an insight and its supporting short video clip."},
                {"role": "user", "content": prompt.format(insight=insight, section=section)}
            ],
            max_tokens=500
        )
        return response.choices[0].message.content.strip()

    # Generate a social media post for each short video, show a progress bar
    st.write("Creating social media posts for each key insight")
    progress_bar2 = st.progress(0)
    for i, section in enumerate(sections):
        post = generate_post(prompts['post'], section, insights[i])
        # create a new folder for the posts for this video using the id of the video
        os.makedirs(f'posts/{youtube_id}', exist_ok=True)
        with open(f'posts/{youtube_id}/post_{i}.txt', 'w') as f:
            f.write(post)
        # Update the progress bar
        progress_bar2.progress((i+1)/len(sections))

    # You are done! Display a message to the user
    st.write("You're all set! You can find the clips and posts in the clips and posts folders respectively.")

    # Add a button to restart from the beginning
    if st.button("Start Over"):
        st.session_state.submitted = False
        st.experimental_rerun()
