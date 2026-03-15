import streamlit as st
import pdfplumber
import pandas as pd
import io

from reportlab.platypus import SimpleDocTemplate, Table, Paragraph, Spacer, TableStyle
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

st.set_page_config(
    page_title="KPMSOL Attendance Calculator",
    page_icon="📊",
    layout="wide"
)

# ---------- HEADER ----------
st.markdown("""
<h1 style="margin-bottom:5px;">KPMSOL Attendance Calculator</h1>
<hr style="margin-top:0px; margin-bottom:10px;">
""", unsafe_allow_html=True)

st.caption("Created by Gaurav Khopkar")

# ---------- BLUE INFO BOX ----------
st.info("""
**How to use**

1. Download your **Detailed Attendance Report** from the SAP Portal. Upload it here.  
2. Note that SAP Portal only displays attendance between 18:00 to 07:00.
3. The tool will automatically calculate your **attendance percentage**.  
4. Cross-check your **cumulative attendance** with the minimum lectures required below.
5. The uploaded attendance report is processed temporarily in memory and is not stored anywhere. Once the session ends, the file is completely gone.
""")

st.markdown(
'### Upload your Detailed Attendance Report from <a href="https://sdc-sppap1.svkm.ac.in:50001/irj/portal" target="_blank">SAP</a> here',
unsafe_allow_html=True
)

st.caption("From: 2ⁿᵈ Jan 2026 To: Yesterday")

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
    nu_message = None

    if not nu_rows.empty:

        nu_count = len(nu_rows)

        try:
            nu_date = pd.to_datetime(nu_rows["Date"]).max().strftime("%d %B")
        except:
            nu_date = nu_rows["Date"].iloc[0]

        nu_message = f"{nu_count} lecture(s) from {nu_date} are marked as Not Updated (NU)."

        st.warning(nu_message)

    # remove NU from calculations
    df_calc = df[df["Attendance"] != "NU"]

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

    # ---------- GROUP T1 AND U1 ----------
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

    # ---------- SHOW TABLE ----------
    st.dataframe(
        result,
        use_container_width=True,
        height=650,
        hide_index=True
    )

    # ---------- DOWNLOAD PDF ----------
    st.markdown("### Download Report")

    pdf_buffer = io.BytesIO()
    styles = getSampleStyleSheet()

    headers = []
    for col in result.columns:
        headers.append(Paragraph("<b>{}</b>".format(col), styles["Normal"]))

    table_data = [headers]

    for row in result.values.tolist():

        wrapped_row = []

        for cell in row:
            wrapped_row.append(Paragraph(str(cell), styles["Normal"]))

        table_data.append(wrapped_row)

    page_width = landscape(letter)[0] - 80
    num_cols = len(result.columns)
    col_width = page_width / num_cols

    table = Table(
        table_data,
        colWidths=[col_width]*num_cols,
        repeatRows=1
    )

    table.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),0.5,colors.grey),
        ("BACKGROUND",(0,0),(-1,0),colors.lightgrey),
        ("VALIGN",(0,0),(-1,-1),"TOP")
    ]))

    elements = []

    elements.append(Paragraph("<b>Attendance Report</b>", styles["Title"]))
    elements.append(Spacer(1,10))

    elements.append(
        Paragraph(
            "This file was downloaded from KPMSOL Attendance Calculator (unofficial)",
            styles["Normal"]
        )
    )

    if nu_message:
        elements.append(Spacer(1,10))
        elements.append(Paragraph(nu_message, styles["Normal"]))

    elements.append(Spacer(1,20))
    elements.append(table)

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

# ---------- CREDITS TABLE ----------
st.markdown("### Credits")

credit_data = {
    "Credits": ["4 Credit","3 Credit","2 Credit","Non-Credit"],
    "Total Lectures": [
        "60 Lectures + 15 Tutorials",
        "45 Lectures + 15 Tutorials",
        "30 Lectures",
        "30 Lectures"
    ],
    "Lectures + Tutorials Required": ["53","42","21","21"]
}

credit_df = pd.DataFrame(credit_data)

st.dataframe(
    credit_df,
    hide_index=True,
    use_container_width=True
)

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
