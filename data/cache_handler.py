import spotipy

class LossyCacheHandler(spotipy.CacheHandler):
    def get_cached_token(self):
        return None

    def save_token_to_cache(self, token_info):
        return None

class FirestoreCacheHandler(spotipy.CacheHandler):
    def __init__(self, username, db) -> None:
        self.cacheHandler = spotipy.CacheFileHandler(username)
        self.username = username
        self.db = db

    def get_cached_token(self):
        cached_token = self.cacheHandler.get_cached_token()
        if not cached_token:
            token_ref = self.db.collection("tokens").document(self.username)
            token = token_ref.get()
            if token.exists:
                token_info = token.to_dict()
                return token_info
        return cached_token
            
    def save_token_to_cache(self, token_info):
        self.cacheHandler.save_token_to_cache(token_info)
        self.db.collection("tokens").document(self.username).set(token_info)