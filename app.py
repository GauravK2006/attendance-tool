import streamlit as st
import pdfplumber
import pandas as pd
import io
from reportlab.platypus import SimpleDocTemplate, Table
from reportlab.lib.pagesizes import letter

st.set_page_config(
    page_title="KPMSOL Attendance Calculator",
    page_icon="📊",
    layout="wide"
)

# ---------- INSTRUCTIONS ----------
if "show_instructions" not in st.session_state:
    st.session_state.show_instructions = True

if st.session_state.show_instructions:
    st.info("""
**How to use**

1. Download your **Detailed Attendance Report** from the SAP Portal and upload it here.
2. Note that SAP Portal only works between 18:00 to 07:00. 
3. Check your **attendance percentage**.  
4. Cross check your **cumulative attendance** with the minimum required lectures listed below according to the credit structure.
5. The uploaded attendance report is processed temporarily in memory and is not stored anywhere. Once the session ends, the file is completely gone.
""")

    if st.button("Close"):
        st.session_state.show_instructions = False


# ---------- HEADER ----------
st.markdown("""
<h1 style="margin-bottom:5px;">KPMSOL Attendance Calculator</h1>
<hr style="margin-top:0px; margin-bottom:10px;">
""", unsafe_allow_html=True)

st.caption("Created by Gaurav Khopkar")

st.markdown(
    '### Upload your Detailed Attendance Report from <a href="https://sdc-sppap1.svkm.ac.in:50001/irj/portal" target="_blank">SAP</a> here',
    unsafe_allow_html=True
)

st.caption("From: 2ⁿᵈ Jan 2026 To: Yesterday")

uploaded_file = st.file_uploader("Upload File", type="pdf")


# ---------- PROCESS PDF ----------
if uploaded_file:

    with st.spinner("Processing attendance report..."):

        rows = []

        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                table = page.extract_table()

                if table:
                    for row in table[1:]:
                        rows.append(row)

        if len(rows) == 0:
            st.error("Invalid file. Please upload the Detailed Attendance Report from SAP.")
            st.stop()

        df = pd.DataFrame(rows)

        try:
            df = df[[1,2,5]]
        except:
            st.error("Invalid file. Please upload the Detailed Attendance Report from SAP.")
            st.stop()

        df.columns = ["Subject","Date","Attendance"]
        df = df.dropna()

        # ---------- NU DETECTION ----------
        nu_rows = df[df["Attendance"] == "NU"]

        if not nu_rows.empty:

            nu_count = len(nu_rows)

            try:
                nu_date = pd.to_datetime(nu_rows["Date"]).max().strftime("%d %B")
            except:
                nu_date = nu_rows["Date"].iloc[0]

            st.warning(f"{nu_count} lecture(s) from {nu_date} are marked as Not Updated (NU).")

        # ---------- LAST UPDATED DATE ----------
        try:
            latest_date = pd.to_datetime(df["Date"]).max().strftime("%d %B %Y")
        except:
            latest_date = df["Date"].max()

        # ---------- REMOVE NU FROM CALCULATIONS ----------
        df_calc = df[df["Attendance"] != "NU"]

        # ---------- SUBJECT LIST ----------
        subjects = df_calc["Subject"].unique()

        result = pd.DataFrame({
            "Subject": subjects
        })

        conducted = df_calc.groupby("Subject").size()
        attended = df_calc[df_calc["Attendance"]=="P"].groupby("Subject").size()

        missed_dates = (
            df_calc[df_calc["Attendance"]=="A"]
            .groupby("Subject")["Date"]
            .apply(lambda x: ", ".join(x.astype(str)))
        )

        result["Total Lectures Conducted"] = result["Subject"].map(conducted).fillna(0)
        result["Total Lectures Attended"] = result["Subject"].map(attended).fillna(0)
        result["Dates Missed"] = result["Subject"].map(missed_dates).fillna("")

        # ---------- GROUP T1 & U1 ----------
        result["Base Subject"] = result["Subject"].str.replace(r" (T1|U1).*","",regex=True)
        result["Type"] = result["Subject"].str.extract(r"(T1|U1)")

        result = result.sort_values(by=["Base Subject","Type"])

        combined_conducted = result.groupby("Base Subject")["Total Lectures Conducted"].transform("sum")
        combined_attended = result.groupby("Base Subject")["Total Lectures Attended"].transform("sum")

        result["Cumulative Attendance"] = combined_attended
        result["Attendance Percentage"] = (combined_attended / combined_conducted * 100).round(2)

        result.drop(columns=["Base Subject","Type"], inplace=True)

        result.insert(0, "Sr. No.", range(1, len(result)+1))

        result = result[
            [
                "Sr. No.",
                "Subject",
                "Total Lectures Conducted",
                "Total Lectures Attended",
                "Cumulative Attendance",
                "Attendance Percentage",
                "Dates Missed"
            ]
        ]

    # ---------- DISPLAY TABLE ----------
    st.dataframe(
        result,
        use_container_width=True,
        height=650,
        hide_index=True
    )

    st.caption(f"Report generated from data up to: {latest_date}")


    # ---------- DOWNLOAD OPTIONS ----------
    st.markdown("### Download Report")

    col1, col2 = st.columns(2)

    # Excel
    excel_buffer = io.BytesIO()

    with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
        result.to_excel(writer, index=False, sheet_name="Attendance")

    excel_buffer.seek(0)

    col1.download_button(
        label="Download as Excel (.xlsx)",
        data=excel_buffer,
        file_name="attendance_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ---------- PDF DOWNLOAD ----------

from reportlab.platypus import SimpleDocTemplate, Table, Paragraph, Spacer
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet

pdf_buffer = io.BytesIO()

styles = getSampleStyleSheet()

table_data = [result.columns.tolist()] + result.values.tolist()

# manual column widths (points)
col_widths = [
    180,  # Subject
    90,   # Conducted
    90,   # Attended
    120,  # Cumulative
    120,  # Percentage
    250   # Dates Missed
]

table = Table(
    table_data,
    colWidths=col_widths
)

title = Paragraph("<b>Attendance Report</b>", styles["Title"])

header = Paragraph(
    "This file was downloaded from KPMSOL Attendance Calculator (unofficial)",
    styles["Normal"]
)

elements = [
    title,
    Spacer(1,10),
    header,
    Spacer(1,20),
    table
]

pdf = SimpleDocTemplate(
    pdf_buffer,
    pagesize=landscape(letter)
)

pdf.build(elements)

pdf_buffer.seek(0)

col2.download_button(
    label="Download as PDF (.pdf)",
    data=pdf_buffer,
    file_name="attendance_report.pdf",
    mime="application/pdf"
)
# ---------- CREDIT STRUCTURE ----------
st.markdown("### Credits")

credit_data = {
    "Credits": ["4 Credit", "3 Credit", "2 Credit", "Non-Credit"],
    "Total Lectures": [
        "60 Lectures + 15 Tutorials",
        "45 Lectures + 15 Tutorials",
        "30 Lectures",
        "30 Lectures"
    ],
    "Lectures + Tutorials Required": ["53", "42", "21", "21"]
}

credit_df = pd.DataFrame(credit_data)

st.dataframe(credit_df, hide_index=True, use_container_width=True)


# ---------- FOOTER ----------
st.markdown("---")

st.markdown(
"""
<p style="font-size:0.85rem; color:gray;">
This page is an independent student-created tool developed by <b>Gaurav Khopkar</b> for convenience in estimating attendance from the SAP Detailed Attendance Report. 
It is not affiliated with or endorsed by NMIMS, KPMSOL, or the SAP portal, and the official records on SAP shall prevail in case of any discrepancy.

<br>
<p style="font-size:0.85rem; color:gray;">
For any defects, queries, or suggestions, contact: <b>gauravkhopkar2006@hotmail.com</b>

<br>
<p style="font-size:0.85rem; color:gray;">
Thank you for using this tool.
</p>
""",
unsafe_allow_html=True
)
