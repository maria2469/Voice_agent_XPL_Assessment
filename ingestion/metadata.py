def classify_content(text: str) -> str:
    """
    Simple text classifier
    """
    text_lower = text.lower()
    if "admission" in text_lower:
        return "admissions"
    elif "fee" in text_lower or "tuition" in text_lower:
        return "fees"
    elif "curriculum" in text_lower or "academic" in text_lower:
        return "curriculum"
    elif "facility" in text_lower or "campus" in text_lower:
        return "facilities"
    elif "sports" in text_lower or "activity" in text_lower:
        return "activities"
    else:
        return "general"