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

    # Count conducted lectures
    conducted = df.groupby("Subject").size()

    # Count attended lectures
    attended = df[df["Attendance"]=="P"].groupby("Subject").size()

    # Collect dates missed
    missed = (
        df[df["Attendance"]=="A"]
        .groupby("Subject")["Date"]
        .apply(lambda x: ", ".join(x.astype(str)))
    )

    # Load template
    template = pd.read_excel("template.xlsx")

    result = template.copy()

    # Fill values according to template order
    result["Total Lectures Conducted"] = result["Subject"].map(conducted).fillna(0)
    result["Total Lectures Attended"] = result["Subject"].map(attended).fillna(0)
    result["Dates Missed"] = result["Subject"].map(missed).fillna("")

    # Calculate cumulative attendance (T1 + U1)
    base_subject = result["Subject"].str.replace(r" (T1|U1) - Div. C","",regex=True)

    combined_conducted = result.groupby(base_subject)["Total Lectures Conducted"].transform("sum")
    combined_attended = result.groupby(base_subject)["Total Lectures Attended"].transform("sum")

    result["Cumulative Attendance "] = combined_attended

    # Attendance %
    result["Attendance Percentage"] = (
        combined_attended / combined_conducted * 100
    ).round(2)

    # Course constants (edit if needed)
    TOTAL_COURSE_LECTURES = 60
    TARGET = 0.75

    result["Lectures Remaining"] = TOTAL_COURSE_LECTURES - combined_conducted

    result["Lectures to be Atended"] = (
        TARGET * TOTAL_COURSE_LECTURES - combined_attended
    ).clip(lower=0).round(0)

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
