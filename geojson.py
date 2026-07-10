import json
import plotly.graph_objects as go

def add_boundaries_to_chart(chart_figure, boundaries_file, label=None):
    with open(boundaries_file) as zones_file:
        boundaries = json.load(zones_file)

        # Add boundary polygons from GeoJSON
        for feature in boundaries.get('features', []):
            if feature['geometry']['type'] == 'Polygon':
                coords = feature['geometry']['coordinates'][0]
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]
                chart_figure.add_trace(go.Scattergeo(
                    lon=lons,
                    lat=lats,
                    mode='lines',
                    line=dict(color='rgba(100, 100, 100, 0.5)', width=1),
                    hoverinfo='skip',
                    showlegend=False,
                    name=feature.get('properties', {}).get('name', label)
                ))
            elif feature['geometry']['type'] == 'MultiPolygon':
                for polygon in feature['geometry']['coordinates']:
                    coords = polygon[0]
                    lons = [c[0] for c in coords]
                    lats = [c[1] for c in coords]
                    chart_figure.add_trace(go.Scattergeo(
                        lon=lons,
                        lat=lats,
                        mode='lines',
                        line=dict(color='rgba(100, 100, 100, 0.5)', width=1),
                        hoverinfo='skip',
                        showlegend=False,
                        name=feature.get('properties', {}).get('name', label)
                    ))
            elif feature['geometry']['type'] == 'LineString':
                coords = feature['geometry']['coordinates']
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]
                chart_figure.add_trace(go.Scattergeo(
                    lon=lons,
                    lat=lats,
                    mode='lines',
                    line=dict(color='rgba(100, 100, 100, 0.5)', width=1),
                    hoverinfo='skip',
                    showlegend=False,
                    name=feature.get('properties', {}).get('name', label)
                ))
                
                # If a label is provided, add it to the chart at the end of the line
                if label:
                    chart_figure.add_trace(go.Scattergeo(
                        lon=[lons[-1] + 0.15],  # Slightly offset the label for better visibility
                        lat=[lats[-1] + 0.02],  # Slightly offset the label for better visibility
                        mode='text',
                        text=[feature['properties'][label]] if 'properties' in feature and label in feature['properties'] else [""],
                        showlegend=False,
                        textposition="middle right",
                        hoverinfo='skip'
                    ))
