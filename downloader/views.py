import os
from django.http import FileResponse, HttpResponse
from django.shortcuts import render
from .backend.spotisnake import download_tracks_threaded, create_archive_id, output_dir
import asyncio

from .forms import URLInputForm

def index(request):

    download_status = ''

    # if this is a POST request we need to process the form data
    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        form = URLInputForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            url = form.data['url']

            url_id = create_archive_id(url)

            asyncio.run(download_tracks_threaded(url))

            download_status = f'Downloaded {url}'

            try:
                return FileResponse(
                    open(f'{url_id}.zip', 'rb'),
                    filename='spotify_tracks',
                    as_attachment=True,
                    content_type='application/zip'
                )
            finally:
                os.remove(f'{url_id}.zip')
        

    # if a GET (or any other method) we'll create a blank form
    else:
        form = URLInputForm()


    return render(request, "downloader/index.html", {
        'form': form,
        'download_status': download_status
    })
    