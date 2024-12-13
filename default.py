# -*- coding: utf-8 -*-
import sys
import xbmc
import xbmcgui
import xbmcplugin
import requests
import urllib
import urlparse
import re
import os
from HTMLParser import HTMLParser

ADDON_NAME = "Newgrounds Audio"
BASE_URL = "https://www.newgrounds.com/audio/"

def clean_html_tags(text):
    """Remove HTML tags from a string."""
    return re.sub(r'<[^>]*>', '', text)

def fetch_tracks(url):
    """Fetch tracks and their thumbnails from a given Newgrounds page."""
    response = requests.get(url)
    if response.status_code != 200:
        xbmcgui.Dialog().ok(ADDON_NAME, "Failed to fetch tracks.")
        return []

    # Parse the HTML content
    h = HTMLParser()
    content = response.text
    tracks = []

    # Search for all the track links and thumbnails in the page
    start = 0
    while True:
        # Find track link
        start = content.find('<a href="https://www.newgrounds.com/audio/listen/', start)
        if start == -1:
            break
        start += len('<a href="https://www.newgrounds.com/audio/listen/')
        end = content.find('"', start)
        if end == -1:
            break  # Prevent infinite loop if '"' not found
        track_id = content[start:end]
        track_url = "https://www.newgrounds.com/audio/listen/" + track_id

        # Find track title and artist name from the <div class="detail-title"> section
        title_start = content.find('<div class="detail-title">', end)
        if title_start != -1:
            title_start = content.find('<h4>', title_start)
            if title_start == -1:
                continue  # Skip if <h4> not found
            title_start += len('<h4>')
            title_end = content.find('</h4>', title_start)
            if title_end == -1:
                continue  # Skip if </h4> not found
            raw_track_title = content[title_start:title_end]
            track_title = h.unescape(clean_html_tags(raw_track_title))  # Clean the <mark> tag and other HTML

            artist_start = content.find('<strong>', title_end)
            if artist_start == -1:
                artist_name = "Unknown Artist"
            else:
                artist_start += len('<strong>')
                artist_end = content.find('</strong>', artist_start)
                if artist_end == -1:
                    artist_name = "Unknown Artist"
                else:
                    raw_artist_name = content[artist_start:artist_end]
                    artist_name = h.unescape(clean_html_tags(raw_artist_name))  # Clean HTML tags from the artist name

            # Ensure both artist_name and track_title are properly handled as Unicode
            try:
                # Decode the artist and track title to unicode and then encode them to UTF-8
                track_title_unicode = track_title.decode('utf-8') if isinstance(track_title, str) else track_title
                artist_name_unicode = artist_name.decode('utf-8') if isinstance(artist_name, str) else artist_name

                # Combine the artist and track names as Unicode strings
                display_name = u"{} - {}".format(artist_name_unicode, track_title_unicode)

                # Log the combined name safely (encode to UTF-8 for logging)
#                xbmc.log(u"Track: {} by Artist: {}".format(track_title_unicode, artist_name_unicode).encode('utf-8'))

            except UnicodeDecodeError as e:
#                xbmc.log("Unicode error: %s" % str(e))
                display_name = u"<non-ASCII track>"

            # Find track thumbnail
            thumbnail_start = content.find('<div class="item-icon">', title_end)
            if thumbnail_start == -1:
                thumbnail_url = None  # No thumbnail found
            else:
                thumbnail_start = content.find('<img src="', thumbnail_start)
                if thumbnail_start == -1:
                    thumbnail_url = None
                else:
                    thumbnail_start += len('<img src="')
                    thumbnail_end = content.find('"', thumbnail_start)
                    if thumbnail_end == -1:
                        thumbnail_url = None
                    else:
                        thumbnail_url = content[thumbnail_start:thumbnail_end]

            tracks.append({
                "title": display_name,
                "url": track_url,
                "thumbnail": thumbnail_url,
                "artist": artist_name_unicode if 'artist_name_unicode' in locals() else "Unknown Artist",
                "track_title": track_title_unicode if 'track_title_unicode' in locals() else "Unknown Title"
            })

    if not tracks:
        xbmcgui.Dialog().ok(ADDON_NAME, "No tracks found.")
    
    return tracks

def download_track(url):
    """Download the selected track with a title and artist-based filename."""
    audio_url = fetch_audio_url(url)
    if not audio_url:
        return

    # Fetch track title and artist name for the filename
    response = requests.get(url)
    if response.status_code != 200:
        xbmcgui.Dialog().ok(ADDON_NAME, "Failed to fetch track details.")
        return

    content = response.text

    # Extract track title and artist name using og:title
    title_start = content.find('<meta property="og:title" content="')
    if title_start == -1:
        track_title = "Unknown Title"
        artist_name = "Unknown Artist"
    else:
        title_start += len('<meta property="og:title" content="')
        title_end = content.find('"', title_start)
        if title_end == -1:
            track_title = "Unknown Title"
            artist_name = "Unknown Artist"
        else:
            og_title_content = content[title_start:title_end]

            # Ensure it's properly decoded to a Unicode string
            if isinstance(og_title_content, bytes):
                og_title_content = og_title_content.decode('utf-8', errors='ignore')
            else:
                og_title_content = str(og_title_content)

            # Attempt to split based on common delimiters
            artist_name = "Unknown Artist"
            track_title = og_title_content.strip()

            # Try splitting by common delimiters
            if " – " in og_title_content:
                artist_name, track_title = og_title_content.split(" – ", 1)
            elif " - " in og_title_content:
                artist_name, track_title = og_title_content.split(" - ", 1)
            elif "(" in og_title_content and ")" in og_title_content:
                artist_name = og_title_content.split("(")[0].strip()
                track_title = og_title_content.split("(")[1].split(")")[0].strip()
            else:
                track_title = og_title_content
                artist_name = "Unknown Artist"

            # Trim extra spaces
            artist_name = artist_name.strip()
            track_title = track_title.strip()

    # Log extracted track title and artist name for debugging
#    xbmc.log("Track Title: {}".format(track_title))
#    xbmc.log("Artist Name: {}".format(artist_name))

    # Attempt to extract artist name from <div class="item-details-main">
    artist_match = re.search(r'<div class="item-details-main">.*?<h4>\s*<a href="[^"]*">(.*?)</a>', content, re.DOTALL)
    
    if artist_match:
        artist_name_from_page = artist_match.group(1).strip()
        if artist_name == "Unknown Artist" and artist_name_from_page:
            # If the artist_name is still unknown, try using the artist name from the page
            artist_name = artist_name_from_page

    # Log the final artist name
#    xbmc.log("Final Artist Name: {}".format(artist_name))

    # Clean the title and artist name to make them filename-safe
    filename_safe_title = re.sub(r'[\\/:*?"<>|]', '', track_title)
    filename_safe_artist = re.sub(r'[\\/:*?"<>|]', '', artist_name)
    final_filename = "{} - {}.mp3".format(filename_safe_artist, filename_safe_title)

    # Create the download directory if it doesn't exist
    download_dir = "F:\Music"  # Use forward slashes or double backslashes
    if not os.path.exists(download_dir):
        try:
            os.makedirs(download_dir)
        except OSError as e:
            xbmcgui.Dialog().ok(ADDON_NAME, "Failed to create download directory: " + str(e))
            return

    filepath = os.path.join(download_dir, final_filename)

    # Download the file
    try:
        response = requests.get(audio_url, stream=True)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            xbmcgui.Dialog().ok("Success!", "Track downloaded to " + filepath)
        else:
            xbmcgui.Dialog().ok("Failure!", "Failed to download track.")
    except Exception as e:
        xbmcgui.Dialog().ok("Failure!", "An error occurred: " + str(e))

def list_tracks(url):
    """List tracks from a given URL with thumbnails and context menu options."""
    tracks = fetch_tracks(url)
    if not tracks:
        return

    for track in tracks:
        list_item = xbmcgui.ListItem(label=track["title"])
        list_item.setInfo('music', {'title': track["track_title"], 'artist': track["artist"]})

        # Set the thumbnail if available (compatible with older Kodi versions)
        if track["thumbnail"]:
            list_item.setThumbnailImage(track["thumbnail"])

        # Format the URL to pass the track URL
        query = urllib.urlencode({'url': track['url']})
        url_with_query = "{0}?{1}".format(sys.argv[0], query)

        # Add context menu items
        context_menu = [
            ('Download Track', 'RunPlugin({0}?action=download&url={1})'.format(sys.argv[0], urllib.quote(track["url"])))
        ]
        list_item.addContextMenuItems(context_menu)

        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url_with_query, listitem=list_item, isFolder=False)

    xbmcplugin.endOfDirectory(addon_handle)

def fetch_audio_url(track_page_url):
    """Fetch the audio URL for a given track page."""
    response = requests.get(track_page_url)
    if response.status_code != 200:
        xbmcgui.Dialog().ok(ADDON_NAME, "Failed to fetch audio URL.")
        return None
    
    content = response.text
    start = content.find('<meta property="og:audio" content="')
    if start == -1:
        xbmcgui.Dialog().ok(ADDON_NAME, "Audio URL not found.")
        return None
    
    start += len('<meta property="og:audio" content="')
    end = content.find('"', start)
    if end == -1:
        xbmcgui.Dialog().ok(ADDON_NAME, "Failed to extract audio URL.")
        return None
    
    audio_url = content[start:end]
#    xbmc.log("Extracted Audio URL: %s" % audio_url)
    return audio_url

def play_audio(url):
    """Play the selected audio URL with proper metadata."""
    audio_url = fetch_audio_url(url)
    if not audio_url:
        return

    # Fetch track title and artist name for metadata
    response = requests.get(url)
    if response.status_code != 200:
        xbmcgui.Dialog().ok(ADDON_NAME, "Failed to fetch track details.")
        return

    content = response.text
    title_start = content.find('<meta property="og:title" content="')
    if title_start == -1:
        track_title = "Unknown Title"
        artist_name = "Unknown Artist"
    else:
        title_start += len('<meta property="og:title" content="')
        title_end = content.find('"', title_start)
        if title_end == -1:
            track_title = "Unknown Title"
            artist_name = "Unknown Artist"
        else:
            og_title_content = content[title_start:title_end]

            # Ensure we're dealing with a Unicode string (decode to UTF-8 if necessary)
            if isinstance(og_title_content, bytes):  # If it's in bytes
                og_title_content = og_title_content.decode('utf-8', errors='ignore')  # Decode it safely
            else:
                og_title_content = str(og_title_content)  # Ensure it's a string if it's not already

            # Log for debugging
#            xbmc.log("og:title content: {}".format(og_title_content))

            # Attempt to split based on common delimiters, prioritize splitting from the end
            artist_name = "Unknown Artist"
            track_title = og_title_content.strip()

            # Try different delimiters to separate artist name and track title
            if " – " in og_title_content:
                # Split based on en dash (with spaces)
                artist_name, track_title = og_title_content.split(" – ", 1)
            elif " - " in og_title_content:
                # Split based on hyphen (with spaces)
                artist_name, track_title = og_title_content.split(" - ", 1)
            elif "(" in og_title_content and ")" in og_title_content:
                # If there are parentheses, assume the artist is outside
                artist_name = og_title_content.split("(")[0].strip()
                track_title = og_title_content.split("(")[1].split(")")[0].strip()
            else:
                # If no delimiter found, consider the entire content as the track title
                track_title = og_title_content
                artist_name = "Unknown Artist"

            # Trim extra spaces
            artist_name = artist_name.strip()
            track_title = track_title.strip()

            # Log for debugging
#            xbmc.log("Track Title: {}".format(track_title))
#            xbmc.log("Artist Name: {}".format(artist_name))

    # Now, attempt to extract artist name from <div class="item-details-main">
    artist_match = re.search(r'<div class="item-details-main">.*?<h4>\s*<a href="[^"]*">(.*?)</a>', content, re.DOTALL)
    
    if artist_match:
        artist_name_from_page = artist_match.group(1).strip()
        if artist_name == "Unknown Artist" and artist_name_from_page:
            # If the artist_name is still unknown, try using the artist name from the page
            artist_name = artist_name_from_page

    # Log the final artist and title
#    xbmc.log("Final Artist Name: {}".format(artist_name))

    # Log the information
#    xbmc.log("Playing: {} by {}".format(track_title, artist_name))

    # Create a ListItem to pass to the player
    li = xbmcgui.ListItem(path=audio_url)
    li.setInfo('music', {'title': track_title, 'artist': artist_name})
    li.setProperty("IsPlayable", "true")

    # Play the audio file using the ListItem
    xbmc.Player().play(audio_url, li)



def main_menu():
    """Show the main menu with Featured and Search options."""
    menu_options = [
        ("Music - Featured", "music-featured"),
        ("Music - Latest", "music-latest"),
        ("Music - Popular", "music-popular"),
        ("Voice - Featured", "voice-featured"),
        ("Voice - Latest", "voice-latest"),
        ("Voice - Popular", "voice-popular"),
        ("Podcasts - Featured", "podcasts-featured"),
        ("Podcasts - Latest", "podcasts-latest"),
        ("Podcasts - Popular", "podcasts-popular"),
        ("Search", "search")
    ]

    for label, action in menu_options:
        list_item = xbmcgui.ListItem(label=label)
        url = "{0}?action={1}".format(sys.argv[0], action)
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=list_item, isFolder=True)

    xbmcplugin.endOfDirectory(addon_handle)

def search_tracks():
    """Prompt the user for a search term and list the results."""
    keyboard = xbmc.Keyboard('', 'Enter search term')
    keyboard.doModal()

    if keyboard.isConfirmed():
        search_term = keyboard.getText()
        if not search_term:
            xbmcgui.Dialog().ok(ADDON_NAME, "Search cancelled.", "No search term entered.")
            return
        search_url = "https://www.newgrounds.com/search/conduct/audio?suitabilities=etm&c=3&terms=" + urllib.quote(search_term)
        list_tracks(search_url)
    else:
        xbmcgui.Dialog().ok(ADDON_NAME, "Search cancelled.")

# Initialize the addon handle (required for XBMC plugin)
addon_handle = int(sys.argv[1])

# Get the query string from the URL
parsed_url = urlparse.urlparse(sys.argv[2])
params = urlparse.parse_qs(parsed_url.query)

# Handle the actions and pagination
if 'action' in params:
    action = params['action'][0]
    if action == 'download' and 'url' in params:
        download_track(params['url'][0])
    elif action == 'music-featured':
        list_tracks("https://www.newgrounds.com/audio/featured?type=1")
    elif action == 'music-latest':
        list_tracks("https://www.newgrounds.com/audio/browse?type=1")
    elif action == 'music-popular':
        list_tracks("https://www.newgrounds.com/audio/popular?type=1")
    elif action == 'voice-featured':
        list_tracks("https://www.newgrounds.com/audio/featured?type=3")
    elif action == 'voice-latest':
        list_tracks("https://www.newgrounds.com/audio/browse?type=3")
    elif action == 'voice-popular':
        list_tracks("https://www.newgrounds.com/audio/popular?type=3")
    elif action == 'podcasts-featured':
        list_tracks("https://www.newgrounds.com/audio/featured?type=4")
    elif action == 'podcasts-latest':
        list_tracks("https://www.newgrounds.com/audio/browse?type=4")
    elif action == 'podcasts-popular':
        list_tracks("https://www.newgrounds.com/audio/popular?type=4")
    elif action == 'search':
        search_tracks()
    else:
        main_menu()
elif 'url' in params:
    play_audio(params['url'][0])
else:
    main_menu()
