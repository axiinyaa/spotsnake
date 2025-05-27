from concurrent.futures import ThreadPoolExecutor
import yt_dlp
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, ID3NoHeaderError, TIT2, TPE1, TPE2, TALB, TDRC, APIC, TRCK, SYLT, USLT
import asyncio
import requests
import os
from spotify_api import SpotifyTrack, Spotify

spotify = Spotify('039021074dc24c1fb46044b619e86702', 'acdff62d36f94e05ab19f32f89e600a3')
    
def sanitize(text: str):
    
    text = text.lower()
    
    illegal_chars = ['*', '"', '/', '\\', '<', '>', ':', '|', '?', '.']
    for char in illegal_chars:
        text = text.replace(char, '')
        
    return text

def download_track(track: SpotifyTrack, index: list[int]):
    
    output_dir_ = os.path.join(output_dir, sanitize(track.album.name))
    final_output = f'{os.path.join(output_dir_, sanitize(track.name))}'
    
    if os.path.exists(final_output + '.mp3'):
        print(f'song already exists, skipping. ({index[0]}/{index[1]})')
        return
    
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
        return print(f'Unable to download {track.name}... unfortunate...')
        
    apply_metadata(track, final_output, index)
    
    print(f"Successfully added {track.name}! ({index[0]}/{index[1]})")
        
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
        print(f"Failed to add metadata to {track.name} {e} ({index[0]}/{index[1]})")
        
        return False
    
async def download_tracks_threaded(url: str):
    
    url += ','
    url = url.replace(' ', '')
    url = url.split(',')
    
    spotify_tracks = await spotify.fetch(url)
    
    print('Successfully got tracks. Downloading will take a while.')
    
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
                print(f"An error occurred while downloading a track: {e}")
                
    input('Finished downloading all tracks possible!\n\n Press enter to exit.')

async def download_tracks(url: str):
    
    url += ','
    url = url.replace(' ', '')
    url = url.split(',')
    
    spotify_tracks = await spotify.fetch(url)
    
    print('Successfully got tracks. Downloading will take a while.')
    
    i = 1
        
    for track in spotify_tracks:
        download_track(track, [i, len(spotify_tracks)])
        i += 1
        
    input('Finished downloading all tracks possible!\n\n Press enter to exit.')
        
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

print('Welcome to SpotiMP3')

# Get user options
option = input('\n\nOptions:\n1 - Download tracks one at a time.\n2 - Download tracks using threading. (Uses a lot of resources)\n3 - Append metadata to existing tracks.\nInput: ')

# Get output directory input
output_dir = input('\n\nInput the location of output files and folders (Creates folders if necessary.)\nInput: ')

# Get the Spotify link
url = input('\n\nFinally, your Spotify link(s) (Seperate with commas):\nInput: ')

# Print the output directory for verification
print(f'\n\nStarting Process in: {output_dir}')

if option == '1':
    asyncio.run(download_tracks(url))
elif option == '2':
    asyncio.run(download_tracks_threaded(url))
elif option == '3':
    asyncio.run(apply_metadata_to_tracks(url))
else:
    input('Invalid option. Press enter to exit.')