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
st.set_page_config(
    page_title="KPMSOL Attendance Calculator",
    page_icon="📊",
    layout="wide"
)

# ---------- HEADER ----------
st.markdown("""
<h1 style="margin-bottom:5px;">KPMSOL Attendance Calculator</h1>
<h1 style="color:red">New Features are being added, please check again later</h1>
<h6>Unofficial</h6>
<hr style="margin-top:0px; margin-bottom:10px;">
""", unsafe_allow_html=True)

st.markdown("Created by Gaurav Khopkar")


# ---------- LOAD CREDIT STRUCTURE ----------
credit_df = pd.read_excel("credit structure.xlsx")
credit_df.columns = credit_df.columns.str.strip()

credit_df["Program"] = credit_df["Program"].str.lower()
credit_df["Semester"] = credit_df["Semester"].str.lower()
credit_df["Subject"] = credit_df["Subject"].str.lower()


# ---------- NORMALIZE SUBJECT ----------
def normalize_subject(text):
    text = text.lower()
    text = re.sub(r'\b(t1|u1)\b', '', text)
    text = re.sub(r'-\s*div.*', '', text)
    text = re.sub(r',\d+', '', text)
    text = re.sub(r'^the\s+', '', text)
    return text.strip()


# ---------- INFO ----------
st.info("""
**How to use**

1. Download your **Detailed Attendance Report** from the SAP Portal and upload it here.
2. Note that SAP only shows attendance updates between **18:00 and 07:00**.
3. The tool calculates your attendance and displays **required lectures automatically**.
4. You can download the generated calculation as a .pdf which includes required lectures for all your subjects.
5. The uploaded attendance report is processed temporarily in memory and is not stored anywhere.
6. As of now, this tool is only **restricted to BALLB Semester I to Semester IV** from the batches 2024-29 and 2025-30.
""")


st.markdown(
'### Upload your Detailed Attendance Report from <a href="https://sdc-sppap1.svkm.ac.in:50001/irj/portal" target="_blank">SAP</a>',
unsafe_allow_html=True
)

uploaded_file = st.file_uploader("Upload File", type="pdf")


# ---------- TARGET SELECT ----------
target_percentage = st.radio(
    "Select Required Attendance %",
    [70, 75, 80],
    horizontal=True
)

generate = st.button("Generate Report")


# ---------- OPTIONAL COLUMNS ----------
st.markdown("### Select Optional Columns")

opt_conducted = st.checkbox("Total Lectures Conducted")
opt_attended = st.checkbox("Total Lectures Attended")
opt_dates = st.checkbox("Dates Missed")
opt_remaining = st.checkbox("Remaining Lectures")
opt_missable = st.checkbox("Lectures That Can Be Missed")


# ---------- BUILD CREDIT MAP ----------
def build_credit_map(target):
    column_map = {
        70: "Required Cumulative Attendance (70%)",
        75: "Required Cumulative Attendance (75%)",
        80: "Required Cumulative Attendance (80%)"
    }
    col = column_map[target]
    return dict(zip(credit_df["Subject"], credit_df[col]))


credit_map = build_credit_map(target_percentage)


# ---------- SUBJECT MATCH ----------
def match_required(subject):
    subject_clean = normalize_subject(subject)

    if subject_clean in credit_map:
        return credit_map[subject_clean]

    match = get_close_matches(subject_clean, credit_map.keys(), n=1, cutoff=0.45)

    if match:
        return credit_map[match[0]]

    return None


# ---------- PROCESS FILE ----------
if uploaded_file and generate:

    rows = []

    with pdfplumber.open(uploaded_file) as pdf:

        first_page_text = pdf.pages[0].extract_text()

        student_name = "Student Name Not Found"

        for line in first_page_text.split("\n"):
            if "Name" in line:
                student_name = line.strip()
                break

        report_duration = ""

        for line in first_page_text.split("\n"):
            if "Attendance Report Duration" in line:
                report_duration = line.strip()
                break

        program = ""

        if "b.a., ll.b" in first_page_text.lower():
            program = "b.a., ll.b.(hons.)"

        if "b.b.a., ll.b" in first_page_text.lower():
            program = "b.b.a., ll.b.(hons.)"

        semester_match = re.search(r"semester\s+[ivx]+", first_page_text.lower())
        semester = semester_match.group(0) if semester_match else ""

        for page in pdf.pages:
            table = page.extract_table()
            if table:
                for row in table[1:]:
                    rows.append(row)

    if len(rows) == 0:
        st.error("Invalid file.")
        st.stop()

    df = pd.DataFrame(rows)
    df = df[[1, 2, 5]]
    df.columns = ["Subject", "Date", "Attendance"]
    df = df.dropna()

    df["Subject"] = df["Subject"].str.strip()
    df["Attendance"] = df["Attendance"].str.strip()


    # ---------- NU DETECTION ----------
    nu_rows = df[df["Attendance"] == "NU"]

    nu_message = None

    if not nu_rows.empty:
        nu_count = len(nu_rows)

        try:
            nu_date = pd.to_datetime(nu_rows["Date"]).max().strftime("%d %B")
        except:
            nu_date = nu_rows["Date"].iloc[0]

        nu_message = f"{nu_count} lecture(s) from {nu_date} are marked as Not Updated (NU)."

        st.warning(nu_message)


    df_calc = df[df["Attendance"] != "NU"]

    subjects = df_calc["Subject"].unique()

    result = pd.DataFrame({"Subject": subjects})

    conducted = df_calc.groupby("Subject").size()

    attended = (
        df_calc[df_calc["Attendance"] == "P"]
        .groupby("Subject")
        .size()
    )

    missed_dates = (
        df_calc[df_calc["Attendance"] == "A"]
        .groupby("Subject")["Date"]
        .apply(lambda x: ", ".join(x.astype(str)))
    )

    result["Total Lectures Conducted"] = result["Subject"].map(conducted).fillna(0)
    result["Total Lectures Attended"] = result["Subject"].map(attended).fillna(0)
    result["Dates Missed"] = result["Subject"].map(missed_dates).fillna("")


    # ---------- GROUP ----------
    result["Base Subject"] = result["Subject"].str.replace(
        r"\s*(T\s*1|U\s*1).*",
        "",
        regex=True
    )

    result = result.sort_values(by=["Base Subject"])

    combined_conducted = (
        result.groupby("Base Subject")["Total Lectures Conducted"].transform("sum")
    )

    combined_attended = (
        result.groupby("Base Subject")["Total Lectures Attended"].transform("sum")
    )

    result["Current Cumulative Attendance"] = combined_attended

    result["Attendance Percentage"] = (
        combined_attended / combined_conducted * 100
    ).round(2)


    # ---------- REQUIRED ----------
    result["Required Cumulative Attendance"] = (
        result["Base Subject"].apply(match_required)
    )

    result["Required Cumulative Attendance"] = (
        result["Required Cumulative Attendance"]
        - result["Current Cumulative Attendance"]
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

    result["Remaining Lectures"] = result["Total Possible"] - combined_conducted


    def calc_missable(row):
        required_total = row["Required Cumulative Attendance"] + row["Current Cumulative Attendance"]

        if row["Current Cumulative Attendance"] >= required_total:
            return "Criteria Fulfilled"

        if row["Required Cumulative Attendance"] > row["Remaining Lectures"]:
            return "All lectures are mandatory"

        val = int(row["Remaining Lectures"] - row["Required Cumulative Attendance"])
        return val


    result["Lectures That Can Be Missed"] = result.apply(calc_missable, axis=1)


    # ---------- FINAL DISPLAY ----------
    final_cols = [
        "Sr. No.",
        "Subject",
        "Attendance Percentage",
        "Required Cumulative Attendance"
    ]

    result.insert(0, "Sr. No.", range(1, len(result) + 1))

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

    display_df = result[final_cols]

    st.dataframe(display_df, use_container_width=True, hide_index=True)


    # ---------- PDF ----------
    st.markdown("### Download Report")

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

        elements.append(
            Paragraph(
                f"This Report has been calculated based on {target_percentage}% chosen criteria.",
                styles["Normal"]
            )
        )

        elements.append(Spacer(1, 10))

    table_data = [display_df.columns.tolist()] + display_df.values.tolist()

    page_width = landscape(letter)[0] - 80
    col_width = page_width / len(display_df.columns)

    table = Table(table_data, colWidths=[col_width]*len(display_df.columns))

    table.setStyle(
        TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey)
        ])
    )

    elements.append(table)

    pdf = SimpleDocTemplate(pdf_buffer, pagesize=landscape(letter))
    pdf.build(elements)

    pdf_buffer.seek(0)

    st.download_button(
        label="Download as PDF",
        data=pdf_buffer,
        file_name="attendance_report.pdf",
        mime="application/pdf"
    )


# ---------- FOOTER ----------
st.markdown("---")

st.markdown("""
<p style="font-size:0.85rem; color:gray;">
This page is an independent student-created tool developed by <b>Gaurav Khopkar</b>.
It is not affiliated with NMIMS, KPMSOL, or the SAP portal.
<br>
<p style="font-size:0.85rem; color:gray;">
For queries or suggestions or any defects on this page, contact: <b>gauravkhopkar2006@hotmail.com</b>
<br>
<p style="font-size:0.85rem; color:gray;">
Thank you for using this tool.
""", unsafe_allow_html=True)
