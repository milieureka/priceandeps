import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime

# Set page configuration
st.set_page_config(
    page_title="EPS and Share Price Visualization",
    page_icon="📊",
    layout="wide",
)

# App title
st.title("📈 EPS and Share Price Visualization")

# Read the CSV file from the same directory
data_file = 'data.csv'

try:
    # Read the CSV file, include all columns including blanks
    df = pd.read_csv(data_file, header=0, skip_blank_lines=False)
except FileNotFoundError:
    st.error(f"Data file '{data_file}' not found. Please ensure the file is in the same directory as this app.")
    st.stop()

# Initialize variables
company_data = {}  # Dictionary to hold data for each company
num_columns = df.shape[1]
i = 0

# Iterate over columns to extract company data
while i < num_columns:
    # Check if the current column has a company name
    company_name = df.columns[i]
    if pd.isna(company_name) or company_name.strip() == '':
        i += 1  # Skip blank columns
        continue

    # Extract columns for the company (Date, EPS, Share Price)
    cols = df.columns[i:i+3]
    company_df = df[cols].copy()

    # Rename columns
    company_df.columns = ['Date', 'EPS', 'Share Price']

    # Handle missing data
    company_df = company_df.dropna(subset=['Date']).reset_index(drop=True)
    company_df['Date'] = pd.to_datetime(company_df['Date'], errors='coerce')
    company_df['EPS'] = pd.to_numeric(company_df['EPS'], errors='coerce')
    company_df['Share Price'] = pd.to_numeric(company_df['Share Price'], errors='coerce')

    # Store the DataFrame in the dictionary
    company_data[company_name.strip()] = company_df

    # Move to the next company's data (3 data columns + 1 blank column)
    i += 4

# List of company names
companies = list(company_data.keys())

# Sidebar for user input
st.sidebar.header("User Input")
selected_company = st.sidebar.selectbox("Select a Company", companies)

data_frequency = st.sidebar.radio("Select Data Frequency", options=["Quarterly", "Annual"])

if selected_company:
    # Get the DataFrame for the selected company
    company_df = company_data[selected_company]

    if not company_df.empty:
        # Determine the available date range
        min_date = company_df['Date'].min()
        max_date = company_df['Date'].max()
        min_year = min_date.year
        max_year = max_date.year

        # Date range selection
        start_year, end_year = st.sidebar.select_slider(
            "Select Date Range",
            options=range(min_year, max_year + 1),
            value=(min_year, max_year)
        )

        # Filter the company_df based on the selected date range
        company_df = company_df[(company_df['Date'].dt.year >= start_year) & (company_df['Date'].dt.year <= end_year)]

        if data_frequency == "Annual":
            # Exclude the current year if not finished
            current_year = datetime.datetime.now().year

            # Remove the last year if it's equal to or greater than the current year
            company_df = company_df[company_df['Date'].dt.year < current_year]

            # Group by year and aggregate data
            company_df['Year'] = company_df['Date'].dt.year
            # Use the last EPS and last Share Price of the year
            aggregated_df = company_df.sort_values('Date').groupby('Year').agg({
                'EPS': 'last',
                'Share Price': 'last',
                'Date': 'last'
            }).reset_index()

            growth_label = 'YoY'
        else:
            # Use quarterly data
            # Ensure 'Quarter' column is present
            company_df['Quarter'] = company_df['Date'].dt.to_period('Q')
            # Use the last EPS and last Share Price of the quarter
            aggregated_df = company_df.sort_values('Date').groupby('Quarter').agg({
                'EPS': 'last',
                'Share Price': 'last',
                'Date': 'last'
            }).reset_index()
            # Convert 'Quarter' period to datetime for plotting (end of quarter)
            aggregated_df['Date'] = aggregated_df['Quarter'].dt.end_time

            growth_label = 'QoQ'

        # Sort the data by date
        aggregated_df = aggregated_df.sort_values('Date')

        # Display EPS and Share Price in the same chart with dual axes
        st.header(f"{selected_company} - EPS and Share Price")

        fig = go.Figure()

        # Bar chart for EPS with adjusted opacity
        fig.add_trace(go.Bar(
            x=aggregated_df['Date'],
            y=aggregated_df['EPS'],
            name='EPS',
            yaxis='y1',
            marker_color='lightskyblue',
            opacity=0.6,
            offsetgroup=1
        ))

        # Line chart for Share Price (plot after EPS to bring it to front)
        fig.add_trace(go.Scatter(
            x=aggregated_df['Date'],
            y=aggregated_df['Share Price'],
            name='Share Price',
            yaxis='y2',
            mode='lines+markers',
            marker_color='darkblue'
        ))

        # Set up the layout with two y-axes
        fig.update_layout(
            xaxis=dict(
                title='Date',
                tickformat='%Y-%m' if data_frequency == "Quarterly" else '%Y'
            ),
            yaxis=dict(
                title='EPS',
                titlefont=dict(
                    color='lightskyblue'
                ),
                tickfont=dict(
                    color='lightskyblue'
                ),
                anchor='x',
                overlaying='y2',
                side='left'
            ),
            yaxis2=dict(
                title='Share Price',
                titlefont=dict(
                    color='darkblue'
                ),
                tickfont=dict(
                    color='darkblue'
                ),
                anchor='x',
                side='right',
                position=1
            ),
            legend=dict(
                x=0.01,
                y=1.0
            ),
            title=f"{selected_company} - EPS and Share Price",
            margin=dict(l=50, r=50, t=50, b=50),
            height=500,
            hovermode='x unified',
            bargap=0.2,  # Adjust bar gap as needed
        )

        st.plotly_chart(fig, use_container_width=True)

        # Calculate growth rates
        aggregated_df = aggregated_df.sort_values('Date')  # Ensure data is sorted
        aggregated_df['EPS Growth Rate'] = aggregated_df['EPS'].pct_change() * 100
        aggregated_df['Price Growth Rate'] = aggregated_df['Share Price'].pct_change() * 100

        # Drop rows with NaN or infinite values in growth rates
        growth_df = aggregated_df.replace([float('inf'), float('-inf')], pd.NA)
        growth_df = growth_df.dropna(subset=['EPS Growth Rate', 'Price Growth Rate'])

        # Display the growth rates chart
        st.header(f"{selected_company} - {growth_label} Growth Rate of EPS and Share Price")

        fig_growth = go.Figure()

        # Line chart for EPS Growth Rate
        fig_growth.add_trace(go.Scatter(
            x=growth_df['Date'],
            y=growth_df['EPS Growth Rate'],
            name=f'EPS {growth_label} Growth Rate (%)',
            mode='lines+markers',
            marker_color='green'
        ))

        # Line chart for Share Price Growth Rate
        fig_growth.add_trace(go.Scatter(
            x=growth_df['Date'],
            y=growth_df['Price Growth Rate'],
            name=f'Price {growth_label} Growth Rate (%)',
            mode='lines+markers',
            marker_color='red'
        ))

        # Set up the layout with a single y-axis
        fig_growth.update_layout(
            xaxis=dict(
                title='Date',
                tickformat='%Y-%m' if data_frequency == "Quarterly" else '%Y'
            ),
            yaxis=dict(
                title='Growth Rate (%)',
            ),
            legend=dict(
                x=0.01,
                y=1.0
            ),
            title=f"{selected_company} - {growth_label} Growth Rate of EPS and Share Price",
            margin=dict(l=50, r=50, t=50, b=50),
            height=500,
            hovermode='x unified'
        )

        st.plotly_chart(fig_growth, use_container_width=True)

    else:
        st.warning(f"No data available for {selected_company}.")

else:
    st.warning("Please select a company.")