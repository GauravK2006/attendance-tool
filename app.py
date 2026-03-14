import streamlit as st
import pdfplumber
import pandas as pd

st.title("Attendance Dashboard")

uploaded_file = st.file_uploader("Upload Attendance PDF", type="pdf")

if uploaded_file:

    rows = []

    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            table = page.extract_table()

            if table:
                for row in table[1:]:
                    rows.append(row)

    df = pd.DataFrame(rows)

    df = df[[1,5]]
    df.columns = ["Course Name","Attendance"]
    df = df.dropna()

    total = df.groupby("Course Name").size()
    present = df[df["Attendance"]=="P"].groupby("Course Name").size()

    summary = pd.DataFrame({
        "Total Lectures Conducted": total,
        "Total Lectures Attended": present
    }).fillna(0)

    summary.reset_index(inplace=True)
    summary.rename(columns={"Course Name":"Subject"}, inplace=True)

    # Combine T1 + U1 rows
    summary["Base Subject"] = summary["Subject"].str.replace(" T1 - Div. C","", regex=False)
    summary["Base Subject"] = summary["Base Subject"].str.replace(" U1 - Div. C","", regex=False)

    grouped = summary.groupby("Base Subject").agg({
        "Total Lectures Conducted":"sum",
        "Total Lectures Attended":"sum"
    })

    grouped["Cumulative Attendance"] = grouped["Total Lectures Attended"]

    grouped["Attendance Percentage"] = (
        grouped["Total Lectures Attended"] /
        grouped["Total Lectures Conducted"]
    ) * 100

    grouped["Attendance Percentage"] = grouped["Attendance Percentage"].round(2)

    grouped["Current Absentism"] = (
        grouped["Total Lectures Conducted"] -
        grouped["Total Lectures Attended"]
    )

    st.subheader("Attendance Table")

    st.dataframe(grouped)
