from dataclasses import dataclass


@dataclass
class SpotifyArgs:
    """Class for making SpotifyUtils arguments easily accessible."""

    username: str
    weekly_name_template: str
    full_playlist_name: str
    dw_id: str
    full_playlist_id: str
