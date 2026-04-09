from playwright.sync_api import sync_playwright
import subprocess
import time

def test_streamlit_question_flow():
    proc = subprocess.Popen(
        ["streamlit", "run", "app.py", "--server.port=8501"],
        cwd="c:\\Users\\Tru1\\Documents\\Projects\\Python_projects\\Mecial_exams",
    )
    time.sleep(5)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto("http://localhost:8501")

            # select exam
            page.get_by_role("button", name="Lung Exams").click()
            time.sleep(1)

            # click a question answer button
            page.get_by_role("button", name="א").click()
            page.get_by_role("button", name="✔ Check Answer").click()

            assert "Correct" in page.inner_text("body")
    finally:
        proc.terminate()
        proc.wait()