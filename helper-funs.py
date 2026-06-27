from datetime import date


def get_current_date() -> str:
    """Gets the current date."""

    return date.today().isoformat()
