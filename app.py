# Streamlit App: Combine Multiple Pipe-Separated TXT Files into One Excel Sheet with Lookup
import streamlit as st
import pandas as pd
import io

# App title
st.title("Combine Multiple TXT Files into One Excel Sheet with Lookup")

# Instructions
st.markdown("""
Upload multiple `.txt` files where data columns are separated using the pipe character (`|`).
Each file must have a header row and consistent column structure.
Additionally, you may upload an Excel file to provide lookup values.
""")

# Split layout into two columns
col1, col2 = st.columns(2)

# Left: TXT file uploader
with col1:
    st.subheader("Upload TXT Files")
    uploaded_txt_files = st.file_uploader("Upload TXT files", type="txt", accept_multiple_files=True, key="txt")

# Right: Excel lookup uploader
with col2:
    st.subheader("Upload Excel Lookup File")
    uploaded_lookup_file = st.file_uploader("Upload Excel file for lookup values", type=["xlsx", "xls"], key="lookup")

if uploaded_txt_files:
    combined_df = pd.DataFrame()

    for file in uploaded_txt_files:
        try:
            df = pd.read_csv(file, delimiter='|', encoding='utf-8')
            df['source_file'] = file.name
            combined_df = pd.concat([combined_df, df], ignore_index=True)
        except Exception as e:
            st.error(f"Error reading {file.name}: {e}")

    if not combined_df.empty:
        if 'source_file' in combined_df.columns:
            combined_df.drop(columns=['source_file'], inplace=True)

        combined_df.reset_index(drop=True, inplace=True)
        if 'No.' in combined_df.columns:
            combined_df.drop(columns=['No.'], inplace=True)
        combined_df.insert(0, 'No.', range(1, len(combined_df) + 1))

        preview_df = combined_df.copy()

        def format_number(val):
            try:
                val = float(val)
                if val.is_integer():
                    return f"{int(val):,}"
                else:
                    return f"{val:,}"
            except:
                return ""

        display_df = preview_df.copy()
        for col in ['Stamp Duty Fee', 'Gross Transaction Amount (IDR Equivalent)']:
            if col in display_df.columns:
                display_df[col] = pd.to_numeric(display_df[col], errors='coerce')
                display_df[col] = display_df[col].apply(format_number)

        st.success("Files combined successfully!")
        st.dataframe(display_df, use_container_width=True)

        # Excel Export Section
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            combined_df.to_excel(writer, index=False, sheet_name='CombinedData')
            workbook = writer.book
            worksheet = writer.sheets['CombinedData']

            number_format = workbook.add_format({"num_format": "#,##0.00"})
            for col_idx, col_name in enumerate(combined_df.columns):
                if col_name in ['Stamp Duty Fee', 'Gross Transaction Amount (IDR Equivalent)']:
                    worksheet.set_column(col_idx, col_idx, 20, number_format)
                else:
                    series = combined_df[col_name].astype(str)
                    max_len = max(series.map(len).max(), len(str(col_name))) + 2
                    worksheet.set_column(col_idx, col_idx, max_len)

        output.seek(0)
        st.download_button(
            label="Download Combined Excel File",
            data=output,
            file_name="combined_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Please upload one or more .txt files to begin.")
