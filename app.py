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
<h1 style="color:red">Site is being refined for better experience, please check back later</h1>
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
6. As of now, this tool is only **restricted to Semester I to Semester IV** from the batches 2024-29 and 2025-30.
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


# ---------- OPTIONAL COLUMNS SELECTOR ----------
st.markdown("#### Select Optional Columns to Display")
st.caption("These columns will appear in both the table below and the downloaded PDF.")

optional_col_definitions = [
    ("Total Lectures Conducted",   "show_conducted"),
    ("Total Lectures Attended",    "show_attended"),
    ("Total Missed",               "show_missed"),
    ("Remaining Lectures",         "show_remaining"),
    ("Lectures That Can Be Missed","show_can_miss"),
    ("Dates Missed",               "show_dates"),
]

# Render checkboxes in a 3-column grid
cols = st.columns(3)
optional_selections = {}
for i, (label, key) in enumerate(optional_col_definitions):
    with cols[i % 3]:
        optional_selections[key] = st.checkbox(label, value=False, key=key)


generate = st.button("Generate Report")


# ---------- BUILD CREDIT MAP ----------
def build_credit_map(target):
    column_map = {
        70: "Required Cumulative Attendance (70%)",
        75: "Required Cumulative Attendance (75%)",
        80: "Required Cumulative Attendance (80%)"
    }
    col = column_map[target]
    return dict(zip(credit_df["Subject"], credit_df[col]))


def build_total_lectures_map():
    """Returns dict: subject -> Total Lectures (T1)"""
    return dict(zip(credit_df["Subject"], credit_df["Total Lectures (T1)"]))


def build_total_tutorials_map():
    """Returns dict: subject -> Total Tutorials (U1)"""
    return dict(zip(credit_df["Subject"], credit_df["Total Tutorials (U1)"]))


credit_map = build_credit_map(target_percentage)
total_lectures_map = build_total_lectures_map()
total_tutorials_map = build_total_tutorials_map()


# ---------- SUBJECT MATCH ----------
def match_required(subject):
    subject_clean = normalize_subject(subject)
    if subject_clean in credit_map:
        return credit_map[subject_clean]
    match = get_close_matches(subject_clean, credit_map.keys(), n=1, cutoff=0.45)
    if match:
        return credit_map[match[0]]
    return None


def match_total_lectures(subject):
    """Match Total Lectures (T1) from credit structure for a base subject."""
    subject_clean = normalize_subject(subject)
    if subject_clean in total_lectures_map:
        return total_lectures_map[subject_clean]
    match = get_close_matches(subject_clean, total_lectures_map.keys(), n=1, cutoff=0.45)
    if match:
        return total_lectures_map[match[0]]
    return None


def match_total_tutorials(subject):
    """Match Total Tutorials (U1) from credit structure for a base subject."""
    subject_clean = normalize_subject(subject)
    if subject_clean in total_tutorials_map:
        return total_tutorials_map[subject_clean]
    match = get_close_matches(subject_clean, total_tutorials_map.keys(), n=1, cutoff=0.45)
    if match:
        return total_tutorials_map[match[0]]
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
    attended = df_calc[df_calc["Attendance"] == "P"].groupby("Subject").size()

    missed_dates = (
        df_calc[df_calc["Attendance"] == "A"]
        .groupby("Subject")["Date"]
        .apply(lambda x: ", ".join(x.astype(str)))
    )

    result["Total Lectures Conducted"] = result["Subject"].map(conducted).fillna(0).astype(int)
    result["Total Lectures Attended"]  = result["Subject"].map(attended).fillna(0).astype(int)
    result["Dates Missed"]             = result["Subject"].map(missed_dates).fillna("")

    # --- Sorting: group T1/U1 under same base subject ---
    result["Base Subject"] = result["Subject"].str.replace(
        r"\s*(T\s*1|U\s*1).*", "", regex=True
    )
    result["Type"] = result["Subject"].str.extract(r"(T\s*1|U\s*1)")
    result = result.sort_values(by=["Base Subject", "Type"])

    # --- Consolidated (T1+U1) aggregations per Base Subject ---
    combined_conducted = result.groupby("Base Subject")["Total Lectures Conducted"].transform("sum")
    combined_attended  = result.groupby("Base Subject")["Total Lectures Attended"].transform("sum")
    combined_missed    = combined_conducted - combined_attended

    result["Current Cumulative Attendance"] = combined_attended

    result["Attendance Percentage"] = (
        combined_attended / combined_conducted * 100
    ).round(2)

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

    # ---------- TOTAL MISSED (consolidated, show once) ----------
    result["Total Missed"] = combined_missed.astype(int).astype(object)

    # ---------- REMAINING LECTURES (per-row: T1 or U1 separately) ----------
    def calc_remaining(row):
        subj_type = str(row.get("Type", "")).strip() if pd.notna(row.get("Type")) else ""
        base = row["Base Subject"]
        conducted_this_row = row["Total Lectures Conducted"]

        if "U" in subj_type.upper():
            # U1 row: Total Tutorials (U1) from xlsx - conducted this row
            total = match_total_tutorials(base)
        else:
            # T1 row (or subject with no type): Total Lectures (T1) from xlsx - conducted this row
            total = match_total_lectures(base)

        if total is None:
            return None
        return max(0, int(total) - int(conducted_this_row))

    result["Remaining Lectures"] = result.apply(calc_remaining, axis=1)

    # ---------- LECTURES THAT CAN BE MISSED (consolidated, show once) ----------
    # Formula: (Total T1 + Total U1) from xlsx - (Conducted T1 + Conducted U1 from SAP) - Required Cumulative Attendance
    def calc_can_miss(base_subject, current_cumulative, req_cumulative_remaining):
        total_t1 = match_total_lectures(base_subject)
        total_u1 = match_total_tutorials(base_subject)
        if total_t1 is None or total_u1 is None:
            return None
        total_from_xlsx = int(total_t1) + int(total_u1)
        # req_cumulative_remaining is already (Required - Current), clipped to 0
        # So lectures that can still be missed = remaining lectures overall - still need to attend
        remaining_overall = total_from_xlsx - int(current_cumulative)
        can_miss = remaining_overall - int(req_cumulative_remaining)
        return max(0, can_miss)

    result["Lectures That Can Be Missed"] = result.apply(
        lambda row: calc_can_miss(
            row["Base Subject"],
            row["Current Cumulative Attendance"],
            row["Required Cumulative Attendance"]
        ),
        axis=1
    )

    # ---------- HIDE DUPLICATE CONSOLIDATED COLUMNS ----------
    # Mark duplicates within each Base Subject group
    duplicated = result.duplicated("Base Subject")

    # Consolidated columns shown only on first row of each base subject group
    consolidated_cols = [
        "Current Cumulative Attendance",
        "Attendance Percentage",
        "Required Cumulative Attendance",
        "Total Missed",
        "Lectures That Can Be Missed",
    ]
    for col in consolidated_cols:
        result.loc[duplicated, col] = ""

    # Remaining Lectures: keep per-row (T1 and U1 separately) — no blanking needed

    # ---------- SR NO ----------
    result.insert(0, "Sr. No.", range(1, len(result) + 1))

    # ---------- BUILD DISPLAY COLUMNS BASED ON SELECTIONS ----------
    # Mandatory columns always shown
    mandatory_cols = [
        "Sr. No.",
        "Subject",
        "Attendance Percentage",
        "Required Cumulative Attendance",
    ]

    # Optional columns — include if user selected
    optional_col_map = {
        "show_conducted":  "Total Lectures Conducted",
        "show_attended":   "Total Lectures Attended",
        "show_missed":     "Total Missed",
        "show_remaining":  "Remaining Lectures",
        "show_can_miss":   "Lectures That Can Be Missed",
        "show_dates":      "Dates Missed",
    }

    selected_optional = [
        optional_col_map[key]
        for key, selected in optional_selections.items()
        if selected
    ]

    # Define a sensible full order so columns always appear in consistent order
    full_column_order = [
        "Sr. No.",
        "Subject",
        "Total Lectures Conducted",
        "Total Lectures Attended",
        "Total Missed",
        "Current Cumulative Attendance",
        "Attendance Percentage",
        "Required Cumulative Attendance",
        "Remaining Lectures",
        "Lectures That Can Be Missed",
        "Dates Missed",
    ]

    display_cols = [
        c for c in full_column_order
        if c in mandatory_cols or c in selected_optional or c == "Current Cumulative Attendance"
    ]

    display_df = result[display_cols].copy()

    # ---------- PDF ----------
    st.markdown("### Download Report")

    pdf_buffer = io.BytesIO()
    styles = getSampleStyleSheet()

    wrap_style   = ParagraphStyle("wrap",   parent=styles["Normal"], wordWrap="CJK", fontSize=7)
    header_style = ParagraphStyle("header", parent=styles["Normal"], alignment=1,   wordWrap="CJK", fontSize=7, fontName="Helvetica-Bold")

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

    if nu_message:
        elements.append(Paragraph(nu_message, styles["Normal"]))
        elements.append(Spacer(1, 15))

    # --- Build PDF table from display_df ---
    headers = [Paragraph(f"<b>{col}</b>", header_style) for col in display_df.columns]
    table_data = [headers]

    for row in display_df.values.tolist():
        table_data.append([Paragraph(str(v), wrap_style) for v in row])

    page_width = landscape(letter)[0] - 60  # ~690 pts usable

    # Assign relative widths per column — will be normalised to page_width
    col_weight_map = {
        "Sr. No.":                      0.04,
        "Subject":                      0.20,
        "Total Lectures Conducted":     0.08,
        "Total Lectures Attended":      0.08,
        "Total Missed":                 0.07,
        "Current Cumulative Attendance":0.09,
        "Attendance Percentage":        0.08,
        "Required Cumulative Attendance":0.10,
        "Remaining Lectures":           0.08,
        "Lectures That Can Be Missed":  0.09,
        "Dates Missed":                 0.19,
    }

    raw_weights = [col_weight_map.get(c, 0.08) for c in display_df.columns]
    total_weight = sum(raw_weights)
    col_widths = [page_width * (w / total_weight) for w in raw_weights]

    attendance_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    attendance_table.setStyle(
        TableStyle([
            ("GRID",       (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1,  0), colors.lightgrey),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
            ("FONTSIZE",   (0, 0), (-1, -1), 7),
        ])
    )

    elements.append(attendance_table)
    elements.append(Spacer(1, 30))

    # --- Credit reference table ---
    relevant_credit_rows = credit_df[
        (credit_df["Program"] == program) &
        (credit_df["Semester"] == semester)
    ].copy()

    col_key = {
        70: "Required Cumulative Attendance (70%)",
        75: "Required Cumulative Attendance (75%)",
        80: "Required Cumulative Attendance (80%)",
    }[target_percentage]

    relevant_credit_rows["Required Cumulative Attendance"] = relevant_credit_rows[col_key]

    credit_columns = [
        "Program",
        "Semester",
        "Subject",
        "Credits",
        "Required Cumulative Attendance",
    ]

    credit_headers = [Paragraph(f"<b>{c}</b>", header_style) for c in credit_columns]
    credit_data = [credit_headers]

    for _, row in relevant_credit_rows.iterrows():
        credit_data.append(
            [Paragraph(str(row[c]), wrap_style) for c in credit_columns]
        )

    credit_table = Table(credit_data, repeatRows=1)
    credit_table.setStyle(
        TableStyle([
            ("GRID",       (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1,  0), colors.lightgrey),
            ("FONTSIZE",   (0, 0), (-1, -1), 7),
        ])
    )

    elements.append(credit_table)

    doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(letter), leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30)
    doc.build(elements)

    pdf_buffer.seek(0)

    st.download_button(
        label="Download as PDF",
        data=pdf_buffer,
        file_name="attendance_report.pdf",
        mime="application/pdf"
    )

    # ---------- STREAMLIT TABLE ----------
    column_config = {}
    if "Dates Missed" in display_df.columns:
        column_config["Dates Missed"] = st.column_config.TextColumn(width="large")
    if "Attendance Percentage" in display_df.columns:
        column_config["Attendance Percentage"] = st.column_config.NumberColumn(format="%.2f%%")

    st.dataframe(
        display_df,
        height=650,
        use_container_width=True,
        hide_index=True,
        column_config=column_config
    )


# ---------- FOOTER ----------
st.markdown("---")

st.markdown("""
<p style="font-size:0.85rem; color:gray;">
This page is an independent student-created tool developed by <b>Gaurav Khopkar</b>.
It is not affiliated with NMIMS, KPMSOL, or the SAP portal.
</p>
<p style="font-size:0.85rem; color:gray;">
For queries or suggestions or any defects on this page, contact: <b>gauravkhopkar2006@hotmail.com</b>
</p>
<p style="font-size:0.85rem; color:gray;">
Thank you for using this tool.
</p>
""", unsafe_allow_html=True)
