import streamlit as st

def _init():
    defaults = dict(
        exam_key    = None,
        q_index     = 0,
        selected    = [],
        result_msg  = "",
        result_ok   = None,
        score_good  = 0,       # correct answers count
        score_bad   = 0,       # wrong answers count
        answered    = set(),   # set of q_index already checked
        show_summary= False,   # show exit summary screen
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
    st.session_state.exam_key     = None
    st.session_state.q_index      = 0
    st.session_state.score_good   = 0
    st.session_state.score_bad    = 0
    st.session_state.answered     = set()
    st.session_state.show_summary = False
    reset_answer()