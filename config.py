import json
import os
from pathlib import Path

LIST_OF_COMMANDS = {";join": "Join the voice channel you're on",
                    ";play / ;pl x": "Play the song x (x can be bind, youtube url or youtube title)",
                    ";random x / ;r x": "Play a random song or x amount of random songs from binds",
                    ";ultrarandom x / ;ur x": "Play a random downloaded song or x amount of random downloaded songs",
                    ";index x": "Play a song with the index x from the list of downloaded songs",
                    ";next x": "Adds the song x to be next in queue",
                    ";play / ;pl": "Resume playing paused music",
                    ";pause": "Pause music",
                    ";stop / ;leave": "Stop music, empty the queue and leave the voice channel",
                    ";skip / ;sk": "Skip the current song",
                    ";skip / ;sk x": "Skip x amount of songs",
                    ";queue": "View the current queue",
                    ";queue x": "Remove song number x from queue",
                    ";move x,y": "Puts xth song to yth place in queue",
                    ";clear": "Clears the current queue",
                    ";history": "Learn about my history",
                    ";bind x url": "Bind x command to a specific url",
                    ";bind list": "Shows the list of current binds",
                    ";bind remove/delete x": "Deletes bind x",
                    ";stats": "View listening stats",
                    ";list": "List all downloaded songs",
                    ";remove [title]": "Removes a song with given title (requires Admin)",
                    ";save": "Saves the current queue",
                    ";load": "Loads a saved queue"
                    }
LIST_OF_ACCEPTED_URLS = {"https://www.youtube.com/",
                         "https://youtu.be/",
                         "http://www.youtube.com/",
                         "http://youtu.be/"}

# Initiate global variables
EMBED_MESSAGE_MAX_CHARACTERS = 2048
MAX_SONG_QUEUE_LENGTH = 250
song_queue = []
binds = {}
binds_by_link = {}
list_of_titles_by_id = {}
current_song = ""

# Paths to different directories
# Will work on all platforms
home = str(Path.home())
path_to_discord = home + os.sep + "Discord"
path_to_binds = path_to_discord + os.sep + "listOfBinds"
path_to_queues = path_to_discord + os.sep + "queues"
path_to_archive_log = path_to_discord + os.sep + "archive.log"
path_to_songs = path_to_discord + os.sep + "songs"

# Create the directories and files if they don't exist
if not os.path.exists(path_to_songs):
    os.makedirs(path_to_songs)
if not os.path.exists(path_to_queues):
    os.makedirs(path_to_queues)
if not os.path.exists(path_to_binds):
    with open(path_to_binds, "w") as file:
        file.close()
if not os.path.exists(path_to_discord + os.sep + "history.json"):
    with open(path_to_discord + os.sep + "history.json", "w") as file:
        file.close()
with open(path_to_discord + os.sep + "history.json", "r", encoding='utf-8') as file:
    data = file.read()
global song_history
if data == "":
    song_history = ""
else:
    song_history = json.loads(data)
if not os.path.exists(path_to_archive_log):
    with open(path_to_archive_log, "w") as file:
        file.close()
# Get song titles and ids from their info-files
with open(path_to_archive_log, "r") as file:
    for line in file.readlines():
        if line.count("youtube") > 0:
            song_id = str(line).split(" ")[1].strip()
            try:
                with open(path_to_songs + os.sep + song_id + '.info.json') as metaFile:
                    file = json.load(metaFile)
                    title = file['title']
            except (FileNotFoundError, PermissionError):
                title = "Title not found"
            list_of_titles_by_id.setdefault(song_id, title)
# Read binds from a file
with open(path_to_binds, "r") as file:
    for line in file.readlines():
        line = line.split(" ")
        binds[line[0]] = line[1].strip()
        binds_by_link.setdefault(line[1].strip(), [])
        binds_by_link[line[1].strip()].append(line[0])
