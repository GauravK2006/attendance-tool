import streamlit as st
import pdfplumber
import pandas as pd

st.set_page_config(layout="wide")

# ---------- PAGE STYLE ----------
st.markdown("""
<style>

.main-container{
    background:#d9d9d9;
    padding:40px;
    border:2px solid #2c3e50;
}

.table-box{
    width:750px;
}

table{
    border-collapse:collapse;
    width:100%;
}

th,td{
    border:1px solid #333;
    padding:8px;
}

thead{
    background:#d9d9d9;
}

</style>
""", unsafe_allow_html=True)

# ---------- MAIN CONTAINER ----------
st.markdown("<div class='main-container'>", unsafe_allow_html=True)

# Header
st.markdown(
"""
<h1 style="font-size:28px;">KPMSOL Attendance Calculator</h1>
<p style="font-size:13px;">Created by Gaurav Khopkar</p>
""",
unsafe_allow_html=True
)

st.markdown("<br>", unsafe_allow_html=True)

# Upload section
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

    st.dataframe(result, width=750, height=200, hide_index=True)

else:

    # Empty placeholder table like the mockup
    placeholder = pd.DataFrame({
        "Column 1":["","","",""],
        "Column 2":["","","",""],
        "Column 3":["","","",""]
    })

    st.dataframe(placeholder, width=750, height=200, hide_index=True)

# ---------- CREDIT STRUCTURE TABLE ----------
st.markdown("<br><br>", unsafe_allow_html=True)

credit_data = {
    "Credits":["4 Credit","3 Credit","2 Credit"],
    "Total Lectures":[
        "60 Lectures + 15 Tutorials",
        "45 Lectures + 15 Tutorials",
        "30 Lectures"
    ],
    "Lectures + Tutorials Required":[
        "53",
        "42",
        "21"
    ]
}

credit_df = pd.DataFrame(credit_data)

st.table(credit_df)

st.markdown("</div>", unsafe_allow_html=True)
