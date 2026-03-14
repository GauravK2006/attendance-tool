import streamlit as st
import pdfplumber
import pandas as pd

st.set_page_config(layout="wide")

# ---------- PAGE STYLE ----------
st.markdown("""
<style>
body {
    background-color:#000;
}
table {
    border-collapse: collapse;
}
thead tr th {
    background-color:#111 !important;
}
tbody tr:nth-child(odd) {
    background-color:#bdbdbd;
}
tbody tr:nth-child(even) {
    background-color:#d0d0d0;
}
</style>
""", unsafe_allow_html=True)

# ---------- HEADER ----------
st.markdown("""
<h1 style="font-size:32px;">KPMSOL Attendance Calculator</h1>
<hr>
<p style="font-size:14px;">Created by Gaurav Khopkar</p>
""", unsafe_allow_html=True)

# ---------- UPLOAD SECTION ----------
st.markdown("### Upload your Detailed Attendance Report from SAP here")
st.caption("From: 2ⁿᵈ Jan 2026 To: Yesterday")

uploaded_file = st.file_uploader("Upload File", type="pdf")

# ---------- CALCULATED TABLE ----------
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

    conducted = df.groupby("Subject").size()
    attended = df[df["Attendance"]=="P"].groupby("Subject").size()

    missed_dates = (
        df[df["Attendance"]=="A"]
        .groupby("Subject")["Date"]
        .apply(lambda x: ", ".join(x.astype(str)))
    )

    result = pd.read_excel("template.xlsx")

    result["Total Lectures Conducted"] = result["Subject"].map(conducted).fillna(0)
    result["Total Lectures Attended"] = result["Subject"].map(attended).fillna(0)
    result["Dates Missed"] = result["Subject"].map(missed_dates).fillna("")

    result["Base Subject"] = result["Subject"].str.replace(r" (T1|U1) - Div. C","",regex=True)

    combined_conducted = result.groupby("Base Subject")["Total Lectures Conducted"].transform("sum")
    combined_attended = result.groupby("Base Subject")["Total Lectures Attended"].transform("sum")

    result["Cumulative Attendance"] = combined_attended

    result["Attendance Percentage"] = (
        combined_attended / combined_conducted * 100
    ).round(2)

    result.drop(columns=["Base Subject"], inplace=True)

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

    st.dataframe(
        result,
        use_container_width=False,
        hide_index=True,
        height=250
    )

# ---------- FIXED CREDIT TABLE ----------
st.markdown("<br>", unsafe_allow_html=True)

credit_data = {
    "Credits": ["4 Credit", "3 Credit", "2 Credit"],
    "Total Lectures": [
        "60 Lectures + 15 Tutorials",
        "45 Lectures + 15 Tutorials",
        "30 Lectures"
    ],
    "Lectures + Tutorials Required": ["53", "42", "21"]
}

credit_df = pd.DataFrame(credit_data)

st.table(credit_df)
