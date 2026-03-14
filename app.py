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

    # Count lectures
    total = df.groupby("Course Name").size()
    present = df[df["Attendance"]=="P"].groupby("Course Name").size()

    summary = pd.DataFrame({
        "Total Lectures Conducted": total,
        "Total Lectures Attended": present
    }).fillna(0)

    summary.reset_index(inplace=True)
    summary.rename(columns={"Course Name":"Subject"}, inplace=True)

    # Identify T1 and U1
    summary["Type"] = summary["Subject"].str.extract(r'(T1|U1)')
    summary["Base Subject"] = summary["Subject"].str.replace(r' (T1|U1) - Div. C','',regex=True)

    # Combined totals for percentage calculation
    combined = summary.groupby("Base Subject").agg({
        "Total Lectures Conducted":"sum",
        "Total Lectures Attended":"sum"
    })

    combined["Attendance Percentage"] = (
        combined["Total Lectures Attended"] /
        combined["Total Lectures Conducted"]
    ) * 100

    combined["Attendance Percentage"] = combined["Attendance Percentage"].round(2)

    combined["Current Absentism"] = (
        combined["Total Lectures Conducted"] -
        combined["Total Lectures Attended"]
    )

    # Total lectures expected in course
    TOTAL_COURSE_LECTURES = 60
    TARGET_ATTENDANCE = 0.75

    combined["Lectures Remaining"] = (
        TOTAL_COURSE_LECTURES -
        combined["Total Lectures Conducted"]
    )

    combined["Total Remaining"] = (
        TOTAL_COURSE_LECTURES -
        combined["Total Lectures Attended"]
    )

    combined["Lectures to be Attended"] = (
        (TARGET_ATTENDANCE * TOTAL_COURSE_LECTURES) -
        combined["Total Lectures Attended"]
    ).clip(lower=0).round(0)

    # Merge combined calculations back to T1/U1 rows
    result = summary.merge(
        combined,
        left_on="Base Subject",
        right_index=True,
        how="left"
    )

    result["Cumulative Attendance"] = result["Total Lectures Attended_x"]

    # Reorder columns
    result = result[[
        "Base Subject",
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

    result.rename(columns={
        "Base Subject":"Subject"
    }, inplace=True)

    st.subheader("Attendance Table")

    st.dataframe(result, use_container_width=True)
