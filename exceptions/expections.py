class AuthenticationError(Exception):
    """Thrown when Spotify authentication fails for some reason"""

    def __init__(self, *args: object) -> None:
        super().__init__(*args)
