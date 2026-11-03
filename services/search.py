import functools
import re
import requests
import yt_dlp

from ytmusicapi import YTMusic

from config import YOUTUBE_PROXY, SEARCH_LIMIT, logger


# --- Сессия для ytmusicapi ---
def _build_ytmusic() -> YTMusic:
    session = requests.Session()
    if YOUTUBE_PROXY:
        session.proxies = {"http": YOUTUBE_PROXY, "https": YOUTUBE_PROXY}
    session.request = functools.partial(session.request, timeout=60)
    return YTMusic(
        requests_session=session,
        location="US"
    )


_yt = _build_ytmusic()


def search_tracks(query: str) -> list[dict]:
    """
    Ищет треки в YouTube Music и сортирует их по релевантности к запросу.
    """
    try:
        results = _yt.search(
            query, 
            filter="songs", 
            limit=20,
            ignore_spelling=True
        )
    except Exception as e:
        logger.error(f"Ошибка YouTube Music API (поиск по песням): {e}")
        results = []

    if not results:
        try:
            raw = _yt.search(query, limit=20, ignore_spelling=True)
            results = [r for r in raw if r.get("videoId")]
        except Exception as e:
            logger.error(f"Ошибка YouTube Music API (общий поиск): {e}")
            results = []

    normalized = [_normalize(t) for t in results if t.get("videoId")]

    # Сортировка по релевантности
    query_words = set(re.findall(r'\w+', query.lower()))
    
    def relevance_score(track: dict) -> int:
        text = f"{track.get('title') or ''} {track.get('artists') or ''}".lower()
        track_words = set(re.findall(r'\w+', text))
        return len(query_words & track_words)

    normalized.sort(key=relevance_score, reverse=True)

    return normalized[:SEARCH_LIMIT]


def search_youtube_regular(query: str) -> list[dict]:
    """
    Ищет треки на обычном YouTube через yt-dlp (ytsearch).
    Используется как запасной вариант, если в YouTube Music ничего нет.
    """
    ydl_opts = {
        "proxy": YOUTUBE_PROXY,
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "socket_timeout": 20,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(f"ytsearch15:{query}", download=False)
            
            tracks = []
            if result and result.get("entries"):
                for entry in result["entries"]:
                    if not entry.get("id"):
                        continue
                        
                    tracks.append({
                        "title": entry.get("title"),
                        "artists": entry.get("channel") or entry.get("uploader"),
                        "video_id": entry.get("id"),
                    })
            return tracks[:SEARCH_LIMIT]
    except Exception as e:
        logger.warning(f"Ошибка поиска на обычном YouTube: {e}")
        return []


def _normalize(track: dict) -> dict:
    artists_list = track.get("artists") or []
    artists = ", ".join(a["name"] for a in artists_list) if artists_list else None
    return {
        "title": track.get("title"),
        "artists": artists,
        "video_id": track["videoId"],
    }