import sys
import re
import json
import requests
from flask import Flask, request, render_template, jsonify, redirect, url_for

app = Flask(__name__)

@app.route('/')
def index():
    query = request.args.get('k', '')
    page = request.args.get('p', '1')
    
    if query:
        url = f'https://www.xvideos.com/?k={query}&p={page}'
    else:
        best_url = 'https://www.xvideos.com/best'
        response = requests.get(best_url)
        redirected_url = response.url
        if page != '1':
            redirected_url = redirected_url.rstrip('/') + f'/{page}'
        url = redirected_url

    try:
        response = requests.get(url)
        if response.status_code == 200:
            videos = extract_best_videos(response.text)
            next_page_url = url_for('index', k=query, p=int(page) + 1)
            next_page_url = next_page_url.replace('&amp;', '&')
            return render_template('index.html', best_videos=videos, query=query, next_page_url=next_page_url)
        else:
            return render_template('index.html', best_videos=[], query=query)
    except requests.exceptions.RequestException as e:
        return render_template('index.html', best_videos=[], error=str(e), query=query)

def extract_best_videos(html):
    video_pattern = re.compile(r'<div class="thumb"><a href="([^"]+)".*?data-src="([^"]+)"')
    videos = video_pattern.findall(html)
    
    best_videos = []
    for href, img in videos:
        img = img.replace("thumbs169/", "thumbs169lll/")
        img = img.replace("thumbs169l/", "thumbs169lll/")
        img = img.replace("thumbs169ll/", "thumbs169lll/")
        img = img.replace("THUMBNUM", "7")
        best_videos.append({'href': f"https://www.xvideos.com{href}", 'image': img})
    
    return best_videos

@app.route('/process', methods=['POST'])
def process_video():
    data = request.get_json()
    video_url = data.get('video_url')
    logs = []

    if not video_url:
        return jsonify({'error': 'No video URL provided'}), 400

    try:
        response = requests.get(video_url)
        logs.append("Fetched the video URL.")

        match = re.search(r'(https?://[^\s]+\.m3u8)', response.text)
        if match:
            video_url = match.group(1)
            logs.append("Extracted .m3u8 URL.")
        else:
            logs.append("Failed to extract .m3u8 URL.")
            return jsonify({'error': 'Failed to extract .m3u8 URL.', 'logs': logs}), 400

        match = re.search(r'var video_related=(\[[^\]]+\])', response.text)
        hrefs, image_links = [], []
        if match:
            video_related_data = json.loads(match.group(1))
            for video in video_related_data:
                href = video.get("u", "")
                image_link = video.get("il", "")
                if href:
                    hrefs.append(f"https://www.xvideos.com{href}")
                if image_link:
                    image_link = image_link.replace("thumbs169/", "thumbs169lll/")
                    image_link = image_link.replace("thumbs169l/", "thumbs169lll/")
                    image_link = image_link.replace("thumbs169ll/", "thumbs169lll/")
                    image_link = image_link.replace("THUMBNUM", "7")
                    image_links.append(image_link)
            logs.append("Extracted related videos.")
        else:
            logs.append("Failed to extract related videos.")
            return jsonify({'error': 'Failed to extract related videos.', 'logs': logs}), 400

        return jsonify({
            'video_url': video_url,
            'hrefs': hrefs,
            'image_links': image_links,
            'logs': logs[-3:] if len(logs) >= 3 else logs
        })
    except requests.exceptions.RequestException as e:
        logs.append(f"RequestException: {str(e)}")
        return jsonify({'error': str(e), 'logs': logs}), 500

@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('query')
    if re.match(r'https?://', query):
        return redirect(url_for('process_video', video_url=query))
    else:
        return redirect(url_for('index', k=query.replace(' ', '+')))

if __name__ == '__main__':
    app.run(debug=True)
