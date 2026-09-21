import pandas as pd
import plotly.graph_objects as go
from figures.chartset import Chart
from constants import DATE_FIELD, FREQ_GROUPS
from  datasources.system import bm_payments_source


def balancing_costs(frequency='Monthly') -> Chart:
    data = bm_payments_source.load_data()
    data[DATE_FIELD] = pd.to_datetime(data[DATE_FIELD], format='%d/%m/%Y', errors='coerce')
    data = data.set_index(DATE_FIELD).resample(FREQ_GROUPS[frequency]).mean().reset_index()

    # Create a stacked area chart for balancing costs with fields: 
    # Energy Imbalance,  Frequency Control,  Positive Reserve,  Constraints,  Negative Reserve, Other
    fig = go.Figure()
    categories = ['Energy Imbalance', 'Frequency Control', 'Positive Reserve', 'Constraints', 'Negative Reserve', 'Other']
    for category in reversed(categories):  # Reverse to have the first category on top
        data[category] = pd.to_numeric(data[category], errors='coerce')/1000000  # Convert to millions
        fig.add_trace(go.Scatter(
            x=data[DATE_FIELD],
            y=data[category],
            name=category,
            hovertemplate=f'{category}: £%{{y:,.2f}} mil<extra></extra>',
            stackgroup='one'
        ))
    fig.update_layout(barmode='stack', 
                      title=f'Balancing Costs by Category ({frequency})',
                      xaxis_title='Date',
                      yaxis_title='Cost (£ million)',
                      hovermode='x unified',
                      height=600)
    return Chart(
        bm_payments_source,
        chart=fig,
        title=f'Balancing Costs by Category ({frequency})',
        description=f'This chart shows the balancing costs incurred by the electricity system operator, broken down by category. The data is aggregated {frequency.lower()}.'
    )