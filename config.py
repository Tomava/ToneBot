import json
import os

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

PATH_TO_DISCORD = "Discord"
PATH_TO_DATA = PATH_TO_DISCORD + os.sep + "data"
PATH_TO_BINDS = PATH_TO_DATA + os.sep + "listOfBinds"
PATH_TO_QUEUES = PATH_TO_DATA + os.sep + "queues"
PATH_TO_ARCHIVE_LOG = PATH_TO_DATA + os.sep + "archive.log"
PATH_TO_SONGS = PATH_TO_DATA + os.sep + "songs"
PATH_TO_HISTORY = PATH_TO_DATA + os.sep + "history.json"

# Create the directories and files if they don't exist
if not os.path.exists(PATH_TO_SONGS):
    os.makedirs(PATH_TO_SONGS)
if not os.path.exists(PATH_TO_QUEUES):
    os.makedirs(PATH_TO_QUEUES)
if not os.path.exists(PATH_TO_BINDS):
    with open(PATH_TO_BINDS, "w") as file:
        file.close()
if not os.path.exists(PATH_TO_HISTORY):
    with open(PATH_TO_HISTORY, "w") as file:
        file.close()
with open(PATH_TO_HISTORY, "r", encoding='utf-8') as file:
    data = file.read()
if data == "":
    song_history = {}
else:
    song_history = json.loads(data)
if not os.path.exists(PATH_TO_ARCHIVE_LOG):
    with open(PATH_TO_ARCHIVE_LOG, "w") as file:
        file.close()
# Get song titles and ids from their info-files
with open(PATH_TO_ARCHIVE_LOG, "r") as file:
    for line in file.readlines():
        if line.count("youtube") > 0:
            song_id = str(line).split(" ")[1].strip()
            try:
                with open(PATH_TO_SONGS + os.sep + song_id + '.info.json', encoding="utf-8") as metaFile:
                    file = json.load(metaFile)
                    title = file['title']
            except (FileNotFoundError, PermissionError):
                title = "Title not found"
            list_of_titles_by_id.setdefault(song_id, title)
# Read binds from a file
with open(PATH_TO_BINDS, "r") as file:
    for line in file.readlines():
        line = line.split(" ")
        binds[line[0]] = line[1].strip()
        binds_by_link.setdefault(line[1].strip(), [])
        binds_by_link[line[1].strip()].append(line[0])
