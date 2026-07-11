
def get_current_date() -> str:
    """Gets the current date."""
    from datetime import date

    return date.today().isoformat()
