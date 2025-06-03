# Streamlit App: Combine Multiple Text Files into One Excel Sheet
import streamlit as st
import pandas as pd
import io
from zipfile import ZipFile

# App title
st.title("Combine Multiple TXT Files into One Excel Sheet")

# File uploader
uploaded_files = st.file_uploader("Upload TXT files", type="txt", accept_multiple_files=True)

if uploaded_files:
    combined_df = pd.DataFrame()

    for file in uploaded_files:
        try:
            df = pd.read_csv(file, delimiter='\t', engine='python')
            df['source_file'] = file.name
            combined_df = pd.concat([combined_df, df], ignore_index=True)
        except Exception as e:
            st.error(f"Error reading {file.name}: {e}")

    st.success("Files combined successfully!")
    st.dataframe(combined_df)

    # Download button for Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        combined_df.to_excel(writer, index=False, sheet_name='CombinedData')
    output.seek(0)

    st.download_button(
        label="Download Combined Excel File",
        data=output,
        file_name="combined_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Please upload one or more .txt files to begin.")
