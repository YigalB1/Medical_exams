import requests
import io
import fitz

# main link: https://www.ima.org.il/internship/Exams.aspx
# link to tr4ial exam: https://ima-files.s3.amazonaws.com/814180_114e80b1-0a46-4046-a7ee-9a69972b31f9.pdf
# link to trial answers: https://ima-files.s3.amazonaws.com/822587_8ebf6f4b-843b-4807-abf2-16767431b006.pdf

def open_pdf_from_url(url):
    response = requests.get(url)
    response.raise_for_status()
    return fitz.open(stream=io.BytesIO(response.content), filetype="pdf")


def get_pdf_bytes(url):
    response = requests.get(url)
    response.raise_for_status()
    return io.BytesIO(response.content)