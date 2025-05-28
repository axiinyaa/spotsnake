from typing import Dict, Union
import aiohttp
import requests
from dataclasses import dataclass
    
@dataclass
class SpotifyAlbum:
    
    name: str
    artists: list[str]
    image: str
    release: str

@dataclass
class SpotifyTrack:
    
    name: str
    artists: str
    album: SpotifyAlbum
    isrc: str
    track_number: int

class Spotify:
    
    def fetch_lyrics(self, track_id):
        url = f'https://beautiful-lyrics.socalifornian.live/lyrics/{track_id}'
        headers = {
            'authorization': 'Bearer litterallyAnythingCanGoHereItJustTakesItLOL'
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200 and response.headers.get('content-length') != '0':
            try:
                data = response.json()
            except:
                return {'Lyrics': [], 'Type': 'None'}

            lyrics = []
            
            if data['Type'] == 'Static':
                for item in data['Lines']:
                    lyrics.append(item['Text'])
                return {'Lyrics': lyrics, 'Type': 'Static'}
            
            if data['Type'] == 'Line':
                for item in data['Content']:
                    if item['Type'] == 'Vocal':
                        line = item['Text']
                        line = (line.strip(), int(item['StartTime'] * 1000))
                        lyrics.append(line)
                return {'Lyrics': lyrics, 'Type': 'Dynamic'}
            
            if data['Type'] == 'Syllable':
                for item in data['Content']:
                    line = ''
                    
                    for word in item['Lead']['Syllables']:
                        if word['IsPartOfWord']:
                            line += word['Text']
                        else:
                            line += word['Text'] + ' '
                    
                    line = (line.strip(), int(item['Lead']['StartTime'] * 1000))
                    lyrics.append(line)
                return {'Lyrics': lyrics, 'Type': 'Dynamic'}
            
        return {'Lyrics': [], 'Type': 'None'}
    
    async def create_track(self, data: dict):

        album_data = data['album']
        artists = [artist['name'] for artist in album_data['artists']]
        album = SpotifyAlbum(
            name=album_data['name'],
            release=album_data['release_date'],
            artists=artists,
            image=album_data['images'][0]['url']
        )
        
        artist = ''
        
        if 'artist' in data:
            artist = data['artist']
        else:
            artist = [artist['name'] for artist in data['artists']]
        
        print(f'Successfully got {data["name"]} from Spotify.')
        
        return SpotifyTrack(
            artists = artist,
            isrc=data['external_ids']['isrc'],
            name=data["name"],
            album=album,
            track_number=data['track_number']
        )
    
    def __init__(self, client_id, secret):
        self.client_id = client_id
        self.secret = secret

    async def get_access_token(self):
        auth_url = "https://accounts.spotify.com/api/token"

        # Your client_id and secret
        client_id = self.client_id
        secret = self.secret

        # Define the headers for the token request
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        # Define the data for the token request
        data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': secret,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(auth_url, headers=headers, data=data) as resp:
                response_data = await resp.json()
                # The access token is in response_data['access_token']
                return response_data['access_token']

    async def get_track(self, query):
        access_token = await self.get_access_token()
        headers = {'Authorization': f'Bearer {access_token}'}

        if 'open.spotify.com/track/' in query:

            query = query.replace('https://open.spotify.com/track/', '')
            query = query.replace('http://open.spotify.com/track/', '')

            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.spotify.com/v1/tracks/{query}/", headers=headers) as resp:
                    data = await resp.json()
                    return await self.create_track(data)
        else:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.spotify.com/v1/search?q={query}&type=track&limit=1",
                                       headers=headers) as resp:
                    data = await resp.json()
                    track = data['tracks']['items'][0]
                    return await self.create_track(track)

    async def get_playlist(self, url):
        access_token = await self.get_access_token()
        headers = {'Authorization': f'Bearer {access_token}'}

        if 'open.spotify.com/playlist/' in url:
            url = url.replace('https://open.spotify.com/playlist/', '')
            url = url.replace('http://open.spotify.com/playlist/', '')
            async with aiohttp.ClientSession() as session:

                url = f"https://api.spotify.com/v1/playlists/{url}"
                tracks = []

                while True:

                    async with session.get(url, headers=headers) as resp:

                        try:
                            data = await resp.json()
                        except:
                            return None

                        try:
                            get_items = data['tracks']
                        except:
                            get_items = data

                        for item in get_items['items']:
                            track = await self.create_track(item['track'])

                            tracks.append(track)

                        url = get_items['next']

                        if url is None:
                            break

                return tracks
        else:
            async with aiohttp.ClientSession() as session:
                url = url.replace('https://open.spotify.com/album/', '')
                url = url.replace('http://open.spotify.com/album/', '')
                async with session.get(f"https://api.spotify.com/v1/albums/{url}", headers=headers) as resp:
                    data = await resp.json()

                    tracks = []

                    for item in data['tracks']['items']:
                        
                        track = await self.get_track(f'https://open.spotify.com/track/{item["id"]}')

                        tracks.append(track)

                    return tracks

                tracks = []
                
    async def get_artist(self, url: str):
        access_token = await self.get_access_token()
        headers = {'Authorization': f'Bearer {access_token}'}
        
        tracks = []
        offset = 0
        
        async with aiohttp.ClientSession() as session:
            url = url.replace('https://open.spotify.com/artist/', '')
            url = url.replace('http://open.spotify.com/artist/', '')
            
            while True:
                
                api_url = f"https://api.spotify.com/v1/artists/{url}/albums?limit=50&offset={offset}"
                
                async with session.get(api_url, headers=headers) as resp:
                    
                    data = await resp.json()
                    
                    if '?si=' in api_url:
                        url = data['id']
                        continue

                    for album_data in data['items']:
                        
                        artist = ''
                        
                        for a in album_data['artists']:
                            if a['id'] == url:
                                artist = a['id']
                        
                        if artist == '':
                            break
                        
                        fetched_tracks = await self.get_playlist(album_data['external_urls']['spotify'])
                        
                        tracks.extend(fetched_tracks)
                        
                offset += 49
                
                if data['total'] < offset:
                    break
            
        return tracks
                
    async def fetch(self, url_list: list[str]) -> list[SpotifyTrack]:
        
        track_list = []
        
        for url in url_list:
            
            if url == '':
                continue
            
            if 'open.spotify.com/playlist/' in url:
                track_list += await self.get_playlist(url)
                continue
                            
            if 'liked' in url:
                track_list += await self.get_liked_tracks()
                continue
            
            if 'open.spotify.com/album/' in url:
                track_list += await self.get_playlist(url)
                continue    
                    
            if 'open.spotify.com/track/' in url:
                track_list += [await self.get_track(url)]
                continue     
                   
            if 'open.spotify.com/artist/' in url:
                track_list += await self.get_artist(url)
                continue
                        
            track_list += [await self.search(url, 1)]
            
        return track_list

    async def search(self, query, limit=25, type='track'):
        access_token = await self.get_access_token()
        headers = {'Authorization': f'Bearer {access_token}'}

        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.spotify.com/v1/search?q={query}&type={type}&limit={limit}",
                                   headers=headers) as resp:

                try:
                    data = await resp.json()
                except:
                    return 'error'

                return data
