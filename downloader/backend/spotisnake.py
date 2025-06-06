from concurrent.futures import ThreadPoolExecutor
import yt_dlp
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, ID3NoHeaderError, TIT2, TPE1, TPE2, TALB, TDRC, APIC, TRCK, SYLT, USLT
import asyncio
import requests
import os
from downloader.backend.spotify_api import SpotifyTrack, Spotify
from dotenv import load_dotenv
from collections.abc import Callable
import shutil
from pathlib import Path

env_path = Path("/home/spotsnake.helioho.st") / ".env"
load_dotenv(dotenv_path=env_path)
spotify = Spotify(os.getenv("SPOTIFY_CLIENT"), os.getenv("SPOTIFY_SECRET"))
output_dir = Path("/home/spotsnake.helioho.st") / "output"

def create_archive_id(urls: str):
    urls = urls.replace(' ', '')
    urls = urls.split('\n')

    url: str = urls[0]
    url = url.replace('https://open.spotify.com/', '')
    url = url.replace('album/', '')
    url = url.replace('track/', '')
    url = url.replace('artist/', '')
    url = url.replace('?', '')
    url = url.replace('=', '')

    return url

def sanitize(text: str):
    
    text = text.lower()
    
    illegal_chars = ['*', '"', '/', '\\', '<', '>', ':', '|', '?', '.']
    for char in illegal_chars:
        text = text.replace(char, '')
        
    return text

def download_track(track: SpotifyTrack, index: list[int]):
    
    output_dir_ = os.path.join(output_dir, sanitize(track.album.name))
    final_output = f'{os.path.join(output_dir_, sanitize(track.name))}'
    
    # Check if the directory exists
    if not os.path.exists(output_dir):
        # Create the directory
        os.makedirs(output_dir)
        
    ydl_opts = {
        'format': 'bestaudio/best',
        'extractaudio': True,  # Download only audio
        'audioformat': 'mp3',  # Convert to mp3
        'audioquality': '0',   # Best quality
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '0',  # Best quality
        }],
        'outtmpl': final_output,
        'quiet': True
    }
    
    # Download the audio
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download(f'ytsearch:{track.isrc}')
        
    if not os.path.exists(final_output + '.mp3'):
        ydl.download(f'ytsearch:{track.name} by {track.artists[0]}')
        
    if not os.path.exists(final_output + '.mp3'):
        return
        
    apply_metadata(track, final_output, index)
        
def apply_metadata(track: SpotifyTrack, output: str, index: list[int]):
    
    try:
        
        image = requests.get(track.album.image, stream=True)
        
        # Add metadata using mutagen
        audio = MP3(f'{output}.mp3', ID3=ID3)
        
        # Set metadata
        audio.tags.add(TIT2(encoding=3, text=track.name))  # Title
        audio.tags.add(TPE1(encoding=3, text=track.artists))  # Artist
        audio.tags.add(TPE2(encoding=3, text=track.album.artists))
        audio.tags.add(TALB(encoding=3, text=track.album.name))  # Album
        audio.tags.add(TDRC(encoding=3, text=track.album.release))  # Release date
        audio.tags.add(TRCK(encoding=3, text=str(track.track_number)))
        
        audio.tags.add(
            APIC(
                encoding=3, # 3 is for utf-8
                mime='image/png', # image/jpeg or image/png
                type=3, # 3 is for the cover image
                desc=u'Cover',
                data=image.content
            )
        )
        
        audio.save()  # Save the changes
        
        return True
        
    except Exception as e:
        return False
    
async def download_tracks_threaded(url: str):

    url_id = create_archive_id(url)
    url = url.replace(' ', '')
    url = url.split('\n')
    
    spotify_tracks = await spotify.fetch(url)

    track_name = spotify_tracks[0].name

    # Use ThreadPoolExecutor to download tracks concurrently
    with ThreadPoolExecutor() as executor:
        # Create a list of futures for each track download
        futures = []
        
        i = 1
        
        for track in spotify_tracks:
            futures.append(executor.submit(download_track, track, [i, len(spotify_tracks)]))
            i += 1
        
        # Wait for all futures to complete
        for future in futures:
            try:
                future.result()  # This will raise an exception if the download failed
            except Exception as e:
                pass

    shutil.make_archive(url_id, 'zip', output_dir)
    shutil.rmtree(output_dir)

async def apply_metadata_to_tracks(url: str):
    spotify_tracks = await spotify.fetch(url)
    
    print('Successfully got tracks. Adding metadata...')
    
    i = 1
    
    for track in spotify_tracks:
        output_dir_ = os.path.join(output_dir, sanitize(track.album.name))
        final_output = f'{os.path.join(output_dir_, sanitize(track.name))}'
        
        result = apply_metadata(track, final_output, [i, len(spotify_tracks)])
        
        if result:
            input(f'Successfully applied metadata to {track.name} ({i}/{len(spotify_tracks)})\n\nPress enter to exit.')
        
        i += 1

if __name__ == '__main__':
    asyncio.run(download_tracks_threaded('https://open.spotify.com/track/795xwo6zlNZ8xgJdfFqVAz?si=254de2345f864e39', lambda status : print(status)))