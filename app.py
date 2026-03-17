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
<h1 style="color:red">New Features are bring added, please check again later</h1>
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


credit_map = dict(
    zip(
        credit_df["Subject"],
        credit_df["Required Cumulative Attendance"]
    )
)


# ---------- NORMALIZE SUBJECT ----------
def normalize_subject(text):

    text = text.lower()

    text = re.sub(r'\b(t1|u1)\b', '', text)
    text = re.sub(r'-\s*div.*', '', text)
    text = re.sub(r',\d+', '', text)
    text = re.sub(r'^the\s+', '', text)

    return text.strip()


# ---------- SUBJECT MATCH ----------
def match_required(subject):

    subject_clean = normalize_subject(subject)

    if subject_clean in credit_map:
        return credit_map[subject_clean]

    match = get_close_matches(subject_clean, credit_map.keys(), n=1, cutoff=0.45)

    if match:
        return credit_map[match[0]]

    return None


# ---------- INFO ----------
st.info("""
**How to use**

1. Download your **Detailed Attendance Report** from the SAP Portal and upload it here.
2. Note that SAP only shows attendance updates between **18:00 and 07:00**.
3. The tool calculates your attendance and displays **required lectures automatically**.
4. While this tool provides an accurate estimate, keeping a buffer of 1–2 lectures above the required count is recommended.
5. You can download the generated calculation as a .pdf which includes required lectures for all your subjects.
6. The uploaded attendance report is processed temporarily in memory and is not stored anywhere.
7. As of now, this tool is only **restricted to Semester I to Semester IV** from the batches 2024-29 and 2025-30.
""")


st.markdown(
'### Upload your Detailed Attendance Report from <a href="https://sdc-sppap1.svkm.ac.in:50001/irj/portal" target="_blank">SAP</a>',
unsafe_allow_html=True
)

uploaded_file = st.file_uploader("Upload File", type="pdf")


# ---------- PROCESS FILE ----------
if uploaded_file:

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


        # ---------- EXTRACT PROGRAM ----------
        program = ""

        if "b.a., ll.b" in first_page_text.lower():
            program = "b.a., ll.b.(hons.)"

        if "b.b.a., ll.b" in first_page_text.lower():
            program = "b.b.a., ll.b.(hons.)"


        # ---------- EXTRACT SEMESTER ----------
        semester_match = re.search(r"semester\s+[ivx]+", first_page_text.lower())

        semester = semester_match.group(0) if semester_match else ""


        # ---------- TABLE EXTRACTION ----------
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

    df.columns = [
        "Subject",
        "Date",
        "Attendance"
    ]

    df = df.dropna()

    df["Subject"] = df["Subject"].str.strip()
    df["Attendance"] = df["Attendance"].str.strip()


    # ---------- NU DETECTION ----------
    nu_rows = df[df["Attendance"] == "NU"]

    nu_message = None

    if not nu_rows.empty:

        nu_count = len(nu_rows)

        try:
            nu_date = pd.to_datetime(
                nu_rows["Date"]
            ).max().strftime("%d %B")

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


    # ---------- GROUP T1/U1 ----------
    result["Base Subject"] = result["Subject"].str.replace(
        r"\s*(T\s*1|U\s*1).*",
        "",
        regex=True
    )

    result["Type"] = result["Subject"].str.extract(
        r"(T\s*1|U\s*1)"
    )

    result = result.sort_values(by=["Base Subject", "Type"])


    combined_conducted = (
        result.groupby("Base Subject")["Total Lectures Conducted"]
        .transform("sum")
    )

    combined_attended = (
        result.groupby("Base Subject")["Total Lectures Attended"]
        .transform("sum")
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

    result["Required Cumulative Attendance"] = (
        result["Required Cumulative Attendance"]
        .fillna(0)
        .astype(int)
        .astype(object)
    )


    duplicated = result.duplicated("Base Subject")

    result.loc[duplicated, "Current Cumulative Attendance"] = ""
    result.loc[duplicated, "Required Cumulative Attendance"] = ""
    result.loc[duplicated, "Attendance Percentage"] = ""


    result.insert(
        0,
        "Sr. No.",
        range(1, len(result) + 1)
    )


    result = result[
        [
            "Sr. No.",
            "Subject",
            "Total Lectures Conducted",
            "Total Lectures Attended",
            "Current Cumulative Attendance",
            "Attendance Percentage",
            "Required Cumulative Attendance",
            "Dates Missed"
        ]
    ]


    # ---------- FILTER CREDIT TABLE BY PROGRAM + SEMESTER ----------
    relevant_credit_rows = credit_df[
        (credit_df["Program"] == program) &
        (credit_df["Semester"] == semester)
    ]


    # ---------- PDF GENERATION ----------
    st.markdown("### Download Report")

    pdf_buffer = io.BytesIO()

    styles = getSampleStyleSheet()

    wrap_style = ParagraphStyle(
        "wrap",
        parent=styles["Normal"],
        wordWrap="CJK"
    )

    header_style = ParagraphStyle(
        "header",
        parent=styles["Normal"],
        alignment=1,
        wordWrap="CJK"
    )

    elements = []

    elements.append(
        Paragraph("<b>Attendance Report</b>", styles["Title"])
    )

    elements.append(Spacer(1, 10))

    elements.append(
        Paragraph(student_name, styles["Normal"])
    )

    elements.append(Spacer(1, 5))

    if report_duration:

        elements.append(
            Paragraph(report_duration, styles["Normal"])
        )

        elements.append(Spacer(1, 10))

    if nu_message:

        elements.append(
            Paragraph(nu_message, styles["Normal"])
        )

        elements.append(Spacer(1, 15))


    headers = [
        Paragraph(f"<b>{col}</b>", header_style)
        for col in result.columns
    ]

    table_data = [headers]

    for row in result.values.tolist():

        table_data.append(
            [Paragraph(str(v), wrap_style) for v in row]
        )

    page_width = landscape(letter)[0] - 80

    col_widths = [
        page_width * 0.05,
        page_width * 0.22,
        page_width * 0.11,
        page_width * 0.11,
        page_width * 0.14,
        page_width * 0.12,
        page_width * 0.14,
        page_width * 0.20
    ]

    attendance_table = Table(
        table_data,
        colWidths=col_widths,
        repeatRows=1
    )

    attendance_table.setStyle(
        TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE")
        ])
    )

    elements.append(attendance_table)

    elements.append(Spacer(1, 30))


    # ---------- CREDIT STRUCTURE TABLE ----------
    credit_headers = [
        Paragraph(f"<b>{c}</b>", header_style)
        for c in relevant_credit_rows.columns
    ]

    credit_data = [credit_headers]

    for _, row in relevant_credit_rows.iterrows():

        credit_data.append(
            [Paragraph(str(v), wrap_style) for v in row]
        )

    credit_table = Table(
        credit_data,
        repeatRows=1
    )

    credit_table.setStyle(
        TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey)
        ])
    )

    elements.append(credit_table)

    pdf = SimpleDocTemplate(
        pdf_buffer,
        pagesize=landscape(letter)
    )

    pdf.build(elements)

    pdf_buffer.seek(0)

    st.download_button(
        label="Download as PDF",
        data=pdf_buffer,
        file_name="attendance_report.pdf",
        mime="application/pdf"
    )


    # ---------- DISPLAY TABLE ----------
    st.dataframe(
        result,
        height=650,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Dates Missed": st.column_config.TextColumn(width="large")
        }
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
