import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from collections import defaultdict

# Scopes define the level of access
SCOPES = ["https://www.googleapis.com/auth/youtube"]

def get_all_playlists(youtube):
    """Retrieve all playlists from the user's YouTube account."""
    playlists = []
    request = youtube.playlists().list(
        part="snippet,contentDetails",
        mine=True,
        maxResults=50
    )

    while request:
        response = request.execute()
        for playlist in response['items']:
            playlists.append({
                'title': playlist['snippet']['title'],
                'id': playlist['id'],
                'video_count': playlist['contentDetails']['itemCount']
            })
        request = youtube.playlists().list_next(request, response)
    
    return playlists

def get_videos_from_playlist(youtube, playlist_id):
    """Retrieve all video IDs from a given playlist."""
    videos = []
    request = youtube.playlistItems().list(
        part="snippet",
        playlistId=playlist_id,
        maxResults=50
    )
    
    while request:
        response = request.execute()
        for item in response['items']:
            videos.append({
                'video_id': item['snippet']['resourceId']['videoId'],
                'channel_title': item['snippet']['videoOwnerChannelTitle']
            })
        request = youtube.playlistItems().list_next(request, response)
    
    return videos

def create_playlist(youtube, title, description):
    """Create a new playlist."""
    request = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description
            },
            "status": {
                "privacyStatus": "private"  # You can set it to "public" or "unlisted"
            }
        }
    )
    response = request.execute()
    return response['id']

def add_video_to_playlist(youtube, playlist_id, video_id):
    """Add a single video to a playlist."""
    request = youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id
                }
            }
        }
    )
    request.execute()

def merge_playlists(youtube, source_playlists, destination_playlist_title):
    """Merge multiple playlists into a new one."""
    # Create a new playlist
    new_playlist_id = create_playlist(youtube, destination_playlist_title, "Merged playlist")
    
    for playlist_id in source_playlists:
        video_ids = get_videos_from_playlist(youtube, playlist_id)
        for video in video_ids:
            add_video_to_playlist(youtube, new_playlist_id, video['video_id'])
    
    print(f"Successfully merged playlists into {destination_playlist_title} (ID: {new_playlist_id})")

def create_playlists_by_creator(youtube, playlist_id):
    """Create new playlists based on the creator of videos in a given playlist."""
    # Get videos grouped by creator
    videos_by_creator = defaultdict(list)
    videos = get_videos_from_playlist(youtube, playlist_id)
    for video in videos:
        videos_by_creator[video['channel_title']].append(video['video_id'])
    
    for creator, video_ids in videos_by_creator.items():
        # Create a new playlist for each creator
        new_playlist_id = create_playlist(youtube, f"{creator}'s Playlist", f"Videos from {creator}")
        
        # Add videos to the new playlist
        for video_id in video_ids:
            add_video_to_playlist(youtube, new_playlist_id, video_id)
        
        print(f"Created playlist for {creator} with {len(video_ids)} videos.")

def select_playlists(playlists):
    """Allow the user to select which playlists to merge."""
    print("Available Playlists:")
    for index, playlist in enumerate(playlists):
        print(f"{index + 1}. {playlist['title']} ({playlist['video_count']} videos)")

    selected_indices = input("Enter the numbers of the playlists you want to merge, separated by commas: ")
    selected_indices = [int(x.strip()) - 1 for x in selected_indices.split(',')]
    
    selected_playlists = [playlists[i]['id'] for i in selected_indices]
    return selected_playlists

def main():
    # Disable OAuthlib's HTTPS verification when running locally.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    # Set up the OAuth 2.0 flow using client secrets file
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        "client_secret.json", SCOPES)
    
    # Run the local server for OAuth 2.0 authentication
    credentials = flow.run_local_server(port=8081)

    # Build the YouTube API client
    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=credentials)

    # Fetch all playlists
    playlists = get_all_playlists(youtube)

    # Ask the user for the action they want to perform
    print("Select an action:")
    print("1. Merge selected playlists")
    print("2. Create new playlists based on video creators from a selected playlist")
    action = input("Enter 1 or 2: ")

    if action == "1":
        # Let the user select playlists to merge
        selected_playlists = select_playlists(playlists)
        # Let the user specify the title for the new playlist
        destination_playlist_title = input("Enter the title for the new merged playlist: ")
        # Merge the selected playlists
        merge_playlists(youtube, selected_playlists, destination_playlist_title)
    elif action == "2":
        # Let the user select a single playlist to process
        selected_playlist = select_playlists(playlists)[0]
        # Create new playlists based on video creators
        create_playlists_by_creator(youtube, selected_playlist)
    else:
        print("Invalid action selected.")

if __name__ == "__main__":
    main()
