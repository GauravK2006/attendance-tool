import streamlit as st
import pdfplumber
import pandas as pd

st.set_page_config(layout="wide")

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

    # Remove old cumulative column from template
    if "Cumulative Attendance" in result.columns:
        result.drop(columns=["Cumulative Attendance"], inplace=True)

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

    st.subheader("Attendance Table")

    st.dataframe(
        result,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Dates Missed": st.column_config.TextColumn(
                "Dates Missed",
                width="large"
            )
        }
    )
