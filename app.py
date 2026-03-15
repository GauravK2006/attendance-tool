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
<h6>Unofficial</h6>
<hr style="margin-top:0px; margin-bottom:10px;">
""", unsafe_allow_html=True)

st.markdown("Created by Gaurav Khopkar")


# ---------- LOAD CREDIT STRUCTURE ----------
credit_df = pd.read_excel("credit structure.xlsx")

credit_df.columns = credit_df.columns.str.strip()

credit_df["Subject"] = (
    credit_df["Subject"]
    .str.lower()
    .str.strip()
)

credit_map = dict(
    zip(
        credit_df["Subject"],
        credit_df["Required Cumulative Attendance"]
    )
)


# ---------- SUBJECT CLEANING ----------
def normalize_subject(text):

    text = text.lower()

    # remove T1/U1
    text = re.sub(r'\b(t1|u1)\b', '', text)

    # remove division
    text = re.sub(r'-\s*div.*', '', text)

    # remove numbers like ,23
    text = re.sub(r',\d+', '', text)

    # remove leading "the"
    text = re.sub(r'^the\s+', '', text)

    text = text.strip()

    return text


# ---------- SUBJECT MATCHING ----------
def match_required(subject):

    subject = normalize_subject(subject)

    # direct match
    if subject in credit_map:
        return credit_map[subject]

    # fuzzy match
    match = get_close_matches(subject, credit_map.keys(), n=1, cutoff=0.45)

    if match:
        return credit_map[match[0]]

    return None


# ---------- INFO BOX ----------
st.info("""
*How to use*

1. Download your *Detailed Attendance Report* from the SAP Portal and upload it here.  
2. SAP only shows attendance updates between *18:00 and 07:00*.  
3. The tool automatically calculates your *attendance percentage*.  
4. Cross-check your *cumulative attendance* with the required lectures below.  
5. The uploaded report is processed *only in memory and never stored*.
""")

st.markdown(
'### Upload your Detailed Attendance Report from <a href="https://sdc-sppap1.svkm.ac.in:50001/irj/portal" target="_blank">SAP</a> here',
unsafe_allow_html=True
)

uploaded_file = st.file_uploader("Upload File", type="pdf")


# ---------- PROCESS FILE ----------
if uploaded_file:

    rows = []

    with pdfplumber.open(uploaded_file) as pdf:

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


    result["Total Lectures Conducted"] = (
        result["Subject"].map(conducted).fillna(0)
    )

    result["Total Lectures Attended"] = (
        result["Subject"].map(attended).fillna(0)
    )

    result["Dates Missed"] = (
        result["Subject"].map(missed_dates).fillna("")
    )


    # ---------- GROUP T1/U1 ----------
    result["Base Subject"] = result["Subject"].str.replace(
        r"\s*(T\s*1|U\s*1).*",
        "",
        regex=True
    )

    result["Type"] = result["Subject"].str.extract(
        r"(T\s*1|U\s*1)"
    )


    result = result.sort_values(
        by=["Base Subject", "Type"]
    )


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


    # ---------- REQUIRED CUMULATIVE ----------
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


    # ---------- OPTION B ----------
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


    # ---------- FORCE HEADER WRAP ----------
    st.markdown(
        """
        <style>
        div[data-testid="stDataFrame"] table {
            table-layout: fixed;
        }

        div[data-testid="stDataFrame"] th {
            white-space: normal !important;
            word-wrap: break-word !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


    st.dataframe(
        result,
        use_container_width=True,
        hide_index=True
    )


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


    headers = [
        Paragraph(
            f"<b>{col}</b>",
            header_style
        )
        for col in result.columns
    ]


    table_data = [headers]


    for row in result.values.tolist():

        wrapped_row = []

        for cell in row:

            wrapped_row.append(
                Paragraph(str(cell), wrap_style)
            )

        table_data.append(wrapped_row)


    page_width = landscape(letter)[0] - 80


    col_widths = [
        page_width * 0.05,
        page_width * 0.22,
        page_width * 0.11,
        page_width * 0.11,
        page_width * 0.14,
        page_width * 0.12,
        page_width * 0.14,
        page_width * 0.11
    ]


    attendance_table = Table(
        table_data,
        colWidths=col_widths,
        repeatRows=1
    )


    attendance_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
            ]
        )
    )


    elements = []


    elements.append(
        Paragraph(
            "<b>Attendance Report</b>",
            styles["Title"]
        )
    )


    elements.append(Spacer(1, 15))


    elements.append(attendance_table)


    pdf = SimpleDocTemplate(
        pdf_buffer,
        pagesize=landscape(letter)
    )


    pdf.build(elements)


    pdf_buffer.seek(0)


    st.download_button(
        label="Download as PDF (.pdf)",
        data=pdf_buffer,
        file_name="attendance_report.pdf",
        mime="application/pdf"
    )


# ---------- FOOTER ----------
st.markdown("---")

st.markdown(
"""
<p style="font-size:0.85rem; color:gray;">
This page is an independent student-created tool developed by <b>Gaurav Khopkar</b>.
It is not affiliated with NMIMS, KPMSOL, or the SAP portal.
</p>
""",
unsafe_allow_html=True
)
