import re
import os
import zipfile
from io import BytesIO
from django.core.cache import cache
from django.http import HttpResponseBadRequest, HttpResponse, Http404
from django.shortcuts import render
from urllib.parse import unquote, urlparse
import requests
import logging

# Set up logging
logger = logging.getLogger(__name__)

def file_list(request):
    public_key = request.GET.get('public_key', '')
    filter_type = request.GET.get('filter_type', '')
    cache_key = f"file_list_{public_key}_{filter_type}"
    files = cache.get(cache_key)

    if not files:
        files = []
        if public_key:
            url = f"https://cloud-api.yandex.net/v1/disk/public/resources?public_key={public_key}"
            try:
                response = requests.get(url)
                response.raise_for_status()  # Ensure we catch HTTP errors
                data = response.json()
                files = data.get('_embedded', {}).get('items', [])

                if filter_type:
                    files = [file for file in files if filter_type in file['mime_type']]

                cache.set(cache_key, files, timeout=60*15)  # Cache for 15 minutes
            except requests.RequestException as e:
                logger.error(f"Error fetching file list: {e}")
                return HttpResponseBadRequest(f"Error fetching file list: {e}")

    return render(request, 'diskviewer/file_list.html', {'files': files, 'filter_type': filter_type})

def download_file(request, file_url):
    file_url = unquote(file_url)  # Decode URL if needed
    try:
        response = requests.get(file_url)
        response.raise_for_status()
    except requests.RequestException as e:
        raise Http404("File not found")

    # Extract MIME type and filename from the response
    content_type = response.headers.get('Content-Type', 'application/octet-stream')
    content_disposition = response.headers.get('Content-Disposition', '')

    # Extract filename from Content-Disposition
    match = re.search(r'filename=["\'](.+?)["\']', content_disposition)
    if match:
        file_name = match.group(1)
    else:
        # Fallback to URL if filename is not present in headers
        file_name = file_url.split("/")[-1]
        # Remove URL parameters
        file_name = file_name.split('?')[0]

    # Ensure filename is URL-safe
    file_name = file_name.encode('ascii', 'ignore').decode('ascii')

    # Prepare response
    response = HttpResponse(response.content, content_type=content_type)
    response['Content-Disposition'] = f'{file_name}'

    return response

def download_selected_files(request):
    selected_files = request.POST.getlist('selected_files')
    if not selected_files:
        return HttpResponseBadRequest("No files selected")

    # Create ZIP archive in memory
    s = BytesIO()
    with zipfile.ZipFile(s, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_url in selected_files:
            file_url = unquote(file_url)  # Decode URL if needed
            try:
                response = requests.get(file_url)
                response.raise_for_status()

                # Extract filename from Content-Disposition or URL
                content_disposition = response.headers.get('Content-Disposition', '')
                match = re.search(r'filename=["\'](.+?)["\']', content_disposition)
                if match:
                    file_name = match.group(1)
                else:
                    # Fallback to URL if filename is not present in headers
                    file_name = os.path.basename(unquote(urlparse(file_url).path))
                    file_name = file_name.split('?')[0]

                # Ensure filename is URL-safe and handle invalid characters
                file_name = re.sub(r'[<>:"/\\|?*]', '', file_name)
                file_name = file_name.encode('ascii', 'ignore').decode('ascii')

                # Write file to ZIP
                zf.writestr(file_name, response.content)
            except requests.RequestException as e:
                logger.error(f"Error downloading file {file_url}: {e}")
                return HttpResponseBadRequest(f"Error downloading file {file_url}: {e}")

    # Prepare response
    s.seek(0)
    response = HttpResponse(s.getvalue(), content_type="application/zip")
    response['Content-Disposition'] = 'attachment; filename="selected_files.zip"'
    return response
