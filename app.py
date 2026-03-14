import streamlit as st
import pdfplumber
import pandas as pd

st.set_page_config(layout="wide")

# ---------------- HEADER ----------------
st.title("KPMSOL Attendance Calculator")
st.markdown("---")
st.caption("Created by Gaurav Khopkar")

st.markdown("### Upload your Detailed Attendance Report from SAP here")
st.caption("From: 2ⁿᵈ Jan 2026 To: Yesterday")

uploaded_file = st.file_uploader("Upload File", type="pdf")

# ---------------- ATTENDANCE TABLE ----------------
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
    result["Attendance Percentage"] = (combined_attended / combined_conducted * 100).round(2)

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
        use_container_width=True,
        height=650,
        hide_index=True
    )

else:

    placeholder = pd.DataFrame({
        "Column 1":["","","",""],
        "Column 2":["","","",""],
        "Column 3":["","","",""]
    })

    st.dataframe(
        placeholder,
        use_container_width=True,
        height=650,
        hide_index=True
    )

# ---------------- CREDIT STRUCTURE ----------------
st.markdown("### Credits")

col1, col2, col3 = st.columns([2,3,2])

with col1:
    st.markdown("**Credits**")
    st.write("4 Credit")
    st.write("3 Credit")
    st.write("2 Credit")

with col2:
    st.markdown("**Total Lectures**")
    st.write("60 Lectures + 15 Tutorials")
    st.write("45 Lectures + 15 Tutorials")
    st.write("30 Lectures")

with col3:
    st.markdown("**Lectures + Tutorials Required**")
    st.write("53")
    st.write("42")
    st.write("21")
