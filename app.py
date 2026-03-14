import streamlit as st
import pdfplumber
import pandas as pd

# Page layout
st.set_page_config(layout="wide")

# Title section
st.markdown(
    """
    <h1 style='font-size:34px;'>KPMSOL Attendance Calculator</h1>
    <hr>
    <p style='font-size:14px;'>Created by Gaurav Khopkar</p>
    """,
    unsafe_allow_html=True
)

# Upload section
st.markdown("### Upload your Detailed Attendance Report from SAP here")
st.caption("From: 2nd Jan 2026 To: Yesterday")

uploaded_file = st.file_uploader("Upload File", type="pdf")

# Process PDF
if uploaded_file:

    rows = []

    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            table = page.extract_table()

            if table:
                for row in table[1:]:
                    rows.append(row)

    df = pd.DataFrame(rows)

    df = df[[1,2,5]]
    df.columns = ["Subject","Date","Attendance"]
    df = df.dropna()

    # Lecture counts
    conducted = df.groupby("Subject").size()
    attended = df[df["Attendance"]=="P"].groupby("Subject").size()

    # Dates missed
    missed_dates = (
        df[df["Attendance"]=="A"]
        .groupby("Subject")["Date"]
        .apply(lambda x: ", ".join(x.astype(str)))
    )

    # Load template for subject order
    result = pd.read_excel("template.xlsx")

    result["Total Lectures Conducted"] = result["Subject"].map(conducted).fillna(0)
    result["Total Lectures Attended"] = result["Subject"].map(attended).fillna(0)
    result["Dates Missed"] = result["Subject"].map(missed_dates).fillna("")

    # Combine T1 and U1 for calculations
    result["Base Subject"] = result["Subject"].str.replace(r" (T1|U1) - Div. C","",regex=True)

    combined_conducted = result.groupby("Base Subject")["Total Lectures Conducted"].transform("sum")
    combined_attended = result.groupby("Base Subject")["Total Lectures Attended"].transform("sum")

    result["Cumulative Attendance"] = combined_attended

    result["Attendance Percentage"] = (
        combined_attended / combined_conducted * 100
    ).round(2)

    result.drop(columns=["Base Subject"], inplace=True)

    # Keep only columns from template
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

    # Calculated table
    st.markdown("### Calculated Attendance")

    st.dataframe(
        result,
        use_container_width=False,
        hide_index=True,
        height=350,
        column_config={
            "Dates Missed": st.column_config.TextColumn(
                "Dates Missed",
                width="large"
            )
        }
    )

# Static credit structure table
st.markdown("### Credit Structure")

credit_data = {
    "Credit": ["4 Credit", "3 Credit", "2 Credit"],
    "Structure": [
        "60 Lectures + 15 Tutorials",
        "45 Lectures + 15 Tutorials",
        "30 Lectures"
    ]
}

credit_df = pd.DataFrame(credit_data)

st.table(credit_df)
