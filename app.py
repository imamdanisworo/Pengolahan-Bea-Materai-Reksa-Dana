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

# Process button
if uploaded_txt_files and st.button("Process Files"):
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

        # Perform SID lookup if Excel uploaded
        if uploaded_lookup_file:
            try:
                lookup_df = pd.read_excel(uploaded_lookup_file, dtype=str)
                if 'SID' in lookup_df.columns and 'Account' in lookup_df.columns:
                    lookup_df = lookup_df.drop_duplicates(subset='SID')
                    combined_df['SID Number'] = combined_df['SID Number'].astype(str)
                    lookup_df['SID'] = lookup_df['SID'].astype(str)
                    combined_df = combined_df.merge(
                        lookup_df[['SID', 'Account']],
                        how='left',
                        left_on='SID Number',
                        right_on='SID',
                        validate='many_to_one'
                    )
                    combined_df.drop(columns=['SID'], inplace=True)
                else:
                    st.warning("Lookup file must contain columns 'SID' and 'Account'.")
            except Exception as e:
                st.error(f"Error reading lookup file: {e}")

        preview_df = combined_df.copy()

        # Add custom Materai description column
        if 'Transaction Type' in preview_df.columns and 'Transaction Date' in preview_df.columns:
            def build_description(row):
                ttype = str(row['Transaction Type'])
                if 'SUBSCR' in ttype.upper():
                    label = 'Subscr'
                elif 'REDEMP' in ttype.upper():
                    label = 'Redemp'
                else:
                    label = ttype[:6]
                try:
                    date_str = str(row['Transaction Date'])
                    date_fmt = pd.to_datetime(date_str, format='%Y%m%d')
                    date_out = date_fmt.strftime('%d %B %Y')
                except:
                    date_out = date_str
                return f"Materai - {label} at {date_out}"

            preview_df['Description'] = preview_df.apply(build_description, axis=1)

        # Fix formatting in 'Account' column only for preview table
        if 'Account' in preview_df.columns:
            def clean_account(val):
                if isinstance(val, str):
                    val = val.replace('000000', '0000')
                    if val.startswith('R10000'):
                        val = 'R10' + val[6:]
                    if val.startswith('S10000'):
                        val = 'S10' + val[6:]
                return val

            preview_df['Account'] = preview_df['Account'].apply(clean_account)

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
            preview_df.to_excel(writer, index=False, sheet_name='CombinedData')
            workbook = writer.book
            worksheet = writer.sheets['CombinedData']

            number_format = workbook.add_format({"num_format": "#,##0.00"})
            for col_idx, col_name in enumerate(preview_df.columns):
                if col_name in ['Stamp Duty Fee', 'Gross Transaction Amount (IDR Equivalent)']:
                    worksheet.set_column(col_idx, col_idx, 20, number_format)
                else:
                    series = preview_df[col_name].astype(str)
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
    if not uploaded_txt_files:
        st.info("Please upload one or more .txt files to begin.")
