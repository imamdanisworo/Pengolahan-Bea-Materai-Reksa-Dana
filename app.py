# Streamlit App: Combine Multiple Pipe-Separated TXT Files into One Excel Sheet
import streamlit as st
import pandas as pd
import io

# App title
st.title("Combine Multiple TXT Files into One Excel Sheet")

# Instructions
st.markdown("""
Upload multiple `.txt` files where data columns are separated using the pipe character (`|`). 
Each file must have a header row and consistent column structure.
""")

# File uploader
uploaded_files = st.file_uploader("Upload TXT files", type="txt", accept_multiple_files=True)

if uploaded_files:
    combined_df = pd.DataFrame()

    for file in uploaded_files:
        try:
            # Read file with pipe delimiter
            df = pd.read_csv(file, delimiter='|', encoding='utf-8')
            df['source_file'] = file.name  # Optional: add column for source tracking
            combined_df = pd.concat([combined_df, df], ignore_index=True)
        except Exception as e:
            st.error(f"Error reading {file.name}: {e}")

    # Display and download section
    if not combined_df.empty:
        # Remove 'source_file' column if it exists
        if 'source_file' in combined_df.columns:
            combined_df.drop(columns=['source_file'], inplace=True)

        # Reset index and insert auto-number column "No."
        combined_df.reset_index(drop=True, inplace=True)
        if 'No.' in combined_df.columns:
            combined_df.drop(columns=['No.'], inplace=True)
        combined_df.insert(0, 'No.', range(1, len(combined_df) + 1))

        # Prepare formatted copy for display
        def format_number(val):
            try:
                val = float(val)
                if val.is_integer():
                    return f"{int(val):,}"
                else:
                    return f"{val:,}"
            except:
                return ""

        display_df = combined_df.copy()
        for col in ['Stamp Duty Fee', 'Gross Transaction Amount (IDR Equivalent)']:
            if col in display_df.columns:
                display_df[col] = pd.to_numeric(display_df[col], errors='coerce')
                display_df[col] = display_df[col].apply(format_number)

        st.success("Files combined successfully!")
        st.dataframe(display_df, use_container_width=True)

        # Create Excel file using XlsxWriter and apply number formatting
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            combined_df.to_excel(writer, index=False, sheet_name='CombinedData', startrow=1, header=False)

            workbook = writer.book
            worksheet = writer.sheets['CombinedData']

            # Write header manually with bold format
            header_format = workbook.add_format({'bold': True, 'bg_color': '#F9F9F9'})
            for col_num, value in enumerate(combined_df.columns):
                worksheet.write(0, col_num, value, header_format)

            # Apply number format with separator to relevant columns
            number_format = workbook.add_format({'num_format': '#,##0.00'})
            for col in ['Stamp Duty Fee', 'Gross Transaction Amount (IDR Equivalent)']:
                if col in combined_df.columns:
                    col_idx = combined_df.columns.get_loc(col)
                    worksheet.set_column(col_idx, col_idx, 20, number_format)

        output.seek(0)

        st.download_button(
            label="Download Combined Excel File",
            data=output,
            file_name="combined_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Please upload one or more .txt files to begin.")
