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

        # Format numeric columns with optional full decimals
        def format_number(val):
            try:
                val = float(val)
                if val.is_integer():
                    return f"{int(val):,}"
                else:
                    return f"{val:,}".rstrip('0').rstrip('.')
            except:
                return ""

        formatted_df = combined_df.copy()
        for col in ['Gross Transaction Amount IDR', 'Stamp Duty Fee', 'Fross Transaction Amount (IDR Equivalent)']:
            if col in formatted_df.columns:
                formatted_df[col] = pd.to_numeric(formatted_df[col], errors='coerce')
                formatted_df[col] = formatted_df[col].apply(format_number)

        st.success("Files combined successfully!")
        st.dataframe(formatted_df, use_container_width=True)

        # Convert to Excel and provide download using formatted display values
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            formatted_df.to_excel(writer, index=False, sheet_name='CombinedData')
        output.seek(0)

        st.download_button(
            label="Download Combined Excel File",
            data=output,
            file_name="combined_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Please upload one or more .txt files to begin.")
