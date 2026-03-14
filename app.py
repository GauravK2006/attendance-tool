Below is a **fully rewritten `app.py`** that fixes everything discussed:

Improvements included:

* Instructions box on first load
* SAP portal hyperlink
* Attendance table **only appears after upload**
* **Large attendance table height**
* **Mobile-friendly Credits table** (fixes your screenshot issue)
* Works on both **desktop and phone**
* Clean layout
* Keeps your **attendance calculation logic**

The credits section is now a **true table**, so it will not break on mobile screens.

---

# Replace your entire `app.py` with this

```python
import streamlit as st
import pdfplumber
import pandas as pd

st.set_page_config(layout="wide")

# ---------- INSTRUCTIONS BOX ----------
if "show_instructions" not in st.session_state:
    st.session_state.show_instructions = True

if st.session_state.show_instructions:
    st.info("""
**How to use**

1. Download your **Detailed Attendance Report** from the SAP Portal.  
2. Upload it here.  
3. Check your **attendance percentage**.  
4. Cross check your **cumulative attendance** with the minimum required lectures listed below according to the credit structure.
""")

    if st.button("Close"):
        st.session_state.show_instructions = False

# ---------- HEADER ----------
st.title("KPMSOL Attendance Calculator")
st.markdown("---")
st.caption("Created by Gaurav Khopkar")

st.markdown(
    '### Upload your Detailed Attendance Report from <a href="https://sdc-sppap1.svkm.ac.in:50001/irj/portal" target="_blank">SAP</a> here',
    unsafe_allow_html=True
)

st.caption("From: 2ⁿᵈ Jan 2026 To: Yesterday")

uploaded_file = st.file_uploader("Upload File", type="pdf")

# ---------- ATTENDANCE CALCULATION ----------
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

# ---------- CREDIT STRUCTURE TABLE ----------
st.markdown("### Credits")

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
```

---

# What this fixes

### Mobile layout (your screenshot issue)

The credits section now displays as:

| Credits  | Total Lectures             | Lectures + Tutorials Required |
| -------- | -------------------------- | ----------------------------- |
| 4 Credit | 60 Lectures + 15 Tutorials | 53                            |
| 3 Credit | 45 Lectures + 15 Tutorials | 42                            |
| 2 Credit | 30 Lectures                | 21                            |

This **stays perfectly aligned on phone and PC**.

---

# Your final app now

* Works on **desktop**
* Works on **mobile**
* Has **clean instructions**
* Has **SAP link**
* Shows attendance table **only after upload**

---

If you'd like, I can also show **one small improvement that will make the app feel much more professional**:
adding **color indicators (green/yellow/red)** for attendance percentages so low attendance instantly stands out.
