import webbrowser
import streamlit as st
import json
import time
import os
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi
import ffmpeg
from dotenv import load_dotenv
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
import requests


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

# Get your Descript API key from the environment variables
descript_api_key = os.getenv('DESCRIPT_API_KEY')
if descript_api_key is None:
    raise ValueError("DESCRIPT_API_KEY environment variable not set")

insights = []



def create_import_url(descript_api_key, file_path):
  # Replace with your Descript API key
  descript_api_key = descript_api_key
  url = "https://api.descript.com/v2/cloud-imports"

  headers = {
      "Authorization": f"Bearer {descript_api_key}"
  }

  data = {
      "source": "LOCAL",  # Local file upload
      "local_file": file_path
  }

  response = requests.post(url, headers=headers, json=data)

  if response.status_code == 200:
    data = response.json()
    return data.get("import_url")
  else:
    print(f"Error creating import URL: {response.text}")
    return None

def import_to_descript(descript_api_key, folder_path):
  for filename in os.listdir(folder_path):
    filepath = os.path.join(folder_path, filename)
    import_url = create_import_url(descript_api_key, filepath)
    if import_url:
        print(f"Import URL for {filename}: {import_url}")
        # Open the import URL in a web browser (optional)
        webbrowser.open(import_url)




# Handle the workload while we don't have insights selected
if 'insights' not in st.session_state:
    st.header("Welcome to the Video Insights App")
    st.write("This app helps you generate key insights, short video clips, and social media posts from a video.")
    st.write("To get started, select a video from the dropdown below.")
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
        st.session_state.transcript_text = transcript_text
        st.session_state.transcript = transcript
        st.session_state.youtube_id = selected_video['youtube_id']
        st.session_state.file = selected_video['file']

        # Save the transcript text to a file
        with open(f'data/{selected_video["youtube_id"]}.txt', 'w') as t:
            t.write(transcript_text)

    # Get the outline from the OpenAI API
    if 'outline' not in st.session_state:
        # Create the prompt to generate the outline based on the transcript
        prompt_for_outline = prompts['outline'] + st.session_state.transcript_text
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
        insight1 = st.text_input("Insight 1", key='insight1')
        insight2 = st.text_input("Insight 2", key='insight2')
        insight3 = st.text_input("Insight 3", key='insight3')

        insights = [insight1, insight2, insight3]
        # When the user presses the 'Submit' button, the form is processed and the app is rerun
        form_submit_button = st.form_submit_button("Submit Insights")
    
    if form_submit_button:
        st.session_state.insights = insights
        print(st.session_state.insights)
        st.write("Insights submitted successfully!")
        st.write("You can now proceed to generate clips and posts.")
        st.write("Click the button below to continue.")
        st.button("Generate Clips and Posts")


# Now that we have the insights, let's generate clips                
else:
    st.header("Creating Clips and Posts")

    
    # stop if the insights are empty
    if len(st.session_state.insights) == 0:
        st.write("You need to provide insights to continue")
        st.stop()

    # Get the variables
    youtube_id = st.session_state.youtube_id
    file = st.session_state.file
    insights = st.session_state.insights
    transcript  = st.session_state.transcript
    transcript_text  = st.session_state.transcript_text
    
    # Store the transcript in a chromadb vector store specific to the video
    db_name = (f'transcript_{youtube_id}')
    # Initialize the ChromaDB vector store
    chroma_client = chromadb.Client()
    # change the chromadb embedding model
    EMBEDDING_MODEL = "text-embedding-3-large"
    embedding_function = OpenAIEmbeddingFunction(api_key=openai_api_key, model_name=EMBEDDING_MODEL)

    # If we've already
    if db_name not in st.session_state:
        collection = chroma_client.get_or_create_collection(db_name, embedding_function=embedding_function)
    
        # Save each transcript line in the vector store
        st.write("Storing the transcript in the vector store")
        i = 0
        # add a progress bar
        progress_bar = st.progress(0)
        for document in transcript:
            # print(document)
            # Assuming your documents have a "text" field containing the content
            collection.add(documents=[document["text"]],
                        metadatas=[{"start": str(document["start"]), "duration": str(document["duration"])}], 
                        ids=[str(i)])
            i += 1
            # Update the progress bar
            progress_bar.progress((i+1)/(len(transcript)+1))
        st.session_state.db_name = db_name
        st.session_state.collection = collection

    # Extract the most relevant short section of the transcript for each key insight
    def extract_sections(collection, insights):
        #TODO: instead of just searching the short 4s sections, we'd want to concatenate some of them
        sections = []
        for insight in insights:
            # For each insight, find the most relevant section of the transcript. We will do this using semantic search with a vector store
            # find the records in the collection that are the most similar to the insight
            results = collection.query(
                query_texts=[insight],
                n_results=1
            )
            # Get the most relevant section of the transcript
            if len(results) > 0:                
                most_relevant = results['documents'][0]
                # Get the index of the most relevant line in the transcript
                index = results['ids'][0]
                # Get the start and end timestamps of the section
                metadata = results['metadatas'][0][0]
                start_time = max(float(metadata['start'])-15, 0)
                end_time = float(metadata['start']) + float(metadata['duration']) + 20
            
            sections.append({
                'insight': insight,
                'timestamps': (start_time, end_time)
            })
        return sections

    # Extract the sections from the transcript
    if 'collection' not in st.session_state:
        st.write("Something went wrong")
    
    print(st.session_state.insights)
    sections = extract_sections(st.session_state.collection, st.session_state.insights)
    # sections = extract_sections(st.session_state.collection, ["PLG is different from ABM, it's a bottom up approach","RevOps should be centralized"])

    # Create short video clips for each of the sections, show a progress bar
    st.write("Creating video clips for each key insight")
    progress_bar = st.progress(0)
    for i, section in enumerate(sections):
        st.write(f"Creating clip for insight: {section['insight']}")
        start_time, end_time = section['timestamps']
        # write the files in a folder named after the video id in the clips folder
        os.makedirs(f'clips/{youtube_id}', exist_ok=True)
        output_file = f'clips/{youtube_id}/clip_{i}.mp4'
        # if the file already exists, delete it
        print(file)
        print(start_time)
        print(end_time)
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
        # display the video in an expandable section
        with st.expander(f"Here's the clip for insight: {section['insight']}"):
            st.video(output_file)

    def generate_post(section, insight):
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompts['outline']},
                {"role": "user", "content": insight}
            ],
            max_tokens=500
        )
        return response.choices[0].message.content.strip()

    # Generate a social media post for each short video, show a progress bar
    st.write("Creating social media posts for each key insight")
    progress_bar2 = st.progress(0)
    for i, section in enumerate(sections):
        st.write(f"Creating post for insight: {section['insight']}")
        post = generate_post(section, insights[i])
        # create a new folder for the posts for this video using the id of the video
        os.makedirs(f'posts/{youtube_id}', exist_ok=True)
        with open(f'posts/{youtube_id}/post_{i}.txt', 'w') as f:
            f.write(post)
        # Update the progress bar
        progress_bar2.progress((i+1)/len(sections))
        # display the post in an expandable section
        with st.expander(f"Here's the post for insight: {section['insight']}"):
            st.write(post)

    # You are done! Display a message to the user
    st.write("You're all set! You can find the clips and posts in the clips and posts folders respectively.")

    #TODO: Add a button to load the videos into Descript and create a project
    # folder_path = f'clips/{youtube_id}'
    # import_to_descript(descript_api_key, folder_path)

    # Add a button to restart from the beginning
    if st.button("Start Over"):
        # clear all session state variables
        st.session_state.clear()
        st.rerun()
