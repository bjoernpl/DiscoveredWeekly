from datetime import datetime

def this_week():
    return datetime.today().isocalendar()[1]

def parse_playlist_name(name):
    today = datetime.today()
    year, week, _ = today.isocalendar()
    name = name.replace("{week_of_year}", f"{week}")
    name = name.replace("{year}", f"{year}")
    name = name.replace("{month}", f"{today.month}")
    return name