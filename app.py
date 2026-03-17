import streamlit as st
import pdfplumber
import pandas as pd
import io
import re
from difflib import get_close_matches

from reportlab.platypus import SimpleDocTemplate, Table, Paragraph, Spacer, TableStyle
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="KPMSOL Attendance Calculator", page_icon="📊", layout="wide")

# ---------- HEADER ----------
st.markdown("""
<h1 style="margin-bottom:5px;">KPMSOL Attendance Calculator</h1>
<h6>Unofficial</h6>
<hr>
""", unsafe_allow_html=True)

st.markdown("Created by Gaurav Khopkar")


# ---------- LOAD CREDIT ----------
credit_df = pd.read_excel("credit structure.xlsx")
credit_df.columns = credit_df.columns.str.strip()

credit_df["Program"] = credit_df["Program"].str.lower()
credit_df["Semester"] = credit_df["Semester"].str.lower()
credit_df["Subject"] = credit_df["Subject"].str.lower()


def normalize_subject(text):
    text = text.lower()
    text = re.sub(r'\b(t1|u1)\b', '', text)
    text = re.sub(r'-\s*div.*', '', text)
    text = re.sub(r',\d+', '', text)
    text = re.sub(r'^the\s+', '', text)
    return text.strip()


# ---------- INPUT ----------
uploaded_file = st.file_uploader("Upload File", type="pdf")

target_percentage = st.radio("Select Required Attendance %", [70, 75, 80], horizontal=True)

# ---------- OPTIONAL COLUMNS ----------
st.markdown("### Select Optional Columns")

opt_conducted = st.checkbox("Total Lectures Conducted")
opt_attended = st.checkbox("Total Lectures Attended")
opt_dates = st.checkbox("Dates Missed")
opt_remaining = st.checkbox("Remaining Lectures")
opt_missable = st.checkbox("Lectures That Can Be Missed")

# ✅ Generate button moved HERE
generate = st.button("Generate Report")


# ---------- CREDIT MAP ----------
def build_credit_map(target):
    col_map = {
        70: "Required Cumulative Attendance (70%)",
        75: "Required Cumulative Attendance (75%)",
        80: "Required Cumulative Attendance (80%)"
    }
    return dict(zip(credit_df["Subject"], credit_df[col_map[target]]))


credit_map = build_credit_map(target_percentage)


def match_required(subject):
    subject_clean = normalize_subject(subject)
    if subject_clean in credit_map:
        return credit_map[subject_clean]
    match = get_close_matches(subject_clean, credit_map.keys(), n=1, cutoff=0.45)
    return credit_map[match[0]] if match else None


# ---------- PROCESS ----------
if uploaded_file and generate:

    rows = []

    with pdfplumber.open(uploaded_file) as pdf:
        text = pdf.pages[0].extract_text()

        student_name = "Student Name Not Found"
        for line in text.split("\n"):
            if "Name" in line:
                student_name = line.strip()
                break

        report_duration = ""
        for line in text.split("\n"):
            if "Attendance Report Duration" in line:
                report_duration = line.strip()
                break

        program = "b.a., ll.b.(hons.)" if "b.a., ll.b" in text.lower() else "b.b.a., ll.b.(hons.)"
        semester = re.search(r"semester\s+[ivx]+", text.lower()).group(0)

        for page in pdf.pages:
            table = page.extract_table()
            if table:
                rows.extend(table[1:])

    df = pd.DataFrame(rows)[[1, 2, 5]]
    df.columns = ["Subject", "Date", "Attendance"]
    df = df.dropna()

    df_calc = df[df["Attendance"] != "NU"]

    conducted = df_calc.groupby("Subject").size()
    attended = df_calc[df_calc["Attendance"] == "P"].groupby("Subject").size()

    missed_dates = (
        df_calc[df_calc["Attendance"] == "A"]
        .groupby("Subject")["Date"]
        .apply(lambda x: ", ".join(x.astype(str)))
    )

    result = pd.DataFrame({"Subject": conducted.index})
    result["Total Lectures Conducted"] = result["Subject"].map(conducted)
    result["Total Lectures Attended"] = result["Subject"].map(attended).fillna(0)
    result["Dates Missed"] = result["Subject"].map(missed_dates).fillna("")

    result["Base Subject"] = result["Subject"].str.replace(r"\s*(T\s*1|U\s*1).*", "", regex=True)

    combined_conducted = result.groupby("Base Subject")["Total Lectures Conducted"].transform("sum")
    combined_attended = result.groupby("Base Subject")["Total Lectures Attended"].transform("sum")

    result["Current Cumulative Attendance"] = combined_attended
    result["Attendance Percentage"] = (combined_attended / combined_conducted * 100).round(2)

    result["Required Cumulative Attendance"] = result["Base Subject"].apply(match_required)
    result["Required Cumulative Attendance"] = (
        result["Required Cumulative Attendance"] - result["Current Cumulative Attendance"]
    ).clip(lower=0)

    # ---------- MERGE CREDIT ----------
    credit_filtered = credit_df[
        (credit_df["Program"] == program) &
        (credit_df["Semester"] == semester)
    ]

    result = result.merge(
        credit_filtered[["Subject", "Total Lectures (T1)", "Total Tutorials (U1)"]],
        left_on="Base Subject",
        right_on="Subject",
        how="left"
    )

    result["Total Possible"] = result["Total Lectures (T1)"].fillna(0) + result["Total Tutorials (U1)"].fillna(0)

    # ---------- NEW CALCULATIONS ----------
    result["Remaining Lectures"] = result["Total Possible"] - combined_conducted

    def calc_missable(row):
        required_remaining = row["Required Cumulative Attendance"]

        if row["Current Cumulative Attendance"] >= (row["Current Cumulative Attendance"] + required_remaining):
            return "Criteria Fulfilled"

        if required_remaining > row["Remaining Lectures"]:
            return "All lectures are mandatory"

        val = int(row["Remaining Lectures"] - required_remaining)
        return "Criteria Fulfilled" if val >= row["Remaining Lectures"] else val

    result["Lectures That Can Be Missed"] = result.apply(calc_missable, axis=1)

    # ---------- FINAL DISPLAY ----------
    result.insert(0, "Sr. No.", range(1, len(result) + 1))

    final_cols = [
        "Sr. No.",
        "Subject",
        "Attendance Percentage",
        "Required Cumulative Attendance"
    ]

    if opt_conducted:
        final_cols.append("Total Lectures Conducted")
    if opt_attended:
        final_cols.append("Total Lectures Attended")
    if opt_dates:
        final_cols.append("Dates Missed")
    if opt_remaining:
        final_cols.append("Remaining Lectures")
    if opt_missable:
        final_cols.append("Lectures That Can Be Missed")

    display_df = result[[col for col in final_cols if col in result.columns]]

    # ---------- PDF ----------
    pdf_buffer = io.BytesIO()
    styles = getSampleStyleSheet()

    elements = []
    elements.append(Paragraph("<b>Attendance Report</b>", styles["Title"]))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(student_name, styles["Normal"]))
    elements.append(Spacer(1, 5))

    if report_duration:
        elements.append(Paragraph(report_duration, styles["Normal"]))
        elements.append(Spacer(1, 5))
        elements.append(Paragraph(
            f"This Report has been calculated based on {target_percentage}% chosen criteria.",
            styles["Normal"]
        ))
        elements.append(Spacer(1, 10))

    table_data = [display_df.columns.tolist()] + display_df.values.tolist()

    page_width = landscape(letter)[0] - 80
    col_width = page_width / len(display_df.columns)

    table = Table(table_data, colWidths=[col_width]*len(display_df.columns))

    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
    ]))

    elements.append(table)

    pdf = SimpleDocTemplate(pdf_buffer, pagesize=landscape(letter))
    pdf.build(elements)

    pdf_buffer.seek(0)

    st.markdown("### Download Report")
    st.download_button("Download as PDF", pdf_buffer, "attendance_report.pdf")

    st.dataframe(display_df, use_container_width=True, hide_index=True)
