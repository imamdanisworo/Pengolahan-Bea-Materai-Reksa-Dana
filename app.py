# Final locked version with auto-clear after download
import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Materai TXT to Excel Tool", layout="centered")

st.title("Combine Multiple TXT Files into One Excel Sheet with Lookup")

st.markdown("""
Upload multiple `.txt` files (pipe `|` separated). Then upload an Excel file for SID-Account lookup.
Click **Process Files** to preview and download the results. After download, files will auto-clear.
""")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Upload TXT Files")
    uploaded_txt_files = st.file_uploader("TXT files", type="txt", accept_multiple_files=True, key=str(st.session_state.get('txt_key', 'txt')))

with col2:
    st.subheader("Upload Excel Lookup File")
    uploaded_lookup_file = st.file_uploader("Excel file for SID lookup", type=["xlsx", "xls"], key=str(st.session_state.get('lookup_key', 'lookup')))

if uploaded_txt_files and st.button("Process Files"):
    combined_df = pd.concat([
        pd.read_csv(file, delimiter='|', encoding='utf-8').assign(source_file=file.name)
        for file in uploaded_txt_files
    ], ignore_index=True)

    if 'source_file' in combined_df.columns:
        combined_df.drop(columns=['source_file'], inplace=True)

    combined_df.reset_index(drop=True, inplace=True)
    if 'No.' in combined_df.columns:
        combined_df.drop(columns=['No.'], inplace=True)
    combined_df.insert(0, 'No.', range(1, len(combined_df) + 1))

    if uploaded_lookup_file:
        try:
            lookup_df = pd.read_excel(uploaded_lookup_file, dtype=str).drop_duplicates(subset='SID')
            combined_df['SID Number'] = combined_df['SID Number'].astype(str)
            lookup_df['SID'] = lookup_df['SID'].astype(str)
            combined_df = combined_df.merge(
                lookup_df[['SID', 'Account']],
                how='left',
                left_on='SID Number',
                right_on='SID',
                validate='many_to_one'
            ).drop(columns=['SID'])
        except Exception as e:
            st.error(f"Error reading lookup file: {e}")

    preview_df = combined_df.copy()

    if 'Transaction Type' in preview_df.columns and 'Transaction Date' in preview_df.columns:
        def build_description(row):
            ttype = str(row['Transaction Type'])
            label = 'Subscr' if 'SUBSCR' in ttype.upper() else 'Redemp' if 'REDEMP' in ttype.upper() else ttype[:6]
            try:
                date_fmt = pd.to_datetime(str(row['Transaction Date']), format='%Y%m%d')
                return f"Materai - {label} at {date_fmt.strftime('%d %B %Y')}"
            except:
                return f"Materai - {label} at {row['Transaction Date']}"
        preview_df['Description'] = preview_df.apply(build_description, axis=1)

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
            return f"{val:,}" if not val.is_integer() else f"{int(val):,}"
        except:
            return ""

    display_df = preview_df.copy()
    for col in ['Stamp Duty Fee', 'Gross Transaction Amount (IDR Equivalent)']:
        if col in display_df.columns:
            display_df[col] = pd.to_numeric(display_df[col], errors='coerce').apply(format_number)

    st.success("Files combined successfully!")
    st.dataframe(display_df, use_container_width=True)

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
                max_len = max(preview_df[col_name].astype(str).map(len).max(), len(str(col_name))) + 2
                worksheet.set_column(col_idx, col_idx, max_len)

    output.seek(0)
    download_clicked = st.download_button(
        label="Download Combined Excel File",
        data=output,
        file_name="combined_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    if download_clicked:
        st.session_state.txt_key = 'txt' + str(pd.Timestamp.now().timestamp())
        st.session_state.lookup_key = 'lookup' + str(pd.Timestamp.now().timestamp())
        st.experimental_rerun()
else:
    if not uploaded_txt_files:
        st.info("Please upload one or more .txt files to begin.")
