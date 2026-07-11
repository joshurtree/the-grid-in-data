"""
GB Electricity Prices - Gradio Web Interface

Multi-tab Gradio application for visualizing GB electricity market data.
Replaces the Taipy implementation with Gradio.
"""

import gradio as gr
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import os
from constants import RAW_DATA_DIR, TRANSFORMED_DATA_DIR

# ============================================================================
# Tab 1: Electricity Prices over Time
# ============================================================================

def create_prices_chart(start_date, end_date, exclude_peak):
    """Create electricity prices scatter chart colored by renewable percentage"""
    try:
        daily_data = pd.read_csv(
            os.path.join(TRANSFORMED_DATA_DIR, 'daily_data.csv'),
            parse_dates=['SettlementDate']
        )
        
        # Filter by date
        daily_data = daily_data[
            (daily_data['SettlementDate'] >= pd.to_datetime(start_date)) &
            (daily_data['SettlementDate'] <= pd.to_datetime(end_date))
        ]
        
        if len(daily_data) == 0:
            return gr.Plot(value=None), "No data available for selected date range"
        
        # Create Plotly scatter chart with color gradient
        fig = go.Figure(data=go.Scatter(
            mode='markers',
            x=daily_data['SettlementDate'],
            y=daily_data['Price'],
            marker=dict(
                size=8,
                color=daily_data.get('RENEWABLE_perc', daily_data['Total']),
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title='Renewable %'),
                opacity=0.7,
                line=dict(width=0)
            ),
            text=[f"Date: {d.strftime('%Y-%m-%d')}<br>Price: £{p:.2f}/MWh" 
                  for d, p in zip(daily_data['SettlementDate'], daily_data['Price'])],
            hovertemplate='%{text}<extra></extra>'
        ))
        
        fig.update_layout(
            title='Wholesale Price vs Date (colored by Renewable Generation %)',
            xaxis_title='Date',
            yaxis_title='Price (£/MWh)',
            hovermode='closest',
            template='plotly_dark',
            height=600
        )
        
        return fig, f"Showing {len(daily_data)} days of data"
    except Exception as e:
        return None, f"Error creating chart: {str(e)}"


def prices_tab():
    """Create the electricity prices tab"""
    with gr.Row():
        gr.Markdown("# GB Wholesale Electricity Prices")
    
    with gr.Row():
        with gr.Column(scale=1):
            start_date = gr.Date(
                value=date.today() - timedelta(days=365),
                label="Start Date"
            )
            end_date = gr.Date(
                value=date.today(),
                label="End Date"
            )
            exclude_peak = gr.Checkbox(
                value=False,
                label="Exclude Peak Hours (7-9am, 4-6pm)"
            )
        
        with gr.Column(scale=3):
            chart = gr.Plot(label="Electricity Prices")
            status = gr.Textbox(label="Status", interactive=False)
    
    # Update chart on input change
    def update_chart(start, end, peak):
        return create_prices_chart(start, end, peak)
    
    inputs = [start_date, end_date, exclude_peak]
    outputs = [chart, status]
    
    start_date.change(update_chart, inputs=inputs, outputs=outputs)
    end_date.change(update_chart, inputs=inputs, outputs=outputs)
    exclude_peak.change(update_chart, inputs=inputs, outputs=outputs)
    
    # Initial load
    start_date.change(update_chart, inputs=inputs, outputs=outputs)
    
    return gr.Tab(label="Electricity Prices", children=[
        gr.Column(children=[start_date, end_date, exclude_peak, chart, status])
    ])


# ============================================================================
# Tab 2: Electricity vs Gas Prices
# ============================================================================

def create_elec_vs_gas_chart(start_date, end_date, period_group):
    """Create electricity vs gas price comparison chart"""
    try:
        elec = pd.read_csv(
            os.path.join(RAW_DATA_DIR, 'market-prices.csv')
        ).rename(columns={'Price': 'Electricity Price', 'SettlementDate': 'Date'})
        elec['Date'] = pd.to_datetime(elec['Date'], format='mixed')
        elec = elec.groupby(elec['Date']).agg({'Electricity Price': 'mean'}).reset_index()
        
        gas = pd.read_csv(
            os.path.join(RAW_DATA_DIR, 'gas_prices.csv')
        ).rename(columns={'SAP actual day': 'Gas Price'})
        gas['Date'] = pd.to_datetime(gas['Date'], format='mixed')
        gas['Gas Price'] = gas['Gas Price'] * 10
        
        data = pd.merge(elec, gas, on='Date', how='inner')
        data = data[
            (data['Date'] >= pd.to_datetime(start_date)) &
            (data['Date'] <= pd.to_datetime(end_date))
        ]
        
        if len(data) == 0:
            return gr.Plot(value=None), "No data available"
        
        fig = go.Figure()
        
        # Add electricity price trace
        fig.add_trace(go.Scatter(
            x=data['Date'],
            y=data['Electricity Price'],
            mode='lines+markers',
            name='Electricity Price',
            line=dict(color='blue', width=2),
            yaxis='y1'
        ))
        
        # Add gas price trace with secondary y-axis
        fig.add_trace(go.Scatter(
            x=data['Date'],
            y=data['Gas Price'],
            mode='lines+markers',
            name='Gas Price',
            line=dict(color='orange', width=2),
            yaxis='y2'
        ))
        
        fig.update_layout(
            title='Electricity vs Gas Prices',
            xaxis_title='Date',
            yaxis=dict(
                title='Electricity Price (£/MWh)',
                side='left',
                titlefont=dict(color='blue'),
                tickfont=dict(color='blue')
            ),
            yaxis2=dict(
                title='Gas Price (£/MWh)',
                overlaying='y',
                side='right',
                titlefont=dict(color='orange'),
                tickfont=dict(color='orange')
            ),
            hovermode='x unified',
            template='plotly_dark',
            height=600
        )
        
        return fig, f"Showing {len(data)} days of data"
    except Exception as e:
        return None, f"Error: {str(e)}"


def elec_vs_gas_tab():
    """Create the electricity vs gas tab"""
    with gr.Row():
        gr.Markdown("# Electricity vs Gas Prices")
    
    with gr.Row():
        with gr.Column(scale=1):
            start_date = gr.Date(
                value=date.today() - timedelta(days=365),
                label="Start Date"
            )
            end_date = gr.Date(
                value=date.today(),
                label="End Date"
            )
            period = gr.Radio(
                choices=["Daily", "Weekly", "Monthly"],
                value="Daily",
                label="Period Grouping"
            )
        
        with gr.Column(scale=3):
            chart = gr.Plot(label="Price Comparison")
            status = gr.Textbox(label="Status", interactive=False)
    
    def update_chart(start, end, p):
        return create_elec_vs_gas_chart(start, end, p)
    
    inputs = [start_date, end_date, period]
    outputs = [chart, status]
    
    start_date.change(update_chart, inputs=inputs, outputs=outputs)
    end_date.change(update_chart, inputs=inputs, outputs=outputs)
    period.change(update_chart, inputs=inputs, outputs=outputs)
    
    return gr.Tab(label="Electricity vs Gas", children=[
        gr.Column(children=[start_date, end_date, period, chart, status])
    ])


# ============================================================================
# Tab 3: Energy Map
# ============================================================================

def create_energy_map():
    """Create the energy generation map"""
    try:
        import json
        
        generators = pd.read_csv(
            os.path.join(RAW_DATA_DIR, 'generators.csv')
        ).groupby(['Name']).first().reset_index()
        
        boundaries = json.load(open(os.path.join(RAW_DATA_DIR, 'tnuosgenzones.geojson')))
        
        fig = go.Figure()
        
        # Add boundary polygons
        for feature in boundaries.get('features', []):
            if feature['geometry']['type'] == 'Polygon':
                coords = feature['geometry']['coordinates'][0]
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]
                fig.add_trace(go.Scattergeo(
                    lon=lons,
                    lat=lats,
                    mode='lines',
                    line=dict(color='rgba(100, 100, 100, 0.5)', width=1),
                    hoverinfo='skip',
                    showlegend=False
                ))
        
        # Add generator markers
        fig.add_trace(go.Scattergeo(
            lon=generators['Longitude'],
            lat=generators['Latitude'],
            mode='markers',
            marker=dict(size=8, color='red', opacity=0.7),
            text=[f"{row['Name']} ({row['Fuel Type']})" for _, row in generators.iterrows()],
            hovertemplate='%{text}<extra></extra>',
            name='Generators'
        ))
        
        fig.update_layout(
            title='GB Generation Live Map',
            geo=dict(
                resolution=50,
                showland=True,
                showocean=True,
                landcolor='rgb(74, 170, 68)',
                oceancolor='rgb(119, 221, 221)',
                lataxis=dict(range=[49.5, 61.5]),
                lonaxis=dict(range=[-7, 2.5])
            ),
            height=700
        )
        
        return fig
    except Exception as e:
        return f"Error loading map: {str(e)}"


def energy_map_tab():
    """Create the energy map tab"""
    with gr.Row():
        gr.Markdown("# GB Energy Generation Map")
    
    chart = gr.Plot(label="Energy Generation Map")
    
    # Load and display the map
    map_fig = create_energy_map()
    if isinstance(map_fig, str):
        gr.Markdown(map_fig)
    else:
        with gr.Row():
            gr.Plot(value=map_fig)
    
    return gr.Tab(label="Energy Map", children=[chart])


# ============================================================================
# Main Application
# ============================================================================

def create_app():
    """Create the main Gradio application with tabs"""
    with gr.Blocks(title="GB Electricity Prices", theme=gr.themes.Soft(primary_hue="blue")) as app:
        gr.Markdown("# GB Electricity Market Analysis")
        gr.Markdown("Explore electricity prices, gas prices, and generation data across Great Britain")
        
        with gr.Tabs():
            with gr.TabItem("Electricity Prices"):
                create_prices_chart_interface()
            
            with gr.TabItem("Electricity vs Gas"):
                create_elec_vs_gas_interface()
            
            with gr.TabItem("Energy Map"):
                create_energy_map_interface()
    
    return app


def create_prices_chart_interface():
    """Create the interface for electricity prices chart"""
    with gr.Row():
        with gr.Column(scale=1):
            start_date = gr.Date(
                value=date.today() - timedelta(days=365),
                label="Start Date"
            )
            end_date = gr.Date(
                value=date.today(),
                label="End Date"
            )
            exclude_peak = gr.Checkbox(value=False, label="Exclude Peak Hours")
        
        with gr.Column(scale=3):
            chart = gr.Plot(label="Electricity Prices")
            status = gr.Textbox(label="Status", interactive=False)
    
    def update(start, end, peak):
        return create_prices_chart(start, end, peak)
    
    start_date.change(update, [start_date, end_date, exclude_peak], [chart, status])
    end_date.change(update, [start_date, end_date, exclude_peak], [chart, status])
    exclude_peak.change(update, [start_date, end_date, exclude_peak], [chart, status])


def create_elec_vs_gas_interface():
    """Create the interface for electricity vs gas chart"""
    with gr.Row():
        with gr.Column(scale=1):
            start_date = gr.Date(
                value=date.today() - timedelta(days=365),
                label="Start Date"
            )
            end_date = gr.Date(
                value=date.today(),
                label="End Date"
            )
            period = gr.Radio(
                choices=["Daily", "Weekly", "Monthly"],
                value="Daily",
                label="Period"
            )
        
        with gr.Column(scale=3):
            chart = gr.Plot(label="Price Comparison")
            status = gr.Textbox(label="Status", interactive=False)
    
    def update(start, end, p):
        return create_elec_vs_gas_chart(start, end, p)
    
    start_date.change(update, [start_date, end_date, period], [chart, status])
    end_date.change(update, [start_date, end_date, period], [chart, status])
    period.change(update, [start_date, end_date, period], [chart, status])


def create_energy_map_interface():
    """Create the interface for the energy map"""
    try:
        map_fig = create_energy_map()
        gr.Plot(value=map_fig, label="GB Energy Generation Map")
    except Exception as e:
        gr.Markdown(f"Error loading map: {str(e)}")


if __name__ == "__main__":
    app = create_app()
    app.launch(server_name="0.0.0.0", server_port=7860, share=False)
