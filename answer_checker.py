def check_answer(selected, correct):
    """
    Check if selected answer(s) match the correct answer(s).
    
    Args:
        selected: List of selected letter answers (e.g., ["א", "ב"])
        correct: Correct answer(s) - single letter string or list of letters
    
    Returns:
        Tuple of (is_correct: bool or None, message: str)
    """
    if correct is None:
        return None, f"No answer key found for this question."
    
    correct_list = correct if isinstance(correct, list) else [correct]
    is_correct = sorted(selected) == sorted(correct_list)
    
    answer_text = " ".join(correct_list)
    if is_correct:
        message = f"✔ Correct!  Answer: {answer_text}"
    else:
        message = f"✘ Wrong.  Correct answer: {answer_text}"
    
    return is_correct, message