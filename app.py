# Final locked version (no reset upload)
import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Materai TXT to Excel Tool", layout="wide")

st.title("📄 Materai TXT to Excel Tool")

st.markdown("""
Upload multiple `.txt` files (pipe `|` separated). Then upload an Excel file for SID-Account lookup.  
Click **✅ Process Files** to preview and **⬇️ Download** the results.
""")

with st.sidebar:
    st.header("📁 File Upload")
    uploaded_txt_files = st.file_uploader("Upload one or more TXT files", type="txt", accept_multiple_files=True)
    uploaded_lookup_file = st.file_uploader("Upload Excel SID Lookup File", type=["xlsx", "xls"])
    process_button = st.button("✅ Process Files")

# Session state to persist across reruns
if 'display_df' not in st.session_state:
    st.session_state.display_df = None
if 'combined_df' not in st.session_state:
    st.session_state.combined_df = None

if uploaded_txt_files and process_button:
    st.info("Processing files... Please wait.")

    combined_df = pd.concat([
        pd.read_csv(file, delimiter='|', encoding='utf-8').assign(source_file=file.name)
        for file in uploaded_txt_files
    ], ignore_index=True)

    combined_df.drop(columns=[col for col in ['source_file', 'No.'] if col in combined_df.columns], inplace=True)
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
            st.error(f"❌ Error reading lookup file: {e}")

    if 'Transaction Type' in combined_df.columns and 'Transaction Date' in combined_df.columns:
        def build_description(row):
            ttype = str(row['Transaction Type'])
            label = 'Subscr' if 'SUBSCR' in ttype.upper() else 'Redemp' if 'REDEMP' in ttype.upper() else ttype[:6]
            try:
                date_fmt = pd.to_datetime(str(row['Transaction Date']), format='%Y%m%d')
                return f"Materai - {label} at {date_fmt.strftime('%d %B %Y')}"
            except:
                return f"Materai - {label} at {row['Transaction Date']}"
        combined_df['Description'] = combined_df.apply(build_description, axis=1)

    if 'Account' in combined_df.columns:
        def clean_account(val):
            if isinstance(val, str):
                val = val.replace('000000', '0000')
                if val.startswith('R10000'):
                    val = 'R10' + val[6:]
                if val.startswith('S10000'):
                    val = 'S10' + val[6:]
            return val
        combined_df['Account'] = combined_df['Account'].apply(clean_account)

    def format_number(val):
        try:
            val = float(val)
            return f"{val:,.0f}" if val.is_integer() else f"{val:,.2f}"
        except:
            return ""

    display_df = combined_df.copy()
    for col in ['Stamp Duty Fee', 'Gross Transaction Amount (IDR Equivalent)']:
        if col in display_df.columns:
            display_df[col] = pd.to_numeric(display_df[col], errors='coerce').apply(format_number)

    st.session_state.display_df = display_df
    st.session_state.combined_df = combined_df
    st.success("✅ Files combined successfully!")

if st.session_state.display_df is not None:
    st.dataframe(st.session_state.display_df, use_container_width=True, height=600)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        st.session_state.combined_df.to_excel(writer, index=False, sheet_name='CombinedData')
        workbook = writer.book
        worksheet = writer.sheets['CombinedData']

        number_format = workbook.add_format({"num_format": "#,##0.00"})
        for col_idx, col_name in enumerate(st.session_state.combined_df.columns):
            if col_name in ['Stamp Duty Fee', 'Gross Transaction Amount (IDR Equivalent)']:
                worksheet.set_column(col_idx, col_idx, 20, number_format)
            else:
                max_len = max(st.session_state.combined_df[col_name].astype(str).map(len).max(), len(str(col_name))) + 2
                worksheet.set_column(col_idx, col_idx, max_len)

    output.seek(0)
    st.download_button(
        label="⬇️ Download Combined Excel File",
        data=output,
        file_name="combined_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

elif not uploaded_txt_files:
    st.warning("⚠️ Please upload at least one .txt file to start.")
