import discord
import asyncio
import youtube_dl
from discord.utils import get
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os
import json
from dotenv import load_dotenv
import random
from config import *

load_dotenv(path_to_discord + os.sep + "ToneBoyToken.env")
token = os.getenv('DISCORD_TOKEN')


def format_bytes(size):
    """
    Gives correct prefixes to sizes
    :param size: int, size in bytes
    :return: str, Returns size in appropriate format
    """
    # 2**10 = 1024
    power = 2 ** 10
    n = 0
    power_labels = {0: '', 1: 'kilo', 2: 'mega', 3: 'giga', 4: 'tera'}
    while size > power:
        size /= power
        n += 1
    return size, power_labels[n] + 'bytes'


class MyClient(discord.Client):

    async def on_ready(self):
        """
        Prints user information when ready and sets activity
        :return: nothing
        """
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('-' * 20)
        await client.change_presence(activity=discord.Game(name=';help'))

    async def join_voice_channel(self, message, print_errors):
        """
        Join the message author's voice channel or moves to it from another channel
        :param message: MessageType, The message that initiated joining
        :return: boolean, Return True if bot is able to join channel and False if not
        """
        server = message.guild
        voice_channel = get(self.voice_clients, guild=server)
        try:
            # If the user is not connected to voice channel this will throw an error
            channel = message.author.voice.channel
            if voice_channel and voice_channel.is_connected():
                await voice_channel.move_to(channel)
            else:
                await channel.connect()
            return True
        except AttributeError:
            if print_errors:
                await message.channel.send("You're not connected to voice channel")
            return False

    async def leave_voice_channel(self, message):
        """
        Leave currently connected voice channel from a given guild
        :param message: MessageType, The message that initiated leaving
        :return: nothing
        """
        server = message.guild
        # channel = server.get_member(self.user.id).voice.channel
        voice_channel = get(self.voice_clients, guild=server)
        global song_queue
        song_queue.clear()
        global current_song
        current_song = ""
        if voice_channel and voice_channel.is_connected():
            if voice_channel.is_playing():
                voice_channel.stop()
                await message.channel.send("Music stopped")
            await voice_channel.disconnect()
        else:
            await message.channel.send("I'm not connected to voice channel!")

    async def check_id(self, message, url, id_from_link, print_this_command):
        """
        Downloads song with given id if it's not already downloaded and there's enough room. Else just returns the id
        :param message: MessageType, For sending error message and to pass it to download_song
        :param url: str, Url of wanted song (needed for downloading it)
        :param id_from_link: str, Id of wanted song
        :param print_this_command: bool, If true will print error messages
        :return: str, Valid song id, None if doesn't exist
        """
        song_id = None
        if id_from_link not in list_of_titles_by_id:
            # Not playable, if this command is currently removing songs from directory
            rootDirectory = Path(path_to_songs)
            # Sum of file sizes in directory
            size = sum(f.stat().st_size for f in rootDirectory.glob('**/*') if f.is_file())
            i = 0
            # If there are more than 50 GB of songs don't do anything
            if size >= 50000000000:
                if print_this_command:
                    await message.channel.send("There are already too many files. Remove them manually.")
                return
            song_id = str(await self.download_song(url, message)).strip()
            if song_id == "None":
                return None
            list_of_titles_by_id.setdefault(song_id.strip(), await self.get_song_title(song_id.strip()))
        elif id_from_link != "":
            song_id = str(id_from_link).strip()
        return song_id

    async def get_url(self, message, key_word):
        """
        Checks if given key word is a bound word or a title of already downloaded song. If neither is true checks if given
        link contains "youtu" to check it's a valid youtube link
        :param message: MessageType, For sending error message
        :param key_word: str, Can be bind, link or a song title
        :return: str, Url of a song
        """
        global list_of_titles_by_id
        url = key_word
        if key_word in binds.keys():
            url = binds.get(key_word)
        # Check if key_word is a title of already downloaded song
        elif key_word in list_of_titles_by_id.values():
            inverted_dict = {value: key for key, value in list_of_titles_by_id.items()}
            this_id = inverted_dict.get(key_word)
            url = "https://www.youtube.com/watch?v=" + this_id
        elif key_word.count("youtu") == 0:
            await message.channel.send("That's not a valid url")
            return None
        return url

    async def download_song(self, url, message):
        """
        Downloads a song with given url
        :param url: str, Url of a song
        :param message: MessageType, For sending error message
        :return: str, Id of the downloaded song
        """
        # Youtube-dl arguments
        ydl_opts = {
            'outtmpl': path_to_songs + os.sep + '%(id)s.%(ext)s',
            'format': 'bestaudio/best',
            'download_archive': path_to_archive_log,
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

    async def play_song(self, message, url, print_this_command):
        """
        Makes everything ready for play to play a song with given url
        :param message: MessageType, Passed to various other functions
        :param url: str, Url of a song
        :param print_this_command: bool, If true, will send messages to server after finishing or in case of errors.
        Passed to various other functions
        :return: nothing
        """
        server = message.guild
        id_from_link = ""
        if url.count("youtu.be") > 0:
            id_from_link = url.split("/")[-1].split("?")[0].strip()
        elif url.count("youtube.com") > 0:
            id_from_link = url.split("/")[-1].split("&")[0].replace("watch?v=", "").strip()

        voice_channel = get(self.voice_clients, guild=server)
        # If the player is already playing something, add the song to the queue
        if voice_channel and voice_channel.is_playing():
            # If already playing something add song to queue
            id = await self.check_id(message, url, id_from_link, print_this_command)
            if id is not None:
                await self.add_to_queue(message.channel, id, message, print_this_command)
            return

        # If the link is valid and player is not playing anything do this
        else:
            # Join voice channel
            if not await self.join_voice_channel(message, print_this_command):
                return
            # Get voice channel again as the first one could have failed if bot wasn't already joined
            voice_channel = get(self.voice_clients, guild=server)
            id = await self.check_id(message, url, id_from_link, print_this_command)
            if id is None:
                return

        await self.play(voice_channel, id, message)
        await self.print_song_queue(message, print_this_command)

    async def play(self, voice_channel, id, message):
        """
        Plays a song with given id
        :param voice_channel: VoiceChannel, Voice channel to which the song requester was connected to
        :param id: str, Id of the song
        :param message: MessageType, Used to get text channel where the song was requested at.
        Passed to check_queue after song finishes
        :return: nothing
        """
        # Find metadata
        if id in list_of_titles_by_id.keys():
            title = list_of_titles_by_id.get(id)
        else:
            title = await self.get_song_title(id)
        global current_song
        current_song = title
        print(title)
        loop = asyncio.get_event_loop()
        # Play the song that just got downloaded
        for file in os.listdir(path_to_songs):
            if file.count(id) > 0 and file.count("json") == 0:
                voice_channel.play(discord.FFmpegPCMAudio(path_to_songs + os.sep + file),
                                   after=lambda e: loop.create_task(self.check_queue(voice_channel, message)))
                voice_channel.source = discord.PCMVolumeTransformer(voice_channel.source)
                voice_channel.source.volume = 0.25
        await self.add_to_stats(id, title)
        return

    async def add_to_stats(self, id, title):
        """
        Adds played song to the stats file
        :param id: str, Id of a given song
        :param title: str, Title of a given song
        :return: nothing
        """
        global song_history
        id_found = False
        if song_history != "":
            for song in song_history['songs']:
                jsonId = song['id']
                if jsonId == id:
                    id_found = True
                    song['value'] = int(song['value']) + 1
                    song['last_played'] = str(datetime.now().timestamp())
                    song_history['sum'] = song_history['sum'] + 1
            if not id_found:
                song_history['songs'].append(
                    {'id': id, 'title': title, 'value': 1, "last_played": str(datetime.now().timestamp())})
                song_history['sum'] = song_history['sum'] + 1
        else:
            song_history = {
                'songs': [{'id': id, 'title': title, 'value': 1, "last_played": str(datetime.now().timestamp())}],
                'sum': 1}
        with open(path_to_discord + os.sep + "history.json", "r", encoding='utf-8') as history_file:
            lines = history_file.readlines()
        with open(path_to_discord + os.sep + "history.json.old", "w", encoding='utf-8') as history_file:
            history_file.close()
        with open(path_to_discord + os.sep + "history.json.old", "r+", encoding='utf-8') as history_file:
            if len(history_file.readlines()) > 1:
                if json.loads(history_file)['sum'] == json.loads(lines)['sum'] - 1:
                    history_file.writelines(lines)
            else:
                history_file.writelines(lines)
        with open(path_to_discord + os.sep + "history.json", "w", encoding='utf-8') as history_file:
            json.dump(song_history, history_file, indent=2, ensure_ascii=False)

    async def check_queue(self, voice_channel, message):
        """
        Plays the next song in queue and prints the queue
        :param voice_channel: VoiceChannel, Voice channel to which the song requester was connected to. Passed to play
        :param message: MessageType, Used to get text channel where the song was requested at. Passed to print_song_queue
        :return: nothing
        """
        global song_queue
        print("Checking queue")
        if len(song_queue) > 0:
            commands = str(song_queue[0]).split(":")
            id = commands[0]
            channel = commands[1]
            song_queue.pop(0)
            await self.play(voice_channel, id, message)
            await self.print_song_queue(message, True)
        else:
            print("The queue is empty")
            current_song = ""

    async def play_randoms(self, message, which_random, how_many):
        """
        Plays how_many amount of random songs according to which_random
        :param message: MessageType, For error messages
        :param which_random: str, Either "ultrarandom" or "random". Decides if song is played from all downloaded songs
        or from binds
        :param how_many: int, How many songs to play (1 - 50)
        :return: nothing
        """
        random_links = []
        if which_random == "ultrarandom":
            song_amount = len(list_of_titles_by_id)
            for number in range(how_many):
                i = random.randint(0, (len(list_of_titles_by_id) - 1))
                url = "https://www.youtube.com/watch?v=" + list(list_of_titles_by_id.keys())[i]
                random_links.append(url)
            if len(list_of_titles_by_id) == 0:
                await message.channel.send("There are no downloaded songs from youtube")
                return
        elif which_random == "random":
            song_amount = len(binds)
            if len(binds) == 0:
                await message.channel.send("There are no binds")
                return
            for number in range(how_many):
                i = random.randint(0, (len(binds_by_link) - 1))
                url = list(binds_by_link.keys())[i]
                random_links.append(url)
        if how_many == 1:
            await message.channel.send(f"Playing song number {i + 1} from {song_amount} songs")
        else:
            await message.channel.send(f"Playing {how_many} songs from {song_amount} songs")
        i = 1
        for url in random_links:
            if i == len(random_links):
                await self.play_song(message, url, True)
            else:
                await self.play_song(message, url, False)
            i += 1

    async def get_song_title(self, id):
        """
        Gets the title of a given song by id from it's info.json file
        :param id: str, Given song id
        :return: str, Title of the song
        """
        try:
            # Get title
            with open(path_to_songs + os.sep + id + '.info.json') as metaFile:
                file = json.load(metaFile)
                title = file['title']
        except FileNotFoundError or PermissionError:
            title = "Title not found"
        return title

    async def add_to_queue(self, channel, id, message, print_this_command):
        """
        Adds a given song to the queue if song queue is not full
        :param channel: VoiceChannel, Voice channel where the song was requested to
        :param id: str, Id of the wanted song
        :param message: MessageType, Passed to print_song_queue to print the queue
        :param print_this_command: bool, Decided if song queue gets printed to text channel
        :return: nothing
        """
        global song_queue
        # Id to identify song and channel to send message to channel where song was requested
        if len(song_queue) < MAX_SONG_QUEUE_LENGTH:
            song_queue.append(id + ":" + str(channel))
        await self.print_song_queue(message, print_this_command)

    async def move_to_index(self, message, from_where, to_where):
        """
        Moves a song from one index to another in the song queue if both indexes are valid
        :param message: MessageType, Passed to print_song_queue to print the queue
        :param from_where: int, Index of a song to move
        :param to_where: int, Index of a song to move
        :return: nothing
        """
        global song_queue
        from_where -= 1
        to_where -= 1
        # Check if indexes are in range of print_song_queue
        if len(song_queue) >= 2 and 0 <= from_where < len(song_queue) and 0 <= to_where < len(song_queue):
            song_to_move = song_queue[from_where]
            song_queue.pop(from_where)
            song_queue.insert(to_where, song_to_move)
        await self.print_song_queue(message, True)

    async def print_song_queue(self, message, print_this_command):
        """
        Prints the current song queue if given boolean is true
        :param message: MessageType, Used to identify text channel where to send message
        :param print_this_command: If false, doesn't do anything
        :return: nothing
        """
        if print_this_command:
            message_to_send = ""
            # List of messages to send
            list_of_lists = []
            index = 1
            global current_song
            if len(song_queue) < 1 and current_song == "":
                await message.channel.send("The queue is empty")
            else:
                this_message_to_send = "```Now: " + current_song + "\n```\n"
                if len(this_message_to_send) > EMBED_MESSAGE_MAX_CHARACTERS:
                    this_message_to_send = this_message_to_send[:EMBED_MESSAGE_MAX_CHARACTERS - 1]
                # Make sure this and previous ones don't exceed 2000 characters
                if (len(this_message_to_send) + len(message_to_send)) >= EMBED_MESSAGE_MAX_CHARACTERS:
                    # Add previous messages to list if true
                    list_of_lists.append(message_to_send)
                    # Empty previous messages
                    message_to_send = ""
                # Add current message to previous messages
                message_to_send = str(message_to_send) + this_message_to_send
                for song in song_queue:
                    # Get song id
                    song = str(song).split(":")[0]
                    # Get song title
                    title = await self.get_song_title(song)
                    # Craft message
                    this_message_to_send = ("```" + str(index) + ": " + title + "\n```")
                    # Make sure this message doesn't exceed 2000 characters
                    if len(this_message_to_send) > EMBED_MESSAGE_MAX_CHARACTERS:
                        this_message_to_send = this_message_to_send[:EMBED_MESSAGE_MAX_CHARACTERS - 1]
                    # Make sure this and previous ones don't exceed 2000 characters
                    if (len(this_message_to_send) + len(message_to_send)) >= EMBED_MESSAGE_MAX_CHARACTERS:
                        # Add previous messages to list if true
                        list_of_lists.append(message_to_send)
                        # Empty previous messages
                        message_to_send = ""
                    # Add current message to previous messages
                    message_to_send = str(message_to_send) + this_message_to_send
                    index += 1
                # Add last messages to list
                list_of_lists.append(message_to_send)
                # Go through list and send as many messages as there are items on this list
                for temp_list in list_of_lists:
                    embed = discord.Embed(title=("Current queue"), description=(temp_list))
                    await message.channel.send(content="", embed=embed)

    async def clear_queue(self, message):
        """
        Clears the song queue and send a notification about it
        :param message: MessageType, Used to identify text channel where to send message
        :return: nothing
        """
        song_queue.clear()
        await message.channel.send("Cleared the queue")

    async def check_dj(self, message):
        """
        Checks if given message's author has a role called "DJ"
        :param message: MessageType, Used to identify author
        :return: bool, True if the author is "DJ"
        """
        dj = False
        for role in message.author.roles:
            if role.name == "DJ":
                dj = True
        if not dj:
            await message.channel.send("You're not a DJ")
        return dj

    async def check_admin(self, message):
        """
        Checks if given message's author has a role called "Admin"
        :param message: MessageType, Used to identify author
        :return: bool, True if the author is "Admin"
        """
        admin = False
        for role in message.author.roles:
            if role.name == "Admin":
                admin = True
        if not admin:
            await message.channel.send("You're not an Admin")
        return admin

    async def on_message(self, message):
        global song_queue
        global list_of_titles_by_id
        message_content = str(message.content).lower()
        # Dont react to own messages
        if message.author.bot:
            return

        elif message_content.startswith(';help'):
            embed = discord.Embed(title="Help on BOT",
                                  description="You must be DJ to use these commands")
            for command in listOfCommands:
                embed.add_field(name="```{}```".format(command), value="```{}```".format(listOfCommands.get(command)))
            await message.channel.send(content=None, embed=embed)

        # Give birthday
        elif message_content.startswith(';history'):
            if not await self.check_dj(message):
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

        elif message_content.startswith(';join'):
            if not await self.check_dj(message):
                return
            await self.join_voice_channel(message, True)

        elif message_content.startswith(';leave') or message_content.startswith(';stop'):
            if not await self.check_dj(message):
                return
            await self.leave_voice_channel(message)

        elif message_content.startswith(';pause'):
            if not await self.check_dj(message):
                return
            server = message.guild
            voiceChannel = get(self.voice_clients, guild=server)
            if voiceChannel and voiceChannel.is_playing():
                voiceChannel.pause()
                await message.channel.send("Music paused")
            else:
                await message.channel.send("I'm not playing music")

        elif message_content.startswith(';skip') or message_content.startswith(";sk"):
            if not await self.check_dj(message):
                return
            server = message.guild
            voiceChannel = get(self.voice_clients, guild=server)
            splitMessage = message_content.split(" ")
            if voiceChannel:
                try:
                    howMany = int(splitMessage[1]) - 1
                except:
                    howMany = 0
                if howMany < 0:
                    howMany = 0
                global song_queue

                if len(song_queue) > howMany:
                    for i in range(howMany):
                        song_queue.pop(0)
                    voiceChannel.stop()
                    # Wait so the queue gets time to refresh
                    await asyncio.sleep(0.8)
                else:
                    await self.clear_queue(message)
                    global current_song
                    current_song = ""
                    voiceChannel.stop()
            else:
                await message.channel.send("I'm not playing music")

        elif message_content.startswith(';queue'):
            if not await self.check_dj(message):
                return
            if len(message_content.split(" ")) > 1:
                try:
                    index = int(message_content.split(" ")[1].strip())
                    if 1 <= index <= len(song_queue):
                        song_queue.pop(index - 1)
                except:
                    pass
            await self.print_song_queue(message, True)

        elif message_content.startswith(';clear'):
            if not await self.check_dj(message):
                return
            await self.clear_queue(message)

        elif message_content.startswith(';play') or message_content.startswith(";pl"):
            if not await self.check_dj(message):
                return
            server = message.guild
            voiceChannel = get(self.voice_clients, guild=server)
            if len(message.content.split(" ")) <= 1:
                # Check if music is already being played but on pause
                if voiceChannel and voiceChannel.is_paused():
                    voiceChannel.resume()
                    await self.print_song_queue(message, True)
                else:
                    await message.channel.send("The queue is empty")
                return

            url = await self.get_url(message, (" ").join(message.content.split(" ")[1:]).strip())
            if url is not None:
                await self.play_song(message, url, True)

        elif message_content.startswith(";move"):
            if not await self.check_dj(message):
                return
            parts = message.content.split(" ")
            if len(parts) >= 2:
                parts = ("").join(parts[1:]).strip()
                parts = parts.split(",")
                try:
                    from_where = int(parts[0])
                    to_where = int(parts[1])
                    await self.move_to_index(message, from_where, to_where)
                except:
                    await message.channel.send("Your message wasn't formatted correctly")

        elif message_content.startswith(';bind'):
            if not await self.check_dj(message):
                return
            messageParts = message.content.split(" ")
            if len(messageParts) == 2:
                if str(messageParts[1]).lower().startswith("list"):
                    listOfLists = []
                    index = 1
                    messageToSend = ""
                    for item in sorted(binds_by_link, key=binds_by_link.get):
                        # for bind in bindsByLink.get(item):
                        #     thisBind = thisBind + bind
                        thisMessageToSend = (", ".join(binds_by_link.get(item)) + " : " + item + "\n")
                        # thisMessageToSend = (item + " : " + binds.get(item).strip() + "\n")
                        # Make sure this message doesn't exceed 2000 characters
                        if len(thisMessageToSend) > EMBED_MESSAGE_MAX_CHARACTERS:
                            thisMessageToSend = thisMessageToSend[:EMBED_MESSAGE_MAX_CHARACTERS - 1]
                        # Make sure this and previous ones don't exceed 2000 characters
                        if (len(thisMessageToSend) + len(messageToSend)) >= EMBED_MESSAGE_MAX_CHARACTERS:
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
                    # Removes this alias from dictionary
                    binds_by_link[url].remove(toBeRemoved)
                    # If there are no other aliases for that link, remove the link
                    if len(binds_by_link[url]) == 0:
                        del binds_by_link[url]
                    with open(path_to_binds, "w") as file:
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
            if url.count("youtube.com") > 0:
                split_character = "&"
            else:
                split_character = "?"
            parts = url.split(split_character)
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
                    newLink = newLink + split_character + part
                else:
                    newLink = part
                i += 1
            url = newLink

            with open(path_to_binds, "r") as file:
                for line in file.readlines():
                    if str(line.split(" ")[0]).lower() == str(shortened).lower():
                        await message.channel.send("That bind is already in use for " + line.split(" ")[1])
                        return
            with open(path_to_binds, "a") as file:
                line = shortened + " " + url + "\n"
                file.write(line)
                binds[shortened] = url
                binds_by_link.setdefault(url.strip(), [])
                binds_by_link[url.strip()].append(shortened)
                await message.channel.send("Bound '" + shortened + "' to " + url)

        elif message_content.startswith(";size"):
            if not await self.check_dj(message):
                return
            rootDirectory = Path(path_to_songs)
            # Sum of file sizes in directory
            size = sum(f.stat().st_size for f in rootDirectory.glob('**/*') if f.is_file())
            formatted_size = format_bytes(size)
            await message.channel.send(
                "Size of songs folder: " + str(round(formatted_size[0], ndigits=2)) + " " + str(formatted_size[1]))

        elif message_content.startswith(";stats"):
            if not await self.check_dj(message):
                return
            global song_history
            songs = {}
            for song in song_history['songs']:
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
                if len(thisMessageToSend) > EMBED_MESSAGE_MAX_CHARACTERS:
                    thisMessageToSend = thisMessageToSend[:EMBED_MESSAGE_MAX_CHARACTERS - 1]
                # Make sure this and previous ones don't exceed 2000 characters
                if (len(thisMessageToSend) + len(messageToSend)) >= EMBED_MESSAGE_MAX_CHARACTERS:
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

        elif message_content.startswith(";list"):
            if not await self.check_dj(message):
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

        elif message_content.startswith(";remove"):
            if not await self.check_admin(message):
                return
            if len(message.content.split(" ")) >= 2:
                title = (" ").join(message.content.split(" ")[1:]).strip()
                message_to_send = ""
                if title in list_of_titles_by_id.values():
                    inverted_dict = {value: key for key, value in list_of_titles_by_id.items()}
                    id_to_remove = inverted_dict.get((" ").join(message.content.split(" ")[1:]).strip())
                    if id_to_remove in list_of_titles_by_id:
                        title = list_of_titles_by_id.get(id_to_remove)
                        if title != current_song:
                            print("Removing '{}'".format(title))
                            try:
                                list_of_files = os.listdir(path_to_songs)
                                for file in list_of_files:
                                    if str(file.split(".")[0]) == id_to_remove:
                                        os.remove(path_to_songs + os.sep + file)
                                        message_to_send = message_to_send + "Removed '{}' from songs\n".format(file)
                                        print("Removed '{}' from songs".format(file))
                                with open(path_to_archive_log, "r") as file:
                                    lines = file.readlines()
                                lines.remove("youtube {}\n".format(id_to_remove))
                                print("Removed 'youtube {}' from archive.log".format(id_to_remove))
                                message_to_send = message_to_send + "Removed 'youtube {}' from archive.log\n".format(
                                    id_to_remove)
                                with open(path_to_archive_log, "w") as file:
                                    file.writelines(lines)
                                list_of_titles_by_id.pop(id_to_remove)
                                message_to_send = message_to_send + "Removed '{}'".format(title)
                                await message.channel.send(message_to_send)
                            except PermissionError:
                                await message.channel.send("Couldn't remove '{}' as it was currently playing".format(title))
                        else:
                            await message.channel.send("Couldn't remove '{}' as it was currently playing".format(title))
                    else:
                        await message.channel.send("Couldn't find id '{}'".format(id_to_remove))
                else:
                    await message.channel.send("Couldn't find song '{}'".format(title))
            else:
                await message.channel.send("Your message wasn't formatted correctly")

        elif message_content.startswith(";ultrarandom") or message_content.startswith(";ur"):
            if not await self.check_dj(message):
                return
            if len(message_content) > 1:
                try:
                    how_many = int(message_content.split(" ")[1])
                    if how_many < 2:
                        await self.play_randoms(message, "ultrarandom", 1)
                    elif how_many <= 50:
                        await self.play_randoms(message, "ultrarandom", how_many)
                    else:
                        await message.channel.send("That's too many (max 50)")
                    return
                except:
                    pass
            await self.play_randoms(message, "ultrarandom", 1)

        elif message_content.startswith(";random") or message_content.startswith(";r"):
            if not await self.check_dj(message):
                return
            if len(message_content) > 1:
                try:
                    how_many = int(message_content.split(" ")[1])
                    if how_many < 2:
                        await self.play_randoms(message, "random", 1)
                    elif how_many <= 50:
                        await self.play_randoms(message, "random", how_many)
                    else:
                        await message.channel.send("That's too many (max 50)")
                    return
                except:
                    pass
            await self.play_randoms(message, "random", 1)

        elif message_content.startswith(";save"):
            if not await self.check_dj(message):
                return
            with open(path_to_queues + os.sep + "saved_queue.txt", "w") as file:
                url = await self.get_url(message, current_song)
                file.write(url + "\n")
                for song in song_queue:
                    url = "https://www.youtube.com/watch?v={}".format(str(song).split(":")[0])
                    file.write(url + "\n")
            await message.channel.send("Saved the current queue")

        elif message_content.startswith(";load"):
            if not await self.check_dj(message):
                return
            if os.path.exists(path_to_queues + os.sep + "saved_queue.txt"):
                with open(path_to_queues + os.sep + "saved_queue.txt", "r") as file:
                    lines = file.readlines()
                i = 1
                for song in lines:
                    # Get song id
                    url = song.strip()
                    if url is not None:
                        if i == len(lines):
                            await self.play_song(message, url, True)
                            return
                        await self.play_song(message, url, False)
                        i += 1

        elif message_content.startswith(";next"):
            if not await self.check_dj(message):
                return
            server = message.guild
            voiceChannel = get(self.voice_clients, guild=server)
            if len(message.content.split(" ")) <= 1:
                # Check if music is already being played but on pause
                if voiceChannel and voiceChannel.is_paused():
                    voiceChannel.resume()
                    await self.print_song_queue(message, True)
                else:
                    await message.channel.send("The queue is empty")
                return

            url = await self.get_url(message, (" ").join(
                message.content.split(" ")[1:]).strip())
            if url is not None:
                await self.play_song(message, url, False)
                await self.move_to_index(message, len(song_queue), 1)

        elif message_content.startswith(";index"):
            if not await self.check_dj(message):
                return
            if len(message_content) > 1:
                try:
                    i = int(message_content.split(" ")[1])
                except ValueError:
                    return await message.channel.send("Your message wasn't formatted correctly. Use \"index x\"")
                if 0 < i <= len(list_of_titles_by_id):
                    url = "https://www.youtube.com/watch?v=" + list(list_of_titles_by_id.keys())[i - 1]
                elif -len(list_of_titles_by_id) <= i < 0:
                    url = "https://www.youtube.com/watch?v=" + list(list_of_titles_by_id.keys())[i]
                    i = len(list_of_titles_by_id) - (abs(i) - 1)
                else:
                    return await message.channel.send(f"Index must be between 1 and {len(list_of_titles_by_id)}")
                await message.channel.send(f"Playing song number {i} from {len(list_of_titles_by_id)} songs")
                await self.play_song(message, url, True)


client = MyClient()
client.run(token)
