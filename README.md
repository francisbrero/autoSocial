# autoSocial
Generate Social Media posts from long format video

## Installation
start a venv environment
```bash
python3 -m venv venv
source venv/bin/activate
```
### Install ffmpeg (1 time only)
```bash
brew install ffmpeg
```
```bash
export PATH=/usr/local/bin:$PATH
```

## install the requirements
```bash
pip install -r requirements.txt
```

## Run the app
```bash
streamlit run app.py
```

# Design / Prompt

A streamlit app that allows a user to pick a video file and its relevant youtube video ID.
The app then:
- Leverages the Youtube API to get the transcript of the video
- Load the transcript into a GPT model to generate a detailed outline of the video using a special prompt
- The user then should share 3 Key Insights from the outline
- The app will then extract the most relevant short section of the transcript for each key insight including timestamps
- Using the timestamps, the app will create short video clips for each of the sections using ffmpeg and the local file
- Each short video clip will be saved in a folder
- For each short video, a social media posts will be generated based on the insight, the section of the transcript and a specific prompt. These posts will be saved in the folder as text files