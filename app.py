from BiliUser import CookieKeepAlive


if __name__ == '__main__':
    cookie = CookieKeepAlive()
    cookie.start()
    try:
        # Wait for thread to complete, but allow KeyboardInterrupt
        while cookie.is_alive():
            cookie.join(timeout=1)
    except KeyboardInterrupt:
        print("\nMain thread caught Ctrl+C! Exiting gracefully...")
