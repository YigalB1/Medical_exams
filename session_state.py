import streamlit as st

def _init():
    defaults = dict(
        exam_key           = None,
        q_index            = 0,
        selected           = [],
        result_msg         = "",
        result_ok          = None,
        score_good         = 0,       # correct answers count
        score_bad          = 0,       # wrong answers count
        answered           = set(),   # set of q_index already checked
        show_summary       = False,   # show exit summary screen
        browsing_category  = None,    # category key while browsing exam list (None = home)
        dyn_questions_url  = None,    # questions PDF URL for a dynamically selected exam
        dyn_answers_url    = None,    # answers PDF URL for a dynamically selected exam
        username           = "user",  # current user (for logging; will support registration later)
        exam_start_time    = None,    # timestamp when exam started (for logging)
    )
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

#_init()


def reset_answer():
    st.session_state.selected   = []
    st.session_state.result_msg = ""
    st.session_state.result_ok  = None


def reset_exam():
    st.session_state.exam_key          = None
    st.session_state.q_index           = 0
    st.session_state.score_good        = 0
    st.session_state.score_bad         = 0
    st.session_state.answered          = set()
    st.session_state.show_summary      = False
    st.session_state.browsing_category = None
    st.session_state.dyn_questions_url = None
    st.session_state.dyn_answers_url   = None
    st.session_state.exam_start_time   = None
    reset_answer()