import streamlit as st
import pandas as pd
import os
import zipfile
from io import BytesIO
from datetime import datetime
from uszipcode import SearchEngine


@st.cache_data(show_spinner="Loading geo data from local database...")
def load_data():
    """
    Loads county to zip code mapping data using the uszipcode library.
    The data is cached to improve performance.
    """
    try:
        # Use uszipcode SearchEngine to get all zip codes
        # This returns a list of SimpleZipcode objects.
        search = SearchEngine()
        all_zips = search.by_state(state=None, returns=0) # returns=0 gets all zipcodes

        # Convert the list of objects to a list of dictionaries
        zips_list = [z.to_dict() for z in all_zips]

        # Create a pandas DataFrame from the list
        df = pd.DataFrame(zips_list)

        df = df[['zipcode', 'county', 'state']]
        df['zipcode'] = df['zipcode'].astype(str)

        # Create a unique identifier for each county in the format "County, State"
        df['county_state'] = df['county'] + ", " + df['state']
        return df
    except Exception as e:
        st.error(f"Failed to load data. Please check the data source. Error: {e}")
        return pd.DataFrame()

def create_zip_archive(df_filtered):
    """
    Creates a zip archive in memory containing a separate CSV file for each selected county.

    Args:
        df_filtered (pd.DataFrame): A DataFrame containing the data for the selected counties.

    Returns:
        BytesIO: A bytes buffer containing the zip archive.
    """
    zip_buffer = BytesIO()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Group data by the unique 'county_state' identifier
        grouped = df_filtered.groupby('county_state')
        for county_name, group in grouped:
            # Sanitize the county name to create a valid filename
            # e.g., "Los Angeles, California" -> "Los_Angeles_California_20231105_045848.csv"
            filename = f"{county_name.replace(', ', '_').replace(' ', '_')}_{timestamp}.csv"

            # Convert the group's zip codes to a CSV string
            csv_string = group[['zipcode']].to_csv(index=False)

            # Write the CSV string to the zip archive
            zip_file.writestr(filename, csv_string)

    # Reset buffer position to the beginning before returning
    zip_buffer.seek(0)
    return zip_buffer

def main():
    """
    Main function to run the Streamlit application.
    """
    st.set_page_config(layout="wide", page_title="US County to Zip Code Finder")

    st.title("U.S. County to Zip Code Finder")
    st.write("Select one or more counties to view their associated zip codes and download the data.")

    df = load_data()

    if df.empty:
        st.warning("The application could not load the necessary geo data. Please try again later.")
        return

    # --- User Input ---
    st.sidebar.header("Filters")
    all_counties = sorted(df['county_state'].unique())

    selected_counties = st.sidebar.multiselect(
        "Select Counties",
        options=all_counties,
        help="You can select multiple counties from the list."
    )

    # --- Display and Export Logic ---
    if not selected_counties:
        st.info("Please select at least one county from the sidebar to see the results.")
    else:
        # Filter the dataframe based on user selection
        df_filtered = df[df['county_state'].isin(selected_counties)].copy()
        df_display = df_filtered[['county_state', 'zipcode']].rename(columns={'county_state': 'County', 'zipcode': 'Zip Code'})

        st.subheader("Selected Zip Codes")
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        # --- Download Button ---
        st.subheader("Export Data")
        st.write("Click the button below to download a .zip file containing a separate CSV for each selected county.")

        zip_buffer = create_zip_archive(df_filtered)

        st.download_button(
            label="Download Zip Codes as CSVs",
            data=zip_buffer,
            file_name="county_zip_codes.zip",
            mime="application/zip"
        )

if __name__ == "__main__":
    main()
