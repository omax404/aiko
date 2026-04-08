

import webview
import sys

def start_office():
    url = "http://127.0.0.1:19000"
    window = webview.create_window(
        'Aiko Mission Control',
        url=url,
        width=1000,
        height=700,
        min_size=(800, 600),
        text_select=False,
        background_color='#0F172A'
    )
    webview.start()

if __name__ == "__main__":
    start_office()
