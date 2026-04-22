"""
instagram.py
------------
Cliente para la API interna de Instagram.
Autenticación exclusivamente por cookies (sessionid + csrftoken).
Sin Selenium, sin BeautifulSoup.
"""

import requests
import time
from typing import Optional


class RateLimitError(Exception):
    pass

class AuthError(Exception):
    pass


class IGClient:
    _API   = "https://i.instagram.com/api/v1"
    _WEB   = "https://www.instagram.com"
    _APP_ID = "936619743392459"

    def __init__(self, session_id: str, csrf_token: str):
        self.http = requests.Session()
        self.http.cookies.set("sessionid", session_id, domain=".instagram.com")
        self.http.cookies.set("csrftoken", csrf_token, domain=".instagram.com")
        self._headers = {
            "user-agent": (
                "Instagram 269.0.0.18.75 Android "
                "(30/11; 420dpi; 1080x1920; Samsung; SM-G998B; samsung; qcom; es_ES; 382214478)"
            ),
            "x-ig-app-id":       self._APP_ID,
            "x-csrftoken":       csrf_token,
            "x-requested-with":  "XMLHttpRequest",
            "accept-language":   "es-ES,es;q=0.9",
            "accept":            "*/*",
            "origin":            "https://www.instagram.com",
            "referer":           "https://www.instagram.com/",
        }

    # ─── internal ────────────────────────────────────────────────────────────

    def _get(self, url: str, params: dict = None, retries: int = 3) -> dict:
        for attempt in range(retries):
            try:
                r = self.http.get(url, headers=self._headers, params=params, timeout=20)
            except requests.RequestException as exc:
                if attempt == retries - 1:
                    raise
                time.sleep(5 * (attempt + 1))
                continue

            if r.status_code == 401:
                raise AuthError("Cookies inválidas o expiradas")
            if r.status_code == 429:
                wait = 60 * (attempt + 1)
                raise RateLimitError(f"Rate limit. Espera {wait}s antes de reintentar.")
            if r.status_code == 404:
                return {}
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")

            return r.json()
        return {}

    # ─── profile ─────────────────────────────────────────────────────────────

    def resolve_username(self, username: str) -> Optional[str]:
        """Username → user_id numérico."""
        data = self._get(f"{self._API}/users/web_profile_info/", {"username": username})
        return (data.get("data") or {}).get("user", {}).get("id")

    def get_profile(self, user_id: str) -> dict:
        """Información completa de un perfil."""
        data = self._get(f"{self._API}/users/{user_id}/info/")
        u = data.get("user", {})
        if not u:
            return {}

        if u.get("is_business"):
            kind = "Empresa"
        elif u.get("is_creator"):
            kind = "Creador"
        else:
            kind = "Personal"

        username = u.get("username", "")
        return {
            "id":              u.get("pk", user_id),
            "username":        username,
            "full_name":       u.get("full_name", ""),
            "biography":       u.get("biography", "").replace("\n", " "),
            "account_type":    kind,
            "category":        u.get("category", ""),
            "followers":       u.get("follower_count", 0),
            "following":       u.get("following_count", 0),
            "posts":           u.get("media_count", 0),
            "is_verified":     u.get("is_verified", False),
            "is_private":      u.get("is_private", False),
            "external_url":    u.get("external_url", ""),
            "profile_pic_url": u.get("profile_pic_url", ""),
            "profile_url":     f"https://www.instagram.com/{username}/",
        }

    # ─── following / followers ────────────────────────────────────────────────

    def _fetch_friendship_page(self, endpoint: str, user_id: str, max_id: str = None) -> tuple[list, str | None]:
        params = {"count": 50}
        if max_id:
            params["max_id"] = max_id
        data = self._get(f"{self._API}/friendships/{user_id}/{endpoint}/", params)
        users    = data.get("users", [])
        next_id  = data.get("next_max_id")
        big_list = data.get("big_list", False)
        return users, (next_id if next_id or big_list else None)

    def iter_following(self, user_id: str, limit: int = None):
        """Genera dicts básicos de cada cuenta seguida."""
        yield from self._iter_friendship("following", user_id, limit)

    def iter_followers(self, user_id: str, limit: int = None):
        """Genera dicts básicos de cada seguidor."""
        yield from self._iter_friendship("followers", user_id, limit)

    def _iter_friendship(self, endpoint: str, user_id: str, limit: int = None):
        next_id = None
        count   = 0
        while True:
            users, next_id = self._fetch_friendship_page(endpoint, user_id, next_id)
            if not users:
                break
            for u in users:
                if limit and count >= limit:
                    return
                yield {
                    "id":          u.get("pk"),
                    "username":    u.get("username", ""),
                    "full_name":   u.get("full_name", ""),
                    "is_verified": u.get("is_verified", False),
                    "is_private":  u.get("is_private", False),
                    "profile_pic": u.get("profile_pic_url", ""),
                }
                count += 1
            if not next_id:
                break

    # ─── posts ───────────────────────────────────────────────────────────────

    def iter_posts(self, user_id: str, limit: int = 12):
        """Genera métricas de los últimos `limit` posts."""
        next_id = None
        count   = 0
        while count < limit:
            params = {"count": min(12, limit - count)}
            if next_id:
                params["max_id"] = next_id
            data = self._get(f"{self._API}/feed/user/{user_id}/", params)
            items = data.get("items", [])
            if not items:
                break
            for item in items:
                if count >= limit:
                    return
                caption_text = ""
                cap = item.get("caption")
                if cap:
                    caption_text = cap.get("text", "").replace("\n", " ")[:200]

                media_type = {1: "photo", 2: "video", 8: "carousel"}.get(item.get("media_type"), "unknown")

                thumb = ""
                if item.get("image_versions2"):
                    candidates = item["image_versions2"].get("candidates", [])
                    if candidates:
                        thumb = candidates[-1].get("url", "")

                code = item.get("code", "")
                yield {
                    "id":         item.get("pk", ""),
                    "shortcode":  code,
                    "url":        f"https://www.instagram.com/p/{code}/",
                    "type":       media_type,
                    "caption":    caption_text,
                    "likes":      item.get("like_count", 0),
                    "comments":   item.get("comment_count", 0),
                    "views":      item.get("view_count", 0),
                    "timestamp":  item.get("taken_at", 0),
                    "thumbnail":  thumb,
                }
                count += 1
            next_id = data.get("next_max_id")
            if not next_id:
                break

    # ─── comments ────────────────────────────────────────────────────────────

    def iter_comments(self, media_id: str, limit: int = 50):
        """Genera comentarios de un post."""
        next_id = None
        count   = 0
        while count < limit:
            params = {"can_support_threading": "true", "permalink_enabled": "false"}
            if next_id:
                params["min_id"] = next_id
            data = self._get(f"{self._API}/media/{media_id}/comments/", params)
            comments = data.get("comments", [])
            if not comments:
                break
            for c in comments:
                if count >= limit:
                    return
                user = c.get("user", {})
                yield {
                    "id":        c.get("pk", ""),
                    "text":      c.get("text", ""),
                    "likes":     c.get("comment_like_count", 0),
                    "timestamp": c.get("created_at", 0),
                    "author":    user.get("username", ""),
                    "author_id": user.get("pk", ""),
                }
                count += 1
            next_id = data.get("next_min_id")
            if not next_id:
                break

    # ─── likers ──────────────────────────────────────────────────────────────

    def iter_likers(self, media_id: str) -> list[dict]:
        """Devuelve la lista de usuarios que dieron like a un post."""
        data = self._get(f"{self._API}/media/{media_id}/likers/")
        for u in data.get("users", []):
            yield {
                "id":          u.get("pk"),
                "username":    u.get("username", ""),
                "full_name":   u.get("full_name", ""),
                "is_verified": u.get("is_verified", False),
            }
