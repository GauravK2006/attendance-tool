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

    # Count lectures conducted and attended
    conducted = df.groupby("Course Name").size()
    attended = df[df["Attendance"]=="P"].groupby("Course Name").size()

    summary = pd.DataFrame({
        "Subject Full": conducted.index,
        "Total Lectures Conducted": conducted.values,
        "Total Lectures Attended": attended.reindex(conducted.index, fill_value=0).values
    })

    # Identify T1 / U1
    summary["Type"] = summary["Subject Full"].str.extract(r"(T1|U1)")
    summary["Subject"] = summary["Subject Full"].str.replace(r" (T1|U1) - Div. C","",regex=True)

    # Combined totals (T1 + U1)
    combined = summary.groupby("Subject").agg({
        "Total Lectures Conducted":"sum",
        "Total Lectures Attended":"sum"
    })

    # Course constants (change if needed)
    TOTAL_COURSE_LECTURES = 60
    TARGET_PERCENT = 0.75

    combined["Attendance Percentage"] = (
        combined["Total Lectures Attended"] /
        combined["Total Lectures Conducted"]
    ) * 100

    combined["Attendance Percentage"] = combined["Attendance Percentage"].round(2)

    combined["Current Absentism"] = (
        combined["Total Lectures Conducted"] -
        combined["Total Lectures Attended"]
    )

    combined["Lectures Remaining"] = (
        TOTAL_COURSE_LECTURES -
        combined["Total Lectures Conducted"]
    )

    combined["Total Remaining"] = (
        TOTAL_COURSE_LECTURES -
        combined["Total Lectures Attended"]
    )

    combined["Lectures to be Attended"] = (
        TARGET_PERCENT * TOTAL_COURSE_LECTURES -
        combined["Total Lectures Attended"]
    ).clip(lower=0).round(0)

    # Map combined calculations back to each T1/U1 row
    summary["Attendance Percentage"] = summary["Subject"].map(combined["Attendance Percentage"])
    summary["Current Absentism"] = summary["Subject"].map(combined["Current Absentism"])
    summary["Lectures Remaining"] = summary["Subject"].map(combined["Lectures Remaining"])
    summary["Total Remaining"] = summary["Subject"].map(combined["Total Remaining"])
    summary["Lectures to be Attended"] = summary["Subject"].map(combined["Lectures to be Attended"])

    summary["Cumulative Attendance"] = summary["Total Lectures Attended"]

    # Final column order
    result = summary[[
        "Subject",
        "Type",
        "Total Lectures Conducted",
        "Total Lectures Attended",
        "Cumulative Attendance",
        "Lectures Remaining",
        "Total Remaining",
        "Attendance Percentage",
        "Current Absentism",
        "Lectures to be Attended"
    ]]

    st.subheader("Attendance Table")

    st.dataframe(result, use_container_width=True)
