import sys
import xbmc
import xbmcgui
import xbmcplugin
import requests
import urllib
import urlparse
from HTMLParser import HTMLParser

ADDON_NAME = "Newgrounds Audio"
BASE_URL = "https://www.newgrounds.com/audio/"

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
        track_id = content[start:end]
        track_url = "https://www.newgrounds.com/audio/listen/" + track_id

        # Find track title and artist name from the <div class="detail-title"> section
        title_start = content.find('<div class="detail-title">', end)
        if title_start != -1:
            title_start = content.find('<h4>', title_start) + len('<h4>')
            title_end = content.find('</h4>', title_start)
            track_title = h.unescape(content[title_start:title_end])

            artist_start = content.find('<strong>', title_end) + len('<strong>')
            artist_end = content.find('</strong>', artist_start)
            artist_name = h.unescape(content[artist_start:artist_end])

            # Ensure both artist_name and track_title are properly handled as Unicode
            try:
                # Decode the artist and track title to unicode and then encode them to UTF-8
                track_title_unicode = track_title.decode('utf-8') if isinstance(track_title, str) else track_title
                artist_name_unicode = artist_name.decode('utf-8') if isinstance(artist_name, str) else artist_name
                
                # Combine the artist and track names as Unicode strings
                display_name = u"{} - {}".format(artist_name_unicode, track_title_unicode)

                # Log the combined name safely (encode to UTF-8 for logging)
                xbmc.log(u"Track: {} by Artist: {}".format(track_title_unicode, artist_name_unicode).encode('utf-8'))

            except UnicodeDecodeError as e:
                xbmc.log("Unicode error: %s" % str(e))
                display_name = u"<non-ASCII track>"

            # Find track thumbnail
            thumbnail_start = content.find('<div class="item-icon">', title_end)
            if thumbnail_start == -1:
                thumbnail_url = None  # No thumbnail found
            else:
                thumbnail_start = content.find('<img src="', thumbnail_start)
                thumbnail_start += len('<img src="')
                thumbnail_end = content.find('"', thumbnail_start)
                thumbnail_url = content[thumbnail_start:thumbnail_end]

            tracks.append({"title": display_name, "url": track_url, "thumbnail": thumbnail_url})

    if not tracks:
        xbmcgui.Dialog().ok(ADDON_NAME, "No tracks found.")
    
    return tracks


def list_tracks(url):
    """List tracks from a given URL with thumbnails."""
    tracks = fetch_tracks(url)
    if not tracks:
        return
    
    for track in tracks:
        list_item = xbmcgui.ListItem(label=track["title"])
        list_item.setInfo('music', {'title': track["title"]})
        
        # Set the thumbnail if available (compatible with older Kodi versions)
        if track["thumbnail"]:
            list_item.setThumbnailImage(track["thumbnail"])

        # Format the URL to pass the track URL
        query = urllib.urlencode({'url': track['url']})
        url_with_query = "{0}?{1}".format(sys.argv[0], query)

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
    xbmc.log("Extracted Audio URL: %s" % audio_url)
    return audio_url

def play_audio(url):
    """Play the selected audio URL."""
    audio_url = fetch_audio_url(url)
    if audio_url:
        xbmc.log("Attempting to play: %s" % audio_url)

        # Create a ListItem to pass to the player
        li = xbmcgui.ListItem(path=audio_url)
        li.setProperty("IsPlayable", "true")

        # Play the audio file using the ListItem
        xbmc.Player().play(audio_url, li)

def main_menu():
    """Show the main menu with Featured and Search options."""
    # Add Featured button
    list_item = xbmcgui.ListItem(label="Featured")
    url = "{0}?action=featured".format(sys.argv[0])
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=list_item, isFolder=True)

    list_item = xbmcgui.ListItem(label="Latest")
    url = "{0}?action=latest".format(sys.argv[0])
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=list_item, isFolder=True)

    list_item = xbmcgui.ListItem(label="Popular")
    url = "{0}?action=popular".format(sys.argv[0])
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=list_item, isFolder=True)

    # Add Search button
    list_item = xbmcgui.ListItem(label="Search")
    url = "{0}?action=search".format(sys.argv[0])
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=list_item, isFolder=True)

    xbmcplugin.endOfDirectory(addon_handle)

def search_tracks():
    """Prompt the user for a search term and list the results."""
    keyboard = xbmc.Keyboard('', 'Enter search term')
    keyboard.doModal()

    if keyboard.isConfirmed():
        search_term = keyboard.getText()
        search_url = "https://www.newgrounds.com/search/conduct/audio?suitabilities=etm&c=3&terms=" + urllib.quote(search_term)
        list_tracks(search_url)
    else:
        xbmcgui.Dialog().ok(ADDON_NAME, "Search cancelled.")

# Initialize the addon handle (required for XBMC plugin)
addon_handle = int(sys.argv[1])

# Get the query string from the URL
parsed_url = urlparse.urlparse(sys.argv[2])
params = urlparse.parse_qs(parsed_url.query)

if 'action' in params:
    action = params['action'][0]
    if action == 'featured':
        list_tracks("https://www.newgrounds.com/audio/featured")
    if action == 'latest':
        list_tracks("https://www.newgrounds.com/audio/browse")
    if action == 'popular':
        list_tracks("https://www.newgrounds.com/audio/popular")
    elif action == 'search':
        search_tracks()
elif 'url' in params:
    play_audio(params['url'][0])
else:
    main_menu()
