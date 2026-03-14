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

    # Count lectures
    conducted = df.groupby("Subject").size()
    attended = df[df["Attendance"]=="P"].groupby("Subject").size()

    # Collect missed dates
    missed_dates = (
        df[df["Attendance"]=="A"]
        .groupby("Subject")["Date"]
        .apply(lambda x: ", ".join(x.astype(str)))
    )

    # Load template
    template = pd.read_excel("template.xlsx")

    result = template.copy()

    # Map conducted and attended
    result["Total Lectures Conducted"] = result["Subject"].map(conducted).fillna(0)
    result["Total Lectures Attended"] = result["Subject"].map(attended).fillna(0)

    # Map missed dates
    result["Dates Missed"] = result["Subject"].map(missed_dates).fillna("")

    # Remove T1/U1 to combine subjects
    result["Base Subject"] = result["Subject"].str.replace(r" (T1|U1) - Div. C","",regex=True)

    combined_conducted = result.groupby("Base Subject")["Total Lectures Conducted"].transform("sum")
    combined_attended = result.groupby("Base Subject")["Total Lectures Attended"].transform("sum")

    # Excel-equivalent calculations
    TOTAL_COURSE_LECTURES = 60
    TARGET_ATTENDANCE = 0.75

    result["Cumulative Attendance"] = combined_attended

    result["Attendance Percentage"] = (
        combined_attended / combined_conducted * 100
    ).round(2)

    result["Lectures Remaining"] = TOTAL_COURSE_LECTURES - combined_conducted

    result["Lectures to be Attended"] = (
        TARGET_ATTENDANCE * TOTAL_COURSE_LECTURES - combined_attended
    ).clip(lower=0).round(0)

    # Remove helper column
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
