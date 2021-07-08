

class User:
    
    def __init__(
            self,
            date_created,
            display_name,
            dw_id,
            recent_weekly_id=None,
            full_playlist_id=None,
            last_cw=None) -> None:
        self.date_created = date_created
        self.display_name = display_name
        self.dw_id = dw_id
        self.recent_weekly_id = recent_weekly_id
        self.full_playlist_id = full_playlist_id
        self.last_cw = last_cw

    @staticmethod
    def from_dict(source):
        return User(
            source["date_created"],
            source["display_name"],
            source["dw_id"],
            source.get("recent_weekly_id"),
            source.get("full_playlist_id"),
            source.get("last_cw")
            )

    def to_dict(self):
        return {
            "date_created": self.date_created,
            "display_name": self.display_name,
            "dw_id": self.dw_id,
            "recent_weekly_id": self.recent_weekly_id,
            "full_playlist_id": self.full_playlist_id,
            "last_cw": self.last_cw
        }

    def __repr__(self) -> str:
        return(
            f"User({self.date_created},\
                {self.display_name},\
                {self.dw_id},\
                {self.recent_weekly_id},\
                {self.full_playlist_id},\
                {self.last_cw})"
        )

