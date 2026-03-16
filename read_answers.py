import re
import fitz

def parse_answer_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    
    lines = [l.strip() for l in full_text.splitlines() if l.strip()]


    # Check what lines 1 and 2 look like
    print("Line 1:", lines[1])
    print("Line 2:", lines[2])

    for i, l in enumerate(lines[:8]):
        print(f"Line {i}: {l}")

    # --- 1. Parse subject line (2nd line) ---
    #subject_line = lines[1]
    subject_line = lines[1] + " " + lines[2] + " " + lines[3] 
    parts = [p.strip() for p in subject_line.split("-")]

    print("Raw parts:", parts)  # check actual split

    subject = {
        "code":     parts[0] if len(parts) > 0 else "",
        "topic":    parts[1] if len(parts) > 1 else "",
        "level":    parts[2] if len(parts) > 2 else "",
        "season":   parts[3] if len(parts) > 3 else "",
        "run_type": parts[4] if len(parts) > 4 else "",
    }
    season_parts = subject["season"].split()

    print(season_parts[0])
    print(season_parts[1])
    print(season_parts[2])

    # --- 2. Parse question/answer table ---
    hebrew_letters = set("אבגד")
    skip_words = {"מספר", "שאלה", "תשובה", "נכונה", "הערה", "מפתח", "תשובות"}
    page_marker = re.compile(r"^\d+/\d+$")

    answers = {}
    i = 0
    while i < len(lines):
        line = lines[i]

        # Skip headers and page markers
        if any(w in line for w in skip_words) or page_marker.match(line):
            i += 1
            continue

        # Match a line starting with a question number
        match = re.match(r"^(\d+)\s*(.*)", line)
        if match:
            q_num = int(match.group(1))
            rest = match.group(2).strip()

            # Collect all hebrew letters from rest of line
            ans_letters = [c for c in rest if c in hebrew_letters]

            # Edge case: answer might be on next line if rest is empty
            if not ans_letters and i + 1 < len(lines):
                next_line = lines[i + 1]
                ans_letters = [c for c in next_line if c in hebrew_letters]
                if ans_letters:
                    i += 1  # consume next line too

            if ans_letters:
                answers[q_num] = ans_letters if len(ans_letters) > 1 else ans_letters[0]

        i += 1

    return subject, answers


# Usage:
subject, answers = parse_answer_pdf("C:/Users/Tru1/Downloads/answers.pdf")



print("Subject info:")
for k, v in subject.items():
    print(f"  {k}: {v}")

print("\nAnswers:")
#for q, a in sorted(answers.items()):
#    print(f"  Q{q}: {a}")
