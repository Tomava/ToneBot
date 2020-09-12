import discord
import asyncio
import youtube_dl
from discord.utils import get
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import os
from pathlib import Path
import json
from dotenv import load_dotenv
import random

listOfCommands = {";join": "Join the voice channel you're on",
                  ";play / ;pl x": "Play the song x (x can be bind, youtube url or youtube title)",
                  ";random x / ;r x": "Play a random song or x amount of random songs from binds",
                  ";ultrarandom x / ;ur x": "Play a random downloaded song or x amount of random downloaded songs",
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
                  ";remove [title]": "Removes a song with given title",
                  ";save": "Saves the current queue",
                  ";load": "Loads a saved queue"
                  }

embedMessageMaxCharacters = 2048

global songQueue
songQueue = []
global playable
playable = True
global binds
binds = {}
global bindsByLink
bindsByLink = {}
global idleTime
idleTime = 0
global list_of_titles_by_id
list_of_titles_by_id = {}
global currentSong
currentSong = ""

# Path to home folder
home = str(Path.home())
pathToDiscord = home + os.sep + "Discord"
pathToBinds = pathToDiscord + os.sep + "listOfBinds"
pathToQueues = pathToDiscord + os.sep + "queues"
pathToArchiveLog = pathToDiscord + os.sep + "archive.log"
pathToSong = pathToDiscord + os.sep + "songs"
# if platform.system() != "Windows":
#     pathToSong = pathToDiscord + os.sep + "songs"
# else:
#     pathToSong = pathToDiscord + os.sep + "songs"
if not os.path.exists(pathToSong):
    os.makedirs(pathToSong)
if not os.path.exists(pathToQueues):
    os.makedirs(pathToQueues)
if not os.path.exists(pathToBinds):
    with open(pathToBinds, "w") as file:
        file.close()
if not os.path.exists(pathToDiscord + os.sep + "history.json"):
    with open(pathToDiscord + os.sep + "history.json", "w") as file:
        file.close()
with open(pathToDiscord + os.sep + "history.json", "r", encoding='utf-8') as file:
    data = file.read()
global songHistory
if data == "":
    songHistory = ""
else:
    songHistory = json.loads(data)
if not os.path.exists(pathToArchiveLog):
    with open(pathToArchiveLog, "w") as file:
        file.close()
with open(pathToArchiveLog, "r") as file:
    for line in file.readlines():
        if line.count("youtube") > 0:
            id = str(line).split(" ")[1].strip()
            try:
                with open(pathToSong + os.sep + id + '.info.json') as metaFile:
                    file = json.load(metaFile)
                    title = file['title']
            except FileNotFoundError and PermissionError:
                title = "Title not found"
            list_of_titles_by_id.setdefault(id, title)
with open(pathToBinds, "r") as file:
    for line in file.readlines():
        line = line.split(" ")
        binds[line[0]] = line[1].strip()
        bindsByLink.setdefault(line[1].strip(), [])
        bindsByLink[line[1].strip()].append(line[0])

load_dotenv(pathToDiscord + os.sep + "ToneBoyToken.env")
token = os.getenv('DISCORD_TOKEN')

def format_bytes(size):
    # 2**10 = 1024
    power = 2**10
    n = 0
    power_labels = {0 : '', 1: 'kilo', 2: 'mega', 3: 'giga', 4: 'tera'}
    while size > power:
        size /= power
        n += 1
    return size, power_labels[n]+'bytes'

class MyClient(discord.Client):

    async def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')
        await client.change_presence(activity=discord.Game(name=';help'))

    async def joinVoiceChannel(self, message):
        server = message.guild
        voiceChannel = get(self.voice_clients, guild=server)
        try:
            # If the user is not connected to voice channel this will throw an error
            channel = message.author.voice.channel
            if voiceChannel and voiceChannel.is_connected():
                await voiceChannel.move_to(channel)
            else:
                await channel.connect()
            return True
        except AttributeError:
            await message.channel.send("You're not connected to voice channel")
            return False

    async def leaveVoiceChannel(self, message):
        server = message.guild
        # channel = server.get_member(self.user.id).voice.channel
        voiceChannel = get(self.voice_clients, guild=server)
        global songQueue
        songQueue.clear()
        global currentSong
        currentSong = ""
        if voiceChannel and voiceChannel.is_connected():
            if voiceChannel.is_playing():
                voiceChannel.stop()
                await message.channel.send("Music stopped")
            await voiceChannel.disconnect()
        else:
            await message.channel.send("I'm not connected to voice channel!")

    async def getId(self, message, url, idFromLink, alreadyDownloaded):
        if idFromLink != "" and alreadyDownloaded:
            id = str(idFromLink).strip()
        else:
            id = str(await self.downloadSong(url, message)).strip()
            if id == "None":
                return None
            if id not in list_of_titles_by_id:
                list_of_titles_by_id.setdefault(id.strip(), await self.getSong(id.strip()))
        return id

    async def getUrl(self, message, keyWord):
        global list_of_titles_by_id
        url = keyWord
        if keyWord.count("youtu") == 0:
            if keyWord in binds.keys():
                url = binds.get(keyWord)
            # Try to make a link
            elif keyWord in list_of_titles_by_id.values():
                inverted_dict = {value: key for key, value in list_of_titles_by_id.items()}
                this_id = inverted_dict.get(keyWord)
                url = "https://www.youtube.com/watch?v=" + this_id
            else:
                await message.channel.send("That's not a valid url")
                return None
        return url

    async def downloadSong(self, url, message):
        # Youtube-dl arguments
        ydl_opts = {
            'outtmpl': pathToSong + os.sep + '%(id)s.%(ext)s',
            'format': 'bestaudio/best',
            'download_archive': pathToArchiveLog,
            'writeinfojson': 'True',
            'noplaylist': 'True',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredquality': '96',
            }],
        }

        # Downloading song and getting it's title
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            print("Downloading song")
            await message.channel.send("Downloading song")
            try:
                ydl.download([url])
                info_dict = ydl.extract_info(url, download=False)
                title = info_dict.get('title', None)
                id = info_dict.get('id', None)
            except:
                await message.channel.send("Couldn't download that song")
                return None
        return id

    async def playSong(self, message, url, print_this_command):
        server = message.guild
        idFromLink = ""
        alreadyDownloaded = False
        if url.count("youtu.be") > 0:
            idFromLink = url.split("/")[-1].split("?")[0].strip()
        elif url.count("youtube.com") > 0:
            idFromLink = url.split("/")[-1].split("&")[0].replace("watch?v=", "").strip()
        if idFromLink in list_of_titles_by_id:
            alreadyDownloaded = True

        if not alreadyDownloaded:
            # Not playable, if this command is currently removing songs from directory
            rootDirectory = Path(pathToSong)
            # Sum of file sizes in directory
            size = sum(f.stat().st_size for f in rootDirectory.glob('**/*') if f.is_file())
            i = 0
            # If there are more than 50 GB of songs remove all of them and archive.log
            if size >= 50000000000:
                return await message.channel.send("There are already too many files. Remove them manually.")
        voiceChannel = get(self.voice_clients, guild=server)
        # If the player is already playing something, add the song to the queue
        if voiceChannel and voiceChannel.is_playing():
            # If already playing something add song to queue
            id = await self.getId(message, url, idFromLink, alreadyDownloaded)
            if id is not None:
                await self.addToQueue(message.channel, url, id, message, print_this_command)
            return

        # If the link is valid and player is not playing anything do this
        else:

            # Join voice channel
            if not await self.joinVoiceChannel(message):
                return
            # Get voice channel again as the first one could have failed if bot wasn't already joined
            voiceChannel = get(self.voice_clients, guild=server)

            id = await self.getId(message, url, idFromLink, alreadyDownloaded)
            if id is None:
                return

        def addToStats(self, id, title):
            global songHistory
            idFound = False
            if songHistory != "":
                for song in songHistory['songs']:
                    jsonId = song['id']
                    if jsonId == id:
                        idFound = True
                        song['value'] = int(song['value']) + 1
                        song['last_played'] = str(datetime.now().timestamp())
                        songHistory['sum'] = songHistory['sum'] + 1
                if not idFound:
                    songHistory['songs'].append({'id': id, 'title': title, 'value': 1, "last_played": str(datetime.now().timestamp())})
                    songHistory['sum']= songHistory['sum'] + 1
            else:
                songHistory = {'songs':[{'id': id, 'title': title, 'value': 1, "last_played": str(datetime.now().timestamp())}], 'sum': 1}
            with open(pathToDiscord + os.sep + "history.json", "r", encoding='utf-8') as file:
                lines = file.readlines()
            with open(pathToDiscord + os.sep + "history.json.old", "w", encoding='utf-8') as file:
                file.close()
            with open(pathToDiscord + os.sep + "history.json.old", "r+", encoding='utf-8') as file:
                if len(file.readlines()) > 1:
                    if json.loads(file)['sum'] == json.loads(lines)['sum'] - 1:
                        file.writelines(lines)
                else:
                    file.writelines(lines)
            with open(pathToDiscord + os.sep + "history.json", "w", encoding='utf-8') as file:
                json.dump(songHistory, file, indent=2)

        def checkQueue(self, channel, voiceChannel):
            global songQueue
            print("Checking queue")
            if len(songQueue) > 0:
                commands = str(songQueue[0]).split(":")
                id = commands[0]
                channel = commands[1]
                songQueue.pop(0)
                play(self, channel, voiceChannel, id)
            else:
                print("The queue is empty")
                currentSong = ""

        def play(self, channel, voiceChannel, id):
            # Find metadata
            if id in list_of_titles_by_id.keys():
                title = list_of_titles_by_id.get(id)
            else:
                try:
                    with open(pathToSong + os.sep + id + '.info.json') as metaFile:
                        file = json.load(metaFile)
                        title = file['title']
                except FileNotFoundError or PermissionError:
                    title = "Title not found"
            global currentSong
            currentSong = title
            print(title)

            # Play the song that just got downloaded
            for file in os.listdir(pathToSong):
                if file.count(id) > 0 and file.count("json") == 0:
                    voiceChannel.play(discord.FFmpegPCMAudio(pathToSong + os.sep + file), after=lambda e: checkQueue(self, channel, voiceChannel))
                    voiceChannel.source = discord.PCMVolumeTransformer(voiceChannel.source)
                    voiceChannel.source.volume = 0.25
            addToStats(self, id, title)
            return title

        title = play(self, message.channel, voiceChannel, id)
        await self.songQueue(message, print_this_command)

    async def playRandoms(self, message, which_random, how_many):
        random_links = []
        if which_random == "ultrarandom":
            with open(pathToArchiveLog, "r") as archiveFile:
                lines = []
                for line in archiveFile.readlines():
                    if line.count("youtube") > 0:
                        lines.append(str(line).split(" ")[1])
            if len(lines) == 0:
                await message.channel.send("There are no downloaded songs from youtube")
                return
            for number in range(how_many):
                i = random.randint(0, (len(lines) - 1))
                linkEnd = str(lines[i])
                url = "https://www.youtube.com/watch?v=" + linkEnd
                random_links.append(url)
            await message.channel.send("Playing song number {} from {} songs".format(i + 1, len(lines)))
        elif which_random == "random":
            if len(binds) == 0:
                await message.channel.send("There are no binds")
                return
            for number in range(how_many):
                i = random.randint(0, (len(bindsByLink) - 1))
                url = list(bindsByLink.keys())[i]
                random_links.append(url)
            await message.channel.send("Playing song number {} from {} songs".format(i + 1, len(bindsByLink)))
        i = 1
        for url in random_links:
            if i == len(random_links):
                await self.playSong(message, url, True)
            else:
                await self.playSong(message, url, False)
            i += 1


    async def getSong(self, id):
        try:
            # Get title
            with open(pathToSong + os.sep + id + '.info.json') as metaFile:
                file = json.load(metaFile)
                title = file['title']
        except FileNotFoundError or PermissionError:
            title = "Title not found"
        return title

    async def addToQueue(self, channel, url, id, message, print_this_command):
        global songQueue
        # Id to identify song and channel to send message to channel where song was requested
        songQueue.append(id + ":" + str(channel))
        if print_this_command:
            await self.songQueue(message, True)

    async def moveToIndex(self, message, from_where, to_where):
        global songQueue
        from_where -= 1
        to_where -= 1
        # Check if indexes are in range of songQueue
        if len(songQueue) >= 2 and 0 <= from_where < len(songQueue) and 0 <= to_where < len(songQueue):
            song_to_move = songQueue[from_where]
            songQueue.pop(from_where)
            songQueue.insert(to_where, song_to_move)
        await self.songQueue(message, True)

    async def songQueue(self, message, print_this_command):
        if print_this_command:
            messageToSend = ""
            # List of messages to send
            listOfLists = []
            index = 1
            global currentSong
            if len(songQueue) < 1 and currentSong == "":
                await message.channel.send("The queue is empty")
            else:
                thisMessageToSend = "```Now: " + currentSong + "\n```\n"
                if len(thisMessageToSend) > embedMessageMaxCharacters:
                    thisMessageToSend = thisMessageToSend[:embedMessageMaxCharacters - 1]
                # Make sure this and previous ones don't exceed 2000 characters
                if (len(thisMessageToSend) + len(messageToSend)) >= embedMessageMaxCharacters:
                    # Add previous messages to list if true
                    listOfLists.append(messageToSend)
                    # Empty previous messages
                    messageToSend = ""
                # Add current message to previous messages
                messageToSend = str(messageToSend) + thisMessageToSend
                for song in songQueue:
                    # Get song id
                    song = str(song).split(":")[0]
                    try:
                        # Get title
                        with open(pathToSong + os.sep + song + '.info.json') as metaFile:
                            file = json.load(metaFile)
                            title = file['title']
                    except FileNotFoundError and PermissionError:
                        title = "Title not found"
                    # Craft message
                    thisMessageToSend = ("```" + str(index) + ": " + title + "\n```")
                    # Make sure this message doesn't exceed 2000 characters
                    if len(thisMessageToSend) > embedMessageMaxCharacters:
                        thisMessageToSend = thisMessageToSend[:embedMessageMaxCharacters - 1]
                    # Make sure this and previous ones don't exceed 2000 characters
                    if (len(thisMessageToSend) + len(messageToSend)) >= embedMessageMaxCharacters:
                        # Add previous messages to list if true
                        listOfLists.append(messageToSend)
                        # Empty previous messages
                        messageToSend = ""
                    # Add current message to previous messages
                    messageToSend = str(messageToSend) + thisMessageToSend
                    index += 1
                # Add last messages to list
                listOfLists.append(messageToSend)
                # Go through list and send as many messages as there are items on this list
                for tempList in listOfLists:
                    embed = discord.Embed(title=("Current queue"),
                                          description=(tempList))
                    await message.channel.send(content="<@" + str(message.author.id) + ">", embed=embed)

    async def clearQueue(self, message):
        songQueue.clear()
        await message.channel.send("Cleared the queue")

    async def checkDJ(self, message):
        dj = False
        for role in message.author.roles:
            if role.name == "DJ":
                dj = True
        if not dj:
            await message.channel.send("You're not a DJ")
        return dj

    async def checkAdmin(self, message):
        admin = False
        for role in message.author.roles:
            if role.name == "Admin":
                admin = True
        if not admin:
            await message.channel.send("You're not an Admin")
        return admin

    async def on_message(self, message):
        global songQueue
        global list_of_titles_by_id
        messageContent = str(message.content).lower()
        # Dont react to own messages
        if message.author.bot:
            return

        elif messageContent.startswith(';help'):
            embed = discord.Embed(title="Help on BOT",
                                  description="You must be DJ to use these commands")
            for command in listOfCommands:
                embed.add_field(name="```{}```".format(command), value="```{}```".format(listOfCommands.get(command)))
            await message.channel.send(content=None, embed=embed)

        # Give birthday
        elif messageContent.startswith(';history'):
            if not await self.checkDJ(message):
                return
            born = datetime.fromisoformat("2020-04-17T10:55:00")
            today = datetime.now()
            currentAge = relativedelta(today, born)
            years = str(currentAge.years)
            months = str(currentAge.months)
            days = str(currentAge.days)
            hours = str(currentAge.hours)
            await message.channel.send("I was created on 17.04.2020 at 10:55 (GMT+3)\n"
                                       "That makes me " + years + " years, " + months + " months, " + days + " days and " + hours + " hours old\n")

        elif messageContent.startswith(';join'):
            if not await self.checkDJ(message):
                return
            await self.joinVoiceChannel(message)

        elif messageContent.startswith(';leave') or messageContent.startswith(';stop'):
            if not await self.checkDJ(message):
                return
            await self.leaveVoiceChannel(message)

        elif messageContent.startswith(';pause'):
            if not await self.checkDJ(message):
                return
            server = message.guild
            voiceChannel = get(self.voice_clients, guild=server)
            if voiceChannel and voiceChannel.is_playing():
                voiceChannel.pause()
                await message.channel.send("Music paused")
            else:
                await message.channel.send("I'm not playing music")

        elif messageContent.startswith(';skip') or messageContent.startswith(";sk"):
            if not await self.checkDJ(message):
                return
            server = message.guild
            voiceChannel = get(self.voice_clients, guild=server)
            splitMessage = messageContent.split(" ")
            if voiceChannel:
                try:
                    howMany = int(splitMessage[1]) - 1
                except:
                    howMany = 0
                if howMany < 0:
                    howMany = 0
                global songQueue

                if len(songQueue) > howMany:
                    title = await self.getSong(str(songQueue[howMany]).split(":")[0])
                    for i in range(howMany):
                        songQueue.pop(0)
                    voiceChannel.stop()
                    # Wait so the queue gets time to refresh
                    await asyncio.sleep(0.8)
                    await self.songQueue(message, True)
                else:
                    await self.clearQueue(message)
                    global currentSong
                    currentSong = ""
                    voiceChannel.stop()
            else:
                await message.channel.send("I'm not playing music")

        elif messageContent.startswith(';queue'):
            if not await self.checkDJ(message):
                return
            if len(messageContent.split(" ")) > 1:
                try:
                    index = int(messageContent.split(" ")[1].strip())
                    if 1 <= index <= len(songQueue):
                        songQueue.pop(index - 1)
                except:
                    pass
            await self.songQueue(message, True)

        elif messageContent.startswith(';clear'):
            if not await self.checkDJ(message):
                return
            await self.clearQueue(message)

        elif messageContent.startswith(';play') or messageContent.startswith(";pl"):
            if not await self.checkDJ(message):
                return
            server = message.guild
            voiceChannel = get(self.voice_clients, guild=server)
            if len(message.content.split(" ")) <= 1:
                # Check if music is already being played but on pause
                if voiceChannel and voiceChannel.is_paused():
                    voiceChannel.resume()
                    await self.songQueue(message, True)
                else:
                    await message.channel.send("The queue is empty")
                return

            url = await self.getUrl(message, (" ").join(message.content.split(" ")[1:]).strip())
            if url is not None:
                await self.playSong(message, url, True)

        elif messageContent.startswith(";move"):
            if not await self.checkDJ(message):
                return
            parts = message.content.split(" ")
            if len(parts) >= 2:
                parts = ("").join(parts[1:]).strip()
                parts = parts.split(",")
                try:
                    from_where = int(parts[0])
                    to_where = int(parts[1])
                    await self.moveToIndex(message, from_where, to_where)
                except:
                    await message.channel.send("Your message wasn't formatted correctly")

        elif messageContent.startswith(';bind'):
            if not await self.checkDJ(message):
                return
            messageParts = message.content.split(" ")
            if len(messageParts) == 2:
                if str(messageParts[1]).lower().startswith("list"):
                    listOfLists = []
                    index = 1
                    messageToSend = ""
                    for item in sorted(bindsByLink, key=bindsByLink.get):
                        # for bind in bindsByLink.get(item):
                        #     thisBind = thisBind + bind
                        thisMessageToSend = (", ".join(bindsByLink.get(item)) + " : " + item + "\n")
                        # thisMessageToSend = (item + " : " + binds.get(item).strip() + "\n")
                        # Make sure this message doesn't exceed 2000 characters
                        if len(thisMessageToSend) > embedMessageMaxCharacters:
                            thisMessageToSend = thisMessageToSend[:embedMessageMaxCharacters - 1]
                        # Make sure this and previous ones don't exceed 2000 characters
                        if (len(thisMessageToSend) + len(messageToSend)) >= embedMessageMaxCharacters:
                            # Add previous messages to list if true
                            listOfLists.append(messageToSend)
                            # Empty previous messages
                            messageToSend = ""
                        # Add current message to previous messages
                        messageToSend = str(messageToSend) + thisMessageToSend
                        index += 1
                    # Add last messages to list
                    listOfLists.append(messageToSend)
                    # Go through list and send as many messages as there are items on this list
                    for tempList in listOfLists:
                        embed = discord.Embed(title=("Binds"),
                                              description=(tempList))
                        await message.channel.send(content="<@" + str(message.author.id) + ">", embed=embed)
                    return
            if len(messageParts) != 3:
                await message.channel.send("Your message wasn't formatted correctly")
                return
            if str(messageParts[1]).lower().startswith("remove") or str(messageParts[1]).lower().startswith("delete"):
                toBeRemoved = messageParts[2]
                if toBeRemoved in binds:
                    url = binds.get(toBeRemoved)
                    del binds[toBeRemoved]
                    bindsByLink[url].remove(toBeRemoved)
                    if len(bindsByLink[url]) == 0:
                        del bindsByLink[url]
                    with open(pathToBinds, "w") as file:
                        for line in binds:
                            file.write(line + " " + binds.get(line) + "\n")
                    await message.channel.send("Removed {} from {}".format(toBeRemoved, url))
                else:
                    await message.channel.send("Couldn't find a bind called '" + toBeRemoved + "'")
                return
            url = messageParts[2]
            shortened = messageParts[1]
            if url.lower().count("youtu") == 0:
                await message.channel.send("That's not a valid url")
                return
            if str(shortened).lower().count("youtu") > 0:
                await message.channel.send("Bind can't contain the word 'youtu'")
                return
            elif str(shortened).lower() == "random" or str(shortened).lower() == "ultrarandom":
                await message.channel.send("Bind can't be the word 'random' or 'ultrarandom'")
                return
            elif str(shortened).lower() == "r" or str(shortened).lower() == "ur":
                await message.channel.send("Bind can't be the word 'r' or 'ur'")
                return

            removeFromLink = ["list=", "index=", "t="]
            if url.count("youtu.be") > 0:
                parts = url.split("?")
            else:
                parts = url.split("&")
            # Create a second list where we remove stuff from
            tempParts = parts.copy()
            for part in parts:
                for removablePart in removeFromLink:
                    if str(part).startswith(removablePart):
                        tempParts.remove(part)
            newLink = ""
            i = 0
            # Creating the new link
            for part in tempParts:
                if i > 0:
                    newLink = newLink + "&" + part
                else:
                    newLink = part
                i += 1
            url = newLink

            with open(pathToBinds, "r") as file:
                for line in file.readlines():
                    if str(line.split(" ")[0]).lower() == str(shortened).lower():
                        await message.channel.send("That bind is already in use for " + line.split(" ")[1])
                        return
            with open(pathToBinds, "a") as file:
                line = shortened + " " + url + "\n"
                file.write(line)
                binds[shortened] = url
                bindsByLink.setdefault(url.strip(), [])
                bindsByLink[url.strip()].append(shortened)
                await message.channel.send("Bound '" + shortened + "' to " + url)

        elif messageContent.startswith(";size"):
            if not await self.checkDJ(message):
                return
            rootDirectory = Path(pathToSong)
            # Sum of file sizes in directory
            size = sum(f.stat().st_size for f in rootDirectory.glob('**/*') if f.is_file())
            formatted_size = format_bytes(size)
            await message.channel.send("Size of songs folder: " + str(round(formatted_size[0], ndigits=2)) + " " + str(formatted_size[1]))

        elif messageContent.startswith(";stats"):
            if not await self.checkDJ(message):
                return
            global songHistory
            songs = {}
            for song in songHistory['songs']:
                songs[song['title']] = song['value']
            i = 0
            messageToSend = ""
            # List of messages to send
            listOfLists = []
            for song in sorted(songs, key=songs.get, reverse=True):
                if songs.get(song) < 2:
                    break
                if i >= 15:
                    break
                i += 1
                thisMessageToSend = "```{} : {}\n```".format(songs.get(song), song)
                # thisMessageToSend = (str(songs.get(song)) + " : " + str(song) + "\n")
                # Make sure this message doesn't exceed 2000 characters
                if len(thisMessageToSend) > embedMessageMaxCharacters:
                    thisMessageToSend = thisMessageToSend[:embedMessageMaxCharacters - 1]
                # Make sure this and previous ones don't exceed 2000 characters
                if (len(thisMessageToSend) + len(messageToSend)) >= embedMessageMaxCharacters:
                    # Add previous messages to list if true
                    listOfLists.append(messageToSend)
                    # Empty previous messages
                    messageToSend = ""
                # Add current message to previous messages
                messageToSend = str(messageToSend) + thisMessageToSend
            # Add last messages to list
            listOfLists.append(messageToSend)
            # Go through list and send as many messages as there are items on this list
            for tempList in listOfLists:
                embed = discord.Embed(title=("Top 15 songs"),
                                      description=(tempList))
                await message.channel.send(content="<@" + str(message.author.id) + ">", embed=embed)

        elif messageContent.startswith(";list"):
            if not await self.checkDJ(message):
                return
            messageToSend = ""
            # List of messages to send
            listOfLists = []
            for id in list_of_titles_by_id.keys():
                # thisMessageToSend = "{} : {}\n".format(id, list_of_titles_by_id.get(id))
                thisMessageToSend = "```{}```".format(list_of_titles_by_id.get(id))
                # Make sure this message doesn't exceed 2000 characters
                if len(thisMessageToSend) > 2000:
                    thisMessageToSend = thisMessageToSend[:2000 - 1]
                # Make sure this and previous ones don't exceed 2000 characters
                if (len(thisMessageToSend) + len(messageToSend)) >= 2000:
                    # Add previous messages to list if true
                    listOfLists.append(messageToSend)
                    # Empty previous messages
                    messageToSend = ""
                # Add current message to previous messages
                messageToSend = str(messageToSend) + thisMessageToSend
                # Add last messages to list
            listOfLists.append(messageToSend)
            # Go through list and send as many messages as there are items on this list
            i = 1
            for tempList in listOfLists:
                embed = discord.Embed(title=("List of downloaded songs {}/{}".format(i, len(listOfLists))),
                                      description=(tempList))
                await message.channel.send(content="<@" + str(message.author.id) + ">", embed=embed)
                i += 1

        elif messageContent.startswith(";remove"):
            if not await self.checkAdmin(message):
                return
            if len(message.content.split(" ")) >= 2:
                title = (" ").join(message.content.split(" ")[1:]).strip()
                message_to_send = ""
                if title in list_of_titles_by_id.values():
                    inverted_dict = {value: key for key, value in list_of_titles_by_id.items()}
                    id_to_remove = inverted_dict.get((" ").join(message.content.split(" ")[1:]).strip())
                    if id_to_remove in list_of_titles_by_id:
                        title = list_of_titles_by_id.get(id_to_remove)
                        print("Removing '{}'".format(title))
                        try:
                            for file in os.listdir(pathToSong):
                                if str(file.split(".")[0]) == id_to_remove:
                                    os.remove(pathToSong + os.sep + file)
                                    message_to_send = message_to_send + "Removed '{}' from songs\n".format(file)
                                    print("Removed '{}' from songs".format(file))
                            with open(pathToArchiveLog, "r") as file:
                                lines = file.readlines()
                            lines.remove("youtube {}\n".format(id_to_remove))
                            print("Removed 'youtube {}' from archive.log".format(id_to_remove))
                            message_to_send = message_to_send + "Removed 'youtube {}' from archive.log\n".format(id_to_remove)
                            with open(pathToArchiveLog, "w") as file:
                                file.writelines(lines)
                            list_of_titles_by_id.pop(id_to_remove)
                            message_to_send = message_to_send + "Removed '{}'".format(title)
                            await message.channel.send(message_to_send)
                        except PermissionError:
                            await message.channel.send("Couldn't remove '{}' as it was currently playing".format(title))
                    else:
                        await message.channel.send("Couldn't find id '{}'".format(id_to_remove))
                else:
                    await message.channel.send("Couldn't find song '{}'".format(title))
            else:
                await message.channel.send("Your message wasn't formatted correctly")

        elif messageContent.startswith(";ultrarandom") or messageContent.startswith(";ur"):
            if not await self.checkDJ(message):
                return
            if len(messageContent) > 1:
                try:
                    how_many = int(messageContent.split(" ")[1])
                    if how_many < 2:
                        await self.playRandoms(message, "ultrarandom", 1)
                    elif how_many <= 50:
                        await self.playRandoms(message, "ultrarandom", how_many)
                    else:
                        await message.channel.send("That's too many (max 50)")
                    return
                except:
                    pass
            await self.playRandoms(message, "ultrarandom", 1)

        elif messageContent.startswith(";random") or messageContent.startswith(";r"):
            if not await self.checkDJ(message):
                return
            if len(messageContent) > 1:
                try:
                    how_many = int(messageContent.split(" ")[1])
                    if how_many < 2:
                        await self.playRandoms(message, "random", 1)
                    elif how_many <= 50:
                        await self.playRandoms(message, "random", how_many)
                    else:
                        await message.channel.send("That's too many (max 50)")
                    return
                except:
                    pass
            await self.playRandoms(message, "random", 1)

        elif messageContent.startswith(";save"):
            if not await self.checkDJ(message):
                return
            with open(pathToQueues + os.sep + "saved_queue.txt", "w") as file:
                url = await self.getUrl(message, currentSong)
                file.write(url + "\n")
                for song in songQueue:
                    url = "https://www.youtube.com/watch?v={}".format(str(song).split(":")[0])
                    file.write(url + "\n")
            await message.channel.send("Saved the current queue")

        elif messageContent.startswith(";load"):
            if not await self.checkDJ(message):
                return
            if os.path.exists(pathToQueues + os.sep + "saved_queue.txt"):
                with open(pathToQueues + os.sep + "saved_queue.txt", "r") as file:
                    lines = file.readlines()
                i = 1
                for song in lines:
                    # Get song id
                    url = song.strip()
                    if url is not None:
                        if i == len(lines):
                            await self.playSong(message, url, True)
                            return
                        await self.playSong(message, url, False)
                        i += 1

        elif messageContent.startswith(";next"):
            if not await self.checkDJ(message):
                return
            server = message.guild
            voiceChannel = get(self.voice_clients, guild=server)
            if len(message.content.split(" ")) <= 1:
                # Check if music is already being played but on pause
                if voiceChannel and voiceChannel.is_paused():
                    voiceChannel.resume()
                    await self.songQueue(message, True)
                else:
                    await message.channel.send("The queue is empty")
                return

            url = await self.getUrl(message, (" ").join(
                message.content.split(" ")[1:]).strip())
            if url is not None:
                await self.playSong(message, url, False)
            await self.moveToIndex(message, len(songQueue), 1)


client = MyClient()
client.run(token)